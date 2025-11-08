"""Tornado framework adapter for x402-connector."""

from typing import Any, Dict, List

from tornado.web import RequestHandler

from ..core.adapters import BaseAdapter
from ..core.context import RequestContext


class TornadoAdapter(BaseAdapter):
    """Tornado framework adapter.
    
    Translates between Tornado's RequestHandler and
    the framework-agnostic RequestContext/responses used by the core processor.
    
    Example:
        >>> adapter = TornadoAdapter()
        >>> context = adapter.extract_request_context(handler)
        >>> # Create 402 response
        >>> adapter.create_payment_required_response(
        ...     handler,
        ...     error='Payment required',
        ...     requirements=[...],
        ...     is_browser=False
        ... )
    """
    
    def extract_request_context(self, handler: RequestHandler) -> RequestContext:
        """Extract request context from Tornado RequestHandler.
        
        Args:
            handler: Tornado RequestHandler instance
            
        Returns:
            RequestContext with path, method, headers, and payment header
        """
        # Get absolute URL
        absolute_url = handler.request.full_url()
        
        # Convert headers to dict
        headers = {k: v for k, v in handler.request.headers.get_all()}
        
        return RequestContext(
            path=handler.request.path,
            method=handler.request.method,
            headers=headers,
            absolute_url=absolute_url,
            payment_header=handler.request.headers.get('X-Payment')
        )
    
    def create_payment_required_response(
        self,
        handler: RequestHandler,
        error: str,
        requirements: List[Any],
        is_browser: bool
    ) -> None:
        """Create Tornado HTTP 402 Payment Required response.
        
        Note: Unlike other adapters, this modifies the handler directly
        instead of returning a response object, as that's how Tornado works.
        
        Args:
            handler: Tornado RequestHandler instance
            error: Error message explaining why payment is required
            requirements: List of payment requirement dicts
            is_browser: Whether the request appears to be from a web browser
        """
        handler.set_status(402)
        
        if is_browser:
            # Return HTML paywall for browsers
            html_content = self._get_fallback_paywall_html(error)
            handler.set_header('Content-Type', 'text/html; charset=utf-8')
            handler.write(html_content)
            handler.finish()
        else:
            # Return JSON for API clients (Solana format)
            response_data = {
                'x402Version': 1,
                'accepts': [r.dict() if hasattr(r, 'dict') else r for r in requirements],
                'error': error,
            }
            handler.set_header('Content-Type', 'application/json')
            handler.write(response_data)
            handler.finish()
    
    def add_payment_response_header(
        self, 
        handler: RequestHandler, 
        header_value: str
    ) -> RequestHandler:
        """Add X-PAYMENT-RESPONSE header to Tornado response.
        
        Args:
            handler: Tornado RequestHandler instance
            header_value: Base64-encoded settlement result
            
        Returns:
            Modified handler (for compatibility with interface)
        """
        handler.set_header('X-PAYMENT-RESPONSE', header_value)
        return handler
    
    def is_success_response(self, handler: RequestHandler) -> bool:
        """Check if Tornado response status code indicates success (2xx).
        
        Args:
            handler: Tornado RequestHandler instance
            
        Returns:
            True if status code is 200-299, False otherwise
        """
        status_code = handler.get_status()
        return 200 <= status_code < 300
    
    def _get_fallback_paywall_html(self, error: str) -> str:
        """Generate simple HTML paywall.
        
        Args:
            error: Error message to display
            
        Returns:
            HTML content for paywall page
        """
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Payment Required</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            background: white;
            padding: 3rem;
            border-radius: 1rem;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            text-align: center;
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 1rem;
        }}
        .error {{
            color: #666;
            margin: 1rem 0;
        }}
        .code {{
            font-size: 4rem;
            font-weight: bold;
            color: #667eea;
            margin: 1rem 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="code">402</div>
        <h1>Payment Required</h1>
        <p class="error">{error}</p>
        <p>This resource requires payment to access.</p>
    </div>
</body>
</html>
        """.strip()

