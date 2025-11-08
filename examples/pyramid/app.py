"""Pyramid application for x402-connector example.

This demonstrates how to integrate x402 payment requirements
into a Pyramid application using Solana blockchain.
"""

import os
import random
import logging
import json
from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from dotenv import load_dotenv

from x402_connector.pyramid import require_payment, includeme

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('PYRAMID_DEBUG', 'False') == 'True' else logging.INFO,
    format='%(levelname)s %(asctime)s %(module)s %(message)s',
)
logger = logging.getLogger(__name__)


# =============================================================================
# VIEW FUNCTIONS
# =============================================================================

def index_view(request):
    """Homepage with interactive demo."""
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    with open(template_path, 'r') as f:
        html_content = f.read()
    return Response(html_content, content_type='text/html')


def random_view(request):
    """Free random number generator (1-6)."""
    number = random.randint(1, 6)
    
    from datetime import datetime
    return Response(
        json.dumps({
            'number': number,
            'range': '1-6',
            'type': 'free',
            'timestamp': datetime.utcnow().isoformat(),
        }),
        content_type='application/json'
    )


@require_payment(price='$0.01')
def premium_random_view(request):
    """Premium random number generator (requires payment)."""
    number = random.randint(1000000, 9999999)
    
    from datetime import datetime
    return Response(
        json.dumps({
            'number': number,
            'range': '1000000-9999999',
            'type': 'premium',
            'digits': 7,
            'timestamp': datetime.utcnow().isoformat(),
            'note': 'This number required payment!',
        }),
        content_type='application/json'
    )


def balances_view(request):
    """Check balances for hot wallet, cold wallet, and user wallet."""
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey
        
        # Get config from registry
        settings = request.registry.settings
        network = settings.get('x402.network', 'solana-devnet')
        rpc_urls = {
            'solana-mainnet': 'https://api.mainnet-beta.solana.com',
            'solana-devnet': 'https://api.devnet.solana.com',
            'solana-testnet': 'https://api.testnet.solana.com',
        }
        rpc_url = rpc_urls.get(network, 'https://api.devnet.solana.com')
        
        client = Client(rpc_url)
        
        # Get addresses
        cold_wallet = settings.get('x402.pay_to_address', '')
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
        user_address = request.params.get('user_address')
        if user_address:
            balances['user_wallet'] = _get_wallet_balances(client, user_address, usdc_mint)
            balances['user_wallet']['address'] = user_address
        else:
            balances['user_wallet'] = {'address': 'Not connected', 'sol': 0, 'usdc': 0}
        
        from datetime import datetime
        return Response(
            json.dumps({
                'balances': balances,
                'network': network,
                'rpc_url': rpc_url,
                'timestamp': datetime.utcnow().isoformat(),
            }),
            content_type='application/json'
        )
        
    except ImportError:
        return Response(
            json.dumps({
                'error': 'Solana libraries not installed',
                'detail': 'Install with: pip install solana solders base58',
            }),
            content_type='application/json',
            status=500
        )
    except Exception as e:
        return Response(
            json.dumps({
                'error': str(e),
                'balances': {
                    'hot_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                    'cold_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                    'user_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                }
            }),
            content_type='application/json'
        )


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
# APPLICATION SETUP
# =============================================================================

def main():
    """Create and start the Pyramid application."""
    
    # x402 Configuration
    settings = {
        # x402 settings (prefix with 'x402.')
        'x402.pay_to_address': os.getenv(
            'X402_PAY_TO_ADDRESS',
            'REPLACE_WITH_YOUR_SOLANA_ADDRESS_44_CHARS'
        ),
        'x402.price': os.getenv('X402_PRICE', '$0.01'),
        'x402.network': os.getenv('X402_NETWORK', 'solana-devnet'),
        'x402.protected_paths': [],  # Use decorator instead
        'x402.description': 'Premium Random Number API',
        'x402.debug_mode': os.getenv('X402_DEBUG_MODE', 'True').lower() == 'true',
        'x402.rpc_url': os.getenv('X402_RPC_URL', ''),
        'x402.use_durable_nonce': os.getenv('X402_USE_DURABLE_NONCE', 'False').lower() == 'true',
        'x402.nonce_account_env': 'X402_NONCE_ACCOUNT',
    }
    
    # Create Pyramid configurator
    config = Configurator(settings=settings)
    
    # Include x402 tween
    config.include('x402_connector.pyramid')
    
    # Add routes
    config.add_route('index', '/')
    config.add_route('random', '/api/random')
    config.add_route('premium_random', '/api/premium/random')
    config.add_route('balances', '/api/balances')
    
    # Add views
    config.add_view(index_view, route_name='index')
    config.add_view(random_view, route_name='random')
    config.add_view(premium_random_view, route_name='premium_random')
    config.add_view(balances_view, route_name='balances')
    
    # Create WSGI app
    app = config.make_wsgi_app()
    
    # Display configuration
    print("=" * 70)
    print("x402-connector - Solana Payment SDK (Pyramid)")
    print("=" * 70)
    print(f"Network:        {settings['x402.network']}")
    print(f"Pay To:         {settings['x402.pay_to_address']}")
    print(f"Default Price:  {settings['x402.price']}")
    print(f"Port:           {os.getenv('PORT', '6543')}")
    print("=" * 70)
    
    # Validate configuration
    pay_to = settings['x402.pay_to_address']
    if not pay_to or len(pay_to) < 32 or pay_to.startswith('REPLACE'):
        print("⚠️  WARNING: X402_PAY_TO_ADDRESS is not properly configured!")
        print("   Set a valid Solana address (base58 format, 32-44 chars)")
        print("   Set environment variable: X402_PAY_TO_ADDRESS=YourAddress")
        print("=" * 70)
    
    # Start server
    port = int(os.getenv('PORT', '6543'))
    server = make_server('0.0.0.0', port, app)
    
    print(f"\n🚀 Server running at http://localhost:{port}")
    print(f"   Demo page: http://localhost:{port}")
    print(f"   Free API:  http://localhost:{port}/api/random")
    print(f"   Paid API:  http://localhost:{port}/api/premium/random\n")
    
    server.serve_forever()


if __name__ == '__main__':
    main()

