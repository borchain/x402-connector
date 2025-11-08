"""Decorators for protecting Pyramid views with x402 payments."""

import json
import logging
from functools import wraps
from typing import Optional, Callable

from pyramid.request import Request

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import PyramidAdapter

logger = logging.getLogger(__name__)

_adapter = PyramidAdapter()


def require_payment(price: Optional[str] = None, description: Optional[str] = None):
    """Decorator to protect a Pyramid view with payment requirement.
    
    Args:
        price: Payment amount (e.g., '$0.01', '10000', '0.01 USDC')
               If None, uses default price from config
        description: Human-readable description for this endpoint
    
    Returns:
        Decorated view function
    
    Example:
        >>> from pyramid.config import Configurator
        >>> from pyramid.response import Response
        >>> from x402_connector.pyramid import require_payment, includeme
        >>> 
        >>> @require_payment(price='$0.01')
        >>> def premium_view(request):
        ...     return Response(json.dumps({'data': 'premium'}))
        >>> 
        >>> @require_payment(price='$0.10', description='AI Inference')
        >>> def ai_view(request):
        ...     return Response(json.dumps({'result': 'AI response'}))
        >>> 
        >>> config = Configurator(settings={
        ...     'x402.pay_to_address': 'YOUR_ADDRESS',
        ...     'x402.network': 'solana-devnet',
        ... })
        >>> config.include('x402_connector.pyramid')
        >>> config.add_route('premium', '/premium')
        >>> config.add_view(premium_view, route_name='premium')
        >>> app = config.make_wsgi_app()
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: Request):
            # Get processor from registry
            processor = request.registry.settings.get('x402_processor')
            
            if processor is None:
                # Tween not configured - return error
                from pyramid.response import Response
                response = Response(json.dumps({
                    'error': 'x402 tween not configured',
                    'detail': 'Use config.include("x402_connector.pyramid") to enable x402',
                }))
                response.status_code = 500
                response.content_type = 'application/json'
                return response
            
            # Extract request context
            context = _adapter.extract_request_context(request)
            
            # Override price/description if specified
            if price is not None or description is not None:
                # Create a modified copy of the config using dataclasses.replace
                from dataclasses import replace
                
                config_kwargs = {}
                if price is not None:
                    config_kwargs['price'] = price
                if description is not None:
                    config_kwargs['description'] = description
                
                config = replace(processor.config, **config_kwargs)
                
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
            
            # Payment verified - call the actual view
            logger.info(f"✨ Payment OK - calling view {view_func.__name__}")
            response = view_func(request)
            
            # Convert to Response if needed
            from pyramid.response import Response
            if not isinstance(response, Response):
                response = Response(response)
            
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


def _is_browser_request(request: Request) -> bool:
    """Check if request appears to be from a web browser.
    
    Args:
        request: Pyramid Request
        
    Returns:
        True if likely a browser, False otherwise
    """
    accept = request.headers.get('Accept', '')
    return 'text/html' in accept.lower()

