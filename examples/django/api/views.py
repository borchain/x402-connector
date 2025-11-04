"""Example API views demonstrating x402 payment integration on Solana."""

import os
import random
import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.conf import settings

from x402_connector.django import require_payment

logger = logging.getLogger(__name__)


# =============================================================================
# DEMO PAGE
# =============================================================================

def index(request):
    """Demo homepage with interactive buttons."""
    return render(request, 'index.html')


# =============================================================================
# BALANCE CHECK API
# =============================================================================

@require_http_methods(["GET"])
def check_balances(request):
    """Check balances for hot wallet, cold wallet, and user wallet.
    
    Query params:
        user_address: Optional user wallet address to check
    """
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey
        
        # Get config
        network = settings.X402_CONFIG.get('network', 'solana-devnet')
        rpc_urls = {
            'solana-mainnet': 'https://api.mainnet-beta.solana.com',
            'solana-devnet': 'https://api.devnet.solana.com',
            'solana-testnet': 'https://api.testnet.solana.com',
        }
        rpc_url = rpc_urls.get(network, 'https://api.devnet.solana.com')
        
        client = Client(rpc_url)
        
        # Get addresses
        cold_wallet = settings.X402_CONFIG.get('pay_to_address', '')
        hot_wallet = None
        
        # Try to get hot wallet from signer key
        signer_key = os.environ.get('X402_SIGNER_KEY', '')
        if signer_key:
            try:
                import base58
                from solders.keypair import Keypair
                private_key_bytes = base58.b58decode(signer_key)
                keypair = Keypair.from_bytes(private_key_bytes)
                hot_wallet = str(keypair.pubkey())
            except:
                pass
        
        # USDC mint addresses
        usdc_mints = {
            'solana-mainnet': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'solana-devnet': 'Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr',
            'solana-testnet': '8zGuJQqwhZafTah7Uc7Z4tXRnguqkn5KLFAP8oV6PHe2',
        }
        usdc_mint = usdc_mints.get(network)
        
        balances = {}
        
        # Check hot wallet balances
        if hot_wallet and not hot_wallet.startswith('REPLACE'):
            balances['hot_wallet'] = _get_wallet_balances(client, hot_wallet, usdc_mint)
            balances['hot_wallet']['address'] = hot_wallet
        else:
            balances['hot_wallet'] = {'address': 'Not configured', 'sol': 0, 'usdc': 0}
        
        # Check cold wallet balances
        if cold_wallet and not cold_wallet.startswith('REPLACE'):
            balances['cold_wallet'] = _get_wallet_balances(client, cold_wallet, usdc_mint)
            balances['cold_wallet']['address'] = cold_wallet
        else:
            balances['cold_wallet'] = {'address': 'Not configured', 'sol': 0, 'usdc': 0}
        
        # Check user wallet if provided
        user_address = request.GET.get('user_address')
        if user_address:
            balances['user_wallet'] = _get_wallet_balances(client, user_address, usdc_mint)
            balances['user_wallet']['address'] = user_address
        else:
            balances['user_wallet'] = {'address': 'Not connected', 'sol': 0, 'usdc': 0}
        
        # Also return RPC URL for frontend to use
        rpc_url = rpc_urls.get(network, 'https://api.devnet.solana.com')
        if settings.X402_CONFIG.get('rpc_url'):
            rpc_url = settings.X402_CONFIG['rpc_url']
        
        return JsonResponse({
            'balances': balances,
            'network': network,
            'rpc_url': rpc_url,  # Frontend will use this
            'timestamp': timezone.now().isoformat(),
        })
        
    except ImportError:
        return JsonResponse({
            'error': 'Solana libraries not installed',
            'detail': 'Install with: pip install solana solders base58',
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'balances': {
                'hot_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                'cold_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                'user_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
            }
        })


def _get_wallet_balances(client, address_str, usdc_mint):
    """Get SOL and USDC balances for an address."""
    try:
        from solders.pubkey import Pubkey
        from solders.token.associated import get_associated_token_address
        
        pubkey = Pubkey.from_string(address_str)
        
        # Get SOL balance
        sol_balance = client.get_balance(pubkey).value / 1_000_000_000  # lamports to SOL
        
        # Get USDC balance
        usdc_balance = 0.0
        if usdc_mint:
            try:
                # Get associated token account address
                usdc_mint_pubkey = Pubkey.from_string(usdc_mint)
                token_account = get_associated_token_address(pubkey, usdc_mint_pubkey)
                
                # Get token account balance
                token_response = client.get_token_account_balance(token_account)
                if token_response.value:
                    # Convert from atomic units (USDC has 6 decimals)
                    usdc_balance = float(token_response.value.amount) / 1_000_000
            except Exception as e:
                # Token account might not exist yet (no USDC held)
                logger.debug(f"No USDC account for {address_str[:8]}...: {e}")
                usdc_balance = 0.0
        
        return {
            'sol': round(sol_balance, 6),
            'usdc': round(usdc_balance, 2),
        }
    except Exception as e:
        return {'sol': 0, 'usdc': 0, 'error': str(e)}


# =============================================================================
# RANDOM NUMBER API
# =============================================================================

@require_http_methods(["GET"])
def random_number(request):
    """Free random number generator (1-6).
    
    No payment required - publicly accessible.
    """
    number = random.randint(1, 6)
    
    return JsonResponse({
        'number': number,
        'range': '1-6',
        'type': 'free',
        'timestamp': timezone.now().isoformat(),
    })


@require_http_methods(["GET"])
@require_payment(price='$0.01')
def premium_random_number(request):
    """Premium random number generator (1000000-9999999).
    
    Requires payment via x402 protocol on Solana blockchain.
    Payment is handled automatically by the @require_payment decorator.
    """
    number = random.randint(1000000, 9999999)
    
    return JsonResponse({
        'number': number,
        'range': '1000000-9999999',
        'type': 'premium',
        'digits': 7,
        'timestamp': timezone.now().isoformat(),
        'note': 'This number required payment!',
    })
