"""Hybrid facilitator for x402 payment processing.

Combines local verification with remote settlement for the best of both worlds:
- Fast local verification (no external API calls)
- Delegated settlement (no hot wallet management)

This is ideal for production deployments where you want:
- Minimum latency for verification
- Professional settlement infrastructure
- No hot wallet private key management
"""

import logging
from typing import Any, Dict, Optional

from .local import SolanaFacilitator
from .payai import PayAIFacilitator
from .corbits import CorbitsFacilitator

logger = logging.getLogger(__name__)


class HybridFacilitator:
    """Hybrid facilitator combining local verification with remote settlement.
    
    Architecture:
    - Verify payments locally (fast, no external calls)
    - Settle via remote facilitator (PayAI or Corbits)
    
    Benefits:
    - Lowest latency for verification (local)
    - No hot wallet management (remote settlement)
    - Fallback capability
    - Maximum privacy for verification
    
    Configuration:
        config = {
            'verify_mode': 'local',  # 'local' only for now
            'settle_mode': 'payai',  # 'payai' or 'corbits'
            'local': {
                # Local facilitator config (for verification)
                'private_key_env': 'X402_SIGNER_KEY',  # Not needed for verify-only
                'rpc_url': 'https://api.mainnet-beta.solana.com',
                'verify_balance': False,
            },
            'payai': {
                # PayAI facilitator config (for settlement)
                'facilitator_url': 'https://facilitator.payai.network',
                'api_key_env': 'PAYAI_API_KEY',
            },
            # OR
            'corbits': {
                # Corbits facilitator config (for settlement)
                'facilitator_url': 'https://api.corbits.dev',
                'api_key_env': 'CORBITS_API_KEY',
            },
        }
    
    Example:
        >>> facilitator = HybridFacilitator({
        ...     'verify_mode': 'local',
        ...     'settle_mode': 'payai',
        ...     'local': {'rpc_url': 'https://api.mainnet-beta.solana.com'},
        ...     'payai': {'facilitator_url': 'https://facilitator.payai.network'},
        ... })
        >>> 
        >>> # Fast local verification
        >>> result = facilitator.verify(payment, requirements)
        >>> 
        >>> # Remote settlement via PayAI
        >>> if result['isValid']:
        ...     settlement = facilitator.settle(payment, requirements)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize hybrid facilitator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Determine modes
        self.verify_mode = self.config.get('verify_mode', 'local')
        self.settle_mode = self.config.get('settle_mode', 'payai')
        
        logger.info(f"Hybrid facilitator: verify={self.verify_mode}, settle={self.settle_mode}")
        
        # Initialize verifier (currently only local supported)
        if self.verify_mode == 'local':
            local_config = self.config.get('local', {})
            self.verifier = SolanaFacilitator(config=local_config)
        else:
            raise ValueError(f"Unsupported verify_mode: {self.verify_mode}")
        
        # Initialize settler (PayAI or Corbits)
        if self.settle_mode == 'payai':
            payai_config = self.config.get('payai', {})
            self.settler = PayAIFacilitator(config=payai_config)
        elif self.settle_mode == 'corbits':
            corbits_config = self.config.get('corbits', {})
            self.settler = CorbitsFacilitator(config=corbits_config)
        else:
            raise ValueError(
                f"Unsupported settle_mode: {self.settle_mode}. "
                f"Must be 'payai' or 'corbits'"
            )
        
        logger.info("✅ Hybrid facilitator initialized successfully")
    
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment locally (fast, no external calls).
        
        Uses local Solana facilitator for verification without external API calls.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements from 402 response
            
        Returns:
            {'isValid': True/False, 'invalidReason': str, 'payer': str}
        """
        logger.debug("Hybrid: verifying payment locally")
        result = self.verifier.verify(payment, requirements)
        
        if result.get('isValid'):
            logger.info(f"✅ Hybrid verification passed (local): {result.get('payer')}")
        else:
            logger.warning(f"❌ Hybrid verification failed (local): {result.get('invalidReason')}")
        
        return result
    
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment via remote facilitator (PayAI or Corbits).
        
        Delegates settlement to the configured remote facilitator.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements from 402 response
            
        Returns:
            {'success': bool, 'transaction': str, 'error': str}
        """
        logger.info(f"Hybrid: settling payment via {self.settle_mode}")
        result = self.settler.settle(payment, requirements)
        
        if result.get('success'):
            logger.info(f"✅ Hybrid settlement successful ({self.settle_mode}): {result.get('transaction')}")
        else:
            logger.error(f"❌ Hybrid settlement failed ({self.settle_mode}): {result.get('error')}")
        
        return result
    
    def get_durable_nonce_info(self) -> Optional[Dict[str, Any]]:
        """Get durable nonce information from remote facilitator.
        
        Returns nonce info from the settler (PayAI or Corbits).
        
        Returns:
            Dict with nonce account and current nonce value, or None
        """
        # Try to get from settler first (remote facilitator)
        if hasattr(self.settler, 'get_durable_nonce_info'):
            nonce_info = self.settler.get_durable_nonce_info()
            if nonce_info:
                logger.info(f"Hybrid: using durable nonce from {self.settle_mode}")
                return nonce_info
        
        # Fallback to local verifier
        if hasattr(self.verifier, 'get_durable_nonce_info'):
            nonce_info = self.verifier.get_durable_nonce_info()
            if nonce_info:
                logger.info("Hybrid: using durable nonce from local")
                return nonce_info
        
        return None

