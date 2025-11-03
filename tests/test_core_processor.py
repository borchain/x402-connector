"""Tests for core payment processor."""

import json
import base64
import pytest
from unittest.mock import Mock, MagicMock, patch

from x402_connector.core.processor import X402PaymentProcessor
from x402_connector.core.config import X402Config
from x402_connector.core.context import RequestContext, ProcessingResult, SettlementResult


class TestX402PaymentProcessor:
    """Tests for X402PaymentProcessor."""
    
    @pytest.fixture
    def config(self):
        """Basic test configuration."""
        return X402Config(
            network='base-sepolia',
            price='$0.01',
            pay_to_address='0x1234567890123456789012345678901234567890',
            protected_paths=['/api/premium/*'],
        )
    
    @pytest.fixture
    def mock_facilitator(self):
        """Mock facilitator for testing."""
        facilitator = Mock()
        facilitator.verify = Mock(return_value={'isValid': True, 'payer': '0xPAYER'})
        facilitator.settle = Mock(return_value={'success': True, 'transaction': '0xabc123'})
        return facilitator
    
    @pytest.fixture
    def processor(self, config, mock_facilitator):
        """Processor with mock facilitator."""
        return X402PaymentProcessor(config, facilitator=mock_facilitator)
    
    def test_initialization_with_facilitator(self, config, mock_facilitator):
        """Test processor initialization with provided facilitator."""
        processor = X402PaymentProcessor(config, facilitator=mock_facilitator)
        assert processor.config is config
        assert processor.facilitator is mock_facilitator
    
    def test_initialization_auto_creates_facilitator(self, config):
        """Test processor auto-creates facilitator if not provided."""
        # Just test that a facilitator is created
        processor = X402PaymentProcessor(config)
        
        # Should have created a facilitator
        assert processor.facilitator is not None
        # Should be a BaseFacilitator instance
        from x402_connector.core.facilitators import BaseFacilitator
        assert hasattr(processor.facilitator, 'verify')
        assert hasattr(processor.facilitator, 'settle')
    
    def test_process_request_unprotected_path(self, processor):
        """Test unprotected paths are allowed through."""
        context = RequestContext(
            path='/public/free',
            method='GET',
            headers={},
            absolute_url='http://example.com/public/free'
        )
        
        result = processor.process_request(context)
        
        assert result.action == 'allow'
        assert result.payment_verified is False
    
    def test_process_request_protected_no_payment(self, processor):
        """Test protected path without payment returns deny."""
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data'
        )
        
        result = processor.process_request(context)
        
        assert result.action == 'deny'
        assert 'No X-PAYMENT header' in result.error
        assert result.requirements is not None
    
    def test_process_request_invalid_payment_header(self, processor):
        """Test invalid payment header format."""
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data',
            payment_header='invalid-not-base64!!'
        )
        
        result = processor.process_request(context)
        
        assert result.action == 'deny'
        assert 'Invalid payment header format' in result.error
    
    def test_process_request_with_valid_payment(self, processor, mock_facilitator):
        """Test valid payment verification."""
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base-sepolia',
            'payload': {
                'signature': '0xdeadbeef',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0x1234567890123456789012345678901234567890',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x01',
                },
            },
        }
        
        payment_header = base64.b64encode(json.dumps(payment).encode()).decode()
        
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data',
            payment_header=payment_header
        )
        
        mock_facilitator.verify.return_value = {'isValid': True, 'payer': '0xPAYER'}
        
        result = processor.process_request(context)
        
        assert result.action == 'allow'
        assert result.payment_verified is True
        assert result.payer_address == '0xPAYER'
        
        # Verify facilitator was called
        mock_facilitator.verify.assert_called_once()
    
    def test_process_request_invalid_payment(self, processor, mock_facilitator):
        """Test invalid payment verification."""
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base-sepolia',
            'payload': {
                'signature': '0xbadsignature',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0xWRONG',  # Wrong recipient
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x01',
                },
            },
        }
        
        payment_header = base64.b64encode(json.dumps(payment).encode()).decode()
        
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data',
            payment_header=payment_header
        )
        
        mock_facilitator.verify.return_value = {
            'isValid': False,
            'invalidReason': 'signature_mismatch'
        }
        
        result = processor.process_request(context)
        
        assert result.action == 'deny'
        assert 'Invalid payment' in result.error
        assert 'signature_mismatch' in result.error
    
    def test_settle_payment_success(self, processor, mock_facilitator):
        """Test successful payment settlement."""
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base-sepolia',
            'payload': {
                'signature': '0xsignature',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0x1234567890123456789012345678901234567890',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x01',
                },
            },
        }
        
        payment_header = base64.b64encode(json.dumps(payment).encode()).decode()
        
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data',
            payment_header=payment_header
        )
        
        mock_facilitator.settle.return_value = {
            'success': True,
            'transaction': '0xabc123'
        }
        
        result = processor.settle_payment(context)
        
        assert result.success is True
        assert result.transaction_hash == '0xabc123'
        assert result.encoded_response is not None
        
        # Verify facilitator was called
        mock_facilitator.settle.assert_called_once()
    
    def test_settle_payment_failure(self, processor, mock_facilitator):
        """Test failed payment settlement."""
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base-sepolia',
            'payload': {
                'signature': '0xsignature',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0x1234567890123456789012345678901234567890',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x02',
                },
            },
        }
        
        payment_header = base64.b64encode(json.dumps(payment).encode()).decode()
        
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data',
            payment_header=payment_header
        )
        
        mock_facilitator.settle.return_value = {
            'success': False,
            'error': 'Insufficient gas'
        }
        
        result = processor.settle_payment(context)
        
        assert result.success is False
        assert 'Insufficient gas' in result.error
    
    def test_settle_payment_with_cache(self, processor, mock_facilitator):
        """Test settlement caching for replay protection."""
        # Enable caching
        processor.config.replay_cache_enabled = True
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base-sepolia',
            'payload': {
                'signature': '0xsignature',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0x1234567890123456789012345678901234567890',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x03',
                },
            },
        }
        
        payment_header = base64.b64encode(json.dumps(payment).encode()).decode()
        
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data',
            payment_header=payment_header
        )
        
        mock_facilitator.settle.return_value = {
            'success': True,
            'transaction': '0xabc123'
        }
        
        # First call
        result1 = processor.settle_payment(context)
        assert result1.success is True
        assert mock_facilitator.settle.call_count == 1
        
        # Second call with same payment - should use cache
        result2 = processor.settle_payment(context)
        assert result2.success is True
        assert result2.transaction_hash == result1.transaction_hash
        # Facilitator should NOT be called again
        assert mock_facilitator.settle.call_count == 1
    
    def test_is_protected_path_exact_match(self, config):
        """Test exact path matching."""
        config.protected_paths = ['/api/premium/data']
        processor = X402PaymentProcessor(config, facilitator=Mock())
        
        assert processor._is_protected_path('/api/premium/data') is True
        assert processor._is_protected_path('/api/premium/other') is False
    
    def test_is_protected_path_glob_match(self, config):
        """Test glob pattern matching."""
        config.protected_paths = ['/api/premium/*']
        processor = X402PaymentProcessor(config, facilitator=Mock())
        
        assert processor._is_protected_path('/api/premium/data') is True
        assert processor._is_protected_path('/api/premium/anything') is True
        assert processor._is_protected_path('/api/public/data') is False
    
    def test_is_protected_path_wildcard(self, config):
        """Test wildcard protection."""
        config.protected_paths = ['*']
        processor = X402PaymentProcessor(config, facilitator=Mock())
        
        assert processor._is_protected_path('/any/path') is True
        assert processor._is_protected_path('/another/path') is True
    
    def test_build_payment_requirements(self, processor):
        """Test building payment requirements."""
        context = RequestContext(
            path='/api/premium/data',
            method='GET',
            headers={},
            absolute_url='http://example.com/api/premium/data'
        )
        
        requirements = processor._build_payment_requirements(context)
        
        assert len(requirements) == 1
        req = requirements[0]
        
        # Check it's a dict with expected fields
        if isinstance(req, dict):
            assert req['scheme'] == 'exact'
            assert req['network'] == 'base-sepolia'
        else:
            # It's a PaymentRequirements object
            assert req.scheme == 'exact'
            assert req.network == 'base-sepolia'

