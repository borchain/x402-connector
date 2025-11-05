"""Tests for FastAPI adapter."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from x402_connector.fastapi.adapter import FastAPIAdapter
from x402_connector.core.context import RequestContext


@pytest.fixture
def adapter():
    """Create FastAPIAdapter instance."""
    return FastAPIAdapter()


@pytest.fixture
def fastapi_app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_route():
        return {"test": "ok"}
    
    return app


@pytest.fixture
def client(fastapi_app):
    """Create test client."""
    return TestClient(fastapi_app)


def test_extract_request_context(adapter, fastapi_app, client):
    """Test extracting request context from FastAPI Request."""
    @fastapi_app.post("/api/test")
    async def test_endpoint(request: Request):
        context = adapter.extract_request_context(request)
        return {
            "path": context.path,
            "method": context.method,
            "payment_header": context.payment_header,
        }
    
    response = client.post(
        "/api/test",
        headers={'X-Payment': 'test_payment', 'User-Agent': 'test'}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['path'] == '/api/test'
    assert data['method'] == 'POST'
    assert data['payment_header'] == 'test_payment'


def test_extract_request_context_no_payment(adapter, fastapi_app, client):
    """Test extracting context without payment header."""
    @fastapi_app.get("/api/test")
    async def test_endpoint(request: Request):
        context = adapter.extract_request_context(request)
        return {"payment_header": context.payment_header}
    
    response = client.get("/api/test")
    
    assert response.status_code == 200
    data = response.json()
    assert data['payment_header'] is None


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
    
    assert response.status_code == 402
    assert response.headers['content-type'] == 'application/json'
    
    # Parse JSON body
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
    
    assert response.status_code == 402
    assert 'text/html' in response.headers['content-type']
    assert b'402' in response.body
    assert b'Payment Required' in response.body
    assert b'Payment required' in response.body


def test_add_payment_response_header(adapter):
    """Test adding X-PAYMENT-RESPONSE header."""
    from fastapi.responses import JSONResponse
    
    response = JSONResponse(content={'test': 'content'})
    
    modified = adapter.add_payment_response_header(
        response,
        'test_settlement_data'
    )
    
    assert 'x-payment-response' in modified.headers
    assert modified.headers['x-payment-response'] == 'test_settlement_data'


def test_is_success_response(adapter):
    """Test checking if response is successful."""
    from fastapi.responses import JSONResponse, Response
    
    # Test 200 OK
    response_200 = JSONResponse(content={'ok': True})
    assert adapter.is_success_response(response_200) is True
    
    # Test 201 Created
    response_201 = Response(status_code=201)
    assert adapter.is_success_response(response_201) is True
    
    # Test 404 Not Found
    response_404 = Response(status_code=404)
    assert adapter.is_success_response(response_404) is False
    
    # Test 500 Internal Server Error
    response_500 = Response(status_code=500)
    assert adapter.is_success_response(response_500) is False


def test_absolute_url_extraction(adapter, fastapi_app, client):
    """Test that absolute URL is properly extracted."""
    @fastapi_app.get("/api/test")
    async def test_endpoint(request: Request):
        context = adapter.extract_request_context(request)
        return {"absolute_url": context.absolute_url}
    
    response = client.get("/api/test?param=value")
    
    assert response.status_code == 200
    data = response.json()
    assert '/api/test' in data['absolute_url']
    assert 'param=value' in data['absolute_url']

