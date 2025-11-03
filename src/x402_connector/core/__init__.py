"""Core x402 payment processing logic.

This module contains framework-agnostic implementations of payment verification,
settlement, and configuration management for Solana.
"""

from .adapters import BaseAdapter
from .config import X402Config
from .context import (
    RequestContext,
    ProcessingResult,
    SettlementResult,
)
from .processor import X402PaymentProcessor

__all__ = [
    # Adapters
    "BaseAdapter",
    # Config
    "X402Config",
    # Context
    "RequestContext",
    "ProcessingResult",
    "SettlementResult",
    # Processor
    "X402PaymentProcessor",
]

