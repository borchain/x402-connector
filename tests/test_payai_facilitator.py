"""Tests for PayAI facilitator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from x402_connector.core.facilitators.payai import PayAIFacilitator

# Test addresses
TEST_ADDRESS_FROM = 'TestFromAddress1234567890123456789ABC'
TEST_ADDRESS_TO = 'TestToAddress567890123456789012345678'


class TestPayAIFacilitator:
    """Tests for PayAIFacilitator."""
    
    def test_initialization(self):
        """Test facilitator initialization with defaults."""
        facilitator = PayAIFacilitator()
        assert facilitator is not None
        assert facilitator.facilitator_url == 'https://facilitator.payai.network'
        assert facilitator.timeout == 30
    
    def test_initialization_with_config(self):
        """Test facilitator initialization with custom config."""
        config = {
            'facilitator_url': 'https://custom.payai.network',
            'api_key_env': 'CUSTOM_KEY',
            'timeout': 60,
        }
        facilitator = PayAIFacilitator(config=config)
        assert facilitator.facilitator_url == 'https://custom.payai.network'
        assert facilitator.timeout == 60
    
    @patch.dict('os.environ', {'PAYAI_API_KEY': 'test_api_key'})
    def test_get_headers_with_api_key(self):
        """Test headers include API key when available."""
        facilitator = PayAIFacilitator()
        headers = facilitator._get_headers()
        
        assert headers['Authorization'] == 'Bearer test_api_key'
        assert headers['Content-Type'] == 'application/json'
        assert 'User-Agent' in headers
    
    def test_get_headers_without_api_key(self):
        """Test headers without API key."""
        facilitator = PayAIFacilitator()
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
        
        facilitator = PayAIFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-mainnet',
            'payload': {'authorization': {'from': TEST_ADDRESS_FROM}},
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-mainnet',
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is True
        assert result['payer'] == TEST_ADDRESS_FROM
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_verify_failure(self, mock_post):
        """Test failed payment verification."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'isValid': False,
            'invalidReason': 'invalid_signature',
        }
        mock_post.return_value = mock_response
        
        facilitator = PayAIFacilitator()
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is False
        assert 'invalid_signature' in result['invalidReason']
    
    @patch('requests.post')
    def test_verify_http_error(self, mock_post):
        """Test verification with HTTP error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response
        
        facilitator = PayAIFacilitator()
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is False
        assert 'facilitator_error' in result['invalidReason']
    
    @patch('requests.post')
    def test_verify_timeout(self, mock_post):
        """Test verification timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        facilitator = PayAIFacilitator()
        
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
        }
        mock_post.return_value = mock_response
        
        facilitator = PayAIFacilitator()
        
        payment = {
            'payload': {
                'authorization': {'from': TEST_ADDRESS_FROM},
            }
        }
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is True
        assert result['transaction'] == '0xabc123def456'
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_settle_no_transaction_hash(self, mock_post):
        """Test settlement without transaction hash in response."""
        # Mock response without transaction hash
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response
        
        facilitator = PayAIFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is False
        assert 'No transaction hash' in result['error']
    
    @patch('requests.post')
    def test_settle_http_error(self, mock_post):
        """Test settlement with HTTP error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response
        
        facilitator = PayAIFacilitator()
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is False
        assert 'Facilitator error' in result['error']
    
    @patch('requests.post')
    def test_settle_timeout(self, mock_post):
        """Test settlement timeout."""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        facilitator = PayAIFacilitator()
        
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
        
        facilitator = PayAIFacilitator()
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is not None
        assert result['account'] == 'NonceAccountAddress1234567890'
        assert result['nonce'] == 'nonce_value_base64'
    
    @patch('requests.get')
    def test_get_durable_nonce_info_not_available(self, mock_get):
        """Test when durable nonce info is not available."""
        # Mock not found response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        facilitator = PayAIFacilitator()
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is None
    
    @patch('requests.get')
    def test_get_durable_nonce_info_error(self, mock_get):
        """Test error handling in durable nonce info."""
        mock_get.side_effect = Exception('Connection error')
        
        facilitator = PayAIFacilitator()
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is None

