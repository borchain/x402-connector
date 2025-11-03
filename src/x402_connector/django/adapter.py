"""Django framework adapter for x402-connector."""

from typing import Any, Dict, List

from django.http import HttpRequest, HttpResponse, JsonResponse

from ..core.adapters import BaseAdapter
from ..core.context import RequestContext


class DjangoAdapter(BaseAdapter):
    """Django framework adapter.
    
    Translates between Django's HttpRequest/HttpResponse objects and
    the framework-agnostic RequestContext/responses used by the core processor.
    
    Example:
        >>> adapter = DjangoAdapter()
        >>> context = adapter.extract_request_context(request)
        >>> response = adapter.create_payment_required_response(
        ...     error='Payment required',
        ...     requirements=[...],
        ...     is_browser=False
        ... )
    """
    
    def extract_request_context(self, request: HttpRequest) -> RequestContext:
        """Extract request context from Django HttpRequest.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            RequestContext with path, method, headers, and payment header
        """
        return RequestContext(
            path=request.path,
            method=request.method,
            headers=dict(request.headers),
            absolute_url=request.build_absolute_uri(),
            payment_header=request.META.get('HTTP_X_PAYMENT')
        )
    
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[Any],
        is_browser: bool
    ) -> HttpResponse:
        """Create Django HTTP 402 Payment Required response.
        
        Args:
            error: Error message explaining why payment is required
            requirements: List of PaymentRequirements objects
            is_browser: Whether the request appears to be from a web browser
            
        Returns:
            Django HttpResponse with status code 402
        """
        try:
            from x402.paywall import get_paywall_html
            from x402.common import x402_VERSION
            from x402.types import x402PaymentRequiredResponse
        except ImportError:
            # Fallback if x402 package not available
            if is_browser:
                html_content = self._get_fallback_paywall_html(error)
                return HttpResponse(
                    html_content,
                    status=402,
                    content_type='text/html; charset=utf-8'
                )
            else:
                response_data = {
                    'x402Version': 1,
                    'accepts': [r.dict() if hasattr(r, 'dict') else r for r in requirements],
                    'error': error,
                }
                return JsonResponse(response_data, status=402)
        
        if is_browser:
            html_content = get_paywall_html(error, requirements, None)
            return HttpResponse(
                html_content,
                status=402,
                content_type='text/html; charset=utf-8'
            )
        
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=requirements,
            error=error,
        ).model_dump(by_alias=True)
        
        return JsonResponse(response_data, status=402)
    
    def add_payment_response_header(
        self, 
        response: HttpResponse, 
        header_value: str
    ) -> HttpResponse:
        """Add X-PAYMENT-RESPONSE header to Django response.
        
        Args:
            response: Django HttpResponse object
            header_value: Base64-encoded settlement result
            
        Returns:
            Modified response with X-PAYMENT-RESPONSE header added
        """
        response['X-PAYMENT-RESPONSE'] = header_value
        return response
    
    def is_success_response(self, response: HttpResponse) -> bool:
        """Check if Django response status code indicates success (2xx).
        
        Args:
            response: Django HttpResponse object
            
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

