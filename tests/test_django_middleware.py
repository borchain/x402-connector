"""Tests for Django middleware."""

import json
import base64
import pytest
from unittest.mock import Mock, patch

pytest.importorskip('django')

from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory
from x402_connector.django.middleware import X402Middleware, is_browser_request


class TestIsBrowserRequest:
    """Tests for browser detection."""
    
    def test_detects_html_accept(self):
        """Test detection via Accept header."""
        headers = {'Accept': 'text/html,application/xhtml+xml'}
        assert is_browser_request(headers) is True
    
    def test_detects_mozilla_user_agent(self):
        """Test detection via Mozilla user agent."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        assert is_browser_request(headers) is True
    
    def test_detects_chrome_user_agent(self):
        """Test detection via Chrome user agent."""
        headers = {'User-Agent': 'Chrome/91.0.4472.124'}
        assert is_browser_request(headers) is True
    
    def test_api_request_not_browser(self):
        """Test API clients not detected as browsers."""
        headers = {'Accept': 'application/json', 'User-Agent': 'python-requests/2.28'}
        assert is_browser_request(headers) is False


class TestX402Middleware:
    """Tests for X402Middleware."""
    
    @pytest.fixture
    def get_response(self):
        """Mock get_response callable."""
        def _get_response(request):
            return JsonResponse({'data': 'success'})
        return _get_response
    
    @pytest.fixture
    def settings_with_x402(self):
        """Mock Django settings with X402 config."""
        settings = Mock()
        settings.X402_CONFIG = {
            'network': 'solana-devnet',
            'price': '$0.01',
            'pay_to_address': 'TestSolanaAddress1234567890123456789012',
            'protected_paths': ['/api/premium/*'],
        }
        return settings
    
    def test_initialization_with_valid_config(self, get_response, settings_with_x402):
        """Test middleware initializes with valid config."""
        with patch('x402_connector.django.middleware.settings', settings_with_x402):
            middleware = X402Middleware(get_response)
            
            assert middleware.enabled is True
            assert middleware.config is not None
            assert middleware.processor is not None
            assert middleware.adapter is not None
    
    def test_initialization_without_config(self, get_response):
        """Test middleware handles missing config gracefully."""
        settings = Mock()
        settings.X402_CONFIG = None
        settings.X402 = {}
        
        with patch('x402_connector.django.middleware.settings', settings):
            middleware = X402Middleware(get_response)
            
            assert middleware.enabled is False
    
    def test_initialization_with_invalid_config(self, get_response):
        """Test middleware handles invalid config gracefully."""
        settings = Mock()
        settings.X402_CONFIG = {
            'network': '',  # Invalid - empty
            'price': '$0.01',
            'pay_to_address': '0x123',
        }
        
        with patch('x402_connector.django.middleware.settings', settings):
            middleware = X402Middleware(get_response)
            
            assert middleware.enabled is False
    
    def test_disabled_middleware_passes_through(self, get_response):
        """Test disabled middleware doesn't interfere."""
        settings = Mock()
        settings.X402_CONFIG = None
        settings.X402 = {}
        
        with patch('x402_connector.django.middleware.settings', settings):
            middleware = X402Middleware(get_response)
            
            request = HttpRequest()
            request.path = '/api/premium/data'
            
            response = middleware(request)
            
            # Should pass through without checking payment
            assert response.status_code == 200
    
    def test_unprotected_path_passes_through(self, get_response, settings_with_x402):
        """Test unprotected paths pass through."""
        with patch('x402_connector.django.middleware.settings', settings_with_x402):
            middleware = X402Middleware(get_response)
            
            request = HttpRequest()
            request.path = '/public/free'
            request.method = 'GET'
            request.META = {}
            request.headers = {}
            request.build_absolute_uri = Mock(return_value='http://test/public/free')
            
            response = middleware(request)
            
            # Should pass through
            assert response.status_code == 200
    
    def test_protected_path_without_payment_returns_402(self, get_response, settings_with_x402):
        """Test protected path without payment returns 402."""
        with patch('x402_connector.django.middleware.settings', settings_with_x402):
            middleware = X402Middleware(get_response)
            
            request = HttpRequest()
            request.path = '/api/premium/data'
            request.method = 'GET'
            request.META = {}
            request.headers = {}
            request.build_absolute_uri = Mock(return_value='http://test/api/premium/data')
            
            response = middleware(request)
            
            assert response.status_code == 402
    
    def test_protected_path_with_valid_payment_allows(self, get_response, settings_with_x402):
        """Test protected path with valid payment allows request."""
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'signature': '0xsig',
                'authorization': {
                    'from': '0xPAYER',
                    'to': 'TestSolanaAddress1234567890123456789012',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x01',
                },
            },
        }
        
        payment_header = base64.b64encode(json.dumps(payment).encode()).decode()
        
        with patch('x402_connector.django.middleware.settings', settings_with_x402):
            middleware = X402Middleware(get_response)
            
            # Mock the processor to return allow
            mock_processor = Mock()
            mock_processor.process_request = Mock(return_value=Mock(
                action='allow',
                payment_verified=True,
                payer_address='0xPAYER'
            ))
            mock_processor.settle_payment = Mock(return_value=Mock(
                success=True,
                encoded_response='encoded_settlement'
            ))
            middleware.processor = mock_processor
            
            request = HttpRequest()
            request.path = '/api/premium/data'
            request.method = 'GET'
            request.META = {'HTTP_X_PAYMENT': payment_header}
            request.headers = {'X-Payment': payment_header}
            request.build_absolute_uri = Mock(return_value='http://test/api/premium/data')
            
            response = middleware(request)
            
            assert response.status_code == 200
            assert response['X-PAYMENT-RESPONSE'] == 'encoded_settlement'
    
    def test_settlement_failure_with_block_policy(self, get_response, settings_with_x402):
        """Test settlement failure returns 402 with block-on-failure policy."""
        payment_header = base64.b64encode(b'{"x402Version":1}').decode()
        
        with patch('x402_connector.django.middleware.settings', settings_with_x402):
            middleware = X402Middleware(get_response)
            
            # Mock processor
            mock_processor = Mock()
            mock_processor.config = Mock(settle_policy='block-on-failure')
            mock_processor.process_request = Mock(return_value=Mock(
                action='allow',
                payment_verified=True,
                requirements=[]
            ))
            mock_processor.settle_payment = Mock(return_value=Mock(
                success=False,
                error='Settlement failed'
            ))
            middleware.processor = mock_processor
            
            request = HttpRequest()
            request.path = '/api/premium/data'
            request.method = 'GET'
            request.META = {'HTTP_X_PAYMENT': payment_header}
            request.headers = {'X-Payment': payment_header}
            request.build_absolute_uri = Mock(return_value='http://test/api/premium/data')
            
            response = middleware(request)
            
            # Should return 402 on settlement failure
            assert response.status_code == 402
    
    def test_settlement_failure_with_continue_policy(self, get_response, settings_with_x402):
        """Test settlement failure continues with log-and-continue policy."""
        payment_header = base64.b64encode(b'{"x402Version":1}').decode()
        
        # Update settings to use log-and-continue policy
        settings_with_x402.X402_CONFIG['settle_policy'] = 'log-and-continue'
        
        with patch('x402_connector.django.middleware.settings', settings_with_x402):
            middleware = X402Middleware(get_response)
            
            # Verify config has log-and-continue policy
            assert middleware.config.settle_policy == 'log-and-continue'
            
            # Mock processor
            from x402_connector.core.context import ProcessingResult, SettlementResult
            
            mock_processor = Mock()
            mock_processor.process_request = Mock(return_value=ProcessingResult(
                action='allow',
                payment_verified=True,
                requirements=[]
            ))
            mock_processor.settle_payment = Mock(return_value=SettlementResult(
                success=False,
                error='Settlement failed'
            ))
            middleware.processor = mock_processor
            
            request = HttpRequest()
            request.path = '/api/premium/data'
            request.method = 'GET'
            request.META = {'HTTP_X_PAYMENT': payment_header}
            request.headers = {'X-Payment': payment_header}
            request.build_absolute_uri = Mock(return_value='http://test/api/premium/data')
            
            response = middleware(request)
            
            # Should return 200 (continue despite settlement failure)
            assert response.status_code == 200
            # Should NOT have payment response header
            assert 'X-PAYMENT-RESPONSE' not in response

