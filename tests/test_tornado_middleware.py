"""Tests for Tornado middleware."""

import pytest
from tornado.testing import AsyncHTTPTestCase
from tornado import web, ioloop
from tornado.httpclient import HTTPRequest

from x402_connector.tornado import X402Middleware, require_payment
from x402_connector.core.config import X402Config


class FreeHandler(web.RequestHandler):
    """Handler without payment requirement."""
    
    x402_skip = True
    
    def get(self):
        self.write({'data': 'free'})


class ProtectedHandler(web.RequestHandler):
    """Handler with payment requirement."""
    
    @require_payment(price='$0.01')
    async def get(self):
        self.write({'data': 'premium'})


class TestTornadoMiddleware(AsyncHTTPTestCase):
    """Test Tornado middleware integration."""
    
    def get_app(self):
        """Create Tornado application with x402 middleware."""
        x402_config = {
            'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
            'price': '$0.01',
            'network': 'solana-devnet',
            'protected_paths': [],
            'debug_mode': True,
        }
        
        app = web.Application(
            [
                (r'/free', FreeHandler),
                (r'/premium', ProtectedHandler),
            ],
            x402_config=x402_config
        )
        
        # Initialize middleware
        X402Middleware(app, **x402_config)
        
        return app
    
    def test_free_endpoint_no_payment(self):
        """Test that free endpoint works without payment."""
        response = self.fetch('/free')
        
        assert response.code == 200
        assert b'free' in response.body
    
    def test_protected_endpoint_no_payment(self):
        """Test that protected endpoint returns 402 without payment."""
        response = self.fetch('/premium')
        
        assert response.code == 402
        assert b'x402Version' in response.body or b'Payment Required' in response.body
    
    def test_protected_endpoint_invalid_payment(self):
        """Test that protected endpoint rejects invalid payment."""
        response = self.fetch(
            '/premium',
            method='GET',
            headers={'X-Payment': 'invalid_payment_data'}
        )
        
        assert response.code == 402
    
    def test_middleware_initialization(self):
        """Test that middleware initializes correctly."""
        x402_config = {
            'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
            'price': '$0.01',
            'network': 'solana-devnet',
            'protected_paths': [],
        }
        
        # Create app with at least one handler to avoid wrapping issues
        class DummyHandler(web.RequestHandler):
            def get(self):
                self.write({'test': 'ok'})
        
        app = web.Application([(r'/test', DummyHandler)], x402_config=x402_config)
        middleware = X402Middleware(app, **x402_config)
        
        assert middleware.enabled is True
        assert middleware.processor is not None
        assert middleware.adapter is not None
    
    def test_middleware_without_config(self):
        """Test that middleware handles missing configuration gracefully."""
        app = web.Application([])
        middleware = X402Middleware(app)
        
        assert middleware.enabled is False


def test_is_browser_request():
    """Test browser detection logic."""
    from x402_connector.tornado.middleware import is_browser_request
    
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

