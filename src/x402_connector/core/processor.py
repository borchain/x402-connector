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
        
        # Parse payment payload (Solana-specific, no EVM package)
        payment_dict = self._parse_payment_header(context.payment_header)
        if not payment_dict:
            logger.warning("Failed to parse payment header")
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='Invalid payment header format'
            )
        
        # Use first requirement (Solana only generates one)
        req_dict = requirements[0] if requirements else {}
        
        # Simple network check
        if payment_dict.get('network') != req_dict.get('network'):
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='Network mismatch'
            )
        
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
            # Parse payment (Solana-specific, no EVM package needed)
            payment_dict = self._parse_payment_header(context.payment_header)
            
            # Build requirements
            requirements = self._build_payment_requirements(context)
            req_dict = requirements[0] if requirements else {}
            
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
        """Build payment requirements for Solana.
        
        Constructs payment requirements for Solana blockchain with USDC.
        
        Args:
            context: Request context
            
        Returns:
            List of payment requirements (usually just one)
        """
        # Convert price to atomic units for Solana USDC (6 decimals)
        max_amount = self._price_to_atomic_units(self.config.price)
        
        # Solana USDC mint addresses by network
        usdc_mints = {
            'solana-mainnet': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'solana-devnet': 'Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr',
            'solana-testnet': '8zGuJQqwhZafTah7Uc7Z4tXRnguqkn5KLFAP8oV6PHe2',
        }
        
        asset = usdc_mints.get(self.config.network, usdc_mints['solana-devnet'])
        
        # Get durable nonce info from facilitator (if available)
        nonce_info = None
        try:
            if hasattr(self.facilitator, 'get_durable_nonce_info'):
                nonce_info = self.facilitator.get_durable_nonce_info()
        except Exception as e:
            logger.debug(f"No durable nonce available: {e}")
        
        # Build Solana-specific payment requirements
        requirements = {
            'scheme': 'exact',
            'network': self.config.network,
            'asset': asset,
            'assetSymbol': 'USDC',
            'maxAmountRequired': str(max_amount),
            'resource': context.absolute_url,
            'description': self.config.description,
            'mimeType': self.config.mime_type,
            'payTo': self.config.pay_to_address,
            'timeout': self.config.max_timeout_seconds,
        }
        
        # Add durable nonce info if available
        if nonce_info:
            requirements['durableNonce'] = nonce_info
            logger.info(f"✅ Including durable nonce: {nonce_info.get('account', 'unknown')[:16]}...")
        
        return [requirements]
    
    def _price_to_atomic_units(self, price: str) -> int:
        """Convert price string to atomic units for Solana USDC.
        
        Solana USDC has 6 decimals, so 1 USDC = 1,000,000 atomic units.
        
        Args:
            price: Price string (e.g., '$0.01', '10000', '0.01 USDC')
            
        Returns:
            Amount in atomic units
            
        Examples:
            >>> _price_to_atomic_units('$0.01')
            10000
            >>> _price_to_atomic_units('1 USDC')
            1000000
            >>> _price_to_atomic_units('10000')
            10000
        """
        price = price.strip()
        
        # Already in atomic units (just a number)
        if price.isdigit():
            return int(price)
        
        # USD format: $0.01
        if price.startswith('$'):
            usd_amount = float(price[1:])
            # Assume 1 USDC = 1 USD
            return int(usd_amount * 1_000_000)
        
        # USDC format: "0.01 USDC" or "1 USDC"
        if 'USDC' in price.upper():
            usdc_amount = float(price.split()[0])
            return int(usdc_amount * 1_000_000)
        
        # Try to parse as float and assume it's USDC
        try:
            usdc_amount = float(price)
            return int(usdc_amount * 1_000_000)
        except ValueError:
            raise ValueError(
                f"Invalid price format: {price}. "
                f"Expected: '$0.01', '10000', '0.01 USDC', or '1.0'"
            )
    
    def _parse_payment_header(self, payment_header: str) -> Optional[Dict[str, Any]]:
        """Parse payment header (handles JSON and base64).
        
        Args:
            payment_header: X-PAYMENT header value
            
        Returns:
            Parsed payment dict or None if invalid
        """
        if not payment_header:
            return None
        
        try:
            # Try direct JSON parsing first
            return json.loads(payment_header)
        except json.JSONDecodeError:
            pass
        
        try:
            # Try base64 decoding then JSON
            decoded = base64.b64decode(payment_header).decode('utf-8')
            return json.loads(decoded)
        except Exception:
            return None
    
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

