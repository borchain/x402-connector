"""Pyramid integration for x402-connector.

This module provides Pyramid web framework integration for the x402 payment
protocol. It includes adapters, decorators, and tween (middleware) for adding
HTTP 402 Payment Required functionality to Pyramid applications.

Example:
    >>> from pyramid.config import Configurator
    >>> from pyramid.response import Response
    >>> from x402_connector.pyramid import require_payment, includeme
    >>> 
    >>> @require_payment(price='$0.01')
    >>> def premium_view(request):
    ...     return Response(json.dumps({'data': 'premium'}))
    >>> 
    >>> config = Configurator(settings={
    ...     'x402.pay_to_address': 'YOUR_SOLANA_ADDRESS',
    ...     'x402.network': 'solana-devnet',
    ... })
    >>> config.include('x402_connector.pyramid')
    >>> config.add_route('premium', '/premium')
    >>> config.add_view(premium_view, route_name='premium')
    >>> app = config.make_wsgi_app()
"""

from .adapter import PyramidAdapter
from .decorators import require_payment
from .middleware import X402Tween, includeme

__all__ = ['PyramidAdapter', 'require_payment', 'X402Tween', 'includeme']

