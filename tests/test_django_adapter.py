"""Tests for Django adapter."""

import pytest
from unittest.mock import Mock

pytest.importorskip('django')

from django.http import HttpRequest
from x402_connector.django.adapter import DjangoAdapter
from x402_connector.core.context import RequestContext


class TestDjangoAdapter:
    """Tests for DjangoAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return DjangoAdapter()
    
    def test_extract_request_context(self, adapter):
        """Test extracting request context from Django request."""
        # Create mock Django request
        request = HttpRequest()
        request.path = '/api/premium/data'
        request.method = 'GET'
        request.META = {
            'HTTP_X_PAYMENT': 'base64_payment_data',
            'HTTP_USER_AGENT': 'TestClient',
        }
        
        # Mock build_absolute_uri
        request.build_absolute_uri = Mock(return_value='http://testserver/api/premium/data')
        
        # Mock headers property (Django 4.2+)
        request.headers = {
            'X-Payment': 'base64_payment_data',
            'User-Agent': 'TestClient',
        }
        
        context = adapter.extract_request_context(request)
        
        assert isinstance(context, RequestContext)
        assert context.path == '/api/premium/data'
        assert context.method == 'GET'
        assert context.payment_header == 'base64_payment_data'
        assert context.absolute_url == 'http://testserver/api/premium/data'
    
    def test_extract_request_context_without_payment(self, adapter):
        """Test extracting context when no payment header."""
        request = HttpRequest()
        request.path = '/api/public/info'
        request.method = 'POST'
        request.META = {}
        request.build_absolute_uri = Mock(return_value='http://testserver/api/public/info')
        request.headers = {}
        
        context = adapter.extract_request_context(request)
        
        assert context.path == '/api/public/info'
        assert context.method == 'POST'
        assert context.payment_header is None
    
    def test_create_payment_required_response_json(self, adapter):
        """Test creating JSON 402 response."""
        # Use fallback mode (when x402 package not available)
        error = 'Payment required'
        requirements = []  # Empty list uses fallback
        
        response = adapter.create_payment_required_response(
            error=error,
            requirements=requirements,
            is_browser=False
        )
        
        assert response.status_code == 402
        assert 'application/json' in response['Content-Type']
        
        # Parse JSON response
        import json
        data = json.loads(response.content.decode())
        assert 'x402Version' in data or 'error' in data
    
    def test_create_payment_required_response_html(self, adapter):
        """Test creating HTML paywall response."""
        error = 'Payment required'
        requirements = []
        
        response = adapter.create_payment_required_response(
            error=error,
            requirements=requirements,
            is_browser=True
        )
        
        assert response.status_code == 402
        assert 'text/html' in response['Content-Type']
        
        # Check HTML content
        content = response.content.decode()
        assert '<html' in content.lower()
        assert '402' in content
    
    def test_add_payment_response_header(self, adapter):
        """Test adding payment response header."""
        from django.http import JsonResponse
        
        response = JsonResponse({'data': 'test'})
        header_value = 'encoded_settlement_data'
        
        modified = adapter.add_payment_response_header(response, header_value)
        
        assert modified['X-PAYMENT-RESPONSE'] == header_value
        assert modified is response  # Same object modified
    
    def test_is_success_response_200(self, adapter):
        """Test success detection for 200 response."""
        from django.http import JsonResponse
        
        response = JsonResponse({'data': 'test'})
        response.status_code = 200
        
        assert adapter.is_success_response(response) is True
    
    def test_is_success_response_201(self, adapter):
        """Test success detection for 201 response."""
        from django.http import JsonResponse
        
        response = JsonResponse({'data': 'test'})
        response.status_code = 201
        
        assert adapter.is_success_response(response) is True
    
    def test_is_success_response_404(self, adapter):
        """Test success detection for 404 response."""
        from django.http import JsonResponse
        
        response = JsonResponse({'error': 'not found'})
        response.status_code = 404
        
        assert adapter.is_success_response(response) is False
    
    def test_is_success_response_500(self, adapter):
        """Test success detection for 500 response."""
        from django.http import JsonResponse
        
        response = JsonResponse({'error': 'server error'})
        response.status_code = 500
        
        assert adapter.is_success_response(response) is False

