"""Core payment processor - framework-agnostic payment verification and settlement."""

import base64
import json
import logging
from typing import List, Optional, Dict, Any

from .config import X402Config
from .context import RequestContext, ProcessingResult, SettlementResult

logger = logging.getLogger(__name__)


class X402PaymentProcessor:
    """Framework-agnostic x402 payment processing engine.
    
    This class handles all payment verification and settlement logic without
    depending on any web framework. Framework adapters use this processor
    to implement middleware or decorators.
    
    The processor:
    1. Checks if request path requires payment
    2. Verifies payment signatures and requirements
    3. Settles payments on blockchain after successful responses
    4. Handles caching and replay protection
    
    Example:
        >>> config = X402Config(
        ...     network='base',
        ...     price='$0.01',
        ...     pay_to_address='0x1234...'
        ... )
        >>> processor = X402PaymentProcessor(config)
        >>> 
        >>> context = RequestContext(
        ...     path='/api/premium',
        ...     method='GET',
        ...     headers={},
        ...     absolute_url='https://example.com/api/premium'
        ... )
        >>> 
        >>> result = processor.process_request(context)
        >>> if result.action == 'deny':
        ...     # Return 402 response
        ...     pass
    """
    
    def __init__(
        self, 
        config: X402Config, 
        facilitator: Optional[Any] = None
    ):
        """Initialize payment processor.
        
        Args:
            config: X402 configuration
            facilitator: Optional custom facilitator (auto-created if None)
        """
        self.config = config
        
        # Create facilitator if not provided
        if facilitator is None:
            from .facilitators import get_facilitator
            self.facilitator = get_facilitator(config)
        else:
            self.facilitator = facilitator
        
        self._payment_cache: Dict[str, SettlementResult] = {}
    
    def process_request(self, context: RequestContext) -> ProcessingResult:
        """Process incoming request for payment verification.
        
        This is the main entry point for payment verification. It:
        1. Checks if the path requires payment
        2. Validates the payment header if present
        3. Verifies payment with facilitator
        4. Returns allow/deny decision
        
        Args:
            context: Framework-agnostic request context
            
        Returns:
            ProcessingResult indicating whether to allow or deny the request
            
        Example:
            >>> result = processor.process_request(context)
            >>> if result.action == 'allow' and result.payment_verified:
            ...     print(f"Payment verified from {result.payer_address}")
            >>> elif result.action == 'deny':
            ...     print(f"Payment required: {result.error}")
        """
        # Check if path is protected
        if not self._is_protected_path(context.path):
            return ProcessingResult(action='allow')
        
        # Build payment requirements for this resource
        requirements = self._build_payment_requirements(context)
        
        # Check for payment header
        if not context.payment_header:
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='No X-PAYMENT header provided'
            )
        
        # Parse payment payload
        try:
            from x402.encoding import safe_base64_decode
            payment_dict = json.loads(safe_base64_decode(context.payment_header))
        except Exception as e:
            logger.warning(f"Failed to parse payment header: {e}")
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='Invalid payment header format'
            )
        
        # Find matching requirements
        try:
            from x402.types import PaymentPayload
            from x402.common import find_matching_payment_requirements
            
            payment = PaymentPayload(**payment_dict)
            
            # Convert requirements to PaymentRequirements objects
            from x402.types import PaymentRequirements
            requirements_objects = [
                PaymentRequirements(**req) if isinstance(req, dict) else req
                for req in requirements
            ]
            
            selected_requirements = find_matching_payment_requirements(
                requirements_objects,
                payment
            )
        except ImportError:
            # Fallback if x402 package not available - use simple matching
            selected_requirements = requirements[0] if requirements else None
            if payment_dict.get('network') != (selected_requirements or {}).get('network'):
                selected_requirements = None
        except Exception as e:
            logger.warning(f"Failed to match requirements: {e}")
            selected_requirements = None
        
        if not selected_requirements:
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='No matching payment requirements found'
            )
        
        # Convert to dict if it's a pydantic model
        req_dict = selected_requirements
        if hasattr(selected_requirements, 'model_dump'):
            req_dict = selected_requirements.model_dump(by_alias=True)
        elif hasattr(selected_requirements, 'dict'):
            req_dict = selected_requirements.dict(by_alias=True)
        
        # Verify payment with facilitator
        verification = self.facilitator.verify(payment_dict, req_dict)
        
        is_valid = verification.get('isValid') or verification.get('is_valid')
        if not is_valid:
            invalid_reason = (
                verification.get('invalidReason') or
                verification.get('invalid_reason') or
                'Unknown error'
            )
            logger.info(f"Payment verification failed: {invalid_reason}")
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error=f'Invalid payment: {invalid_reason}'
            )
        
        logger.info(f"Payment verified from {verification.get('payer')}")
        return ProcessingResult(
            action='allow',
            payment_verified=True,
            payer_address=verification.get('payer')
        )
    
    def settle_payment(self, context: RequestContext) -> SettlementResult:
        """Settle verified payment after successful response.
        
        After a protected endpoint returns a 2xx response, this method:
        1. Checks cache for idempotent settlement
        2. Calls facilitator to broadcast transaction
        3. Encodes settlement result for response header
        4. Caches result for replay protection
        
        Args:
            context: Request context with payment header
            
        Returns:
            SettlementResult with transaction details
            
        Example:
            >>> settlement = processor.settle_payment(context)
            >>> if settlement.success:
            ...     print(f"Transaction: {settlement.transaction_hash}")
            ...     # Add settlement.encoded_response to response header
            >>> else:
            ...     print(f"Settlement failed: {settlement.error}")
        """
        # Check cache for idempotency
        if self.config.replay_cache_enabled:
            cached = self._get_cached_settlement(context.payment_header)
            if cached:
                logger.info("Using cached settlement result")
                return cached
        
        try:
            # Parse payment
            from x402.encoding import safe_base64_decode
            payment_dict = json.loads(safe_base64_decode(context.payment_header))
            
            # Build requirements
            requirements = self._build_payment_requirements(context)
            
            # Find matching requirements
            try:
                from x402.types import PaymentPayload
                from x402.common import find_matching_payment_requirements
                from x402.types import PaymentRequirements
                
                payment = PaymentPayload(**payment_dict)
                requirements_objects = [
                    PaymentRequirements(**req) if isinstance(req, dict) else req
                    for req in requirements
                ]
                selected = find_matching_payment_requirements(requirements_objects, payment)
            except ImportError:
                selected = requirements[0] if requirements else None
            
            if not selected:
                return SettlementResult(
                    success=False,
                    error='No matching requirements for settlement'
                )
            
            # Convert to dict
            req_dict = selected
            if hasattr(selected, 'model_dump'):
                req_dict = selected.model_dump(by_alias=True)
            elif hasattr(selected, 'dict'):
                req_dict = selected.dict(by_alias=True)
            
            # Settle via facilitator
            settlement = self.facilitator.settle(payment_dict, req_dict)
            
            # Check success
            success = settlement.get('success', False)
            if not success:
                error = settlement.get('error', 'Settlement failed')
                logger.error(f"Settlement failed: {error}")
                result = SettlementResult(success=False, error=error)
            else:
                # Encode response
                encoded = base64.b64encode(
                    json.dumps(settlement).encode('utf-8')
                ).decode('ascii')
                
                result = SettlementResult(
                    success=True,
                    transaction_hash=settlement.get('transaction'),
                    encoded_response=encoded,
                    receipt=settlement.get('receipt')
                )
                
                logger.info(f"Settlement successful: {result.transaction_hash}")
            
            # Cache result
            if self.config.replay_cache_enabled and context.payment_header:
                self._cache_settlement(context.payment_header, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Settlement error: {e}", exc_info=True)
            return SettlementResult(success=False, error=str(e))
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path matches protected patterns.
        
        Supports glob patterns like '/api/premium/*'.
        
        Args:
            path: Request path
            
        Returns:
            True if path requires payment
        """
        # Simple implementation - full version would use x402.path.path_is_match
        protected = self.config.protected_paths
        
        # Special case: '*' matches everything
        if '*' in protected:
            return True
        
        # Check each pattern
        for pattern in protected:
            if pattern.endswith('/*'):
                prefix = pattern[:-2]
                if path.startswith(prefix):
                    return True
            elif pattern == path:
                return True
        
        return False
    
    def _build_payment_requirements(
        self, 
        context: RequestContext
    ) -> List[Any]:
        """Build payment requirements for this request.
        
        Converts price to atomic units, gets EIP-712 domain, and constructs
        PaymentRequirements object with all necessary information.
        
        Args:
            context: Request context
            
        Returns:
            List of PaymentRequirements (usually just one)
        """
        try:
            from x402.common import process_price_to_atomic_amount
            from x402.types import PaymentRequirements
            
            # Convert price to atomic units and get EIP-712 domain
            max_amount, asset, eip712_domain = process_price_to_atomic_amount(
                self.config.price,
                self.config.network
            )
            
            return [
                PaymentRequirements(
                    scheme='exact',
                    network=self.config.network,
                    asset=asset,
                    max_amount_required=max_amount,
                    resource=context.absolute_url,
                    description=self.config.description,
                    mime_type=self.config.mime_type,
                    pay_to=self.config.pay_to_address,
                    max_timeout_seconds=self.config.max_timeout_seconds,
                    output_schema={
                        'input': {
                            'type': 'http',
                            'method': context.method.upper(),
                            'discoverable': self.config.discoverable,
                        },
                        'output': {'type': self.config.mime_type},
                    },
                    extra=eip712_domain,
                )
            ]
        except ImportError:
            # Fallback if x402 package not available
            logger.warning("x402 package not available, using fallback requirements")
            return [{
                'scheme': 'exact',
                'network': self.config.network,
                'asset': '0x0000000000000000000000000000000000000000',
                'maxAmountRequired': '10000',
                'resource': context.absolute_url,
                'description': self.config.description,
                'mimeType': self.config.mime_type,
                'payTo': self.config.pay_to_address,
                'maxTimeoutSeconds': self.config.max_timeout_seconds,
            }]
    
    def _get_cached_settlement(
        self, 
        payment_header: Optional[str]
    ) -> Optional[SettlementResult]:
        """Get cached settlement result for idempotency.
        
        Args:
            payment_header: Payment header to look up
            
        Returns:
            Cached SettlementResult if found, None otherwise
        """
        if not payment_header:
            return None
        return self._payment_cache.get(payment_header)
    
    def _cache_settlement(
        self, 
        payment_header: str, 
        result: SettlementResult
    ):
        """Cache settlement result for idempotency.
        
        Args:
            payment_header: Payment header to cache under
            result: SettlementResult to cache
        """
        self._payment_cache[payment_header] = result

