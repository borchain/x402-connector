"""Flask integration for x402-connector.

This module provides Flask middleware, decorators, and utilities for
integrating x402 payment requirements into Flask applications.

Example:
    >>> from flask import Flask
    >>> from x402_connector.flask import X402, require_payment
    >>> 
    >>> app = Flask(__name__)
    >>> x402 = X402(app, pay_to_address='YOUR_SOLANA_ADDRESS')
    >>> 
    >>> @app.route('/premium')
    >>> @require_payment(price='$0.01')
    >>> def premium_endpoint():
    ...     return {'data': 'premium'}
"""

from .middleware import X402
from .decorators import require_payment

__all__ = ['X402', 'require_payment']

