"""Django integration for x402-connector.

Provides middleware, views, and utilities for integrating x402 payment
requirements into Django applications.

Quick Start:
    # settings.py
    MIDDLEWARE = [
        'x402_connector.django.X402Middleware',
    ]
    
    X402_CONFIG = {
        'network': 'base',
        'price': '$0.01',
        'pay_to_address': '0xYourAddress',
        'protected_paths': ['/api/premium/*'],
    }
"""

from .adapter import DjangoAdapter
from .middleware import X402Middleware

__all__ = [
    'DjangoAdapter',
    'X402Middleware',
]

