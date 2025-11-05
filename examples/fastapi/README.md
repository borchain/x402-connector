# x402-connector FastAPI Example

Interactive demo showing HTTP 402 Payment Required with Solana micropayments using FastAPI.

## What This Demonstrates

- ✨ **Decorator-based pricing** - Use `@require_payment(price='$0.01')` on any route
- ⚡ **Solana blockchain** - Fast (400ms), cheap ($0.00001/tx), native USDC
- 🎯 **Two endpoints** - One free, one paid (shows the contrast)
- 💡 **Clean code** - Minimal setup, maximum clarity
- 🚀 **FastAPI integration** - Native FastAPI middleware with async support

## Quick Start

```bash
# 1. Install dependencies
cd examples/fastapi
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your Solana addresses

# 3. Run server
python app.py
# Or: uvicorn app:app --reload

# 4. Open browser
open http://localhost:8000
```

## The Code

### Two Simple Endpoints

```python
# app.py

# Free endpoint - no decorator
@app.get('/api/random')
async def random_number():
    number = random.randint(1, 6)
    return {'number': number}

# Paid endpoint - with decorator
@app.get('/api/premium/random')
@require_payment(price='$0.01')
async def premium_random_number(request: Request):
    number = random.randint(1000000, 9999999)
    return {'number': number}
```

That's it! The decorator handles everything:
- Payment verification
- 402 responses
- On-chain settlement
- Error handling

### Configuration

```python
# app.py

app.add_middleware(
    X402Middleware,
    pay_to_address='YOUR_SOLANA_ADDRESS',  # Where payments go
    price='$0.01',                         # Default price
    network='solana-devnet',               # Network
)
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
@app.get('/api/premium/random')
@require_payment(price='$0.01')
async def premium_random_number(request: Request):
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
examples/fastapi/
├── app.py              # Main FastAPI application
├── templates/
│   └── index.html      # Interactive demo UI
├── env.example         # Configuration template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Customization

### Different Prices Per Endpoint

```python
@app.get('/api/cheap')
@require_payment(price='$0.01')
async def cheap_api():
    return {'data': 'cheap'}

@app.get('/api/expensive')
@require_payment(price='$0.10')
async def expensive_api():
    return {'data': 'expensive'}

@app.get('/api/premium-ai')
@require_payment(price='$1.00')
async def premium_ai():
    return {'result': 'AI output'}
```

### Add Description

```python
@app.get('/api/generate-image')
@require_payment(price='$0.10', description='AI Image Generation')
async def generate_image():
    return {'image_url': '...'}
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
│ FastAPI Route                            │
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

## FastAPI Features

FastAPI integration includes:

- **Async Support** - Full async/await compatibility
- **Type Hints** - Python type hints for better IDE support
- **Auto Docs** - Automatic OpenAPI/Swagger documentation at `/docs`
- **Fast Performance** - Built on Starlette and Pydantic

### View API Docs

```bash
# Start server
python app.py

# Open docs
open http://localhost:8000/docs

# Or ReDoc
open http://localhost:8000/redoc
```

## Development Tips

### Running in Debug Mode

```bash
# .env
FASTAPI_DEBUG=True
X402_DEBUG_MODE=True  # Simulates transactions

python app.py
```

### Production Deployment

```bash
# Use uvicorn for production
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# Or with environment variables
PORT=8000 uvicorn app:app --workers 4
```

### Testing with httpx

```bash
# Install httpx
pip install httpx

# Test free endpoint
python -c "import httpx; print(httpx.get('http://localhost:8000/api/random').json())"

# Test premium endpoint (expect 402)
python -c "import httpx; print(httpx.get('http://localhost:8000/api/premium/random').status_code)"
```

## Next Steps

1. ✅ Run this example
2. 📖 Read [API.md](../../API.md) for full reference
3. 🚀 Integrate into your FastAPI app
4. 🌐 Deploy to production

## Troubleshooting

### "x402 middleware not configured"

Make sure you add the middleware:
```python
app.add_middleware(X402Middleware, pay_to_address='YOUR_ADDRESS')
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

**Built with ❤️ for FastAPI + Solana developers**

