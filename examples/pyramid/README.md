# x402-connector Pyramid Example

Interactive demo showing HTTP 402 Payment Required with Solana micropayments using Pyramid.

## What This Demonstrates

- ✨ **Decorator-based pricing** - Use `@require_payment(price='$0.01')` on any view
- ⚡ **Solana blockchain** - Fast (400ms), cheap ($0.00001/tx), native USDC
- 🎯 **Two endpoints** - One free, one paid (shows the contrast)
- 💡 **Clean code** - Minimal setup, maximum clarity
- 🔺 **Pyramid integration** - Uses Pyramid tweens (middleware) with declarative configuration

## Quick Start

```bash
# 1. Install dependencies
cd examples/pyramid
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your Solana addresses

# 3. Run server
python app.py

# 4. Open browser
open http://localhost:6543
```

## The Code

### Two Simple Views

```python
# app.py

# Free view - no decorator
def random_view(request):
    number = random.randint(1, 6)
    return Response(json.dumps({'number': number}))

# Paid view - with decorator
@require_payment(price='$0.01')
def premium_random_view(request):
    number = random.randint(1000000, 9999999)
    return Response(json.dumps({'number': number}))
```

That's it! The decorator handles everything:
- Payment verification
- 402 responses
- On-chain settlement
- Error handling

### Configuration

```python
# app.py

settings = {
    'x402.pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'x402.price': '$0.01',
    'x402.network': 'solana-devnet',
}

config = Configurator(settings=settings)

# Include x402 tween (middleware)
config.include('x402_connector.pyramid')

app = config.make_wsgi_app()
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
curl http://localhost:6543/api/random
# {"number": 4, "range": "1-6", "type": "free"}
```

### Test Paid Endpoint (No Payment)

```bash
curl -i http://localhost:6543/api/premium/random
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
def premium_random_view(request):
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
examples/pyramid/
├── app.py              # Main Pyramid application
├── templates/
│   └── index.html      # Interactive demo UI
├── env.example         # Configuration template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Customization

### Different Prices Per View

```python
@require_payment(price='$0.01')
def cheap_view(request):
    return Response(json.dumps({'data': 'cheap'}))

@require_payment(price='$0.10')
def expensive_view(request):
    return Response(json.dumps({'data': 'expensive'}))

@require_payment(price='$1.00')
def premium_ai_view(request):
    return Response(json.dumps({'result': 'AI output'}))
```

### Add Description

```python
@require_payment(price='$0.10', description='AI Image Generation')
def generate_image_view(request):
    return Response(json.dumps({'image_url': '...'}))
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
│ Pyramid View                             │
│ @require_payment(price='$0.01')         │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ x402 Decorator/Tween                     │
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

## Pyramid Features

Pyramid is a flexible web framework with powerful configuration:

| Feature | Pyramid Support |
|---------|----------------|
| Tweens (Middleware) | ✅ Native |
| Configurator | ✅ Declarative |
| URL Dispatch | ✅ Flexible |
| Traversal | ✅ Advanced |
| Decorator | `@require_payment()` |
| Middleware | `config.include('x402_connector.pyramid')` |

## Development Tips

### Running in Debug Mode

```bash
# .env
PYRAMID_DEBUG=True
X402_DEBUG_MODE=True  # Simulates transactions

python app.py
```

### Custom Port

```bash
PORT=8080 python app.py
```

### Testing with curl

```bash
# Test free endpoint
curl http://localhost:6543/api/random

# Test premium endpoint (expect 402)
curl -i http://localhost:6543/api/premium/random

# Check balances
curl http://localhost:6543/api/balances
```

### Production Deployment

```bash
# Use gunicorn or waitress for production
pip install waitress
waitress-serve --port=8080 app:main

# Or with gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:8080 app:main
```

## Next Steps

1. ✅ Run this example
2. 📖 Read [API.md](../../API.md) for full reference
3. 🚀 Integrate into your Pyramid app
4. 🌐 Deploy to production

## Troubleshooting

### "x402 tween not configured"

Make sure you include the tween:
```python
config.include('x402_connector.pyramid')
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

**Built with ❤️ for Pyramid + Solana developers**

