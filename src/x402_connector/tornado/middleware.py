"""Tornado middleware for x402 payment processing."""

import logging
from typing import Optional, Dict, Any, Callable

from tornado.web import Application, RequestHandler

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import TornadoAdapter

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
    """Tornado middleware for x402 payment processing.
    
    This middleware integrates x402 payment requirements into Tornado applications
    by wrapping request handlers and intercepting requests/responses.
    
    Usage:
        >>> from tornado import web
        >>> from x402_connector.tornado import X402Middleware
        >>> 
        >>> app = web.Application([
        ...     (r'/api/premium', PremiumHandler),
        ... ])
        >>> 
        >>> # Initialize middleware
        >>> X402Middleware(app, pay_to_address='YOUR_SOLANA_ADDRESS')
        >>> 
        >>> app.listen(8888)
    
    Configuration:
        Pass configuration as kwargs or use app settings:
        
        >>> app.settings['x402_config'] = {
        ...     'pay_to_address': 'YOUR_SOLANA_ADDRESS',
        ...     'price': '$0.01',
        ...     'network': 'solana-devnet',
        ... }
        >>> X402Middleware(app)
    
    Behavior:
        1. Intercepts requests before handler execution
        2. Checks if request path requires payment
        3. Verifies payment if X-PAYMENT header present
        4. Returns 402 if payment missing/invalid
        5. Allows request if payment valid
        6. Settles payment after successful response (2xx)
        7. Adds X-PAYMENT-RESPONSE header with settlement details
    """
    
    def __init__(
        self,
        app: Application,
        pay_to_address: Optional[str] = None,
        **kwargs
    ):
        """Initialize X402 middleware for Tornado.
        
        Args:
            app: Tornado Application instance
            pay_to_address: Solana address for receiving payments
            **kwargs: Additional configuration options
        """
        self.app = app
        self.adapter = TornadoAdapter()
        self.enabled = False
        
        # Load configuration from app settings or kwargs
        config_dict = app.settings.get('x402_config', {}).copy()
        
        # Override with explicit kwargs
        if pay_to_address:
            config_dict['pay_to_address'] = pay_to_address
        config_dict.update(kwargs)
        
        if not config_dict:
            logger.warning(
                "No x402_config found in Tornado app.settings. "
                "x402 middleware will not protect any paths."
            )
            self.enabled = False
            return
        
        try:
            self.config = X402Config.from_dict(config_dict)
            self.processor = X402PaymentProcessor(self.config)
            self.enabled = True
            
            # Store processor in app settings for decorator access
            app.settings['x402_processor'] = self.processor
            app.settings['x402_adapter'] = self.adapter
            
            # Wrap all handlers
            self._wrap_handlers()
            
            logger.info(
                f"x402 middleware initialized: "
                f"protecting paths {self.config.protected_paths}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize x402 middleware: {e}")
            self.enabled = False
    
    def _wrap_handlers(self):
        """Wrap all request handlers to intercept requests."""
        # Get handlers - in newer Tornado versions, they're stored differently
        handlers = getattr(self.app, 'handlers', None)
        if handlers is None:
            # Try default_router for newer Tornado versions
            if hasattr(self.app, 'default_router') and hasattr(self.app.default_router, 'rules'):
                handlers = [(r'.*$', self.app.default_router.rules)]
            else:
                logger.warning("Could not access Tornado handlers for wrapping")
                return
        
        for spec in handlers:
            # Each spec is (host_pattern, [URLSpec, URLSpec, ...])
            url_specs = spec[1] if isinstance(spec, tuple) else spec
            if not isinstance(url_specs, list):
                continue
                
            for url_spec in url_specs:
                if not hasattr(url_spec, 'handler_class'):
                    continue
                    
                original_handler = url_spec.handler_class
                
                # Only wrap if not already wrapped
                if not hasattr(original_handler, '_x402_wrapped'):
                    wrapped_handler = self._create_wrapped_handler(original_handler)
                    url_spec.handler_class = wrapped_handler
    
    def _create_wrapped_handler(self, handler_class):
        """Create a wrapped version of a handler class.
        
        Args:
            handler_class: Original RequestHandler class
            
        Returns:
            Wrapped handler class with x402 payment processing
        """
        middleware = self
        
        class WrappedHandler(handler_class):
            """Wrapped handler with x402 payment processing."""
            
            _x402_wrapped = True
            
            async def prepare(self):
                """Called before handler method (GET, POST, etc)."""
                # Call original prepare if exists
                if hasattr(handler_class, 'prepare'):
                    result = super().prepare()
                    if result is not None:
                        await result
                
                # Skip if middleware not enabled
                if not middleware.enabled:
                    return
                
                # Skip if handler has x402_skip attribute
                if getattr(self, 'x402_skip', False):
                    return
                
                # Extract context
                context = middleware.adapter.extract_request_context(self)
                
                # Store context for later use
                self._x402_context = context
                self._x402_payment_verified = False
                self._x402_payer_address = None
                
                # Process payment
                result = middleware.processor.process_request(context)
                
                if result.action == 'deny':
                    # Return 402 response
                    is_browser = is_browser_request(context.headers)
                    logger.info(
                        f"Payment required for {context.path}: {result.error}"
                    )
                    middleware.adapter.create_payment_required_response(
                        self,
                        error=result.error or 'Payment required',
                        requirements=result.requirements or [],
                        is_browser=is_browser
                    )
                    # This will prevent handler method from being called
                    return
                
                # Store verification status
                self._x402_payment_verified = result.payment_verified
                self._x402_payer_address = result.payer_address
            
            def on_finish(self):
                """Called after request is finished."""
                # Call original on_finish if exists
                if hasattr(handler_class, 'on_finish'):
                    super().on_finish()
                
                # Skip if middleware not enabled or no context stored
                if not middleware.enabled or not hasattr(self, '_x402_context'):
                    return
                
                # Settle payment if verified and successful response
                if self._x402_payment_verified and middleware.adapter.is_success_response(self):
                    logger.info(
                        f"Settling payment for {self._x402_context.path} "
                        f"from payer {self._x402_payer_address}"
                    )
                    
                    settlement = middleware.processor.settle_payment(self._x402_context)
                    
                    if settlement.success:
                        middleware.adapter.add_payment_response_header(
                            self,
                            settlement.encoded_response
                        )
                        logger.info(
                            f"Payment settled successfully: {settlement.transaction_hash}"
                        )
                    elif middleware.config.settle_policy == 'block-on-failure':
                        # Log error (can't change response at this point)
                        logger.error(
                            f"Settlement failed: {settlement.error}. "
                            f"Policy=block-on-failure (response already sent)"
                        )
                    else:
                        # log-and-continue policy
                        logger.warning(
                            f"Settlement failed: {settlement.error}. "
                            f"Policy=log-and-continue, response already sent"
                        )
        
        return WrappedHandler

