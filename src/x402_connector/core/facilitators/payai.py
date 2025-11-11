"""PayAI facilitator for x402 payment processing.

PayAI (https://payai.network) provides a facilitator service for x402 payments
on Solana. This module implements the remote facilitator interface for PayAI.

PayAI handles:
- Payment verification
- Transaction settlement
- Network fee management
- Multiple Solana networks (mainnet, devnet, testnet)

Documentation: https://docs.payai.network/
"""

import os
import logging
import requests
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PayAIFacilitator:
    """PayAI remote facilitator for x402 payment processing.
    
    Delegates payment verification and settlement to PayAI's facilitator service.
    
    Configuration:
        config = {
            'facilitator_url': 'https://facilitator.payai.network',
            'api_key_env': 'PAYAI_API_KEY',  # Optional: for authenticated endpoints
            'timeout': 30,  # Request timeout in seconds
        }
    
    Example:
        >>> facilitator = PayAIFacilitator({
        ...     'facilitator_url': 'https://facilitator.payai.network',
        ... })
        >>> 
        >>> result = facilitator.verify(payment, requirements)
        >>> if result['isValid']:
        ...     settlement = facilitator.settle(payment, requirements)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize PayAI facilitator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.facilitator_url = self.config.get(
            'facilitator_url',
            os.getenv('PAYAI_FACILITATOR_URL', 'https://facilitator.payai.network')
        )
        
        # Get API key from environment if specified
        api_key_env = self.config.get('api_key_env', 'PAYAI_API_KEY')
        self.api_key = os.getenv(api_key_env)
        
        self.timeout = self.config.get('timeout', 30)
        
        logger.info(f"PayAI facilitator initialized: {self.facilitator_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for PayAI API requests.
        
        Returns:
            Headers dictionary with optional Authorization
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'x402-connector/0.1.0',
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment via PayAI facilitator.
        
        Sends payment and requirements to PayAI for verification.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements from 402 response
            
        Returns:
            {'isValid': True/False, 'invalidReason': str, 'payer': str}
        """
        try:
            # PayAI verification endpoint
            verify_url = f"{self.facilitator_url}/verify"
            
            payload = {
                'payment': payment,
                'requirements': requirements,
            }
            
            logger.debug(f"Verifying payment with PayAI: {verify_url}")
            
            response = requests.post(
                verify_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"PayAI verification result: {result.get('isValid', False)}")
                return result
            else:
                logger.error(f"PayAI verification failed: {response.status_code} - {response.text}")
                return {
                    'isValid': False,
                    'invalidReason': f'facilitator_error: HTTP {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"PayAI verification timeout after {self.timeout}s")
            return {
                'isValid': False,
                'invalidReason': 'facilitator_timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"PayAI verification request failed: {e}")
            return {
                'isValid': False,
                'invalidReason': f'facilitator_error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"PayAI verification error: {e}", exc_info=True)
            return {
                'isValid': False,
                'invalidReason': f'unexpected_error: {str(e)}'
            }
    
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment via PayAI facilitator.
        
        Sends verified payment to PayAI for settlement on Solana blockchain.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements from 402 response
            
        Returns:
            {'success': bool, 'transaction': str, 'error': str}
        """
        try:
            # PayAI settlement endpoint
            settle_url = f"{self.facilitator_url}/settle"
            
            payload = {
                'payment': payment,
                'requirements': requirements,
            }
            
            logger.info(f"Settling payment with PayAI: {settle_url}")
            
            response = requests.post(
                settle_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                tx_hash = result.get('transaction', result.get('transactionHash'))
                
                if tx_hash:
                    logger.info(f"PayAI settlement successful: {tx_hash}")
                    return {
                        'success': True,
                        'transaction': tx_hash,
                    }
                else:
                    logger.warning("PayAI settlement response missing transaction hash")
                    return {
                        'success': False,
                        'error': 'No transaction hash returned'
                    }
            else:
                logger.error(f"PayAI settlement failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Facilitator error: HTTP {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"PayAI settlement timeout after {self.timeout}s")
            return {
                'success': False,
                'error': f'Settlement timeout after {self.timeout}s'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"PayAI settlement request failed: {e}")
            return {
                'success': False,
                'error': f'Facilitator request failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"PayAI settlement error: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def get_durable_nonce_info(self) -> Optional[Dict[str, Any]]:
        """Get durable nonce information from PayAI facilitator.
        
        PayAI may provide durable nonce accounts for long-lived transactions.
        
        Returns:
            Dict with nonce account and current nonce value, or None
        """
        try:
            nonce_url = f"{self.facilitator_url}/nonce"
            
            response = requests.get(
                nonce_url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                nonce_info = response.json()
                logger.info(f"PayAI durable nonce available: {nonce_info.get('account', 'unknown')[:16]}...")
                return nonce_info
            else:
                logger.debug(f"PayAI durable nonce not available: {response.status_code}")
                return None
                
        except Exception as e:
            logger.debug(f"PayAI durable nonce request failed: {e}")
            return None

