"""Django middleware for x402 payment processing."""

import logging
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import DjangoAdapter

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


class X402Middleware:
    """Django middleware for x402 payment processing.
    
    This middleware intercepts requests to protected paths and enforces
    payment requirements using the x402 protocol.
    
    Configuration:
        Add to MIDDLEWARE in settings.py:
            MIDDLEWARE = [
                ...
                'x402_connector.django.X402Middleware',
            ]
        
        Configure in settings.py:
            X402_CONFIG = {
                'network': 'base',
                'price': '$0.01',
                'pay_to_address': '0xYourAddress',
                'protected_paths': ['/api/premium/*'],
            }
    
    Behavior:
        1. Checks if request path requires payment
        2. Verifies payment if X-PAYMENT header present
        3. Returns 402 if payment missing/invalid
        4. Allows request if payment valid
        5. Settles payment after successful response (2xx)
        6. Adds X-PAYMENT-RESPONSE header with settlement details
    """
    
    async_capable = False
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """Initialize middleware and load configuration from Django settings.
        
        Args:
            get_response: Django's next middleware or view function
        """
        self.get_response = get_response
        
        # Load configuration from Django settings
        config_dict = getattr(settings, 'X402_CONFIG', None) or \
                     getattr(settings, 'X402', {})
        
        if not config_dict:
            logger.warning(
                "No X402_CONFIG found in Django settings. "
                "x402 middleware will not protect any paths."
            )
            self.enabled = False
            return
        
        try:
            self.config = X402Config.from_dict(config_dict)
            self.processor = X402PaymentProcessor(self.config)
            self.adapter = DjangoAdapter()
            self.enabled = True
            logger.info(
                f"x402 middleware initialized: "
                f"protecting paths {self.config.protected_paths}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize x402 middleware: {e}")
            self.enabled = False
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request through x402 payment gate.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            Django HttpResponse (either 402 or from the view)
        """
        # Skip if middleware not properly configured
        if not self.enabled:
            return self.get_response(request)
        
        # Extract context
        context = self.adapter.extract_request_context(request)
        
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
        
        # Call view
        response = self.get_response(request)
        
        # Settle payment if verified and successful response
        if result.payment_verified and self.adapter.is_success_response(response):
            logger.info(
                f"Settling payment for {context.path} "
                f"from payer {result.payer_address}"
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
                    requirements=result.requirements or [],
                    is_browser=False
                )
            else:
                # log-and-continue policy
                logger.warning(
                    f"Settlement failed: {settlement.error}. "
                    f"Policy=log-and-continue, allowing response"
                )
        
        return response

