"""Tests for core facilitators."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from x402_connector.core.facilitators import (
    LocalFacilitator,
    RemoteFacilitator,
    HybridFacilitator,
    get_facilitator,
)
from x402_connector.core.config import X402Config, RemoteFacilitatorConfig


class TestLocalFacilitator:
    """Tests for LocalFacilitator."""
    
    def test_initialization(self):
        """Test local facilitator initialization."""
        fac = LocalFacilitator(config={'verify_balance': True})
        assert fac.config['verify_balance'] is True
        assert isinstance(fac._used_nonces, set)
    
    def test_verify_basic_fields(self):
        """Test basic field verification."""
        fac = LocalFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base-sepolia',
            'payload': {
                'signature': '0xdeadbeef',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0xPAYEE',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x01',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'base-sepolia',
            'asset': '0xUSDC',
            'maxAmountRequired': '10000',
            'payTo': '0xPAYEE',
            'maxTimeoutSeconds': 60,
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is True
        assert result['payer'] == '0xPAYER'
    
    def test_verify_invalid_version(self):
        """Test verification fails with wrong x402 version."""
        fac = LocalFacilitator(config={})
        
        payment = {'x402Version': 2}
        requirements = {}
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'version' in result['invalidReason'].lower()
    
    def test_verify_network_mismatch(self):
        """Test verification fails with network mismatch."""
        fac = LocalFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base',
            'payload': {'authorization': {}, 'signature': ''},
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'polygon',
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'network' in result['invalidReason'].lower()
    
    def test_verify_recipient_mismatch(self):
        """Test verification fails with wrong recipient."""
        fac = LocalFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base',
            'payload': {
                'signature': '',
                'authorization': {
                    'to': '0xWRONG',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'base',
            'payTo': '0xRIGHT',
            'maxAmountRequired': '10000',
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'recipient' in result['invalidReason'].lower()
    
    def test_verify_amount_mismatch(self):
        """Test verification fails with wrong amount."""
        fac = LocalFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base',
            'payload': {
                'signature': '',
                'authorization': {
                    'to': '0xPAYEE',
                    'value': '5000',  # Wrong amount
                    'validAfter': '0',
                    'validBefore': '9999999999',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'base',
            'payTo': '0xPAYEE',
            'maxAmountRequired': '10000',
        }
        
        result = fac.verify(payment, requirements)
        assert result['isValid'] is False
        assert 'value' in result['invalidReason'].lower()
    
    def test_verify_nonce_replay_protection(self):
        """Test nonce replay protection."""
        fac = LocalFacilitator(config={})
        
        payment = {
            'x402Version': 1,
            'scheme': 'exact',
            'network': 'base',
            'payload': {
                'signature': '',
                'authorization': {
                    'from': '0xPAYER',
                    'to': '0xPAYEE',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x123',
                },
            },
        }
        
        requirements = {
            'scheme': 'exact',
            'network': 'base',
            'payTo': '0xPAYEE',
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
        fac = LocalFacilitator(config={
            'private_key_env': 'NONEXISTENT_KEY',
            'rpc_url_env': 'NONEXISTENT_RPC',
        })
        
        payment = {}
        requirements = {}
        
        result = fac.settle(payment, requirements)
        assert result['success'] is False
        assert 'not set' in result['error'].lower()
    
    @patch('os.environ.get')
    def test_settle_successful_transaction(self, mock_env):
        """Test successful settlement with mocked Web3."""
        mock_env.side_effect = lambda key, default='': {
            'X402_SIGNER_KEY': '0x' + '11' * 32,
            'X402_RPC_URL': 'http://localhost:8545',
        }.get(key, default)
        
        payment = {
            'payload': {
                'signature': '0x' + 'aa' * 65,
                'authorization': {
                    'from': '0x1111111111111111111111111111111111111111',
                    'to': '0x2222222222222222222222222222222222222222',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x' + '11' * 32,
                },
            },
        }
        
        requirements = {
            'asset': '0x0000000000000000000000000000000000000001',
            'maxAmountRequired': '10000',
        }
        
        # Mock Web3
        with patch('web3.Web3') as mock_web3_class:
            mock_account = Mock()
            mock_account.address = '0xfeed000000000000000000000000000000000000'
            
            mock_eth = Mock()
            mock_eth.account.from_key.return_value = mock_account
            mock_eth.get_transaction_count.return_value = 7
            mock_eth.gas_price = 1000000000
            mock_eth.call.return_value = b'\x00' * 32  # Simulation success
            mock_eth.send_raw_transaction.return_value = Mock(hex=lambda: '0xabc123')
            
            signed_tx = Mock()
            signed_tx.raw_transaction = b'signed_bytes'
            mock_eth.account.sign_transaction.return_value = signed_tx
            
            mock_w3 = Mock()
            mock_w3.eth = mock_eth
            mock_w3.is_connected.return_value = True
            mock_web3_class.return_value = mock_w3
            
            # Mock Web3.keccak
            mock_web3_class.keccak = lambda text: b'\x12\x34\x56\x78' + b'\x00' * 28
            
            fac = LocalFacilitator(config={})
            result = fac.settle(payment, requirements)
            
            assert result['success'] is True
            assert result['transaction'] == '0xabc123'
    
    @patch('os.environ.get')
    def test_settle_simulation_failure(self, mock_env):
        """Test settlement fails when simulation fails."""
        mock_env.side_effect = lambda key, default='': {
            'X402_SIGNER_KEY': '0x' + '11' * 32,
            'X402_RPC_URL': 'http://localhost:8545',
        }.get(key, default)
        
        payment = {
            'payload': {
                'signature': '0x' + 'aa' * 65,
                'authorization': {
                    'from': '0x1111111111111111111111111111111111111111',
                    'to': '0x2222222222222222222222222222222222222222',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x' + '11' * 32,
                },
            },
        }
        
        requirements = {
            'asset': '0x0000000000000000000000000000000000000001',
        }
        
        # Mock Web3 with simulation failure
        with patch('web3.Web3') as mock_web3_class:
            mock_account = Mock()
            mock_account.address = '0xfeed000000000000000000000000000000000000'
            
            mock_eth = Mock()
            mock_eth.account.from_key.return_value = mock_account
            mock_eth.get_transaction_count.return_value = 7
            mock_eth.gas_price = 1000000000
            # Simulation fails
            mock_eth.call.side_effect = Exception('ERC20: transfer amount exceeds balance')
            
            mock_w3 = Mock()
            mock_w3.eth = mock_eth
            mock_w3.is_connected.return_value = True
            mock_web3_class.return_value = mock_w3
            mock_web3_class.keccak = lambda text: b'\x12\x34\x56\x78' + b'\x00' * 28
            
            fac = LocalFacilitator(config={'simulate_before_send': True})
            result = fac.settle(payment, requirements)
            
            assert result['success'] is False
            assert 'simulation failed' in result['error'].lower()
    
    @patch('os.environ.get')
    def test_settle_with_wait_for_receipt(self, mock_env):
        """Test settlement with wait_for_receipt option."""
        mock_env.side_effect = lambda key, default='': {
            'X402_SIGNER_KEY': '0x' + '11' * 32,
            'X402_RPC_URL': 'http://localhost:8545',
        }.get(key, default)
        
        payment = {
            'payload': {
                'signature': '0x' + 'aa' * 65,
                'authorization': {
                    'from': '0x1111111111111111111111111111111111111111',
                    'to': '0x2222222222222222222222222222222222222222',
                    'value': '10000',
                    'validAfter': '0',
                    'validBefore': '9999999999',
                    'nonce': '0x' + '11' * 32,
                },
            },
        }
        
        requirements = {
            'asset': '0x0000000000000000000000000000000000000001',
        }
        
        # Mock Web3 with receipt
        with patch('web3.Web3') as mock_web3_class:
            mock_receipt = {
                'status': 1,
                'blockNumber': 12345,
                'transactionHash': b'\xab\xcd',
            }
            
            mock_account = Mock()
            mock_account.address = '0xfeed000000000000000000000000000000000000'
            
            mock_eth = Mock()
            mock_eth.account.from_key.return_value = mock_account
            mock_eth.get_transaction_count.return_value = 7
            mock_eth.gas_price = 1000000000
            mock_eth.call.return_value = b'\x00' * 32
            mock_eth.send_raw_transaction.return_value = Mock(hex=lambda: '0xabc123')
            mock_eth.wait_for_transaction_receipt.return_value = mock_receipt
            
            signed_tx = Mock()
            signed_tx.raw_transaction = b'signed_bytes'
            mock_eth.account.sign_transaction.return_value = signed_tx
            
            mock_w3 = Mock()
            mock_w3.eth = mock_eth
            mock_w3.is_connected.return_value = True
            mock_web3_class.return_value = mock_w3
            mock_web3_class.keccak = lambda text: b'\x12\x34\x56\x78' + b'\x00' * 28
            
            fac = LocalFacilitator(config={'wait_for_receipt': True})
            result = fac.settle(payment, requirements)
            
            assert result['success'] is True
            assert 'receipt' in result


class TestRemoteFacilitator:
    """Tests for RemoteFacilitator."""
    
    def test_initialization(self):
        """Test remote facilitator initialization."""
        fac = RemoteFacilitator(
            url='https://facilitator.example.com',
            headers={'Authorization': 'Bearer token'},
            timeout=30
        )
        
        assert fac.url == 'https://facilitator.example.com'
        assert fac.headers == {'Authorization': 'Bearer token'}
        assert fac.timeout == 30
    
    @patch('httpx.post')
    def test_verify_success(self, mock_post):
        """Test successful remote verification."""
        mock_response = Mock()
        mock_response.json.return_value = {'isValid': True, 'payer': '0xPAYER'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        fac = RemoteFacilitator(url='https://fac.example.com')
        result = fac.verify({'payment': 'data'}, {'requirements': 'data'})
        
        assert result['isValid'] is True
        assert result['payer'] == '0xPAYER'
        
        # Check correct endpoint called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://fac.example.com/verify'
    
    @patch('httpx.post')
    def test_verify_http_error(self, mock_post):
        """Test verification handles HTTP errors."""
        mock_post.side_effect = Exception('Connection error')
        
        fac = RemoteFacilitator(url='https://fac.example.com')
        result = fac.verify({}, {})
        
        assert result['isValid'] is False
        assert 'remote_error' in result['invalidReason']
    
    @patch('httpx.post')
    def test_settle_success(self, mock_post):
        """Test successful remote settlement."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'transaction': '0xabc123'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        fac = RemoteFacilitator(url='https://fac.example.com')
        result = fac.settle({}, {})
        
        assert result['success'] is True
        assert result['transaction'] == '0xabc123'
    
    @patch('httpx.post')
    def test_settle_http_error(self, mock_post):
        """Test settlement handles HTTP errors."""
        mock_post.side_effect = Exception('Network error')
        
        fac = RemoteFacilitator(url='https://fac.example.com')
        result = fac.settle({}, {})
        
        assert result['success'] is False
        assert 'remote_error' in result['error']


