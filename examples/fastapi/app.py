"""FastAPI application for x402-connector example.

This demonstrates how to integrate x402 payment requirements
into a FastAPI application using Solana blockchain.
"""

import os
import random
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from x402_connector.fastapi import X402Middleware, require_payment

# Load environment variables from .env file
print("=" * 70)
print("Loading .env file...")
print("=" * 70)

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print(f"✅ Found .env file at: {env_path}")
    load_dotenv(env_path)
    print("✅ .env file loaded successfully")
    
    # Check if X402_SIGNER_KEY is loaded
    signer_key = os.getenv('X402_SIGNER_KEY', '')
    if signer_key and len(signer_key) > 10:
        print(f"🔑 X402_SIGNER_KEY: Loaded ({len(signer_key)} chars)")
        print(f"   Preview: {signer_key[:20]}...{signer_key[-8:]}")
        print("   Status: ✅ REAL MODE (transactions will be broadcast)")
    else:
        print("⚠️  X402_SIGNER_KEY: NOT SET")
        print("   Status: ⚠️  DEMO MODE (signatures verified, no real transactions)")
        print("   To enable: Set X402_SIGNER_KEY in .env file")
else:
    print(f"⚠️  No .env file found at: {env_path}")
    print("   Copy env.example to .env and configure your keys")

print("=" * 70)
print()

# Initialize FastAPI app
app = FastAPI(
    title="x402 Random Number Generator",
    description="FastAPI + Solana Micropayments Demo",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('FASTAPI_DEBUG', 'False') == 'True' else logging.INFO,
    format='%(levelname)s %(asctime)s %(module)s %(message)s',
)
logger = logging.getLogger(__name__)

# ========================================================================
# x402 Configuration - Solana Payment Required
# ========================================================================

app.add_middleware(
    X402Middleware,
    # Required: Your Solana address for receiving payments
    pay_to_address=os.getenv(
        'X402_PAY_TO_ADDRESS',
        'REPLACE_WITH_YOUR_SOLANA_ADDRESS_44_CHARS'
    ),
    
    # Optional: Default price
    price=os.getenv('X402_PRICE', '$0.01'),
    
    # Optional: Solana network
    network=os.getenv('X402_NETWORK', 'solana-devnet'),
    
    # Protected paths - empty by default, use @require_payment() decorator instead
    protected_paths=[],
    
    # Optional: Description
    description='Premium Random Number API',
    
    # Debug mode (True = simulated, False = requires pre-signed transactions)
    debug_mode=os.getenv('X402_DEBUG_MODE', 'True').lower() == 'true',
    
    # Optional: Custom RPC URL
    rpc_url=os.getenv('X402_RPC_URL'),
    
    # Optional: Durable nonce
    use_durable_nonce=os.getenv('X402_USE_DURABLE_NONCE', 'False').lower() == 'true',
    nonce_account_env='X402_NONCE_ACCOUNT',
)

# Setup templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Display current configuration
print("=" * 70)
print("x402-connector - Solana Payment SDK")
print("=" * 70)
print(f"Network:        {os.getenv('X402_NETWORK', 'solana-devnet')}")
print(f"Pay To:         {os.getenv('X402_PAY_TO_ADDRESS', 'NOT SET')}")
print(f"Default Price:  {os.getenv('X402_PRICE', '$0.01')}")
print("=" * 70)

# Validate configuration
pay_to = os.getenv('X402_PAY_TO_ADDRESS', '')
if not pay_to or len(pay_to) < 32 or pay_to.startswith('REPLACE'):
    print("⚠️  WARNING: X402_PAY_TO_ADDRESS is not properly configured!")
    print("   Set a valid Solana address (base58 format, 32-44 chars)")
    print("   Set environment variable: X402_PAY_TO_ADDRESS=YourAddress")
    print("=" * 70)


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Demo homepage with interactive buttons."""
    return templates.TemplateResponse("index.html", {"request": request})


# =============================================================================
# BALANCE CHECK API
# =============================================================================

@app.get("/api/balances")
async def check_balances(user_address: str = None):
    """Check balances for hot wallet, cold wallet, and user wallet.
    
    Query params:
        user_address: Optional user wallet address to check
    """
    try:
        from solana.rpc.api import Client
        from solders.pubkey import Pubkey
        
        # Get config
        network = os.getenv('X402_NETWORK', 'solana-devnet')
        rpc_urls = {
            'solana-mainnet': 'https://api.mainnet-beta.solana.com',
            'solana-devnet': 'https://api.devnet.solana.com',
            'solana-testnet': 'https://api.testnet.solana.com',
        }
        rpc_url = rpc_urls.get(network, 'https://api.devnet.solana.com')
        
        client = Client(rpc_url)
        
        # Get addresses
        cold_wallet = os.getenv('X402_PAY_TO_ADDRESS', '')
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
        if user_address:
            balances['user_wallet'] = _get_wallet_balances(client, user_address, usdc_mint)
            balances['user_wallet']['address'] = user_address
        else:
            balances['user_wallet'] = {'address': 'Not connected', 'sol': 0, 'usdc': 0}
        
        # Also return RPC URL for frontend to use
        rpc_url = rpc_urls.get(network, 'https://api.devnet.solana.com')
        if os.getenv('X402_RPC_URL'):
            rpc_url = os.getenv('X402_RPC_URL')
        
        return {
            'balances': balances,
            'network': network,
            'rpc_url': rpc_url,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
    except ImportError:
        return {
            'error': 'Solana libraries not installed',
            'detail': 'Install with: pip install solana solders base58',
        }
    except Exception as e:
        return {
            'error': str(e),
            'balances': {
                'hot_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                'cold_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
                'user_wallet': {'address': 'Error checking', 'sol': 0, 'usdc': 0},
            }
        }


def _get_wallet_balances(client, address_str, usdc_mint):
    """Get SOL and USDC balances for an address."""
    try:
        from solders.pubkey import Pubkey
        from solders.token.associated import get_associated_token_address
        
        pubkey = Pubkey.from_string(address_str)
        
        # Get SOL balance
        sol_balance = client.get_balance(pubkey).value / 1_000_000_000
        
        # Get USDC balance
        usdc_balance = 0.0
        if usdc_mint:
            try:
                usdc_mint_pubkey = Pubkey.from_string(usdc_mint)
                token_account = get_associated_token_address(pubkey, usdc_mint_pubkey)
                token_response = client.get_token_account_balance(token_account)
                if token_response.value:
                    usdc_balance = float(token_response.value.amount) / 1_000_000
            except Exception as e:
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

@app.get("/api/random")
async def random_number():
    """Free random number generator (1-6).
    
    No payment required - publicly accessible.
    """
    number = random.randint(1, 6)
    
    return {
        'number': number,
        'range': '1-6',
        'type': 'free',
        'timestamp': datetime.utcnow().isoformat(),
    }


@app.get("/api/premium/random")
@require_payment(price='$0.01')
async def premium_random_number(request: Request):
    """Premium random number generator (1000000-9999999).
    
    Requires payment via x402 protocol on Solana blockchain.
    Payment is handled automatically by the @require_payment decorator.
    """
    number = random.randint(1000000, 9999999)
    
    return {
        'number': number,
        'range': '1000000-9999999',
        'type': 'premium',
        'digits': 7,
        'timestamp': datetime.utcnow().isoformat(),
        'note': 'This number required payment!',
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv('FASTAPI_DEBUG', 'False') == 'True'
    )

