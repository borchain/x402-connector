# x402-connector Flask Example

Interactive demo showing HTTP 402 Payment Required with Solana micropayments using Flask.

## Quick Start

```bash
# 1. Install dependencies
cd examples/flask
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your Solana address

# 3. Run server
python app.py

# 4. Open browser
open http://localhost:5001
```

## 5-Minute Integration Guide

### Installation

```bash
pip install x402-connector[flask]
```

### Basic Setup

```python
from flask import Flask, jsonify
from x402_connector.flask import X402, require_payment

app = Flask(__name__)

# Configure x402
app.config['X402_CONFIG'] = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'price': '$0.01',
    'network': 'solana-mainnet',
}

# Initialize extension
x402 = X402(app)

# Free endpoint
@app.route('/api/free')
def free_data():
    return jsonify({'data': 'available to everyone'})

# Paid endpoint
@app.route('/api/premium')
@require_payment(price='$0.01')
def premium_data():
    return jsonify({'data': 'premium content'})

if __name__ == '__main__':
    app.run(port=5000)
```

That's it! Your API now requires payment for premium endpoints.

## What This Example Demonstrates

- ✨ **Decorator-based pricing** - Use `@require_payment(price='$0.01')` on any route
- ⚡ **Solana blockchain** - Fast (400ms), cheap ($0.00001/tx), native USDC
- 🎯 **Two endpoints** - One free, one paid (shows the contrast)
- 💡 **Clean code** - Minimal setup, maximum clarity
- 🧪 **Flask integration** - Native Flask extension with before/after request hooks

## Configuration

### Required Environment Variables

```bash
# .env file
X402_PAY_TO_ADDRESS=your_solana_address_here
X402_SIGNER_KEY=your_private_key_base58  # For settlement
X402_NETWORK=solana-mainnet
```

### Configuration Options

```python
app.config['X402_CONFIG'] = {
    # Required
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    
    # Optional (with defaults)
    'price': '$0.01',                      # Default price
    'network': 'solana-mainnet',           # or 'solana-devnet' for testing
    'protected_paths': [],                 # Empty = decorator-only mode
    'debug_mode': False,                   # True = simulate transactions
    'rpc_url': None,                       # Custom RPC endpoint
    'description': 'API Access',           # Description for payment UI
    
    # Facilitator mode (see FACILITATORS_INTEGRATION.md for details)
    'facilitator_mode': 'local',           # 'local', 'payai', or 'corbits'
}
```

### Facilitator Configuration

**Local Mode (Default - Self-hosted):**

```python
app.config['X402_CONFIG'] = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
    'facilitator_mode': 'local',  # Default
}
```

**PayAI Mode (Managed Service):**

```python
app.config['X402_CONFIG'] = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
    'facilitator_mode': 'payai',
    'payai': {
        'facilitator_url': 'https://facilitator.payai.network',
    }
}
```

See [FACILITATORS_INTEGRATION.md](../../FACILITATORS_INTEGRATION.md) for complete facilitator documentation.

## Testing

### Test Free Endpoint

```bash
curl http://localhost:5001/api/random
# {"number": 4, "range": "1-6", "type": "free"}
```

### Test Paid Endpoint (No Payment)

```bash
curl -i http://localhost:5001/api/premium/random
# HTTP/1.1 402 Payment Required
# {
#   "x402Version": 1,
#   "accepts": [{
#     "network": "solana-mainnet",
#     "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
#     "assetSymbol": "USDC",
#     "maxAmountRequired": "10000",
#     "payTo": "YOUR_SOLANA_ADDRESS"
#   }]
# }
```

## How It Works

### 1. User Requests Premium Endpoint

```http
GET /api/premium/random
```

### 2. Decorator Intercepts

The `@require_payment` decorator checks for payment:

```python
@require_payment(price='$0.01')
def premium_random_number():
    # Only called if payment is valid
    number = random.randint(1000000, 9999999)
    return jsonify({'number': number})
```

### 3. Returns 402 If No Payment

```json
{
  "status": 402,
  "message": "Payment Required",
  "accepts": [{
    "network": "solana-mainnet",
    "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "maxAmountRequired": "10000",
    "payTo": "YOUR_ADDRESS"
  }]
}
```

