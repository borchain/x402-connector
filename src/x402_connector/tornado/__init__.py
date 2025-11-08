"""Tornado integration for x402-connector.

This module provides Tornado web framework integration for the x402 payment
protocol. It includes adapters, decorators, and middleware for adding HTTP 402
Payment Required functionality to Tornado applications.

Example:
    >>> from tornado import web, ioloop
    >>> from x402_connector.tornado import X402Middleware, require_payment
    >>> 
    >>> class PremiumHandler(web.RequestHandler):
    ...     @require_payment(price='$0.01')
    ...     async def get(self):
    ...         self.write({'data': 'premium'})
    >>> 
    >>> app = web.Application([(r'/premium', PremiumHandler)])
    >>> X402Middleware(app, pay_to_address='YOUR_SOLANA_ADDRESS')
    >>> 
    >>> app.listen(8888)
    >>> ioloop.IOLoop.current().start()
"""

from .adapter import TornadoAdapter
from .decorators import require_payment
from .middleware import X402Middleware

__all__ = ['TornadoAdapter', 'require_payment', 'X402Middleware']

