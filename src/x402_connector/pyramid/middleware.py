"""Pyramid tween (middleware) for x402 payment processing."""

import logging
from typing import Optional, Dict, Any, Callable

from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.response import Response

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import PyramidAdapter

logger = logging.getLogger(__name__)


def is_browser_request(headers: dict) -> bool:
    """Check if request is from a browser based on headers.
    
    Args:
        headers: Request headers dictionary
        
    Returns:
        True if request appears to be from a browser
    """
    accept = headers.get('Accept', '')
    user_agent = headers.get('User-Agent', '')
    
    # Check if HTML is accepted
    if 'text/html' in accept:
        return True
    
    # Check for common browser user agents
    browser_keywords = [
        'Mozilla', 'Chrome', 'Safari', 'Firefox', 'Edge', 'Opera'
    ]
    return any(keyword in user_agent for keyword in browser_keywords)


class X402Tween:
    """Pyramid tween (middleware) for x402 payment processing.
    
    A tween in Pyramid is similar to middleware in other frameworks.
    It wraps the request/response cycle and can intercept both.
    
    This tween:
    1. Checks if request path requires payment
    2. Verifies payment if X-PAYMENT header present
    3. Returns 402 if payment missing/invalid
    4. Allows request if payment valid
    5. Settles payment after successful response (2xx)
    6. Adds X-PAYMENT-RESPONSE header with settlement details
    """
    
    def __init__(
        self, 
        handler: Callable, 
        registry: Any,
        processor: X402PaymentProcessor,
        adapter: PyramidAdapter
    ):
        """Initialize tween.
        
        Args:
            handler: Next handler in the tween chain
            registry: Pyramid registry
            processor: X402 payment processor
            adapter: Pyramid adapter
        """
        self.handler = handler
        self.registry = registry
        self.processor = processor
        self.adapter = adapter
        self.config = processor.config
    
    def __call__(self, request: Request) -> Response:
        """Process request through x402 payment verification.
        
        Args:
            request: Pyramid Request
            
        Returns:
            Pyramid Response (either 402 or from downstream handler)
        """
        # Extract context
        context = self.adapter.extract_request_context(request)
        
        # Store context in request for decorator access
        request.x402_context = context
        request.x402_payment_verified = False
        request.x402_payer_address = None
        
        # Process payment
        result = self.processor.process_request(context)
        
        if result.action == 'deny':
            # Return 402 response
            is_browser = is_browser_request(context.headers)
            logger.info(
                f"Payment required for {context.path}: {result.error}"
            )
            return self.adapter.create_payment_required_response(
                error=result.error or 'Payment required',
                requirements=result.requirements or [],
                is_browser=is_browser
            )
        
        # Store verification status
        request.x402_payment_verified = result.payment_verified
        request.x402_payer_address = result.payer_address
        
        # Call downstream handler
        response = self.handler(request)
        
        # Settle payment if verified and successful response
        if request.x402_payment_verified and self.adapter.is_success_response(response):
            logger.info(
                f"Settling payment for {context.path} "
                f"from payer {request.x402_payer_address}"
            )
            
            settlement = self.processor.settle_payment(context)
            
            if settlement.success:
                response = self.adapter.add_payment_response_header(
                    response,
                    settlement.encoded_response
                )
                logger.info(
                    f"Payment settled successfully: {settlement.transaction_hash}"
                )
            elif self.config.settle_policy == 'block-on-failure':
                # Return 402 on settlement failure
                logger.error(
                    f"Settlement failed: {settlement.error}. "
                    f"Policy=block-on-failure, returning 402"
                )
                return self.adapter.create_payment_required_response(
                    error=f'Settlement failed: {settlement.error}',
                    requirements=self.processor._build_payment_requirements(context),
                    is_browser=False
                )
            else:
                # log-and-continue policy
                logger.warning(
                    f"Settlement failed: {settlement.error}. "
                    f"Policy=log-and-continue, allowing response"
                )
        
        return response


def x402_tween_factory(handler: Callable, registry: Any) -> Callable:
    """Tween factory for Pyramid.
    
    Args:
        handler: Next handler in chain
        registry: Pyramid registry
        
    Returns:
        Tween callable
    """
    # Get processor and adapter from registry
    processor = registry.settings.get('x402_processor')
    adapter = registry.settings.get('x402_adapter')
    
    if processor is None or adapter is None:
        # Not configured - pass through
        logger.warning("x402 tween factory called but processor not configured")
        return handler
    
    # Return tween instance
    tween = X402Tween(handler, registry, processor, adapter)
    return tween


def includeme(config: Configurator):
    """Pyramid includeme hook for easy configuration.
    
    This allows users to simply call config.include('x402_connector.pyramid')
    to set up x402 payment processing.
    
    Usage:
        >>> from pyramid.config import Configurator
        >>> 
        >>> config = Configurator(settings={
        ...     'x402.pay_to_address': 'YOUR_SOLANA_ADDRESS',
        ...     'x402.price': '$0.01',
        ...     'x402.network': 'solana-devnet',
        ... })
        >>> 
        >>> config.include('x402_connector.pyramid')
        >>> app = config.make_wsgi_app()
    
    Args:
        config: Pyramid Configurator instance
    """
    settings = config.registry.settings
    
    # Extract x402 settings (prefix with 'x402.')
    x402_settings = {}
    for key, value in settings.items():
        if key.startswith('x402.'):
            # Remove 'x402.' prefix and convert to snake_case
            config_key = key[5:].replace('.', '_')
            x402_settings[config_key] = value
    
    if not x402_settings:
        logger.warning(
            "No x402.* settings found in Pyramid config. "
            "x402 tween will not be configured."
        )
        return
    
    try:
        # Create config
        x402_config = X402Config.from_dict(x402_settings)
        
        # Create processor and adapter
        processor = X402PaymentProcessor(x402_config)
        adapter = PyramidAdapter()
        
        # Store in registry for tween access
        config.registry.settings['x402_processor'] = processor
        config.registry.settings['x402_adapter'] = adapter
        config.registry.settings['x402_config_obj'] = x402_config
        
        # Add tween to the pipeline
        config.add_tween('x402_connector.pyramid.middleware.x402_tween_factory')
        
        logger.info(
            f"x402 tween configured: "
            f"protecting paths {x402_config.protected_paths}"
        )
    except Exception as e:
        logger.error(f"Failed to configure x402 tween: {e}")

