"""Decorators for protecting FastAPI routes with x402 payments."""

import logging
from functools import wraps
from typing import Optional, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse as FastAPIJSONResponse

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import FastAPIAdapter

logger = logging.getLogger(__name__)

_adapter = FastAPIAdapter()
_processor: Optional[X402PaymentProcessor] = None


def set_processor(processor: X402PaymentProcessor):
    """Set global processor instance (called by middleware).
    
    Args:
        processor: X402PaymentProcessor instance
    """
    global _processor
    _processor = processor


def require_payment(price: Optional[str] = None, description: Optional[str] = None):
    """Decorator to protect a FastAPI route with payment requirement.
    
    Args:
        price: Payment amount (e.g., '$0.01', '10000', '0.01 USDC')
               If None, uses default price from config
        description: Human-readable description for this endpoint
    
    Returns:
        Decorated route function
    
    Example:
        >>> from fastapi import FastAPI
        >>> from x402_connector.fastapi import X402Middleware, require_payment
        >>> 
        >>> app = FastAPI()
        >>> app.add_middleware(X402Middleware, pay_to_address='YOUR_ADDRESS')
        >>> 
        >>> @app.get('/premium')
        >>> @require_payment(price='$0.01')
        >>> async def premium_api():
        ...     return {'data': 'premium'}
        >>> 
        >>> @app.get('/expensive')
        >>> @require_payment(price='$0.10', description='AI Inference')
        >>> async def ai_endpoint():
        ...     return {'result': 'AI response'}
        >>> 
        >>> @app.get('/default')
        >>> @require_payment()  # Uses default price
        >>> async def default_price():
        ...     return {'data': 'content'}
    """
    def decorator(route_func: Callable) -> Callable:
        @wraps(route_func)
        async def wrapper(request: Request, *args, **kwargs):
            # Try to get processor from request state (set by middleware)
            processor = getattr(request.state, 'x402_processor', None) or _processor
            
            if processor is None:
                # Middleware not configured - return error
                return FastAPIJSONResponse(
                    content={
                        'error': 'x402 middleware not configured',
                        'detail': 'Add X402Middleware: app.add_middleware(X402Middleware, pay_to_address=...)',
                    },
                    status_code=500
                )
            
            # Extract request context
            context = _adapter.extract_request_context(request)
            
            # Override price/description if specified
            if price is not None or description is not None:
                # Create a modified copy of the config using dataclasses.replace
                from dataclasses import replace
                
                kwargs_dict = {}
                if price is not None:
                    kwargs_dict['price'] = price
                if description is not None:
                    kwargs_dict['description'] = description
                
                config = replace(processor.config, **kwargs_dict)
                
                # Create temporary processor with modified config
                temp_processor = X402PaymentProcessor(config)
            else:
                temp_processor = processor
            
            # For decorator, ALWAYS require payment (bypass path check)
            logger.info(f"🔒 @require_payment: Protecting {context.path} (price={price or 'default'})")
            
            # Build payment requirements
            requirements = temp_processor._build_payment_requirements(context)
            logger.debug(f"💰 Payment requirements: amount={requirements[0]['maxAmountRequired']}, asset={requirements[0].get('assetSymbol', 'USDC')}")
            
            # Check for payment header
            if not context.payment_header:
                # No payment provided - return 402
                logger.info(f"❌ No X-PAYMENT header - returning 402 Payment Required")
                return _adapter.create_payment_required_response(
                    error='No X-PAYMENT header provided',
                    requirements=requirements,
                    is_browser=_is_browser_request(request)
                )
            
            # Verify payment with facilitator
            logger.info(f"🔍 Verifying payment signature...")
            facilitator = temp_processor.facilitator
            
            import json
            try:
                # Parse payment header into dict
                payment_data = json.loads(context.payment_header)
                logger.debug(f"📝 Payment from: {payment_data.get('payload', {}).get('authorization', {}).get('from', 'unknown')}")
            except Exception as e:
                logger.warning(f"⚠️  Could not parse payment header: {e}")
                return _adapter.create_payment_required_response(
                    error=f'Invalid payment format: {e}',
                    requirements=requirements,
                    is_browser=_is_browser_request(request)
                )
            
            # Verify payment (pass parsed dict, not string)
            verify_result = facilitator.verify(
                payment=payment_data,
                requirements=requirements[0] if requirements else {}
            )
            
            if not verify_result.get('isValid', False):
                # Payment invalid - return 402
                reason = verify_result.get('invalidReason', 'unknown')
                logger.warning(f"❌ Payment verification FAILED: {reason}")
                return _adapter.create_payment_required_response(
                    error=f"Payment verification failed: {reason}",
                    requirements=requirements,
                    is_browser=_is_browser_request(request)
                )
            
            logger.info(f"✅ Payment verified successfully from {verify_result.get('payer', 'unknown')}")
            
            # Payment verified - call the actual route
            logger.info(f"✨ Payment OK - calling route {route_func.__name__}")
            response = await route_func(request, *args, **kwargs)
            
            # Convert to Response object if needed
            if not isinstance(response, Response):
                response = FastAPIJSONResponse(content=response)
            
            # If successful response, settle the payment
            if _adapter.is_success_response(response):
                logger.info(f"💸 Settling payment on Solana blockchain...")
                # Settle payment
                settlement = temp_processor.settle_payment(context)
                if settlement.success:
                    tx_hash = settlement.encoded_response or settlement.transaction_hash or 'demo_settled'
                    logger.info(f"🎉 Payment settled! TX: {tx_hash[:16]}...")
                    # Add settlement header to response
                    response = _adapter.add_payment_response_header(
                        response,
                        settlement.encoded_response or 'settled'
                    )
                else:
                    logger.error(f"⚠️  Settlement failed: {settlement.error}")
            
            return response
        
        return wrapper
    return decorator


def _is_browser_request(req: Request) -> bool:
    """Check if request appears to be from a web browser.
    
    Args:
        req: FastAPI Request
        
    Returns:
        True if likely a browser, False otherwise
    """
    accept = req.headers.get('accept', '')
    return 'text/html' in accept.lower()

