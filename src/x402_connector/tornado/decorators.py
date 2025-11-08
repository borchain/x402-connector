"""Decorators for protecting Tornado handlers with x402 payments."""

import logging
from functools import wraps
from typing import Optional

from tornado.web import RequestHandler

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import TornadoAdapter

logger = logging.getLogger(__name__)

_adapter = TornadoAdapter()


def require_payment(price: Optional[str] = None, description: Optional[str] = None):
    """Decorator to protect a Tornado handler method with payment requirement.
    
    Args:
        price: Payment amount (e.g., '$0.01', '10000', '0.01 USDC')
               If None, uses default price from config
        description: Human-readable description for this endpoint
    
    Returns:
        Decorated handler method
    
    Example:
        >>> from tornado import web, ioloop
        >>> from x402_connector.tornado import X402Middleware, require_payment
        >>> 
        >>> class PremiumHandler(web.RequestHandler):
        ...     @require_payment(price='$0.01')
        ...     async def get(self):
        ...         self.write({'data': 'premium content'})
        >>> 
        >>> class ExpensiveHandler(web.RequestHandler):
        ...     @require_payment(price='$0.10', description='AI Inference')
        ...     async def post(self):
        ...         self.write({'result': 'AI response'})
        >>> 
        >>> app = web.Application([
        ...     (r'/premium', PremiumHandler),
        ...     (r'/expensive', ExpensiveHandler),
        ... ])
        >>> X402Middleware(app, pay_to_address='YOUR_ADDRESS')
        >>> 
        >>> app.listen(8888)
        >>> ioloop.IOLoop.current().start()
    """
    def decorator(method):
        @wraps(method)
        async def wrapper(self: RequestHandler, *args, **kwargs):
            # Get processor from app settings
            processor = self.application.settings.get('x402_processor')
            
            if processor is None:
                # Middleware not configured - return error
                self.set_status(500)
                self.write({
                    'error': 'x402 middleware not configured',
                    'detail': 'Initialize X402Middleware: X402Middleware(app, pay_to_address=...)',
                })
                self.finish()
                return
            
            # Extract request context
            context = _adapter.extract_request_context(self)
            
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
                _adapter.create_payment_required_response(
                    self,
                    error='No X-PAYMENT header provided',
                    requirements=requirements,
                    is_browser=_is_browser_request(self)
                )
                return
            
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
                _adapter.create_payment_required_response(
                    self,
                    error=f'Invalid payment format: {e}',
                    requirements=requirements,
                    is_browser=_is_browser_request(self)
                )
                return
            
            # Verify payment (pass parsed dict, not string)
            verify_result = facilitator.verify(
                payment=payment_data,
                requirements=requirements[0] if requirements else {}
            )
            
            if not verify_result.get('isValid', False):
                # Payment invalid - return 402
                reason = verify_result.get('invalidReason', 'unknown')
                logger.warning(f"❌ Payment verification FAILED: {reason}")
                _adapter.create_payment_required_response(
                    self,
                    error=f"Payment verification failed: {reason}",
                    requirements=requirements,
                    is_browser=_is_browser_request(self)
                )
                return
            
            logger.info(f"✅ Payment verified successfully from {verify_result.get('payer', 'unknown')}")
            
            # Payment verified - call the actual handler method
            logger.info(f"✨ Payment OK - calling handler {method.__name__}")
            result = method(self, *args, **kwargs)
            
            # Await if it's a coroutine
            if result is not None:
                await result
            
            # If successful response, settle the payment
            if _adapter.is_success_response(self):
                logger.info(f"💸 Settling payment on Solana blockchain...")
                # Settle payment
                settlement = temp_processor.settle_payment(context)
                if settlement.success:
                    tx_hash = settlement.encoded_response or settlement.transaction_hash or 'demo_settled'
                    logger.info(f"🎉 Payment settled! TX: {tx_hash[:16]}...")
                    # Add settlement header to response
                    _adapter.add_payment_response_header(
                        self,
                        settlement.encoded_response or 'settled'
                    )
                else:
                    logger.error(f"⚠️  Settlement failed: {settlement.error}")
        
        return wrapper
    return decorator


def _is_browser_request(handler: RequestHandler) -> bool:
    """Check if request appears to be from a web browser.
    
    Args:
        handler: Tornado RequestHandler
        
    Returns:
        True if likely a browser, False otherwise
    """
    accept = handler.request.headers.get('Accept', '')
    return 'text/html' in accept.lower()

