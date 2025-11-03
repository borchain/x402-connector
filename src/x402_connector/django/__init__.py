"""Django integration for x402-connector.

Provides middleware, views, and utilities for integrating x402 payment
requirements into Django applications.

Quick Start:
    # settings.py
    MIDDLEWARE = [
        'x402_connector.django.X402Middleware',
    ]
    
    X402_CONFIG = {
        'pay_to_address': 'YOUR_SOLANA_ADDRESS',
        'price': '$0.01',
        'network': 'solana-devnet',
    }
    
    # views.py
    from x402_connector.django import require_payment
    
    @require_payment(price='$0.01')
    def premium_endpoint(request):
        return JsonResponse({'data': 'premium'})
"""

from .adapter import DjangoAdapter
from .middleware import X402Middleware
from .decorators import require_payment

__all__ = [
    'DjangoAdapter',
    'X402Middleware',
    'require_payment',
]

