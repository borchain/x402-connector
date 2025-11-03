"""Payment facilitators for x402-connector.

Facilitators handle payment verification and settlement. This module is
completely framework-agnostic and can be used with any Python web framework.

Three facilitator modes:
- Local: Self-hosted verification and settlement
- Remote: External facilitator service via HTTP API
- Hybrid: Local verification with remote settlement
"""

import os
import time
import logging
from typing import Any, Dict, Optional, Set, cast
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class BaseFacilitator(ABC):
    """Base facilitator interface.
    
    All facilitator implementations must inherit from this class and
    implement the verify() and settle() methods.
    """
    
    @abstractmethod
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment signature and requirements.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements for this resource
            
        Returns:
            Dict with 'isValid' (bool) and optional 'invalidReason', 'payer'
        """
        pass
    
    @abstractmethod
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment on blockchain.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements for this resource
            
        Returns:
            Dict with 'success' (bool), optional 'transaction', 'error', 'receipt'
        """
        pass


class LocalFacilitator(BaseFacilitator):
    """Local facilitator for self-hosted payment processing.
    
    Handles verification and settlement locally:
    - Verifies EIP-712 signatures
    - Checks balances (optional)
    - Tracks nonces to prevent replay attacks
    - Simulates transactions before broadcasting (optional)
    - Broadcasts EIP-3009 transferWithAuthorization transactions
    
    Configuration:
        config = {
            'private_key_env': 'X402_SIGNER_KEY',
            'rpc_url_env': 'X402_RPC_URL',
            'verify_balance': True,
            'simulate_before_send': True,
            'wait_for_receipt': False,
        }
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize local facilitator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._used_nonces: Set[str] = set()
        
        logger.info("LocalFacilitator initialized")
    
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment locally.
        
        Steps:
        1. Check x402 version
        2. Check scheme and network match
        3. Verify EIP-712 signature (if domain provided)
        4. Check authorization fields (amount, recipient, timing)
        5. Check nonce not used (replay protection)
        6. Check balance (optional)
        
        Args:
            payment: Payment payload
            requirements: Payment requirements
            
        Returns:
            {'isValid': True/False, 'invalidReason': str, 'payer': str}
        """
        try:
            # Step 1: Check x402 version
            if int(payment.get('x402Version', 0)) != 1:
                return {'isValid': False, 'invalidReason': 'invalid_x402_version'}
            
            # Step 2: Check scheme and network
            if payment.get('scheme') != 'exact' or requirements.get('scheme') != 'exact':
                return {'isValid': False, 'invalidReason': 'invalid_scheme'}
            
            if payment.get('network') != requirements.get('network'):
                return {'isValid': False, 'invalidReason': 'invalid_network'}
            
            # Extract payload
            payload = cast(Dict[str, Any], payment.get('payload', {}))
            auth = cast(Dict[str, Any], payload.get('authorization', {}))
            signature = cast(str, payload.get('signature', ''))
            
            # Step 3: Verify authorization fields
            to_addr = str(auth.get('to', '')).lower()
            value = str(auth.get('value', ''))
            now = int(time.time())
            valid_after = int(str(auth.get('validAfter', '0')) or 0)
            valid_before = int(str(auth.get('validBefore', '0')) or 0)
            nonce = auth.get('nonce')
            
            # Check recipient matches
            if to_addr != str(requirements.get('payTo', '')).lower():
                return {
                    'isValid': False,
                    'invalidReason': 'invalid_exact_evm_payload_recipient_mismatch'
                }
            
            # Check amount matches
            if value != str(requirements.get('maxAmountRequired', '')):
                return {
                    'isValid': False,
                    'invalidReason': 'invalid_exact_evm_payload_authorization_value'
                }
            
            # Check timing
            if now < valid_after:
                return {
                    'isValid': False,
                    'invalidReason': 'invalid_exact_evm_payload_authorization_valid_after'
                }
            
            if valid_before and now > valid_before:
                return {
                    'isValid': False,
                    'invalidReason': 'invalid_exact_evm_payload_authorization_valid_before'
                }
            
            # Step 4: Check nonce not used (replay protection)
            nonce_str = str(nonce) if nonce else ''
            if nonce_str in self._used_nonces:
                return {'isValid': False, 'invalidReason': 'nonce_already_used'}
            
            # Step 5: Verify EIP-712 signature (if full domain provided)
            domain = cast(Dict[str, Any], requirements.get('extra', {}))
            has_full_domain = all(
                k in domain for k in ('name', 'version', 'chainId', 'verifyingContract')
            )
            
            if has_full_domain and signature:
                try:
                    from eth_account import Account
                    from eth_account.messages import encode_typed_data
                except ImportError:
                    logger.warning("eth-account not available, skipping signature verification")
                else:
                    # Build EIP-712 message
                    types = {
                        'EIP712Domain': [
                            {'name': 'name', 'type': 'string'},
                            {'name': 'version', 'type': 'string'},
                            {'name': 'chainId', 'type': 'uint256'},
                            {'name': 'verifyingContract', 'type': 'address'},
                        ],
                        'TransferWithAuthorization': [
                            {'name': 'from', 'type': 'address'},
                            {'name': 'to', 'type': 'address'},
                            {'name': 'value', 'type': 'uint256'},
                            {'name': 'validAfter', 'type': 'uint256'},
                            {'name': 'validBefore', 'type': 'uint256'},
                            {'name': 'nonce', 'type': 'bytes32'},
                        ],
                    }
                    
                    message = {
                        'from': auth.get('from'),
                        'to': auth.get('to'),
                        'value': int(str(auth.get('value', '0')) or 0),
                        'validAfter': int(str(auth.get('validAfter', '0')) or 0),
                        'validBefore': int(str(auth.get('validBefore', '0')) or 0),
                        'nonce': auth.get('nonce'),
                    }
                    
                    full_message = {
                        'types': types,
                        'primaryType': 'TransferWithAuthorization',
                        'domain': domain,
                        'message': message,
                    }
                    
                    signable = encode_typed_data(full_message=full_message)
                    
                    try:
                        recovered = Account.recover_message(signable, signature=signature)
                    except Exception as e:
                        logger.warning(f"Signature verification failed: {e}")
                        return {
                            'isValid': False,
                            'invalidReason': 'invalid_exact_evm_payload_signature'
                        }
                    
                    if str(recovered).lower() != str(auth.get('from', '')).lower():
                        return {
                            'isValid': False,
                            'invalidReason': 'invalid_exact_evm_payload_signature'
                        }
            
            # Step 6: Verify balance (optional)
            if self._should_check_balance():
                balance_check = self._check_erc20_balance(
                    auth.get('from'),
                    requirements.get('asset'),
                    int(value),
                    payment.get('network')
                )
                if not balance_check.get('sufficient', False):
                    return {'isValid': False, 'invalidReason': 'insufficient_balance'}
            
            # All checks passed - mark nonce as used
            if nonce_str:
                self._used_nonces.add(nonce_str)
            
            logger.info(f"Payment verified from {auth.get('from')}")
            return {'isValid': True, 'payer': auth.get('from')}
            
        except Exception as exc:
            logger.error(f"Verification error: {exc}", exc_info=True)
            return {
                'isValid': False,
                'invalidReason': f'unexpected_verify_error: {exc}'
            }
    
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment by broadcasting EIP-3009 transaction.
        
        Steps:
        1. Load configuration (private key, RPC URL)
        2. Build transferWithAuthorization transaction
        3. Simulate transaction (optional)
        4. Sign transaction
        5. Broadcast to blockchain
        6. Wait for receipt (optional)
        
        Args:
            payment: Payment payload
            requirements: Payment requirements
            
        Returns:
            {'success': bool, 'transaction': str, 'error': str, 'receipt': dict}
        """
        try:
            logger.info("LocalFacilitator.settle called")
            
            # Load configuration
            local_cfg = self.config or {}
            priv_key_env = str(local_cfg.get('private_key_env', 'X402_SIGNER_KEY'))
            rpc_url_env = str(local_cfg.get('rpc_url_env', 'X402_RPC_URL'))
            wait_for_receipt = bool(local_cfg.get('wait_for_receipt', False))
            
            # Get private key from environment
            private_key = os.environ.get(priv_key_env, '')
            if not private_key:
                return {'success': False, 'error': f'{priv_key_env} not set'}
            
            # Get RPC URL from environment
            rpc_url = os.environ.get(rpc_url_env, '')
            if not rpc_url:
                return {'success': False, 'error': f'{rpc_url_env} not set'}
            
            logger.info(f"Connecting to RPC: {rpc_url}")
            
            # Initialize Web3
            try:
                from web3 import Web3
            except ImportError:
                return {'success': False, 'error': 'web3 package not installed'}
            
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Check connection
            if not w3.is_connected():
                return {'success': False, 'error': 'Failed to connect to RPC'}
            
            # Load account
            acct = w3.eth.account.from_key(private_key)
            logger.info(f"Loaded account: {acct.address}")
            
            # Extract payment data
            auth = cast(Dict[str, Any], payment.get('payload', {}).get('authorization', {}))
            from_addr = auth.get('from')
            to = auth.get('to')
            value = int(str(auth.get('value', '0')) or 0)
            valid_after = int(str(auth.get('validAfter', '0')) or 0)
            valid_before = int(str(auth.get('validBefore', '0')) or 0)
            nonce = auth.get('nonce')
            signature = cast(str, payment.get('payload', {}).get('signature', ''))
            
            # Parse signature (r, s, v)
            sig_hex = signature[2:] if signature.startswith('0x') else signature
            r = bytes.fromhex(sig_hex[0:64]) if len(sig_hex) >= 64 else b'\x00' * 32
            s = bytes.fromhex(sig_hex[64:128]) if len(sig_hex) >= 128 else b'\x00' * 32
            v = int(sig_hex[128:130], 16) if len(sig_hex) >= 130 else 27
            if v in (0, 1):
                v += 27
            
            # Normalize nonce to 32 bytes
            if isinstance(nonce, str) and nonce.startswith('0x'):
                nonce_bytes = bytes.fromhex(nonce[2:].zfill(64))
            elif isinstance(nonce, (bytes, bytearray)):
                nb = bytes(nonce)
                nonce_bytes = (b'\x00' * (32 - len(nb))) + nb if len(nb) < 32 else nb[:32]
            else:
                n_int = int(nonce or 0)
                nonce_bytes = n_int.to_bytes(32, byteorder='big')
            
            # Build transaction data
            # transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)
            selector = Web3.keccak(
                text='transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)'
            )[:4]
            
            try:
                from eth_abi import encode as abi_encode
            except ImportError:
                from eth_abi.abi import encode as abi_encode
            
            data = selector + abi_encode(
                ['address', 'address', 'uint256', 'uint256', 'uint256', 'bytes32', 'uint8', 'bytes32', 'bytes32'],
                [from_addr, to, value, valid_after, valid_before, nonce_bytes, v, r, s]
            )
            
            # Build transaction
            tx = {
                'to': requirements.get('asset'),
                'from': acct.address,
                'data': data,
                'value': 0,
                'nonce': w3.eth.get_transaction_count(acct.address),
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
            }
            
            # Step 3: Simulate transaction (optional)
            simulate = bool(local_cfg.get('simulate_before_send', True))
            if simulate:
                try:
                    simulation_tx = {
                        'to': requirements.get('asset'),
                        'from': from_addr,
                        'data': data,
                        'value': 0,
                    }
                    w3.eth.call(simulation_tx)
                    logger.info("Transaction simulation successful")
                except Exception as sim_error:
                    logger.error(f"Transaction simulation failed: {sim_error}")
                    return {
                        'success': False,
                        'error': f'Transaction simulation failed: {str(sim_error)}'
                    }
            
            # Step 4 & 5: Sign and broadcast
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            
            logger.info(f"Transaction broadcast: {tx_hash}")
            
            # Step 6: Wait for receipt (optional)
            if wait_for_receipt:
                try:
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    status = getattr(receipt, 'status', None) if hasattr(receipt, 'status') else receipt.get('status')
                    
                    logger.info(f"Transaction mined: {tx_hash} (status={status})")
                    
                    # Convert receipt to serializable dict
                    def convert_to_serializable(obj):
                        if hasattr(obj, 'hex'):
                            return obj.hex()
                        elif hasattr(obj, '__dict__') and not isinstance(obj, type):
                            return {k: convert_to_serializable(v) for k, v in dict(obj).items()}
                        elif isinstance(obj, dict):
                            return {k: convert_to_serializable(v) for k, v in obj.items()}
                        elif isinstance(obj, (list, tuple)):
                            return [convert_to_serializable(v) for v in obj]
                        else:
                            return obj
                    
                    receipt_dict = convert_to_serializable(dict(receipt))
                    
                    if status == 0:
                        logger.error(f"Transaction reverted: {tx_hash}")
                        return {
                            'success': False,
                            'error': 'Transaction reverted',
                            'transaction': tx_hash,
                            'receipt': receipt_dict
                        }
                    
                    return {
                        'success': True,
                        'transaction': tx_hash,
                        'receipt': receipt_dict
                    }
                except Exception as e:
                    logger.warning(f"Failed to wait for receipt: {e}")
                    return {'success': True, 'transaction': tx_hash}
            
            return {'success': True, 'transaction': tx_hash}
            
        except Exception as exc:
            logger.error(f"Settlement error: {exc}", exc_info=True)
            return {'success': False, 'error': str(exc)}
    
    def _should_check_balance(self) -> bool:
        """Check if balance verification is enabled."""
        return bool(self.config.get('verify_balance', False))
    
    def _check_erc20_balance(
        self,
        from_addr: str,
        asset: str,
        required_amount: int,
        network: str
    ) -> Dict[str, Any]:
        """Check if address has sufficient ERC20 balance."""
        try:
            from web3 import Web3
            
            rpc_url_env = str(self.config.get('rpc_url_env', 'X402_RPC_URL'))
            rpc_url = os.environ.get(rpc_url_env, '')
            
            if not rpc_url:
                return {'sufficient': True, 'checked': False}
            
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # balanceOf(address)
            balance_selector = Web3.keccak(text='balanceOf(address)')[:4]
            
            try:
                from eth_abi import encode as abi_encode
            except ImportError:
                from eth_abi.abi import encode as abi_encode
            
            data = balance_selector + abi_encode(['address'], [from_addr])
            
            result = w3.eth.call({'to': asset, 'data': data})
            balance = int.from_bytes(result, byteorder='big')
            
            logger.info(f"Balance check: {balance} >= {required_amount} = {balance >= required_amount}")
            
            return {
                'sufficient': balance >= required_amount,
                'balance': balance,
                'required': required_amount,
                'checked': True
            }
        except Exception as e:
            logger.warning(f"Failed to check balance: {e}")
            return {'sufficient': True, 'checked': False, 'error': str(e)}


class RemoteFacilitator(BaseFacilitator):
    """Remote facilitator using external HTTP API.
    
    Delegates verification and settlement to an external service.
    
    Configuration:
        config = {
            'url': 'https://facilitator.example.com',
            'headers': {'Authorization': 'Bearer token'},
            'timeout': 20,
        }
    """
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 20):
        """Initialize remote facilitator.
        
        Args:
            url: Base URL of facilitator service
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.headers = headers or {}
        self.timeout = timeout
        
        logger.info(f"RemoteFacilitator initialized: {self.url}")
    
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment via remote API.
        
        Args:
            payment: Payment payload
            requirements: Payment requirements
            
        Returns:
            {'isValid': bool, 'invalidReason': str, 'payer': str}
        """
        try:
            resp = httpx.post(
                f'{self.url}/verify',
                json={'payment': payment, 'requirements': requirements},
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return cast(Dict[str, Any], resp.json())
        except Exception as e:
            logger.error(f"Remote verify failed: {e}")
            return {'isValid': False, 'invalidReason': f'remote_error: {e}'}
    
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment via remote API.
        
        Args:
            payment: Payment payload
            requirements: Payment requirements
            
        Returns:
            {'success': bool, 'transaction': str, 'error': str}
        """
        try:
            resp = httpx.post(
                f'{self.url}/settle',
                json={'payment': payment, 'requirements': requirements},
                headers=self.headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return cast(Dict[str, Any], resp.json())
        except Exception as e:
            logger.error(f"Remote settle failed: {e}")
            return {'success': False, 'error': f'remote_error: {e}'}


class HybridFacilitator(BaseFacilitator):
    """Hybrid facilitator combining local and remote modes.
    
    - Verification: Try local first, fallback to remote
    - Settlement: Always use remote (for reliability)
    """
    
    def __init__(
        self,
        local: LocalFacilitator,
        remote: RemoteFacilitator,
        fallback_to_remote: bool = True
    ):
        """Initialize hybrid facilitator.
        
        Args:
            local: LocalFacilitator instance
            remote: RemoteFacilitator instance
            fallback_to_remote: Whether to fallback to remote on local errors
        """
        self.local = local
        self.remote = remote
        self.fallback_to_remote = fallback_to_remote
        
        logger.info("HybridFacilitator initialized")
    
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment - try local first, fallback to remote."""
        try:
            local_res = self.local.verify(payment, requirements)
            if local_res.get('isValid') is True:
                return local_res
            if not self.fallback_to_remote:
                return local_res
        except Exception as e:
            logger.warning(f"Local verify failed, falling back to remote: {e}")
        
        return self.remote.verify(payment, requirements)
    
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment - always use remote for reliability."""
        return self.remote.settle(payment, requirements)


def get_facilitator(config: Any) -> BaseFacilitator:
    """Factory function to create facilitator based on configuration.
    
    Args:
        config: X402Config instance
        
    Returns:
        BaseFacilitator instance (Local, Remote, or Hybrid)
        
    Example:
        >>> from x402_connector.core.config import X402Config
        >>> config = X402Config(
        ...     network='base',
        ...     price='$0.01',
        ...     pay_to_address='0x...',
        ...     facilitator_mode='local'
        ... )
        >>> facilitator = get_facilitator(config)
    """
    mode = getattr(config, 'facilitator_mode', 'local')
    
    if mode == 'local':
        local_cfg = getattr(config, 'local', None)
        local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
        return LocalFacilitator(config=local_dict)
    
    elif mode == 'remote':
        remote_cfg = getattr(config, 'remote', None)
        if not remote_cfg:
            raise ValueError("remote facilitator config required when mode='remote'")
        
        url = getattr(remote_cfg, 'url', '')
        headers = getattr(remote_cfg, 'headers', None)
        timeout = getattr(remote_cfg, 'timeout', 20)
        
        return RemoteFacilitator(url=url, headers=headers, timeout=timeout)
    
    elif mode == 'hybrid':
        local_cfg = getattr(config, 'local', None)
        local_dict = local_cfg.__dict__ if hasattr(local_cfg, '__dict__') else (local_cfg or {})
        local = LocalFacilitator(config=local_dict)
        
        remote_cfg = getattr(config, 'remote', None)
        if not remote_cfg:
            raise ValueError("remote facilitator config required when mode='hybrid'")
        
        url = getattr(remote_cfg, 'url', '')
        headers = getattr(remote_cfg, 'headers', None)
        timeout = getattr(remote_cfg, 'timeout', 20)
        
        remote = RemoteFacilitator(url=url, headers=headers, timeout=timeout)
        
        return HybridFacilitator(local, remote)
    
    else:
        raise ValueError(f"Unknown facilitator mode: {mode}")

