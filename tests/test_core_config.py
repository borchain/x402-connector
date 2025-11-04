"""Tests for Solana-specific configuration."""

import os
import pytest
from x402_connector.core.config import X402Config

# Test placeholder address (not a real wallet)
TEST_ADDRESS = 'TestSolanaAddress1234567890123456789012'


class TestX402Config:
    """Tests for X402Config (Solana-only)."""
    
    def test_minimal_config(self):
        """Test minimal valid configuration."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS
        )
        
        assert config.pay_to_address == TEST_ADDRESS
        assert config.price == '$0.01'
        assert config.network == 'solana-mainnet'
        assert config.protected_paths == ['*']
    
    def test_custom_price(self):
        """Test custom price configuration."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            price='$0.10'
        )
        assert config.price == '$0.10'
    
    def test_custom_network(self):
        """Test custom network configuration."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            network='solana-devnet'
        )
        assert config.network == 'solana-devnet'
    
    def test_invalid_network_raises_error(self):
        """Test that invalid network raises ValueError."""
        with pytest.raises(ValueError, match='network must be one of'):
            X402Config(
                pay_to_address=TEST_ADDRESS,
                network='ethereum'  # Invalid - not Solana
            )
    
    def test_missing_pay_to_address_raises_error(self):
        """Test that missing pay_to_address raises ValueError."""
        with pytest.raises(ValueError, match='pay_to_address is required'):
            X402Config(pay_to_address='')
    
    def test_protected_paths(self):
        """Test protected paths configuration."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            protected_paths=['/api/premium/*']
        )
        assert config.protected_paths == ['/api/premium/*']
    
    def test_custom_rpc_url(self):
        """Test custom RPC URL."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            rpc_url='https://api.devnet.solana.com'
        )
        assert config.rpc_url == 'https://api.devnet.solana.com'
    
    def test_local_config_auto_created(self):
        """Test that local facilitator config is auto-created."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            network='solana-devnet'
        )
        
        assert config.local is not None
        assert config.local['private_key_env'] == 'X402_SIGNER_KEY'
        assert config.local['rpc_url'] == 'https://api.devnet.solana.com'
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            'pay_to_address': TEST_ADDRESS,
            'price': '$0.05',
            'network': 'solana-devnet',
        }
        
        config = X402Config.from_dict(config_dict)
        
        assert config.pay_to_address == TEST_ADDRESS
        assert config.price == '$0.05'
        assert config.network == 'solana-devnet'
    
    def test_from_env(self):
        """Test creating config from environment variables."""
        os.environ['X402_PAY_TO_ADDRESS'] = TEST_ADDRESS
        os.environ['X402_PRICE'] = '$0.02'
        os.environ['X402_NETWORK'] = 'solana-testnet'
        
        try:
            config = X402Config.from_env()
            
            assert config.pay_to_address == TEST_ADDRESS
            assert config.price == '$0.02'
            assert config.network == 'solana-testnet'
        finally:
            del os.environ['X402_PAY_TO_ADDRESS']
            del os.environ['X402_PRICE']
            del os.environ['X402_NETWORK']
    
    def test_from_env_missing_required_raises_error(self):
        """Test that missing required env vars raise ValueError."""
        # Make sure PAY_TO_ADDRESS is not set
        os.environ.pop('X402_PAY_TO_ADDRESS', None)
        
        with pytest.raises(ValueError, match='Missing required environment variable'):
            X402Config.from_env()
    
    def test_verify_balance_option(self):
        """Test verify_balance configuration."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            verify_balance=True
        )
        assert config.verify_balance is True
    
    def test_wait_for_confirmation_option(self):
        """Test wait_for_confirmation configuration."""
        config = X402Config(
            pay_to_address=TEST_ADDRESS,
            wait_for_confirmation=True
        )
        assert config.wait_for_confirmation is True
