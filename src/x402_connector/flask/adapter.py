"""Flask framework adapter for x402-connector."""

from typing import Any, Dict, List

from flask import Request, Response, jsonify, make_response

from ..core.adapters import BaseAdapter
from ..core.context import RequestContext


class FlaskAdapter(BaseAdapter):
    """Flask framework adapter.
    
    Translates between Flask's Request/Response objects and
    the framework-agnostic RequestContext/responses used by the core processor.
    
    Example:
        >>> adapter = FlaskAdapter()
        >>> context = adapter.extract_request_context(request)
        >>> response = adapter.create_payment_required_response(
        ...     error='Payment required',
        ...     requirements=[...],
        ...     is_browser=False
        ... )
    """
    
    def extract_request_context(self, request: Request) -> RequestContext:
        """Extract request context from Flask Request.
        
        Args:
            request: Flask Request object
            
        Returns:
            RequestContext with path, method, headers, and payment header
        """
        return RequestContext(
            path=request.path,
            method=request.method,
            headers=dict(request.headers),
            absolute_url=request.url,
            payment_header=request.headers.get('X-Payment')
        )
    
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[Any],
        is_browser: bool
    ) -> Response:
        """Create Flask HTTP 402 Payment Required response (Solana-specific).
        
        Args:
            error: Error message explaining why payment is required
            requirements: List of payment requirement dicts
            is_browser: Whether the request appears to be from a web browser
            
        Returns:
            Flask Response with status code 402
        """
        if is_browser:
            # Return HTML paywall for browsers
            html_content = self._get_fallback_paywall_html(error)
            response = make_response(html_content, 402)
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            return response
        
        # Return JSON for API clients (Solana format)
        response_data = {
            'x402Version': 1,
            'accepts': [r.dict() if hasattr(r, 'dict') else r for r in requirements],
            'error': error,
        }
        response = jsonify(response_data)
        response.status_code = 402
        return response
    
    def add_payment_response_header(
        self, 
        response: Response, 
        header_value: str
    ) -> Response:
        """Add X-PAYMENT-RESPONSE header to Flask response.
        
        Args:
            response: Flask Response object
            header_value: Base64-encoded settlement result
            
        Returns:
            Modified response with X-PAYMENT-RESPONSE header added
        """
        response.headers['X-PAYMENT-RESPONSE'] = header_value
        return response
    
    def is_success_response(self, response: Response) -> bool:
        """Check if Flask response status code indicates success (2xx).
        
        Args:
            response: Flask Response object
            
        Returns:
            True if status code is 200-299, False otherwise
        """
        return 200 <= response.status_code < 300
    
    def _get_fallback_paywall_html(self, error: str) -> str:
        """Generate simple HTML paywall when x402 package not available.
        
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

