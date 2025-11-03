"""Tests for core configuration classes."""

import os
import pytest
from x402_connector.core.config import (
    X402Config,
    LocalFacilitatorConfig,
    RemoteFacilitatorConfig,
)


class TestLocalFacilitatorConfig:
    """Tests for LocalFacilitatorConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = LocalFacilitatorConfig()
        
        assert config.private_key_env == 'X402_SIGNER_KEY'
        assert config.rpc_url_env == 'X402_RPC_URL'
        assert config.verify_balance is False
        assert config.simulate_before_send is True
        assert config.wait_for_receipt is False
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = LocalFacilitatorConfig(
            private_key_env='MY_KEY',
            rpc_url_env='MY_RPC',
            verify_balance=True,
            simulate_before_send=False,
            wait_for_receipt=True
        )
        
        assert config.private_key_env == 'MY_KEY'
        assert config.rpc_url_env == 'MY_RPC'
        assert config.verify_balance is True
        assert config.simulate_before_send is False
        assert config.wait_for_receipt is True


class TestRemoteFacilitatorConfig:
    """Tests for RemoteFacilitatorConfig."""
    
    def test_required_url(self):
        """Test that URL is required."""
        config = RemoteFacilitatorConfig(url='https://facilitator.example.com')
        assert config.url == 'https://facilitator.example.com'
    
    def test_optional_headers(self):
        """Test optional headers."""
        config = RemoteFacilitatorConfig(
            url='https://facilitator.example.com',
            headers={'Authorization': 'Bearer token'}
        )
        assert config.headers == {'Authorization': 'Bearer token'}
    
    def test_custom_timeout(self):
        """Test custom timeout."""
        config = RemoteFacilitatorConfig(
            url='https://facilitator.example.com',
            timeout=30
        )
        assert config.timeout == 30


class TestX402Config:
    """Tests for main X402Config class."""
    
    def test_minimal_config(self):
        """Test minimal valid configuration."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x1234567890123456789012345678901234567890'
        )
        
        assert config.network == 'base'
        assert config.price == '$0.01'
        assert config.pay_to_address == '0x1234567890123456789012345678901234567890'
        assert config.protected_paths == ['*']
        assert config.facilitator_mode == 'local'
    
    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match='network is required'):
            X402Config(network='', price='$0.01', pay_to_address='0x123')
        
        with pytest.raises(ValueError, match='price is required'):
            X402Config(network='base', price='', pay_to_address='0x123')
        
        with pytest.raises(ValueError, match='pay_to_address is required'):
            X402Config(network='base', price='$0.01', pay_to_address='')
    
    def test_invalid_facilitator_mode_raises_error(self):
        """Test that invalid facilitator mode raises ValueError."""
        with pytest.raises(ValueError, match='facilitator_mode must be'):
            X402Config(
                network='base',
                price='$0.01',
                pay_to_address='0x123',
                facilitator_mode='invalid'
            )
    
    def test_custom_protected_paths(self):
        """Test custom protected paths."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            protected_paths=['/api/premium/*', '/api/paid/*']
        )
        
        assert config.protected_paths == ['/api/premium/*', '/api/paid/*']
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config = X402Config.from_dict({
            'network': 'base',
            'price': '$0.01',
            'pay_to_address': '0x123',
            'protected_paths': ['/api/*'],
            'facilitator_mode': 'local',
            'local': {
                'verify_balance': True,
                'simulate_before_send': False,
            }
        })
        
        assert config.network == 'base'
        assert config.protected_paths == ['/api/*']
        assert config.local is not None
        assert config.local.verify_balance is True
        assert config.local.simulate_before_send is False
    
    def test_from_env(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv('X402_NETWORK', 'base')
        monkeypatch.setenv('X402_PRICE', '$0.01')
        monkeypatch.setenv('X402_PAY_TO_ADDRESS', '0x123')
        monkeypatch.setenv('X402_PROTECTED_PATHS', '/api/premium/*,/api/paid/*')
        
        config = X402Config.from_env()
        
        assert config.network == 'base'
        assert config.price == '$0.01'
        assert config.pay_to_address == '0x123'
        assert config.protected_paths == ['/api/premium/*', '/api/paid/*']
    
    def test_from_env_missing_required_raises_error(self):
        """Test that from_env raises error when required vars missing."""
        with pytest.raises(ValueError, match='Missing required environment variables'):
            X402Config.from_env()
    
    def test_local_mode_creates_default_local_config(self):
        """Test that local mode creates default local config."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            facilitator_mode='local'
        )
        
        assert config.local is not None
        assert isinstance(config.local, LocalFacilitatorConfig)
    
    def test_remote_mode_requires_remote_config(self):
        """Test that remote mode requires remote config."""
        with pytest.raises(ValueError, match='remote facilitator config required'):
            X402Config(
                network='base',
                price='$0.01',
                pay_to_address='0x123',
                facilitator_mode='remote'
            )
    
    def test_remote_mode_with_config(self):
        """Test remote mode with proper config."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            facilitator_mode='remote',
            remote=RemoteFacilitatorConfig(url='https://facilitator.example.com')
        )
        
        assert config.facilitator_mode == 'remote'
        assert config.remote is not None
        assert config.remote.url == 'https://facilitator.example.com'
    
    def test_settle_policy_validation(self):
        """Test settle policy validation."""
        # Valid values should work
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            settle_policy='block-on-failure'
        )
        assert config.settle_policy == 'block-on-failure'
        
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            settle_policy='log-and-continue'
        )
        assert config.settle_policy == 'log-and-continue'
        
        # Invalid value should raise error
        with pytest.raises(ValueError, match='settle_policy must be'):
            X402Config(
                network='base',
                price='$0.01',
                pay_to_address='0x123',
                settle_policy='invalid'
            )