class TestHybridFacilitator:
    """Tests for HybridFacilitator."""
    
    def test_initialization(self):
        """Test hybrid facilitator initialization."""
        local = LocalFacilitator(config={})
        remote = RemoteFacilitator(url='https://fac.example.com')
        
        hybrid = HybridFacilitator(local, remote)
        
        assert hybrid.local is local
        assert hybrid.remote is remote
        assert hybrid.fallback_to_remote is True
    
    def test_verify_uses_local_when_valid(self):
        """Test hybrid uses local verification when valid."""
        local = Mock()
        local.verify.return_value = {'isValid': True, 'payer': '0xPAYER'}
        
        remote = Mock()
        
        hybrid = HybridFacilitator(local, remote)
        result = hybrid.verify({}, {})
        
        assert result['isValid'] is True
        local.verify.assert_called_once()
        remote.verify.assert_not_called()
    
    def test_verify_falls_back_to_remote_on_local_invalid(self):
        """Test hybrid falls back to remote when local returns invalid."""
        local = Mock()
        local.verify.return_value = {'isValid': False}
        
        remote = Mock()
        remote.verify.return_value = {'isValid': True, 'payer': '0xPAYER'}
        
        hybrid = HybridFacilitator(local, remote, fallback_to_remote=True)
        result = hybrid.verify({}, {})
        
        assert result['isValid'] is True
        local.verify.assert_called_once()
        remote.verify.assert_called_once()
    
    def test_verify_no_fallback_when_disabled(self):
        """Test hybrid doesn't fallback when disabled."""
        local = Mock()
        local.verify.return_value = {'isValid': False}
        
        remote = Mock()
        
        hybrid = HybridFacilitator(local, remote, fallback_to_remote=False)
        result = hybrid.verify({}, {})
        
        assert result['isValid'] is False
        remote.verify.assert_not_called()
    
    def test_verify_falls_back_on_local_exception(self):
        """Test hybrid falls back to remote when local raises exception."""
        local = Mock()
        local.verify.side_effect = Exception('Local error')
        
        remote = Mock()
        remote.verify.return_value = {'isValid': True}
        
        hybrid = HybridFacilitator(local, remote)
        result = hybrid.verify({}, {})
        
        assert result['isValid'] is True
        remote.verify.assert_called_once()
    
    def test_settle_always_uses_remote(self):
        """Test hybrid always uses remote for settlement."""
        local = Mock()
        remote = Mock()
        remote.settle.return_value = {'success': True, 'transaction': '0xabc'}
        
        hybrid = HybridFacilitator(local, remote)
        result = hybrid.settle({}, {})
        
        assert result['success'] is True
        local.settle.assert_not_called()
        remote.settle.assert_called_once()


