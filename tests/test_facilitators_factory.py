"""Tests for facilitators factory function."""

import pytest
from unittest.mock import patch

from x402_connector.core.facilitators import get_facilitator
from x402_connector.core.facilitators.local import SolanaFacilitator
from x402_connector.core.facilitators.payai import PayAIFacilitator
from x402_connector.core.facilitators.corbits import CorbitsFacilitator
from x402_connector.core.facilitators.hybrid import HybridFacilitator
from x402_connector.core.config import X402Config


class TestFacilitatorsFactory:
    """Tests for get_facilitator factory function."""
    
    def test_get_facilitator_local_mode(self):
        """Test factory creates local facilitator."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='local',
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, SolanaFacilitator)
    
    def test_get_facilitator_local_mode_default(self):
        """Test factory defaults to local mode."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            # No facilitator_mode specified, should default to 'local'
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, SolanaFacilitator)
    
    def test_get_facilitator_payai_mode(self):
        """Test factory creates PayAI facilitator."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='payai',
            payai={
                'facilitator_url': 'https://facilitator.payai.network',
            }
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, PayAIFacilitator)
    
    def test_get_facilitator_corbits_mode(self):
        """Test factory creates Corbits facilitator."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='corbits',
            corbits={
                'facilitator_url': 'https://api.corbits.dev',
            }
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, CorbitsFacilitator)
    
    def test_get_facilitator_hybrid_mode(self):
        """Test factory creates Hybrid facilitator."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='hybrid',
            local={'rpc_url': 'https://api.mainnet-beta.solana.com'},
            payai={'facilitator_url': 'https://facilitator.payai.network'},
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, HybridFacilitator)
    
    def test_get_facilitator_hybrid_mode_with_corbits(self):
        """Test factory creates Hybrid facilitator with Corbits settlement."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='hybrid',
            local={'rpc_url': 'https://api.mainnet-beta.solana.com'},
            corbits={'facilitator_url': 'https://api.corbits.dev'},
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, HybridFacilitator)
        assert facilitator.settle_mode == 'corbits'
    
    def test_get_facilitator_hybrid_mode_prefers_corbits(self):
        """Test hybrid mode prefers Corbits if PayAI not configured."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='hybrid',
            local={'rpc_url': 'https://api.mainnet-beta.solana.com'},
            payai=None,
            corbits={'facilitator_url': 'https://api.corbits.dev'},
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, HybridFacilitator)
        assert facilitator.settle_mode == 'corbits'
    
    def test_get_facilitator_invalid_mode(self):
        """Test factory raises error for invalid mode."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='invalid_mode',
        )
        
        with pytest.raises(ValueError, match='Unsupported facilitator_mode'):
            get_facilitator(config)
    
    def test_get_facilitator_case_insensitive(self):
        """Test factory handles case-insensitive mode names."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='LOCAL',  # Uppercase
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, SolanaFacilitator)
    
    def test_get_facilitator_with_local_config_object(self):
        """Test factory handles config objects (not just dicts)."""
        # Create a config with nested config object
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='local',
        )
        
        # Config should auto-setup local config
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, SolanaFacilitator)
    
    def test_get_facilitator_payai_with_empty_config(self):
        """Test factory with PayAI mode but empty config (uses defaults)."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='payai',
            payai={},  # Empty config, should use defaults
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, PayAIFacilitator)
        assert facilitator.facilitator_url == 'https://facilitator.payai.network'
    
    def test_get_facilitator_corbits_with_empty_config(self):
        """Test factory with Corbits mode but empty config (uses defaults)."""
        config = X402Config(
            pay_to_address='TestAddress1234567890123456789012',
            network='solana-mainnet',
            facilitator_mode='corbits',
            corbits={},  # Empty config, should use defaults
        )
        
        facilitator = get_facilitator(config)
        
        assert isinstance(facilitator, CorbitsFacilitator)
        assert facilitator.facilitator_url == 'https://api.corbits.dev'