### 4. User Signs Payment with Wallet

Client uses Phantom, Solflare, or another Solana wallet to sign the payment.

### 5. User Retries with Payment

```http
GET /api/premium/random
X-PAYMENT: {signed_payment_data}
```

### 6. Decorator Verifies & Settles

- Verifies signature
- Checks amount
- Broadcasts to Solana
- Returns data + transaction hash

## Customization

### Different Prices Per Endpoint

```python
@app.route('/api/cheap')
@require_payment(price='$0.01')
def cheap_api():
    return jsonify({'data': 'cheap'})

@app.route('/api/expensive')
@require_payment(price='$1.00')
def expensive_api():
    return jsonify({'data': 'expensive'})

@app.route('/api/premium-ai')
@require_payment(price='$0.10', description='AI Image Generation')
def premium_ai():
    return jsonify({'result': 'AI output'})
```

### Factory Pattern

For application factories:

```python
from flask import Flask
from x402_connector.flask import X402

x402 = X402()

def create_app():
    app = Flask(__name__)
    app.config['X402_CONFIG'] = {
        'pay_to_address': 'YOUR_SOLANA_ADDRESS',
        'network': 'solana-mainnet',
    }
    
    x402.init_app(app)
    
    return app
```

## Project Structure

```
examples/flask/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Interactive demo UI
├── env.example         # Configuration template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Development Tips

### Running in Debug Mode

```bash
# .env
FLASK_DEBUG=True
X402_DEBUG_MODE=True  # Simulates transactions (no real blockchain)
X402_NETWORK=solana-devnet  # Use devnet for testing

python app.py
```

### Production Deployment

```bash
# Use gunicorn for production
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with environment variables
PORT=8000 gunicorn app:app
```

### Testing with curl

```bash
# Test free endpoint
curl http://localhost:5001/api/random

# Test premium endpoint (expect 402)
curl -i http://localhost:5001/api/premium/random

# Check balances (if available)
curl http://localhost:5001/api/balances
```

## Architecture

```
┌─────────────────────────────────────────┐
│ Flask Route                              │
│ @require_payment(price='$0.01')         │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ x402 Decorator/Extension                 │
│ - Checks for X-PAYMENT header           │
│ - Verifies signature                     │
│ - Settles on Solana                      │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ Solana Blockchain                        │
│ - USDC transfer                          │
│ - 400ms finality                         │
│ - $0.00001 fee                           │
└─────────────────────────────────────────┘
```

## Troubleshooting

### "x402 extension not configured"

Make sure you initialize the extension:

```python
x402 = X402(app)
```

Or use factory pattern:

```python
x402 = X402()
x402.init_app(app, pay_to_address='YOUR_ADDRESS')
```

### "X402_SIGNER_KEY not set"

Set environment variable:

```bash
export X402_SIGNER_KEY=your_base58_private_key
```

Or add to `.env` file.

### "Payment verification failed"

Check:
- Signature format is correct
- Amount matches requirements
- Network matches (devnet vs mainnet)
- Timing is valid (not expired)
- Payment destination matches your address

### Network Issues

For testing, use Solana devnet:

```python
# .env
X402_NETWORK=solana-devnet
```

For production, use mainnet:

```python
# .env
X402_NETWORK=solana-mainnet
X402_RPC_URL=https://api.mainnet-beta.solana.com  # Optional: custom RPC
```

## Additional Resources

- [Full Documentation](../../README.md) - Main SDK documentation
- [API Reference](../../API.md) - Complete API documentation
- [Facilitators Guide](../../FACILITATORS_INTEGRATION.md) - PayAI, Corbits, local modes
- [Quick Start Guide](../../QUICKSTART.md) - Get started in 5 minutes
- [GitHub Issues](https://github.com/borchain/x402-connector/issues) - Report bugs

## Next Steps

1. ✅ Run this example
2. 📖 Read [API.md](../../API.md) for full reference
3. 🔧 Explore [Facilitators Guide](../../FACILITATORS_INTEGRATION.md)
4. 🚀 Integrate into your Flask app
5. 🌐 Deploy to production

---

**Built with ❤️ for Flask + Solana developers**
