# x402-connector Flask Example

Interactive demo showing HTTP 402 Payment Required with Solana micropayments using Flask.

## What This Demonstrates

- ✨ **Decorator-based pricing** - Use `@require_payment(price='$0.01')` on any route
- ⚡ **Solana blockchain** - Fast (400ms), cheap ($0.00001/tx), native USDC
- 🎯 **Two endpoints** - One free, one paid (shows the contrast)
- 💡 **Clean code** - Minimal setup, maximum clarity
- 🧪 **Flask integration** - Native Flask extension with before/after request hooks

## Quick Start

```bash
# 1. Install dependencies
cd examples/flask
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your Solana addresses

# 3. Run server
python app.py

# 4. Open browser
open http://localhost:5001
```

## The Code

### Two Simple Endpoints

```python
# app.py

# Free endpoint - no decorator
@app.route('/api/random')
def random_number():
    number = random.randint(1, 6)
    return jsonify({'number': number})

# Paid endpoint - with decorator
@app.route('/api/premium/random')
@require_payment(price='$0.01')
def premium_random_number():
    number = random.randint(1000000, 9999999)
    return jsonify({'number': number})
```

That's it! The decorator handles everything:
- Payment verification
- 402 responses
- On-chain settlement
- Error handling

### Configuration

```python
# app.py

app.config['X402_CONFIG'] = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',  # Where payments go
    'price': '$0.01',                         # Default price
    'network': 'solana-devnet',               # Network
}

# Initialize extension
x402 = X402(app)
```

### Environment Variables

```bash
# .env
X402_PAY_TO_ADDRESS=DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK
X402_SIGNER_KEY=your_base58_private_key
X402_NETWORK=solana-devnet
```

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
#     "network": "solana-devnet",
#     "asset": "USDC",
#     "maxAmountRequired": "10000",
#     "payTo": "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK"
#   }]
# }
```

## How It Works

### 1. User Requests Premium Endpoint

```
GET /api/premium/random
```

### 2. Decorator Intercepts

The `@require_payment` decorator checks for payment:

```python
@require_payment(price='$0.01')
def premium_random_number():
    # Only called if payment is valid
    ...
```

### 3. Returns 402 If No Payment

```json
{
  "status": 402,
  "message": "Payment Required",
  "accepts": [...]
}
```

### 4. User Signs Payment with Wallet

Client uses Phantom, Solflare, or another Solana wallet to sign.

### 5. User Retries with Payment

```
GET /api/premium/random
X-PAYMENT: {signed_payment_data}
```

### 6. Decorator Verifies & Settles

- Verifies signature
- Checks amount
- Broadcasts to Solana
- Returns data + transaction hash

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

## Customization

### Different Prices Per Endpoint

```python
@app.route('/api/cheap')
@require_payment(price='$0.01')
def cheap_api():
    return jsonify({'data': 'cheap'})

@app.route('/api/expensive')
@require_payment(price='$0.10')
def expensive_api():
    return jsonify({'data': 'expensive'})

@app.route('/api/premium-ai')
@require_payment(price='$1.00')
def premium_ai():
    return jsonify({'result': 'AI output'})
```

### Add Description

```python
@app.route('/api/generate-image')
@require_payment(price='$0.10', description='AI Image Generation')
def generate_image():
    return jsonify({'image_url': '...'})
```

### Use Mainnet

```bash
# .env
X402_NETWORK=solana-mainnet
X402_PAY_TO_ADDRESS=YourMainnetAddress
X402_RPC_URL=https://api.mainnet-beta.solana.com
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

## Flask vs Django

Both frameworks are fully supported with identical functionality:

| Feature | Flask | Django |
|---------|-------|--------|
| Decorator | `@require_payment()` | `@require_payment()` |
| Extension/Middleware | `X402(app)` | `X402Middleware` |
| Configuration | `app.config['X402_CONFIG']` | `settings.X402_CONFIG` |
| Hooks | `@app.before_request` | Middleware `__call__` |
| Protected Paths | Decorator-based | Decorator or path-based |

## Development Tips

### Running in Debug Mode

```bash
# .env
FLASK_DEBUG=True
X402_DEBUG_MODE=True  # Simulates transactions

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

# Check balances
curl http://localhost:5001/api/balances
```

## Next Steps

1. ✅ Run this example
2. 📖 Read [API.md](../../API.md) for full reference
3. 🚀 Integrate into your Flask app
4. 🌐 Deploy to production

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

### Need Help?

- [Full Documentation](../../README.md)
- [API Reference](../../API.md)
- [GitHub Issues](https://github.com/yourusername/x402-connector/issues)

---

**Built with ❤️ for Flask + Solana developers**

