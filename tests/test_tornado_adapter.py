"""Tests for Tornado adapter."""

import pytest
from unittest.mock import Mock, MagicMock
from tornado import web

from x402_connector.tornado.adapter import TornadoAdapter
from x402_connector.core.context import RequestContext


@pytest.fixture
def adapter():
    """Create TornadoAdapter instance."""
    return TornadoAdapter()


def create_mock_handler(path='/api/test', method='GET', headers=None):
    """Create a mock Tornado RequestHandler for testing."""
    if headers is None:
        headers = {}
    
    handler = Mock(spec=web.RequestHandler)
    handler.request = Mock()
    handler.request.path = path
    handler.request.method = method
    
    # Create mock headers object with dict-like methods
    mock_headers = Mock()
    mock_headers.get = Mock(side_effect=lambda k: headers.get(k))
    mock_headers.get_all = Mock(return_value=list(headers.items()))
    
    handler.request.headers = mock_headers
    handler.request.full_url = Mock(return_value=f'http://example.com{path}')
    handler._status_code = 200
    handler._headers = {}
    
    # Mock methods
    handler.get_status = Mock(return_value=handler._status_code)
    handler.set_status = Mock(side_effect=lambda code: setattr(handler, '_status_code', code))
    handler.set_header = Mock(side_effect=lambda k, v: handler._headers.__setitem__(k, v))
    handler.write = Mock()
    handler.finish = Mock()
    
    return handler


class TestTornadoAdapter:
    """Test Tornado adapter functionality."""
    
    def test_extract_request_context(self, adapter):
        """Test extracting request context from Tornado RequestHandler."""
        headers = {'X-Payment': 'test_payment', 'User-Agent': 'test'}
        handler = create_mock_handler(path='/api/test', method='POST', headers=headers)
        
        # Extract context
        context = adapter.extract_request_context(handler)
        
        assert isinstance(context, RequestContext)
        assert context.path == '/api/test'
        assert context.method == 'POST'
        assert context.payment_header == 'test_payment'
        assert 'User-Agent' in context.headers
        assert context.headers['User-Agent'] == 'test'
    
    def test_extract_request_context_no_payment(self, adapter):
        """Test extracting context without payment header."""
        handler = create_mock_handler(path='/api/test', method='GET')
        
        context = adapter.extract_request_context(handler)
        
        assert context.payment_header is None
    
    def test_create_payment_required_response_json(self, adapter):
        """Test creating JSON 402 response."""
        requirements = [
            {
                'network': 'solana-devnet',
                'asset': 'USDC',
                'maxAmountRequired': '10000'
            }
        ]
        
        handler = create_mock_handler()
        
        # Create response
        adapter.create_payment_required_response(
            handler,
            error='Payment required',
            requirements=requirements,
            is_browser=False
        )
        
        # Check handler state
        handler.set_status.assert_called_with(402)
        handler.write.assert_called_once()
        handler.finish.assert_called_once()
    
    def test_create_payment_required_response_html(self, adapter):
        """Test creating HTML 402 response for browsers."""
        requirements = [
            {
                'network': 'solana-devnet',
                'asset': 'USDC',
                'maxAmountRequired': '10000'
            }
        ]
        
        handler = create_mock_handler()
        
        # Create response
        adapter.create_payment_required_response(
            handler,
            error='Payment required',
            requirements=requirements,
            is_browser=True
        )
        
        # Check handler state
        handler.set_status.assert_called_with(402)
        handler.set_header.assert_any_call('Content-Type', 'text/html; charset=utf-8')
        handler.write.assert_called_once()
        handler.finish.assert_called_once()
    
    def test_add_payment_response_header(self, adapter):
        """Test adding X-PAYMENT-RESPONSE header."""
        handler = create_mock_handler()
        
        # Add header
        adapter.add_payment_response_header(handler, 'test_settlement_data')
        
        # Verify header was added
        handler.set_header.assert_called_with('X-PAYMENT-RESPONSE', 'test_settlement_data')
    
    def test_is_success_response(self, adapter):
        """Test checking if response is successful."""
        # Test 200 OK
        handler_200 = create_mock_handler()
        handler_200.get_status = Mock(return_value=200)
        assert adapter.is_success_response(handler_200) is True
        
        # Test 201 Created
        handler_201 = create_mock_handler()
        handler_201.get_status = Mock(return_value=201)
        assert adapter.is_success_response(handler_201) is True
        
        # Test 404 Not Found
        handler_404 = create_mock_handler()
        handler_404.get_status = Mock(return_value=404)
        assert adapter.is_success_response(handler_404) is False
        
        # Test 500 Internal Server Error
        handler_500 = create_mock_handler()
        handler_500.get_status = Mock(return_value=500)
        assert adapter.is_success_response(handler_500) is False
    
    def test_absolute_url_extraction(self, adapter):
        """Test that absolute URL is properly extracted."""
        handler = create_mock_handler(path='/api/test')
        handler.request.full_url = Mock(return_value='http://example.com/api/test?param=value')
        
        context = adapter.extract_request_context(handler)
        
        assert 'example.com' in context.absolute_url
        assert '/api/test' in context.absolute_url

