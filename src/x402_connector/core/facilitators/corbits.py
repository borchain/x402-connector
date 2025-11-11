"""Corbits facilitator for x402 payment processing.

Corbits (https://corbits.dev) provides a facilitator service and marketplace
for x402 payments on Solana. This module implements the remote facilitator
interface for Corbits.

Corbits features:
- Payment verification and settlement
- API marketplace integration
- Analytics dashboard
- Multiple Solana networks support

Documentation: https://docs.corbits.dev/
"""

import os
import logging
import requests
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CorbitsFacilitator:
    """Corbits remote facilitator for x402 payment processing.
    
    Delegates payment verification and settlement to Corbits' facilitator service.
    
    Configuration:
        config = {
            'facilitator_url': 'https://api.corbits.dev',
            'api_key_env': 'CORBITS_API_KEY',  # Required for most operations
            'timeout': 30,  # Request timeout in seconds
        }
    
    Example:
        >>> facilitator = CorbitsFacilitator({
        ...     'facilitator_url': 'https://api.corbits.dev',
        ...     'api_key_env': 'CORBITS_API_KEY',
        ... })
        >>> 
        >>> result = facilitator.verify(payment, requirements)
        >>> if result['isValid']:
        ...     settlement = facilitator.settle(payment, requirements)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Corbits facilitator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.facilitator_url = self.config.get(
            'facilitator_url',
            os.getenv('CORBITS_FACILITATOR_URL', 'https://api.corbits.dev')
        )
        
        # Get API key from environment
        api_key_env = self.config.get('api_key_env', 'CORBITS_API_KEY')
        self.api_key = os.getenv(api_key_env)
        
        if not self.api_key:
            logger.warning(
                f"⚠️  {api_key_env} not set - Corbits requires an API key"
            )
        
        self.timeout = self.config.get('timeout', 30)
        
        logger.info(f"Corbits facilitator initialized: {self.facilitator_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Corbits API requests.
        
        Returns:
            Headers dictionary with Authorization
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'x402-connector/0.1.0',
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    def verify(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Verify payment via Corbits facilitator.
        
        Sends payment and requirements to Corbits for verification.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements from 402 response
            
        Returns:
            {'isValid': True/False, 'invalidReason': str, 'payer': str}
        """
        try:
            # Corbits verification endpoint
            verify_url = f"{self.facilitator_url}/v1/payments/verify"
            
            payload = {
                'payment': payment,
                'requirements': requirements,
            }
            
            logger.debug(f"Verifying payment with Corbits: {verify_url}")
            
            response = requests.post(
                verify_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                is_valid = result.get('isValid', result.get('valid', False))
                logger.info(f"Corbits verification result: {is_valid}")
                
                # Normalize response format
                return {
                    'isValid': is_valid,
                    'invalidReason': result.get('invalidReason', result.get('reason')),
                    'payer': result.get('payer', result.get('from')),
                }
            elif response.status_code == 401:
                logger.error("Corbits API key invalid or missing")
                return {
                    'isValid': False,
                    'invalidReason': 'facilitator_auth_error'
                }
            else:
                logger.error(f"Corbits verification failed: {response.status_code} - {response.text}")
                return {
                    'isValid': False,
                    'invalidReason': f'facilitator_error: HTTP {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"Corbits verification timeout after {self.timeout}s")
            return {
                'isValid': False,
                'invalidReason': 'facilitator_timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Corbits verification request failed: {e}")
            return {
                'isValid': False,
                'invalidReason': f'facilitator_error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Corbits verification error: {e}", exc_info=True)
            return {
                'isValid': False,
                'invalidReason': f'unexpected_error: {str(e)}'
            }
    
    def settle(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Settle payment via Corbits facilitator.
        
        Sends verified payment to Corbits for settlement on Solana blockchain.
        
        Args:
            payment: Payment payload from X-PAYMENT header
            requirements: Payment requirements from 402 response
            
        Returns:
            {'success': bool, 'transaction': str, 'error': str}
        """
        try:
            # Corbits settlement endpoint
            settle_url = f"{self.facilitator_url}/v1/payments/settle"
            
            payload = {
                'payment': payment,
                'requirements': requirements,
            }
            
            logger.info(f"Settling payment with Corbits: {settle_url}")
            
            response = requests.post(
                settle_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # Handle response
            if response.status_code == 200:
                result = response.json()
                tx_hash = result.get('transaction', result.get('transactionHash', result.get('txHash')))
                
                if tx_hash:
                    logger.info(f"Corbits settlement successful: {tx_hash}")
                    return {
                        'success': True,
                        'transaction': tx_hash,
                        'receipt': result.get('receipt'),
                    }
                else:
                    logger.warning("Corbits settlement response missing transaction hash")
                    return {
                        'success': False,
                        'error': 'No transaction hash returned'
                    }
            elif response.status_code == 401:
                logger.error("Corbits API key invalid or missing")
                return {
                    'success': False,
                    'error': 'Authentication failed - check CORBITS_API_KEY'
                }
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_data.get('message', error_msg))
                except:
                    pass
                
                logger.error(f"Corbits settlement failed: {response.status_code} - {error_msg}")
                return {
                    'success': False,
                    'error': f'Facilitator error: {error_msg}'
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"Corbits settlement timeout after {self.timeout}s")
            return {
                'success': False,
                'error': f'Settlement timeout after {self.timeout}s'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Corbits settlement request failed: {e}")
            return {
                'success': False,
                'error': f'Facilitator request failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Corbits settlement error: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def get_durable_nonce_info(self) -> Optional[Dict[str, Any]]:
        """Get durable nonce information from Corbits facilitator.
        
        Corbits may provide durable nonce accounts for long-lived transactions.
        
        Returns:
            Dict with nonce account and current nonce value, or None
        """
        try:
            nonce_url = f"{self.facilitator_url}/v1/nonce"
            
            response = requests.get(
                nonce_url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                nonce_info = response.json()
                logger.info(f"Corbits durable nonce available: {nonce_info.get('account', 'unknown')[:16]}...")
                return nonce_info
            else:
                logger.debug(f"Corbits durable nonce not available: {response.status_code}")
                return None
                
        except Exception as e:
            logger.debug(f"Corbits durable nonce request failed: {e}")
            return None

