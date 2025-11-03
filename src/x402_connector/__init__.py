"""x402-connector: Universal Python SDK for the x402 Payment Required protocol.

This package provides framework-agnostic payment processing with adapters for
Django, Flask, FastAPI, and other Python web frameworks.

Basic usage:

    # Django
    from x402_connector.django import X402Middleware

    # Flask
    from x402_connector.flask import X402Flask
    app = Flask(__name__)
    x402 = X402Flask(app, config={...})

    # FastAPI
    from x402_connector.fastapi import X402Middleware
    app.add_middleware(X402Middleware, config={...})

For more information, see: https://github.com/yourusername/x402-connector
"""

__version__ = "0.1.0"
__author__ = "x402 Contributors"
__license__ = "MIT"

# Core exports
from .core.config import (
    X402Config,
    LocalFacilitatorConfig,
    RemoteFacilitatorConfig,
)
from .core.context import (
    RequestContext,
    ProcessingResult,
    SettlementResult,
)
from .core.processor import X402PaymentProcessor

__all__ = [
    # Version
    "__version__",
    # Config
    "X402Config",
    "LocalFacilitatorConfig", 
    "RemoteFacilitatorConfig",
    # Context
    "RequestContext",
    "ProcessingResult",
    "SettlementResult",
    # Processor
    "X402PaymentProcessor",
]

