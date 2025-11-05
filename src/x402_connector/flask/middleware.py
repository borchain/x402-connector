"""Flask middleware/extension for x402 payment processing."""

import logging
from typing import Optional, Dict, Any

from flask import Flask, request, g
from flask.ctx import RequestContext as FlaskRequestContext

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import FlaskAdapter

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


class X402:
    """Flask extension for x402 payment processing.
    
    This extension integrates x402 payment requirements into Flask applications
    using Flask's before_request and after_request hooks.
    
    Usage:
        # Method 1: Direct initialization
        app = Flask(__name__)
        x402 = X402(app, pay_to_address='YOUR_SOLANA_ADDRESS')
        
        # Method 2: Factory pattern
        x402 = X402()
        x402.init_app(app, pay_to_address='YOUR_SOLANA_ADDRESS')
        
        # Method 3: From app config
        app.config['X402_CONFIG'] = {
            'pay_to_address': 'YOUR_SOLANA_ADDRESS',
            'price': '$0.01',
            'network': 'solana-devnet',
        }
        x402 = X402(app)
    
    Configuration:
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
    
    def __init__(
        self,
        app: Optional[Flask] = None,
        pay_to_address: Optional[str] = None,
        **kwargs
    ):
        """Initialize X402 extension.
        
        Args:
            app: Flask application instance (optional)
            pay_to_address: Solana address for receiving payments
            **kwargs: Additional configuration options
        """
        self.processor: Optional[X402PaymentProcessor] = None
        self.adapter = FlaskAdapter()
        self.enabled = False
        
        if app is not None:
            self.init_app(app, pay_to_address=pay_to_address, **kwargs)
    
    def init_app(
        self,
        app: Flask,
        pay_to_address: Optional[str] = None,
        **kwargs
    ):
        """Initialize extension with Flask app.
        
        Args:
            app: Flask application instance
            pay_to_address: Solana address for receiving payments
            **kwargs: Additional configuration options
        """
        # Load configuration from app config or kwargs
        config_dict = app.config.get('X402_CONFIG', {}).copy()
        
        # Override with explicit kwargs
        if pay_to_address:
            config_dict['pay_to_address'] = pay_to_address
        config_dict.update(kwargs)
        
        if not config_dict:
            logger.warning(
                "No X402_CONFIG found in Flask app.config. "
                "x402 extension will not protect any paths."
            )
            self.enabled = False
            return
        
        try:
            self.config = X402Config.from_dict(config_dict)
            self.processor = X402PaymentProcessor(self.config)
            self.enabled = True
            
            # Register hooks
            app.before_request(self._before_request)
            app.after_request(self._after_request)
            
            # Store processor in app for decorator access
            if not hasattr(app, 'extensions'):
                app.extensions = {}
            app.extensions['x402'] = self
            
            logger.info(
                f"x402 extension initialized: "
                f"protecting paths {self.config.protected_paths}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize x402 extension: {e}")
            self.enabled = False
    
    def _before_request(self):
        """Process request before view function (Flask hook)."""
        # Skip if extension not properly configured
        if not self.enabled:
            return None
        
        # Extract context
        context = self.adapter.extract_request_context(request)
        
        # Store context in g for after_request
        g.x402_context = context
        g.x402_payment_verified = False
        g.x402_payer_address = None
        
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
        
        # Store verification status for after_request
        g.x402_payment_verified = result.payment_verified
        g.x402_payer_address = result.payer_address
        
        return None  # Allow request to proceed
    
    def _after_request(self, response):
        """Process response after view function (Flask hook).
        
        Args:
            response: Flask Response object
            
        Returns:
            Modified Flask Response
        """
        # Skip if extension not enabled or no context stored
        if not self.enabled or not hasattr(g, 'x402_context'):
            return response
        
        # Settle payment if verified and successful response
        if g.x402_payment_verified and self.adapter.is_success_response(response):
            logger.info(
                f"Settling payment for {g.x402_context.path} "
                f"from payer {g.x402_payer_address}"
            )
            
            settlement = self.processor.settle_payment(g.x402_context)
            
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
                    requirements=self.processor._build_payment_requirements(g.x402_context),
                    is_browser=False
                )
            else:
                # log-and-continue policy
                logger.warning(
                    f"Settlement failed: {settlement.error}. "
                    f"Policy=log-and-continue, allowing response"
                )
        
        return response

