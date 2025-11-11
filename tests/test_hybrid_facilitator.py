"""Tests for Hybrid facilitator."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from x402_connector.core.facilitators.hybrid import HybridFacilitator
from x402_connector.core.facilitators.local import SolanaFacilitator
from x402_connector.core.facilitators.payai import PayAIFacilitator
from x402_connector.core.facilitators.corbits import CorbitsFacilitator

# Test addresses
TEST_ADDRESS_FROM = 'TestFromAddress1234567890123456789ABC'
TEST_ADDRESS_TO = 'TestToAddress567890123456789012345678'


class TestHybridFacilitator:
    """Tests for HybridFacilitator."""
    
    def test_initialization_with_payai(self):
        """Test hybrid facilitator initialization with PayAI settlement."""
        config = {
            'verify_mode': 'local',
            'settle_mode': 'payai',
            'local': {'rpc_url': 'https://api.mainnet-beta.solana.com'},
            'payai': {'facilitator_url': 'https://facilitator.payai.network'},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        assert facilitator is not None
        assert facilitator.verify_mode == 'local'
        assert facilitator.settle_mode == 'payai'
        assert isinstance(facilitator.verifier, SolanaFacilitator)
        assert isinstance(facilitator.settler, PayAIFacilitator)
    
    def test_initialization_with_corbits(self):
        """Test hybrid facilitator initialization with Corbits settlement."""
        config = {
            'verify_mode': 'local',
            'settle_mode': 'corbits',
            'local': {'rpc_url': 'https://api.mainnet-beta.solana.com'},
            'corbits': {'facilitator_url': 'https://api.corbits.dev'},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        assert facilitator is not None
        assert facilitator.verify_mode == 'local'
        assert facilitator.settle_mode == 'corbits'
        assert isinstance(facilitator.verifier, SolanaFacilitator)
        assert isinstance(facilitator.settler, CorbitsFacilitator)
    
    def test_initialization_defaults_to_payai(self):
        """Test hybrid facilitator defaults to PayAI for settlement."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        assert facilitator.verify_mode == 'local'
        assert facilitator.settle_mode == 'payai'
    
    def test_initialization_invalid_verify_mode(self):
        """Test initialization with invalid verify mode."""
        config = {
            'verify_mode': 'remote',  # Not supported
            'settle_mode': 'payai',
        }
        
        with pytest.raises(ValueError, match='Unsupported verify_mode'):
            HybridFacilitator(config=config)
    
    def test_initialization_invalid_settle_mode(self):
        """Test initialization with invalid settle mode."""
        config = {
            'verify_mode': 'local',
            'settle_mode': 'invalid',  # Not supported
        }
        
        with pytest.raises(ValueError, match='Unsupported settle_mode'):
            HybridFacilitator(config=config)
    
    def test_verify_delegates_to_local(self):
        """Test verification delegates to local facilitator."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock the verifier
        facilitator.verifier = Mock()
        facilitator.verifier.verify = Mock(return_value={
            'isValid': True,
            'payer': TEST_ADDRESS_FROM,
        })
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is True
        assert result['payer'] == TEST_ADDRESS_FROM
        facilitator.verifier.verify.assert_called_once_with(payment, requirements)
    
    def test_verify_failure_logged(self):
        """Test verification failure is logged."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock the verifier to return failure
        facilitator.verifier = Mock()
        facilitator.verifier.verify = Mock(return_value={
            'isValid': False,
            'invalidReason': 'invalid_signature',
        })
        
        payment = {'x402Version': 1}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.verify(payment, requirements)
        
        assert result['isValid'] is False
        assert result['invalidReason'] == 'invalid_signature'
    
    def test_settle_delegates_to_payai(self):
        """Test settlement delegates to PayAI facilitator."""
        config = {
            'local': {},
            'payai': {},
            'settle_mode': 'payai',
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock the settler
        facilitator.settler = Mock()
        facilitator.settler.settle = Mock(return_value={
            'success': True,
            'transaction': '0xabc123',
        })
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is True
        assert result['transaction'] == '0xabc123'
        facilitator.settler.settle.assert_called_once_with(payment, requirements)
    
    def test_settle_delegates_to_corbits(self):
        """Test settlement delegates to Corbits facilitator."""
        config = {
            'local': {},
            'corbits': {},
            'settle_mode': 'corbits',
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock the settler
        facilitator.settler = Mock()
        facilitator.settler.settle = Mock(return_value={
            'success': True,
            'transaction': '0xdef456',
        })
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is True
        assert result['transaction'] == '0xdef456'
        facilitator.settler.settle.assert_called_once_with(payment, requirements)
    
    def test_settle_failure_logged(self):
        """Test settlement failure is logged."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock the settler to return failure
        facilitator.settler = Mock()
        facilitator.settler.settle = Mock(return_value={
            'success': False,
            'error': 'Network error',
        })
        
        payment = {'payload': {'authorization': {}}}
        requirements = {'payTo': TEST_ADDRESS_TO}
        
        result = facilitator.settle(payment, requirements)
        
        assert result['success'] is False
        assert result['error'] == 'Network error'
    
    def test_get_durable_nonce_info_from_settler(self):
        """Test getting durable nonce info from settler first."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock settler with nonce info
        facilitator.settler = Mock()
        facilitator.settler.get_durable_nonce_info = Mock(return_value={
            'account': 'NonceAccountFromPayAI',
            'nonce': 'nonce_value',
        })
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is not None
        assert result['account'] == 'NonceAccountFromPayAI'
        facilitator.settler.get_durable_nonce_info.assert_called_once()
    
    def test_get_durable_nonce_info_fallback_to_verifier(self):
        """Test fallback to verifier if settler doesn't have nonce info."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock settler without nonce info
        facilitator.settler = Mock()
        facilitator.settler.get_durable_nonce_info = Mock(return_value=None)
        
        # Mock verifier with nonce info
        facilitator.verifier = Mock()
        facilitator.verifier.get_durable_nonce_info = Mock(return_value={
            'account': 'NonceAccountFromLocal',
            'nonce': 'nonce_value',
        })
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is not None
        assert result['account'] == 'NonceAccountFromLocal'
    
    def test_get_durable_nonce_info_returns_none(self):
        """Test returns None when no nonce info available."""
        config = {
            'local': {},
            'payai': {},
        }
        
        facilitator = HybridFacilitator(config=config)
        
        # Mock both without nonce info
        facilitator.settler = Mock()
        facilitator.settler.get_durable_nonce_info = Mock(return_value=None)
        
        facilitator.verifier = Mock()
        facilitator.verifier.get_durable_nonce_info = Mock(return_value=None)
        
        result = facilitator.get_durable_nonce_info()
        
        assert result is None

