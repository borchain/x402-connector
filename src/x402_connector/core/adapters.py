"""Base adapter interface for framework integrations."""

from abc import ABC, abstractmethod
from typing import Any, List

from .context import RequestContext


class BaseAdapter(ABC):
    """Base adapter interface that all framework adapters must implement.
    
    This interface defines the contract between the core payment processor
    (framework-agnostic) and framework-specific code (Django, Flask, FastAPI, etc.).
    
    Each framework adapter translates between framework-specific types
    (HttpRequest, Response, etc.) and our core abstractions (RequestContext,
    ProcessingResult, etc.).
    
    Example:
        >>> class MyFrameworkAdapter(BaseAdapter):
        ...     def extract_request_context(self, request):
        ...         return RequestContext(
        ...             path=request.path,
        ...             method=request.method,
        ...             headers=dict(request.headers),
        ...             absolute_url=request.build_absolute_uri(),
        ...             payment_header=request.headers.get('X-Payment')
        ...         )
        ...     
        ...     def create_payment_required_response(self, error, requirements, is_browser):
        ...         # Return framework-specific 402 response
        ...         pass
        ...     
        ...     # ... implement other methods
    """
    
    @abstractmethod
    def extract_request_context(self, request: Any) -> RequestContext:
        """Extract framework-agnostic request context from framework request.
        
        This method takes a framework-specific request object (Django's HttpRequest,
        Flask's Request, FastAPI's Request, etc.) and extracts the information
        needed for payment processing into a RequestContext.
        
        Args:
            request: Framework-specific request object
            
        Returns:
            RequestContext with path, method, headers, and payment header
            
        Example:
            >>> adapter = DjangoAdapter()
            >>> context = adapter.extract_request_context(django_request)
            >>> print(context.path)
            '/api/premium/data'
        """
        pass
    
    @abstractmethod
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[Any],
        is_browser: bool
    ) -> Any:
        """Create HTTP 402 Payment Required response in framework-specific format.
        
        When payment is missing or invalid, this method creates an appropriate
        402 response. For browser requests (detected via Accept and User-Agent
        headers), return an HTML paywall. For API requests, return JSON.
        
        Args:
            error: Error message explaining why payment is required
            requirements: List of PaymentRequirements objects
            is_browser: Whether the request appears to be from a web browser
            
        Returns:
            Framework-specific response object with status code 402
            
        Example:
            >>> adapter = DjangoAdapter()
            >>> response = adapter.create_payment_required_response(
            ...     error='Payment required',
            ...     requirements=[payment_requirements],
            ...     is_browser=False
            ... )
            >>> print(response.status_code)
            402
        """
        pass
    
    @abstractmethod
    def add_payment_response_header(self, response: Any, header_value: str) -> Any:
        """Add X-PAYMENT-RESPONSE header to successful response.
        
        After successful payment settlement, add the base64-encoded settlement
        result to the response headers so the client can verify the transaction.
        
        Args:
            response: Framework-specific response object
            header_value: Base64-encoded settlement result
            
        Returns:
            Modified response with X-PAYMENT-RESPONSE header added
            
        Example:
            >>> adapter = DjangoAdapter()
            >>> response = adapter.add_payment_response_header(
            ...     response,
            ...     'eyJ0cmFuc2FjdGlvbiI6IjB4YWJjMTIzIn0='
            ... )
            >>> print(response['X-PAYMENT-RESPONSE'])
            'eyJ0cmFuc2FjdGlvbiI6IjB4YWJjMTIzIn0='
        """
        pass
    
    @abstractmethod
    def is_success_response(self, response: Any) -> bool:
        """Check if response status code indicates success (2xx).
        
        Payment settlement only happens for successful responses. This method
        checks if the response from the protected endpoint was successful.
        
        Args:
            response: Framework-specific response object
            
        Returns:
            True if status code is 200-299, False otherwise
            
        Example:
            >>> adapter = DjangoAdapter()
            >>> print(adapter.is_success_response(response_200))
            True
            >>> print(adapter.is_success_response(response_404))
            False
        """
        pass

