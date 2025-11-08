"""Tests for Pyramid middleware (tween)."""

import pytest
from pyramid import testing
from pyramid.config import Configurator
from pyramid.response import Response
from webtest import TestApp

from x402_connector.pyramid import require_payment, includeme
from x402_connector.core.config import X402Config


def free_view(request):
    """View without payment requirement."""
    import json
    response = Response(json.dumps({'data': 'free'}))
    response.content_type = 'application/json'
    return response


@require_payment(price='$0.01')
def premium_view(request):
    """View with payment requirement."""
    import json
    response = Response(json.dumps({'data': 'premium'}))
    response.content_type = 'application/json'
    return response


@pytest.fixture
def testapp():
    """Create test Pyramid application with x402 tween."""
    settings = {
        'x402.pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'x402.price': '$0.01',
        'x402.network': 'solana-devnet',
        'x402.protected_paths': [],
        'x402.debug_mode': 'True',
    }
    
    config = Configurator(settings=settings)
    config.include('x402_connector.pyramid')
    
    # Add routes
    config.add_route('free', '/free')
    config.add_route('premium', '/premium')
    
    # Add views
    config.add_view(free_view, route_name='free')
    config.add_view(premium_view, route_name='premium')
    
    app = config.make_wsgi_app()
    return TestApp(app)


def test_free_endpoint_no_payment(testapp):
    """Test that free endpoint works without payment."""
    response = testapp.get('/free')
    
    assert response.status_code == 200
    assert b'free' in response.body


def test_protected_endpoint_no_payment(testapp):
    """Test that protected endpoint returns 402 without payment."""
    response = testapp.get('/premium', status=402)
    
    assert response.status_code == 402
    assert b'x402Version' in response.body or b'Payment Required' in response.body


def test_protected_endpoint_invalid_payment(testapp):
    """Test that protected endpoint rejects invalid payment."""
    response = testapp.get(
        '/premium',
        headers={'X-Payment': 'invalid_payment_data'},
        status=402
    )
    
    assert response.status_code == 402


def test_includeme_configuration():
    """Test that includeme hook configures x402 correctly."""
    settings = {
        'x402.pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'x402.price': '$0.01',
        'x402.network': 'solana-devnet',
    }
    
    config = Configurator(settings=settings)
    config.include('x402_connector.pyramid')
    
    # Check that processor and adapter were configured
    assert 'x402_processor' in config.registry.settings
    assert 'x402_adapter' in config.registry.settings
    assert 'x402_config_obj' in config.registry.settings
    
    # Check config object
    x402_config = config.registry.settings['x402_config_obj']
    assert isinstance(x402_config, X402Config)
    assert x402_config.pay_to_address == 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK'
    assert x402_config.price == '$0.01'
    assert x402_config.network == 'solana-devnet'


def test_includeme_without_config():
    """Test that includeme handles missing configuration gracefully."""
    config = Configurator(settings={})
    
    # Should not raise an error, just log a warning
    config.include('x402_connector.pyramid')
    
    # Processor should not be configured
    assert 'x402_processor' not in config.registry.settings


def test_is_browser_request():
    """Test browser detection logic."""
    from x402_connector.pyramid.middleware import is_browser_request
    
    # Test with HTML accept header
    headers = {'Accept': 'text/html,application/xhtml+xml'}
    assert is_browser_request(headers) is True
    
    # Test with JSON accept header
    headers = {'Accept': 'application/json'}
    assert is_browser_request(headers) is False
    
    # Test with browser user agent
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    assert is_browser_request(headers) is True
    
    # Test with API client user agent
    headers = {'User-Agent': 'python-requests/2.28.0'}
    assert is_browser_request(headers) is False


def test_tween_factory():
    """Test tween factory creation."""
    from x402_connector.pyramid.middleware import x402_tween_factory
    
    settings = {
        'x402.pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'x402.price': '$0.01',
        'x402.network': 'solana-devnet',
    }
    
    config = Configurator(settings=settings)
    config.include('x402_connector.pyramid')
    
    # Test that tween factory was registered
    def mock_handler(request):
        return Response('test')
    
    tween = x402_tween_factory(mock_handler, config.registry)
    
    # Should return a tween instance or the handler
    assert tween is not None


def test_decorator_without_config():
    """Test that decorator handles missing configuration gracefully."""
    # Create a request without x402 configured
    request = testing.DummyRequest()
    request.registry.settings = {}
    
    # Try to call a protected view
    response = premium_view(request)
    
    # Should return error response
    assert response.status_code == 500
    assert b'x402 tween not configured' in response.body

