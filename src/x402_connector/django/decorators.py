"""Decorators for protecting Django views with x402 payments."""

import logging
from functools import wraps
from typing import Optional, Callable
from django.http import HttpRequest, HttpResponse

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import DjangoAdapter

logger = logging.getLogger(__name__)

# Global processor instance (initialized by middleware)
_processor: Optional[X402PaymentProcessor] = None
_adapter = DjangoAdapter()


def set_processor(processor: X402PaymentProcessor):
    """Set global processor instance (called by middleware).
    
    Args:
        processor: X402PaymentProcessor instance
    """
    global _processor
    _processor = processor


def require_payment(price: Optional[str] = None, description: Optional[str] = None):
    """Decorator to protect a Django view with payment requirement.
    
    Args:
        price: Payment amount (e.g., '$0.01', '10000', '0.01 USDC')
               If None, uses default price from config
        description: Human-readable description for this endpoint
    
    Returns:
        Decorated view function
    
    Example:
        >>> from x402_connector.django import require_payment
        >>> 
        >>> @require_payment(price='$0.01')
        >>> def premium_api(request):
        ...     return JsonResponse({'data': 'premium'})
        >>> 
        >>> @require_payment(price='$0.10', description='AI Inference')
        >>> def ai_endpoint(request):
        ...     return JsonResponse({'result': 'AI response'})
        >>> 
        >>> @require_payment()  # Uses default price
        >>> def default_price(request):
        ...     return JsonResponse({'data': 'content'})
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if _processor is None:
                # Middleware not configured - return error
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'x402 middleware not configured',
                    'detail': 'Add X402Middleware to MIDDLEWARE in settings.py',
                }, status=500)
            
            # Extract request context
            context = _adapter.extract_request_context(request)
            
            # Override price/description if specified
            if price is not None or description is not None:
                # Create a modified copy of the config using dataclasses.replace
                from dataclasses import replace
                from ..core.processor import X402PaymentProcessor
                
                config_kwargs = {}
                if price is not None:
                    config_kwargs['price'] = price
                if description is not None:
                    config_kwargs['description'] = description
                
                config = replace(_processor.config, **config_kwargs)
                
                # Create temporary processor with modified config
                processor = X402PaymentProcessor(config)
            else:
                processor = _processor
            
            # For decorator, ALWAYS require payment (bypass path check)
            logger.info(f"🔒 @require_payment: Protecting {context.path} (price={price or 'default'})")
            
            # Build payment requirements
            requirements = processor._build_payment_requirements(context)
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
            facilitator = processor.facilitator
            
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
                payment=payment_data,  # ← Pass dict, not string
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
            response = view_func(request, *args, **kwargs)
            
            # If successful response, settle the payment
            if _adapter.is_success_response(response):
                logger.info(f"💸 Settling payment on Solana blockchain...")
                # Settle payment
                settlement = processor.settle_payment(context)
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


def _is_browser_request(request: HttpRequest) -> bool:
    """Check if request appears to be from a web browser.
    
    Args:
        request: Django HttpRequest
        
    Returns:
        True if likely a browser, False otherwise
    """
    accept = request.headers.get('Accept', '')
    return 'text/html' in accept.lower()

