"""Facilitator factory for x402-connector.

This module provides the facilitator factory that creates the appropriate
payment facilitator based on configuration (local, PayAI, Corbits, or hybrid).
"""

from .facilitators_solana import SolanaFacilitator
from .facilitators_payai import PayAIFacilitator

__all__ = [
    'SolanaFacilitator',
    'PayAIFacilitator',
    'get_facilitator',
]


def get_facilitator(config):
    """Factory function to create appropriate facilitator based on configuration.
    
    Supports multiple facilitator modes:
    - 'local': Self-hosted verification and settlement (default)
    - 'payai': Use PayAI facilitator service
    - 'corbits': Use Corbits facilitator service (future)
    - 'hybrid': Local verification, remote settlement (future)
    
    Args:
        config: X402Config instance
        
    Returns:
        Appropriate facilitator instance
        
    Examples:
        >>> # Local mode (default)
        >>> config = X402Config(pay_to_address='...', facilitator_mode='local')
        >>> facilitator = get_facilitator(config)  # Returns SolanaFacilitator
        >>> 
        >>> # PayAI mode
        >>> config = X402Config(
        ...     pay_to_address='...',
        ...     facilitator_mode='payai',
        ...     payai={'facilitator_url': 'https://facilitator.payai.network'}
        ... )
        >>> facilitator = get_facilitator(config)  # Returns PayAIFacilitator
    """
    mode = getattr(config, 'facilitator_mode', 'local').lower()
    
    if mode == 'payai':
        # Use PayAI facilitator service
        payai_cfg = getattr(config, 'payai', None)
        payai_dict = payai_cfg.__dict__ if hasattr(payai_cfg, '__dict__') else (payai_cfg or {})
        return PayAIFacilitator(config=payai_dict)
    
    elif mode == 'corbits':
        # Use Corbits facilitator service (future)
        # For now, fall back to local mode
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Corbits facilitator mode not yet implemented, using local mode")
        local_cfg = getattr(config, 'local', None)
        local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
        return SolanaFacilitator(config=local_dict)
    
    elif mode == 'hybrid':
        # Hybrid mode: local verification, remote settlement (future)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Hybrid facilitator mode not yet implemented, using local mode")
        local_cfg = getattr(config, 'local', None)
        local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
        return SolanaFacilitator(config=local_dict)
    
    else:
        # Default: local mode (self-hosted)
        local_cfg = getattr(config, 'local', None)
        local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
        return SolanaFacilitator(config=local_dict)
