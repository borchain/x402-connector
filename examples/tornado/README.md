# x402-connector Tornado Example

Interactive demo showing HTTP 402 Payment Required with Solana micropayments using Tornado.

## What This Demonstrates

- ✨ **Decorator-based pricing** - Use `@require_payment(price='$0.01')` on any handler method
- ⚡ **Solana blockchain** - Fast (400ms), cheap ($0.00001/tx), native USDC
- 🎯 **Two endpoints** - One free, one paid (shows the contrast)
- 💡 **Clean code** - Minimal setup, maximum clarity
- 🌪️ **Tornado integration** - Native Tornado middleware with async support

## Quick Start

```bash
# 1. Install dependencies
cd examples/tornado
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your Solana addresses

# 3. Run server
python app.py

# 4. Open browser
open http://localhost:8888
```

## The Code

### Two Simple Endpoints

```python
# app.py

# Free endpoint - no decorator
class RandomHandler(web.RequestHandler):
    def get(self):
        number = random.randint(1, 6)
        self.write({'number': number})

# Paid endpoint - with decorator
class PremiumRandomHandler(web.RequestHandler):
    @require_payment(price='$0.01')
    async def get(self):
        number = random.randint(1000000, 9999999)
        self.write({'number': number})
```

That's it! The decorator handles everything:
- Payment verification
- 402 responses
- On-chain settlement
- Error handling

### Configuration

```python
# app.py

x402_config = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',  # Where payments go
    'price': '$0.01',                         # Default price
    'network': 'solana-devnet',               # Network
}

app = web.Application([...], x402_config=x402_config)

# Initialize middleware
X402Middleware(app, **x402_config)
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
curl http://localhost:8888/api/random
# {"number": 4, "range": "1-6", "type": "free"}
```

### Test Paid Endpoint (No Payment)

```bash
curl -i http://localhost:8888/api/premium/random
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
async def get(self):
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
examples/tornado/
├── app.py              # Main Tornado application
├── templates/
│   └── index.html      # Interactive demo UI
├── env.example         # Configuration template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Customization

### Different Prices Per Endpoint

```python
class CheapHandler(web.RequestHandler):
    @require_payment(price='$0.01')
    async def get(self):
        self.write({'data': 'cheap'})

class ExpensiveHandler(web.RequestHandler):
    @require_payment(price='$0.10')
    async def get(self):
        self.write({'data': 'expensive'})

class PremiumAIHandler(web.RequestHandler):
    @require_payment(price='$1.00')
    async def post(self):
        self.write({'result': 'AI output'})
```

### Add Description

```python
class GenerateImageHandler(web.RequestHandler):
    @require_payment(price='$0.10', description='AI Image Generation')
    async def post(self):
        self.write({'image_url': '...'})
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
│ Tornado Handler                          │
│ @require_payment(price='$0.01')         │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ x402 Decorator/Middleware                │
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

## Tornado Features

Tornado is an async web framework perfect for high-performance applications:

| Feature | Tornado Support |
|---------|----------------|
| Async/Await | ✅ Full Support |
| Websockets | ✅ Native |
| Long Polling | ✅ Native |
| Performance | ⚡ Very High |
| Decorator | `@require_payment()` |
| Middleware | `X402Middleware` |

## Development Tips

### Running in Debug Mode

```bash
# .env
TORNADO_DEBUG=True
X402_DEBUG_MODE=True  # Simulates transactions

python app.py --debug
```

### Custom Port

```bash
python app.py --port=8080
```

### Testing with curl

```bash
# Test free endpoint
curl http://localhost:8888/api/random

# Test premium endpoint (expect 402)
curl -i http://localhost:8888/api/premium/random

# Check balances
curl http://localhost:8888/api/balances
```

## Next Steps

1. ✅ Run this example
2. 📖 Read [API.md](../../API.md) for full reference
3. 🚀 Integrate into your Tornado app
4. 🌐 Deploy to production

## Troubleshooting

### "x402 middleware not configured"

Make sure you initialize the middleware:
```python
X402Middleware(app, **x402_config)
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

**Built with ❤️ for Tornado + Solana developers**

