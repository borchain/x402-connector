"""FastAPI middleware for x402 payment processing."""

import logging
from typing import Optional, Dict, Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import FastAPIAdapter

logger = logging.getLogger(__name__)


def is_browser_request(headers: dict) -> bool:
    """Check if request is from a browser based on headers.
    
    Args:
        headers: Request headers dictionary
        
    Returns:
        True if request appears to be from a browser
    """
    accept = headers.get('accept', '')
    user_agent = headers.get('user-agent', '')
    
    # Check if HTML is accepted
    if 'text/html' in accept:
        return True
    
    # Check for common browser user agents
    browser_keywords = [
        'Mozilla', 'Chrome', 'Safari', 'Firefox', 'Edge', 'Opera'
    ]
    return any(keyword in user_agent for keyword in browser_keywords)


class X402Middleware(BaseHTTPMiddleware):
    """FastAPI middleware for x402 payment processing.
    
    This middleware intercepts requests to protected paths and enforces
    payment requirements using the x402 protocol.
    
    Usage:
        app = FastAPI()
        app.add_middleware(
            X402Middleware,
            pay_to_address='YOUR_SOLANA_ADDRESS',
            price='$0.01',
            network='solana-devnet'
        )
    
    Configuration:
        All X402Config options can be passed as kwargs to add_middleware
    
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
        app: ASGIApp,
        pay_to_address: Optional[str] = None,
        **kwargs
    ):
        """Initialize X402 middleware.
        
        Args:
            app: ASGI application
            pay_to_address: Solana address for receiving payments
            **kwargs: Additional X402Config options
        """
        super().__init__(app)
        
        self.adapter = FastAPIAdapter()
        self.enabled = False
        
        # Build config from kwargs
        if pay_to_address:
            kwargs['pay_to_address'] = pay_to_address
        
        if not kwargs:
            logger.warning(
                "No configuration provided to X402Middleware. "
                "Middleware will not protect any paths."
            )
            return
        
        try:
            self.config = X402Config.from_dict(kwargs)
            self.processor = X402PaymentProcessor(self.config)
            self.enabled = True
            
            # Set global processor for decorators
            from .decorators import set_processor
            set_processor(self.processor)
            
            logger.info(
                f"x402 middleware initialized: "
                f"protecting paths {self.config.protected_paths}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize x402 middleware: {e}")
            self.enabled = False
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """Process request through x402 payment gate.
        
        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler
            
        Returns:
            FastAPI Response (either 402 or from the route)
        """
        # Skip if middleware not properly configured
        if not self.enabled:
            return await call_next(request)
        
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
        
        # Store verification status for after response
        request.state.x402_payment_verified = result.payment_verified
        request.state.x402_payer_address = result.payer_address
        request.state.x402_context = context
        
        # Call route handler
        response = await call_next(request)
        
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

