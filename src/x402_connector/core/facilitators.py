"""Solana facilitator for x402-connector.

This module provides the Solana payment facilitator that handles
payment verification and settlement on the Solana blockchain.
"""

from .facilitators_solana import SolanaFacilitator

__all__ = [
    'SolanaFacilitator',
    'get_facilitator',
]


def get_facilitator(config):
    """Factory function to create Solana facilitator.
    
    Args:
        config: X402Config instance
        
    Returns:
        SolanaFacilitator instance
    """
    local_cfg = getattr(config, 'local', None)
    local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
    
    return SolanaFacilitator(config=local_dict)
