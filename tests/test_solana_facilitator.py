"""Tests for Solana facilitator (Solana-only framework)."""

import pytest
from unittest.mock import Mock, patch

from x402_connector.core.facilitators.local import SolanaFacilitator

# Test placeholder addresses (not real wallets)
TEST_ADDRESS_FROM = 'TestFromAddress1234567890123456789ABC'
TEST_ADDRESS_TO = 'TestToAddress567890123456789012345678'


class TestSolanaFacilitator:
    """Tests for SolanaFacilitator."""
    
    def test_initialization(self):
        """Test facilitator initialization."""
        facilitator = SolanaFacilitator()
        assert facilitator is not None
        assert facilitator.config is not None
    
    def test_initialization_with_config(self):
        """Test facilitator initialization with custom config."""
        config = {
            'private_key_env': 'MY_KEY',
            'rpc_url_env': 'MY_RPC',
            'verify_balance': True,
        }
        facilitator = SolanaFacilitator(config=config)
        assert facilitator.config == config
    
    def test_verify_invalid_version(self):
        """Test payment verification with invalid x402 version."""
        facilitator = SolanaFacilitator()
        
        payment = {
            'x402Version': 2,  # Invalid version
            'scheme': 'exact',
            'network': 'solana-devnet',
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        result = facilitator.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'invalid_x402_version' in result['invalidReason']
    
    def test_verify_invalid_scheme(self):
        """Test payment verification with invalid scheme."""
        facilitator = SolanaFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'invalid',
            'network': 'solana-devnet',
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        result = facilitator.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'invalid_scheme' in result['invalidReason']
    
    def test_verify_network_mismatch(self):
        """Test payment verification with network mismatch."""
        facilitator = SolanaFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-mainnet',
            'payload': {
                'authorization': {},
                'signature': '',
            }
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',  # Different network
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        result = facilitator.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'invalid_network' in result['invalidReason']
    
    def test_verify_recipient_mismatch(self):
        """Test payment verification with recipient mismatch."""
        facilitator = SolanaFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'authorization': {
                    'from': TEST_ADDRESS_FROM,
                    'to': 'WrongAddress123456789012345678901234',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '123',
                },
                'signature': '',
            }
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        result = facilitator.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'recipient_mismatch' in result['invalidReason']
    
    def test_verify_amount_mismatch(self):
        """Test payment verification with amount mismatch."""
        facilitator = SolanaFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'authorization': {
                    'from': TEST_ADDRESS_FROM,
                    'to': TEST_ADDRESS_TO,
                    'value': '5000',  # Wrong amount
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '123',
                },
                'signature': '',
            }
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        result = facilitator.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'amount_mismatch' in result['invalidReason']
    
    def test_verify_nonce_reuse(self):
        """Test payment verification rejects reused nonce."""
        facilitator = SolanaFacilitator()
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'authorization': {
                    'from': TEST_ADDRESS_FROM,
                    'to': TEST_ADDRESS_TO,
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '42',
                },
                'signature': '',
            }
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': TEST_ADDRESS_TO,
            'maxAmountRequired': '10000',
        }
        
        # First verification should pass (nonce '42' is new)
        result1 = facilitator.verify(payment, requirements)
        assert result1['isValid'] is True
        
        # Second verification with same nonce should fail
        result2 = facilitator.verify(payment, requirements)
        assert result2['isValid'] is False
        assert 'nonce_already_used' in result2['invalidReason']
    
    @patch('os.environ.get')
    def test_settle_missing_private_key(self, mock_environ_get):
        """Test settlement runs in DEMO mode without private key."""
        mock_environ_get.return_value = None
        
        facilitator = SolanaFacilitator()
        
        payment = {
            'payload': {
                'authorization': {
                    'from': TEST_ADDRESS_FROM,
                    'to': TEST_ADDRESS_TO,
                    'value': '10000',
                }
            }
        }
        
        requirements = {
            'asset': 'TestUSDCMint123456789012345678901234',
        }
        
        result = facilitator.settle(payment, requirements)
        # Should succeed in DEMO mode
        assert result['success'] is True
        assert 'demo_mode_tx_' in result['transaction']
        assert 'DEMO MODE' in result['note']
