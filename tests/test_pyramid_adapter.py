"""Tests for Pyramid adapter."""

import pytest
from pyramid.testing import DummyRequest
from pyramid.response import Response

from x402_connector.pyramid.adapter import PyramidAdapter
from x402_connector.core.context import RequestContext


@pytest.fixture
def adapter():
    """Create PyramidAdapter instance."""
    return PyramidAdapter()


def test_extract_request_context(adapter):
    """Test extracting request context from Pyramid Request."""
    from pyramid.request import Request
    from io import BytesIO
    
    # Create a proper WSGI environ
    environ = {
        'REQUEST_METHOD': 'POST',
        'PATH_INFO': '/api/test',
        'SERVER_NAME': 'example.com',
        'SERVER_PORT': '80',
        'wsgi.url_scheme': 'http',
        'wsgi.input': BytesIO(),
        'HTTP_X_PAYMENT': 'test_payment',
        'HTTP_USER_AGENT': 'test'
    }
    
    request = Request(environ)
    
    context = adapter.extract_request_context(request)
    
    assert isinstance(context, RequestContext)
    assert context.path == '/api/test'
    assert context.method == 'POST'
    assert context.payment_header == 'test_payment'
    assert 'User-Agent' in context.headers


def test_extract_request_context_no_payment(adapter):
    """Test extracting context without payment header."""
    request = DummyRequest(path='/api/test')
    request.method = 'GET'
    request.url = 'http://example.com/api/test'
    
    context = adapter.extract_request_context(request)
    
    assert context.payment_header is None


def test_create_payment_required_response_json(adapter):
    """Test creating JSON 402 response."""
    requirements = [
        {
            'network': 'solana-devnet',
            'asset': 'USDC',
            'maxAmountRequired': '10000'
        }
    ]
    
    response = adapter.create_payment_required_response(
        error='Payment required',
        requirements=requirements,
        is_browser=False
    )
    
    assert isinstance(response, Response)
    assert response.status_code == 402
    assert response.content_type == 'application/json'
    
    import json
    data = json.loads(response.body)
    assert data['x402Version'] == 1
    assert data['error'] == 'Payment required'
    assert len(data['accepts']) == 1
    assert data['accepts'][0]['network'] == 'solana-devnet'


def test_create_payment_required_response_html(adapter):
    """Test creating HTML 402 response for browsers."""
    requirements = [
        {
            'network': 'solana-devnet',
            'asset': 'USDC',
            'maxAmountRequired': '10000'
        }
    ]
    
    response = adapter.create_payment_required_response(
        error='Payment required',
        requirements=requirements,
        is_browser=True
    )
    
    assert isinstance(response, Response)
    assert response.status_code == 402
    assert 'text/html' in response.content_type
    assert b'402' in response.body
    assert b'Payment Required' in response.body
    assert b'Payment required' in response.body


def test_add_payment_response_header(adapter):
    """Test adding X-PAYMENT-RESPONSE header."""
    response = Response('test content')
    
    modified = adapter.add_payment_response_header(
        response,
        'test_settlement_data'
    )
    
    assert 'X-PAYMENT-RESPONSE' in modified.headers
    assert modified.headers['X-PAYMENT-RESPONSE'] == 'test_settlement_data'


def test_is_success_response(adapter):
    """Test checking if response is successful."""
    # Test 200 OK
    response_200 = Response('ok')
    response_200.status_code = 200
    assert adapter.is_success_response(response_200) is True
    
    # Test 201 Created
    response_201 = Response('created')
    response_201.status_code = 201
    assert adapter.is_success_response(response_201) is True
    
    # Test 404 Not Found
    response_404 = Response('not found')
    response_404.status_code = 404
    assert adapter.is_success_response(response_404) is False
    
    # Test 500 Internal Server Error
    response_500 = Response('error')
    response_500.status_code = 500
    assert adapter.is_success_response(response_500) is False


def test_absolute_url_extraction(adapter):
    """Test that absolute URL is properly extracted."""
    request = DummyRequest(
        path='/api/test',
        params={'param': 'value'}
    )
    request.method = 'GET'
    request.url = 'http://example.com/api/test?param=value'
    
    context = adapter.extract_request_context(request)
    
    assert 'example.com' in context.absolute_url
    assert '/api/test' in context.absolute_url

