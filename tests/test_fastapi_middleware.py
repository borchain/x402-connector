"""Tests for FastAPI middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from x402_connector.fastapi import X402Middleware, require_payment


@pytest.fixture
def app():
    """Create FastAPI app."""
    return FastAPI()


@pytest.fixture
def configured_app():
    """Create FastAPI app with x402 configuration."""
    app = FastAPI()
    
    app.add_middleware(
        X402Middleware,
        pay_to_address='DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        price='$0.01',
        network='solana-devnet',
        debug_mode=True,
        protected_paths=[],  # Empty - use decorator only
    )
    
    return app


def test_middleware_initialization(configured_app):
    """Test X402 middleware initialization."""
    # Middleware is initialized via add_middleware
    # We can test by checking routes work
    @configured_app.get('/test')
    async def test_route():
        return {'test': 'ok'}
    
    client = TestClient(configured_app)
    response = client.get('/test')
    
    assert response.status_code == 200


def test_middleware_without_config(app):
    """Test X402 middleware without configuration."""
    # Add middleware without config
    app.add_middleware(X402Middleware)
    
    @app.get('/test')
    async def test_route():
        return {'test': 'ok'}
    
    client = TestClient(app)
    response = client.get('/test')
    
    # Should still work, just middleware is disabled
    assert response.status_code == 200


def test_free_endpoint_no_payment_required():
    """Test that free endpoints work without payment."""
    app = FastAPI()
    
    app.add_middleware(
        X402Middleware,
        pay_to_address='DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        price='$0.01',
        network='solana-devnet',
        debug_mode=True,
        protected_paths=[],  # Empty - no paths protected
    )
    
    @app.get('/free')
    async def free_endpoint():
        return {'data': 'free'}
    
    client = TestClient(app)
    response = client.get('/free')
    
    assert response.status_code == 200
    data = response.json()
    assert data['data'] == 'free'


def test_protected_endpoint_decorator(configured_app):
    """Test protected endpoint with @require_payment decorator."""
    @configured_app.get('/premium')
    @require_payment(price='$0.01')
    async def premium_endpoint(request: Request):
        return {'data': 'premium'}
    
    client = TestClient(configured_app)
    
    # Request without payment should return 402
    response = client.get('/premium')
    assert response.status_code == 402
    
    data = response.json()
    assert 'x402Version' in data
    assert 'accepts' in data


def test_protected_endpoint_with_invalid_payment(configured_app):
    """Test protected endpoint with invalid payment."""
    @configured_app.get('/premium')
    @require_payment(price='$0.01')
    async def premium_endpoint(request: Request):
        return {'data': 'premium'}
    
    client = TestClient(configured_app)
    
    # Request with invalid payment
    response = client.get(
        '/premium',
        headers={'X-Payment': '{"invalid": "payment"}'}
    )
    
    assert response.status_code == 402


def test_decorator_without_middleware():
    """Test decorator returns error when middleware not configured."""
    # Reset processor to simulate no middleware
    from x402_connector.fastapi.decorators import set_processor
    set_processor(None)
    
    app = FastAPI()
    
    @app.get('/premium')
    @require_payment(price='$0.01')
    async def premium_endpoint(request: Request):
        return {'data': 'premium'}
    
    client = TestClient(app)
    response = client.get('/premium')
    
    assert response.status_code == 500
    data = response.json()
    assert 'error' in data
    assert 'not configured' in data['error']


def test_custom_price_in_decorator():
    """Test decorator with custom price."""
    app = FastAPI()
    
    app.add_middleware(
        X402Middleware,
        pay_to_address='DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        price='$0.01',  # Default price
        network='solana-devnet',
        debug_mode=True,
        protected_paths=[],  # Don't let middleware interfere
    )
    
    @app.get('/expensive')
    @require_payment(price='$1.00')  # Custom price
    async def expensive_endpoint(request: Request):
        return {'data': 'expensive'}
    
    client = TestClient(app)
    response = client.get('/expensive')
    
    assert response.status_code == 402
    data = response.json()
    
    # Check that requirements reflect custom price
    assert 'accepts' in data
    # Price conversion: $1.00 = 1000000 atomic units (USDC has 6 decimals)
    assert data['accepts'][0]['maxAmountRequired'] == '1000000'


def test_custom_description_in_decorator(configured_app):
    """Test decorator with custom description."""
    @configured_app.get('/ai')
    @require_payment(price='$0.10', description='AI Inference')
    async def ai_endpoint(request: Request):
        return {'result': 'AI output'}
    
    client = TestClient(configured_app)
    response = client.get('/ai')
    
    assert response.status_code == 402


def test_async_route_support():
    """Test that async routes work properly."""
    app = FastAPI()
    
    app.add_middleware(
        X402Middleware,
        pay_to_address='DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        price='$0.01',
        network='solana-devnet',
        debug_mode=True,
        protected_paths=[],
    )
    
    @app.get('/async')
    async def async_endpoint():
        return {'async': True}
    
    client = TestClient(app)
    response = client.get('/async')
    
    assert response.status_code == 200
    data = response.json()
    assert data['async'] is True

