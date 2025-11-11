"""Facilitators module - compatibility wrapper.

This module provides backward compatibility by importing from the new
facilitators package structure.

New code should import directly from:
    from x402_connector.core.facilitators import get_facilitator
"""

# Import everything from the new package
from .facilitators import (
    SolanaFacilitator,
    PayAIFacilitator,
    CorbitsFacilitator,
    HybridFacilitator,
    get_facilitator,
)

__all__ = [
    'SolanaFacilitator',
    'PayAIFacilitator',
    'CorbitsFacilitator',
    'HybridFacilitator',
    'get_facilitator',
]
