"""Decorators for protecting Django views with x402 payments."""

from functools import wraps
from typing import Optional, Callable
from django.http import HttpRequest, HttpResponse

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import DjangoAdapter


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
            
            # Override price if specified
            if price is not None:
                # Create temporary config with custom price
                config = _processor.config
                custom_config = X402Config(
                    pay_to_address=config.pay_to_address,
                    price=price,
                    network=config.network,
                    description=description or config.description,
                    protected_paths=config.protected_paths,
                    rpc_url=config.rpc_url,
                    signer_key_env=config.signer_key_env,
                    max_timeout_seconds=config.max_timeout_seconds,
                    verify_balance=config.verify_balance,
                    wait_for_confirmation=config.wait_for_confirmation,
                )
                # Create temporary processor with custom config
                from ..core.processor import X402PaymentProcessor
                processor = X402PaymentProcessor(custom_config)
            else:
                processor = _processor
            
            # Process request
            result = processor.process_request(context)
            
            if result.action == 'deny':
                # Return 402 Payment Required
                return _adapter.create_payment_required_response(
                    error=result.message,
                    requirements=result.requirements,
                    is_browser=_is_browser_request(request)
                )
            
            # Allow - call the actual view
            response = view_func(request, *args, **kwargs)
            
            # If successful and payment was made, settle it
            if result.action == 'allow' and result.settlement_needed:
                if _adapter.is_success_response(response):
                    # Settle payment
                    settlement = processor.settle_payment(context, result.payment_data)
                    if settlement.success:
                        # Add settlement header to response
                        response = _adapter.add_payment_response_header(
                            response,
                            settlement.transaction_hash or 'settled'
                        )
            
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

