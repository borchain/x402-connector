"""Tests for Solana facilitator."""

import pytest
from unittest.mock import Mock, patch

from x402_connector.core.facilitators_solana import SolanaFacilitator
from x402_connector.core.facilitators_base import detect_chain_type, is_solana_network, is_evm_network


class TestChainDetection:
    """Tests for chain type detection."""
    
    def test_detect_solana_networks(self):
        """Test Solana network detection."""
        assert is_solana_network('solana') is True
        assert is_solana_network('solana-mainnet') is True
        assert is_solana_network('solana-devnet') is True
        assert is_solana_network('solana-testnet') is True
        assert is_solana_network('SOLANA-DEVNET') is True  # Case insensitive
    
    def test_detect_evm_networks(self):
        """Test EVM network detection."""
        assert is_evm_network('base') is True
        assert is_evm_network('base-mainnet') is True
        assert is_evm_network('base-sepolia') is True
        assert is_evm_network('ethereum') is True
        assert is_evm_network('polygon') is True
        assert is_evm_network('BASE-SEPOLIA') is True  # Case insensitive
    
    def test_detect_chain_type_solana(self):
        """Test chain type detection for Solana."""
        assert detect_chain_type('solana-devnet') == 'solana'
        assert detect_chain_type('solana-mainnet') == 'solana'
    
    def test_detect_chain_type_evm(self):
        """Test chain type detection for EVM."""
        assert detect_chain_type('base') == 'evm'
        assert detect_chain_type('base-sepolia') == 'evm'
        assert detect_chain_type('polygon') == 'evm'
    
    def test_detect_chain_type_unknown(self):
        """Test chain type detection for unknown network."""
        with pytest.raises(ValueError, match='Unknown network'):
            detect_chain_type('unknown-chain')


class TestSolanaFacilitator:
    """Tests for SolanaFacilitator."""
    
    def test_initialization(self):
        """Test Solana facilitator initialization."""
        fac = SolanaFacilitator(config={'verify_balance': True})
        assert fac.config['verify_balance'] is True
        assert isinstance(fac._used_nonces, set)
    
    def test_verify_basic_fields(self):
        """Test basic field verification on Solana."""
        fac = SolanaFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'signature': '',  # Empty signature (won't trigger verification)
                'authorization': {
                    'from': 'PAYER_ADDRESS',
                    'to': 'PAYEE_ADDRESS',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': 'nonce123',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'asset': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC on Solana
            'maxAmountRequired': '10000',
            'payTo': 'PAYEE_ADDRESS',
            'maxTimeoutSeconds': 60,
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is True
        assert result['payer'] == 'PAYER_ADDRESS'
    
    def test_verify_invalid_version(self):
        """Test verification fails with wrong x402 version."""
        fac = SolanaFacilitator(config={})
        
        payment = {'x402Version': 2}
        requirements = {}
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'version' in result['invalidReason'].lower()
    
    def test_verify_network_mismatch(self):
        """Test verification fails with network mismatch."""
        fac = SolanaFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {'authorization': {}, 'signature': ''},
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-mainnet',  # Different network
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'network' in result['invalidReason'].lower()
    
    def test_verify_recipient_mismatch(self):
        """Test verification fails with wrong recipient."""
        fac = SolanaFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'signature': '',
                'authorization': {
                    'to': 'WRONG_ADDRESS',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': 'RIGHT_ADDRESS',
            'maxAmountRequired': '10000',
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'recipient' in result['invalidReason'].lower()
    
    def test_verify_nonce_replay_protection(self):
        """Test nonce replay protection on Solana."""
        fac = SolanaFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payload': {
                'signature': '',
                'authorization': {
                    'from': 'PAYER',
                    'to': 'PAYEE',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': 'unique_nonce_123',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'solana-devnet',
            'payTo': 'PAYEE',
            'maxAmountRequired': '10000',
        }
        
        # First use should succeed
        result1 = fac.verify(payment, requirements)
        assert result1['isValid'] is True
        
        # Second use of same nonce should fail
        result2 = fac.verify(payment, requirements)
        assert result2['isValid'] is False
        assert 'nonce' in result2['invalidReason'].lower()
    
    def test_settle_missing_env_vars(self):
        """Test settlement fails gracefully when env vars missing."""
        fac = SolanaFacilitator(config={
            'private_key_env': 'NONEXISTENT_SOLANA_KEY',
            'rpc_url_env': 'NONEXISTENT_SOLANA_RPC',
        })
        
        payment = {}
        requirements = {}
        
        result = fac.settle(payment, requirements)
        assert result['success'] is False
        assert 'not set' in result['error'].lower()