class TestGetFacilitator:
    """Tests for get_facilitator factory function."""
    
    def test_creates_local_facilitator(self):
        """Test factory creates local facilitator."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            facilitator_mode='local',
        )
        
        fac = get_facilitator(config)
        
        assert isinstance(fac, LocalFacilitator)
    
    def test_creates_remote_facilitator(self):
        """Test factory creates remote facilitator."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            facilitator_mode='remote',
            remote=RemoteFacilitatorConfig(url='https://fac.example.com'),
        )
        
        fac = get_facilitator(config)
        
        assert isinstance(fac, RemoteFacilitator)
        assert fac.url == 'https://fac.example.com'
    
    def test_creates_hybrid_facilitator(self):
        """Test factory creates hybrid facilitator."""
        config = X402Config(
            network='base',
            price='$0.01',
            pay_to_address='0x123',
            facilitator_mode='hybrid',
            remote=RemoteFacilitatorConfig(url='https://fac.example.com'),
        )
        
        fac = get_facilitator(config)
        
        assert isinstance(fac, HybridFacilitator)
    
    def test_raises_on_invalid_mode(self):
        """Test config validation raises error on invalid mode."""
        # Config validation should catch invalid mode before get_facilitator
        with pytest.raises(ValueError, match="facilitator_mode must be"):
            X402Config(
                network='base',
                price='$0.01',
                pay_to_address='0x123',
                facilitator_mode='invalid',
            )
    
    def test_raises_on_missing_remote_config(self):
        """Test config validation raises error when remote config missing."""
        # Config validation should catch missing remote config
        with pytest.raises(ValueError, match='remote facilitator config required'):
            X402Config(
                network='base',
                price='$0.01',
                pay_to_address='0x123',
                facilitator_mode='remote',
                # Missing remote config
            )

