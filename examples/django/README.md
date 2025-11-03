# x402-connector Django Example

Interactive demo showing HTTP 402 Payment Required with Solana micropayments.

## What This Demonstrates

- ✨ **Decorator-based pricing** - Use `@require_payment(price='$0.01')` on any view
- ⚡ **Solana blockchain** - Fast (400ms), cheap ($0.00001/tx), native USDC
- 🎯 **Two endpoints** - One free, one paid (shows the contrast)
- 💡 **Clean code** - Minimal setup, maximum clarity

## Quick Start

```bash
# 1. Setup (from example directory)
./quickstart.sh

# 2. Run server
python manage.py runserver

# 3. Open browser
open http://localhost:8000
```

## The Code

### Two Simple Endpoints

```python
# views.py

# Free endpoint - no decorator
def random_number(request):
    number = random.randint(1, 6)
    return JsonResponse({'number': number})

# Paid endpoint - with decorator
@require_payment(price='$0.01')
def premium_random_number(request):
    number = random.randint(1000000, 9999999)
    return JsonResponse({'number': number})
```

That's it! The decorator handles everything:
- Payment verification
- 402 responses
- On-chain settlement
- Error handling

### Configuration

```python
# settings.py

X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',  # Where payments go
    'price': '$0.01',                         # Default price
    'network': 'solana-devnet',               # Network
}
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
curl http://localhost:8000/api/random
# {"number": 4, "range": "1-6", "type": "free"}
```

### Test Paid Endpoint (No Payment)

```bash
curl -i http://localhost:8000/api/premium/random
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
def premium_random_number(request):
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
examples/django/
├── api/
│   ├── views.py          # Two endpoints (free + paid)
│   └── urls.py           # URL routes
├── config/
│   ├── settings.py       # x402 configuration
│   └── urls.py
├── templates/
│   └── index.html        # Interactive demo UI
├── env.example           # Configuration template
├── manage.py
├── quickstart.sh         # One-command setup
└── README.md            # This file
```

## Customization

### Different Prices Per Endpoint

```python
@require_payment(price='$0.01')
def cheap_api(request):
    return JsonResponse({'data': 'cheap'})

@require_payment(price='$0.10')
def expensive_api(request):
    return JsonResponse({'data': 'expensive'})

@require_payment(price='$1.00')
def premium_ai(request):
    return JsonResponse({'result': 'AI output'})
```

### Add Description

```python
@require_payment(price='$0.10', description='AI Image Generation')
def generate_image(request):
    return JsonResponse({'image_url': '...'})
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
│ Django View                              │
│ @require_payment(price='$0.01')         │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ x402 Decorator                           │
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

## Next Steps

1. ✅ Run this example
2. 📖 Read [API.md](../../API.md) for full reference
3. 🚀 Integrate into your Django app
4. 🌐 Deploy to production

## Troubleshooting

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

**Built with ❤️ for Solana developers**
