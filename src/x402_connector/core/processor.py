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
        self.facilitator = facilitator  # Will be populated in full implementation
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
        
        # TODO: Implement full payment verification with facilitator
        # For skeleton, just return basic structure
        logger.info("Payment verification would happen here")
        
        return ProcessingResult(
            action='deny',
            requirements=requirements,
            error='Payment verification not yet implemented in skeleton'
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
        
        # TODO: Implement full settlement with facilitator
        # For skeleton, return basic structure
        logger.info("Payment settlement would happen here")
        
        result = SettlementResult(
            success=False,
            error='Payment settlement not yet implemented in skeleton'
        )
        
        # Cache result
        if self.config.replay_cache_enabled and context.payment_header:
            self._cache_settlement(context.payment_header, result)
        
        return result
    
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
        # TODO: Use x402.common.process_price_to_atomic_amount
        # For skeleton, return placeholder
        return [{
            'scheme': 'exact',
            'network': self.config.network,
            'price': self.config.price,
            'payTo': self.config.pay_to_address,
            'resource': context.absolute_url,
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

