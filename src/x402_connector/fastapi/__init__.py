"""FastAPI integration for x402-connector.

This module provides FastAPI middleware, decorators, and utilities for
integrating x402 payment requirements into FastAPI applications.

Example:
    >>> from fastapi import FastAPI
    >>> from x402_connector.fastapi import X402Middleware, require_payment
    >>> 
    >>> app = FastAPI()
    >>> app.add_middleware(
    ...     X402Middleware,
    ...     pay_to_address='YOUR_SOLANA_ADDRESS'
    ... )
    >>> 
    >>> @app.get('/premium')
    >>> @require_payment(price='$0.01')
    >>> async def premium_endpoint():
    ...     return {'data': 'premium'}
"""

from .middleware import X402Middleware
from .decorators import require_payment

__all__ = ['X402Middleware', 'require_payment']

