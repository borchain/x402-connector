"""Tornado application for x402-connector example.

This demonstrates how to integrate x402 payment requirements
into a Tornado application using Solana blockchain.
"""

import os
import random
import logging
import json
from tornado import web, ioloop
from tornado.options import define, options
from dotenv import load_dotenv

from x402_connector.tornado import X402Middleware, require_payment

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Define command line options
define("port", default=8888, help="Port to listen on", type=int)
define("debug", default=False, help="Run in debug mode", type=bool)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('TORNADO_DEBUG', 'False') == 'True' else logging.INFO,
    format='%(levelname)s %(asctime)s %(module)s %(message)s',
)
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST HANDLERS
# =============================================================================

class IndexHandler(web.RequestHandler):
    """Homepage with interactive demo."""
    
    def get(self):
        """Render the demo page."""
        self.render('index.html')


class RandomHandler(web.RequestHandler):
    """Free random number generator (1-6)."""
    
    x402_skip = True  # Skip payment verification for this endpoint
    
    def get(self):
        """Generate a free random number."""
        number = random.randint(1, 6)
        
        from datetime import datetime
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
            'number': number,
            'range': '1-6',
            'type': 'free',
            'timestamp': datetime.utcnow().isoformat(),
        }))


class PremiumRandomHandler(web.RequestHandler):
    """Premium random number generator (requires payment)."""
    
    @require_payment(price='$0.01')
    async def get(self):
        """Generate a premium random number (requires payment)."""
        number = random.randint(1000000, 9999999)
        
        from datetime import datetime
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({
            'number': number,
            'range': '1000000-9999999',
            'type': 'premium',
            'digits': 7,
            'timestamp': datetime.utcnow().isoformat(),
            'note': 'This number required payment!',
        }))


class BalancesHandler(web.RequestHandler):
    """Check balances for hot wallet, cold wallet, and user wallet."""
    
    x402_skip = True  # Skip payment verification
    
    async def get(self):
        """Get wallet balances."""
        try:
            from solana.rpc.api import Client
            from solders.pubkey import Pubkey
            
            # Get config from app settings
            network = self.application.settings.get('x402_config', {}).get('network', 'solana-devnet')
            rpc_urls = {
                'solana-mainnet': 'https://api.mainnet-beta.solana.com',
                'solana-devnet': 'https://api.devnet.solana.com',
                'solana-testnet': 'https://api.testnet.solana.com',
            }
            rpc_url = rpc_urls.get(network, 'https://api.devnet.solana.com')
            
            client = Client(rpc_url)
            
            # Get addresses
            cold_wallet = self.application.settings.get('x402_config', {}).get('pay_to_address', '')
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
                balances['hot_wallet'] = self._get_wallet_balances(client, hot_wallet, usdc_mint)
                balances['hot_wallet']['address'] = hot_wallet
            else:
                balances['hot_wallet'] = {'address': 'Not configured', 'sol': 0, 'usdc': 0}
            
            # Check cold wallet balances
            if cold_wallet and not cold_wallet.startswith('REPLACE'):
                balances['cold_wallet'] = self._get_wallet_balances(client, cold_wallet, usdc_mint)
                balances['cold_wallet']['address'] = cold_wallet
            else:
                balances['cold_wallet'] = {'address': 'Not configured', 'sol': 0, 'usdc': 0}
            
            # Check user wallet if provided
            user_address = self.get_argument('user_address', None)
            if user_address:
                balances['user_wallet'] = self._get_wallet_balances(client, user_address, usdc_mint)
                balances['user_wallet']['address'] = user_address
            else:
                balances['user_wallet'] = {'address': 'Not connected', 'sol': 0, 'usdc': 0}
            
            # Also return RPC URL for frontend to use
            from datetime import datetime
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({
                'balances': balances,
                'network': network,
                'rpc_url': rpc_url,
                'timestamp': datetime.utcnow().isoformat(),
            }))
            
        except ImportError:
            self.set_status(500)
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({
                'error': 'Solana libraries not installed',
                'detail': 'Install with: pip install solana solders base58',
            }))
        except Exception as e:
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({
                'error': str(e),
                'balances': {
                    'hot_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                    'cold_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                    'user_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                }
            }))
    
    def _get_wallet_balances(self, client, address_str, usdc_mint):
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

def make_app():
    """Create and configure the Tornado application."""
    
    # x402 Configuration
    x402_config = {
        # Required: Your Solana address for receiving payments
        'pay_to_address': os.getenv(
            'X402_PAY_TO_ADDRESS',
            'REPLACE_WITH_YOUR_SOLANA_ADDRESS_44_CHARS'  # Change this!
        ),
        
        # Optional: Default price
        'price': os.getenv('X402_PRICE', '$0.01'),
        
        # Optional: Solana network
        'network': os.getenv('X402_NETWORK', 'solana-devnet'),
        
        # Protected paths - empty by default, use @require_payment() decorator instead
        'protected_paths': [],
        
        # Optional: Description
        'description': 'Premium Random Number API',
        
        # Debug mode (True = simulated, False = requires pre-signed transactions)
        'debug_mode': os.getenv('X402_DEBUG_MODE', 'True').lower() == 'true',
        
        # Optional: Custom RPC URL
        'rpc_url': os.getenv('X402_RPC_URL'),
        
        # Optional: Durable nonce
        'use_durable_nonce': os.getenv('X402_USE_DURABLE_NONCE', 'False').lower() == 'true',
        'nonce_account_env': 'X402_NONCE_ACCOUNT',
    }
    
    # Create application
    app = web.Application(
        [
            (r'/', IndexHandler),
            (r'/api/random', RandomHandler),
            (r'/api/premium/random', PremiumRandomHandler),
            (r'/api/balances', BalancesHandler),
        ],
        template_path=os.path.join(os.path.dirname(__file__), 'templates'),
        static_path=os.path.join(os.path.dirname(__file__), 'static'),
        debug=options.debug,
        x402_config=x402_config,
    )
    
    # Initialize x402 middleware
    X402Middleware(app, **x402_config)
    
    return app


def main():
    """Start the Tornado server."""
    # Parse command line options
    options.parse_command_line()
    
    # Create application
    app = make_app()
    
    # Display configuration
    config = app.settings.get('x402_config', {})
    print("=" * 70)
    print("x402-connector - Solana Payment SDK (Tornado)")
    print("=" * 70)
    print(f"Network:        {config.get('network')}")
    print(f"Pay To:         {config.get('pay_to_address')}")
    print(f"Default Price:  {config.get('price')}")
    print(f"Port:           {options.port}")
    print("=" * 70)
    
    # Validate configuration
    pay_to = config.get('pay_to_address', '')
    if not pay_to or len(pay_to) < 32 or pay_to.startswith('REPLACE'):
        print("⚠️  WARNING: X402_PAY_TO_ADDRESS is not properly configured!")
        print("   Set a valid Solana address (base58 format, 32-44 chars)")
        print("   Set environment variable: X402_PAY_TO_ADDRESS=YourAddress")
        print("=" * 70)
    
    # Start server
    app.listen(options.port)
    print(f"\n🚀 Server running at http://localhost:{options.port}")
    print(f"   Demo page: http://localhost:{options.port}")
    print(f"   Free API:  http://localhost:{options.port}/api/random")
    print(f"   Paid API:  http://localhost:{options.port}/api/premium/random\n")
    
    # Start event loop
    ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()

