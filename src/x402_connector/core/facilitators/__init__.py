"""Facilitators package for x402 payment processing.

This package provides multiple facilitator implementations:
- Local: Self-hosted verification and settlement on Solana
- PayAI: Managed service at https://payai.network
- Corbits: Managed service at https://corbits.dev
- Hybrid: Local verification + remote settlement

Usage:
    >>> from x402_connector.core.facilitators import get_facilitator
    >>> from x402_connector.core.config import X402Config
    >>> 
    >>> # Local mode (default)
    >>> config = X402Config(pay_to_address='...', facilitator_mode='local')
    >>> facilitator = get_facilitator(config)
    >>> 
    >>> # PayAI mode
    >>> config = X402Config(
    ...     pay_to_address='...',
    ...     facilitator_mode='payai',
    ...     payai={'facilitator_url': 'https://facilitator.payai.network'}
    ... )
    >>> facilitator = get_facilitator(config)
    >>> 
    >>> # Hybrid mode
    >>> config = X402Config(
    ...     pay_to_address='...',
    ...     facilitator_mode='hybrid',
    ...     payai={'facilitator_url': 'https://facilitator.payai.network'}
    ... )
    >>> facilitator = get_facilitator(config)
"""

import logging
from typing import Any

from .local import SolanaFacilitator
from .payai import PayAIFacilitator
from .corbits import CorbitsFacilitator
from .hybrid import HybridFacilitator

logger = logging.getLogger(__name__)

__all__ = [
    'SolanaFacilitator',
    'PayAIFacilitator',
    'CorbitsFacilitator',
    'HybridFacilitator',
    'get_facilitator',
]


def get_facilitator(config):
    """Factory function to create appropriate facilitator based on configuration.
    
    Supports multiple facilitator modes:
    - 'local': Self-hosted verification and settlement (default)
    - 'payai': Use PayAI facilitator service
    - 'corbits': Use Corbits facilitator service
    - 'hybrid': Local verification + remote settlement
    
    Args:
        config: X402Config instance with facilitator configuration
        
    Returns:
        Appropriate facilitator instance based on mode
        
    Raises:
        ValueError: If facilitator_mode is not supported
        
    Examples:
        >>> # Local mode (default - self-hosted)
        >>> config = X402Config(
        ...     pay_to_address='YOUR_ADDRESS',
        ...     facilitator_mode='local'
        ... )
        >>> facilitator = get_facilitator(config)
        >>> # Returns: SolanaFacilitator
        
        >>> # PayAI mode (managed service)
        >>> config = X402Config(
        ...     pay_to_address='YOUR_ADDRESS',
        ...     facilitator_mode='payai',
        ...     payai={
        ...         'facilitator_url': 'https://facilitator.payai.network',
        ...         'api_key_env': 'PAYAI_API_KEY',
        ...     }
        ... )
        >>> facilitator = get_facilitator(config)
        >>> # Returns: PayAIFacilitator
        
        >>> # Corbits mode (managed service)
        >>> config = X402Config(
        ...     pay_to_address='YOUR_ADDRESS',
        ...     facilitator_mode='corbits',
        ...     corbits={
        ...         'facilitator_url': 'https://api.corbits.dev',
        ...         'api_key_env': 'CORBITS_API_KEY',
        ...     }
        ... )
        >>> facilitator = get_facilitator(config)
        >>> # Returns: CorbitsFacilitator
        
        >>> # Hybrid mode (local verify + remote settle)
        >>> config = X402Config(
        ...     pay_to_address='YOUR_ADDRESS',
        ...     facilitator_mode='hybrid',
        ...     local={'rpc_url': 'https://api.mainnet-beta.solana.com'},
        ...     payai={'facilitator_url': 'https://facilitator.payai.network'},
        ... )
        >>> facilitator = get_facilitator(config)
        >>> # Returns: HybridFacilitator (verify=local, settle=payai)
    """
    mode = getattr(config, 'facilitator_mode', 'local').lower()
    
    logger.info(f"Creating facilitator: mode={mode}")
    
    if mode == 'local':
        # Self-hosted mode (default)
        local_cfg = getattr(config, 'local', None)
        local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
        logger.info("✅ Using LOCAL facilitator (self-hosted)")
        return SolanaFacilitator(config=local_dict)
    
    elif mode == 'payai':
        # PayAI managed service
        payai_cfg = getattr(config, 'payai', None)
        payai_dict = payai_cfg.__dict__ if hasattr(payai_cfg, '__dict__') else (payai_cfg or {})
        logger.info("✅ Using PAYAI facilitator (https://payai.network)")
        return PayAIFacilitator(config=payai_dict)
    
    elif mode == 'corbits':
        # Corbits managed service
        corbits_cfg = getattr(config, 'corbits', None)
        corbits_dict = corbits_cfg.__dict__ if hasattr(corbits_cfg, '__dict__') else (corbits_cfg or {})
        logger.info("✅ Using CORBITS facilitator (https://corbits.dev)")
        return CorbitsFacilitator(config=corbits_dict)
    
    elif mode == 'hybrid':
        # Hybrid mode: local verification + remote settlement
        hybrid_config = {
            'verify_mode': 'local',
            'settle_mode': getattr(config, 'hybrid_settle_mode', 'payai'),  # Default to PayAI
            'local': None,
            'payai': None,
            'corbits': None,
        }
        
        # Get local config
        local_cfg = getattr(config, 'local', None)
        if local_cfg:
            hybrid_config['local'] = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else local_cfg
        
        # Get PayAI config
        payai_cfg = getattr(config, 'payai', None)
        if payai_cfg:
            hybrid_config['payai'] = payai_cfg.__dict__ if hasattr(payai_cfg, '__dict__') else payai_cfg
        
        # Get Corbits config
        corbits_cfg = getattr(config, 'corbits', None)
        if corbits_cfg:
            hybrid_config['corbits'] = corbits_cfg.__dict__ if hasattr(corbits_cfg, '__dict__') else corbits_cfg
        
        # Determine settlement mode based on what's configured
        if hybrid_config['corbits'] and not hybrid_config['payai']:
            hybrid_config['settle_mode'] = 'corbits'
        elif not hybrid_config['payai'] and not hybrid_config['corbits']:
            logger.warning("⚠️  Hybrid mode requires PayAI or Corbits config for settlement")
        
        logger.info(f"✅ Using HYBRID facilitator (verify=local, settle={hybrid_config['settle_mode']})")
        return HybridFacilitator(config=hybrid_config)
    
    else:
        # Unknown mode
        raise ValueError(
            f"Unsupported facilitator_mode: '{mode}'. "
            f"Must be one of: 'local', 'payai', 'corbits', 'hybrid'"
        )

