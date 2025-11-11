"""Tests for Corbits facilitator."""

import pytest
from unittest.mock import Mock, patch
import requests

from x402_connector.core.facilitators.corbits import CorbitsFacilitator

# Test addresses
TEST_ADDRESS_FROM = 'TestFromAddress1234567890123456789ABC'
TEST_ADDRESS_TO = 'TestToAddress567890123456789012345678'


class TestCorbitsFacilitator:
    """Tests for CorbitsFacilitator."""
    
    def test_initialization(self):
        """Test facilitator initialization with defaults."""
        facilitator = CorbitsFacilitator()
        assert facilitator is not None
        assert facilitator.facilitator_url == 'https://api.corbits.dev'
        assert facilitator.timeout == 30
    
    def test_initialization_with_config(self):
        """Test facilitator initialization with custom config."""
        config = {
            'facilitator_url': 'https://custom.corbits.dev',
            'api_key_env': 'CUSTOM_KEY',
            'timeout': 60,
        }
        facilitator = CorbitsFacilitator(config=config)
        assert facilitator.facilitator_url == 'https://custom.corbits.dev'
        assert facilitator.timeout == 60
    
    @patch.dict('os.environ', {'CORBITS_API_KEY': 'test_api_key'})
    def test_get_headers_with_api_key(self):
        """Test headers include API key when available."""
        facilitator = CorbitsFacilitator()
        headers = facilitator._get_headers()
        
        assert headers['Authorization'] == 'Bearer test_api_key'
        assert headers['Content-Type'] == 'application/json'
        assert 'User-Agent' in headers
    
    def test_get_headers_without_api_key(self):
        """Test headers without API key (warning logged)."""
        facilitator = CorbitsFacilitator()
        headers = facilitator._get_headers()
        
        assert 'Authorization' not in headers
        assert headers['Content-Type'] == 'application/json'
    
    @patch('requests.post')
    def test_verify_success(self, mock_post):
        """Test successful payment verification."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'isValid': True,
            'payer': TEST_ADDRESS_FROM,
        }
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-mainnet',
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-mainnet',
            'payTo': TEST_ADDRESS_TO,
        }
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is True
        assert result['payer'] == TEST_ADDRESS_FROM
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_verify_with_alternative_response_format(self, mock_post):
        """Test verification with alternative response format."""
        # Mock response with 'valid' instead of 'isValid'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'valid': True,
            'from': TEST_ADDRESS_FROM,
            'reason': None,
        }
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is True
        assert result['payer'] == TEST_ADDRESS_FROM
    
    @patch('requests.post')
    def test_verify_auth_error(self, mock_post):
        """Test verification with authentication error."""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is False
        assert result['invalidReason'] == 'facilitator_auth_error'
    
    @patch('requests.post')
    def test_verify_timeout(self, mock_post):
        """Test verification timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        facilitator = CorbitsFacilitator()
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is False
        assert result['invalidReason'] == 'facilitator_timeout'
    
    @patch('requests.post')
    def test_settle_success(self, mock_post):
        """Test successful payment settlement."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'transaction': '0xabc123def456',
            'receipt': {'status': 'confirmed'},
        }
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is True
        assert result['transaction'] == '0xabc123def456'
        assert 'receipt' in result
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_settle_with_alternative_field_names(self, mock_post):
        """Test settlement with alternative transaction field names."""
        # Mock response with 'transactionHash' instead of 'transaction'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'transactionHash': '0xdef456abc789',
        }
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is True
        assert result['transaction'] == '0xdef456abc789'
    
    @patch('requests.post')
    def test_settle_auth_error(self, mock_post):
        """Test settlement with authentication error."""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is False
        assert 'Authentication failed' in result['error']
    
    @patch('requests.post')
    def test_settle_error_with_json_response(self, mock_post):
        """Test settlement error with JSON error message."""
        # Mock error response with JSON
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_response.json.return_value = {
            'error': 'Invalid payment data',
            'message': 'Amount mismatch',
        }
        mock_post.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is False
        assert 'Invalid payment data' in result['error']
    
    @patch('requests.post')
    def test_settle_timeout(self, mock_post):
        """Test settlement timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        facilitator = CorbitsFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is False
        assert 'timeout' in result['error']
    
    @patch('requests.get')
    def test_get_durable_nonce_info_success(self, mock_get):
        """Test getting durable nonce info successfully."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'account': 'NonceAccountAddress1234567890',
            'nonce': 'nonce_value_base64',
            'authorizedPubkey': 'AuthorityPubkey12345678',
        }
        mock_get.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is not None
        assert result['account'] == 'NonceAccountAddress1234567890'
    
    @patch('requests.get')
    def test_get_durable_nonce_info_not_available(self, mock_get):
        """Test when durable nonce info is not available."""
        # Mock not found response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        facilitator = CorbitsFacilitator()
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is None

