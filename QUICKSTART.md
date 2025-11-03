# Quick Start Guide

Get x402-connector running in 5 minutes.

## Prerequisites

- Python 3.10+
- pip or poetry
- Solana wallet (for production) or devnet wallet (for testing)

## Installation

### Option 1: pip (Recommended)

```bash
# Core + Django
pip install x402-connector[django]

# Core + Flask
pip install x402-connector[flask]

# Core + FastAPI
pip install x402-connector[fastapi]

# Everything
pip install x402-connector[all]
```

### Option 2: Development Install

```bash
git clone https://github.com/yourusername/x402-connector.git
cd x402-connector
pip install -e ".[dev,tests]"
pytest  # Verify installation
```

## 1. Django Integration

### Step 1: Install

```bash
pip install x402-connector[django]
```

### Step 2: Configure

Edit `settings.py`:

```python
# Add middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'x402_connector.django.X402Middleware',  # ← Add this
    # ... other middleware
]

# Configure x402
X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'price': '$0.01',  # Default price
    'network': 'solana-devnet',  # or 'solana-mainnet'
}
```

### Step 3: Protect Endpoints

```python
# views.py
from django.http import JsonResponse
from x402_connector.django import require_payment

# Free endpoint - no decorator
def free_data(request):
    return JsonResponse({'data': 'public data'})

# Paid endpoint - with decorator
@require_payment(price='$0.01')
def premium_data(request):
    return JsonResponse({'data': 'premium content'})

# Custom price per endpoint
@require_payment(price='$0.10')
def expensive_ai_call(request):
    return JsonResponse({'result': 'AI response'})
```

### Step 4: Set Environment Variables

```bash
# .env
X402_SIGNER_KEY=your_base58_private_key
X402_PAY_TO_ADDRESS=YourSolanaAddress
```

### Step 5: Run

```bash
python manage.py runserver
```

Visit `http://localhost:8000/free_data` - works without payment
Visit `http://localhost:8000/premium_data` - returns 402 Payment Required

## 2. Flask Integration

### Step 1: Install

```bash
pip install x402-connector[flask]
```

### Step 2: Create App

```python
# app.py
from flask import Flask, jsonify
from x402_connector.flask import X402, require_payment
import os

app = Flask(__name__)

# Initialize x402
x402 = X402(app, config={
    'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS'),
    'price': '$0.01',
    'network': 'solana-devnet',
})

@app.route('/free')
def free_endpoint():
    return jsonify({'data': 'free'})

@app.route('/premium')
@require_payment(price='$0.01')
def premium_endpoint():
    return jsonify({'data': 'premium'})

if __name__ == '__main__':
    app.run(debug=True)
```

### Step 3: Run

```bash
export X402_SIGNER_KEY=your_key
export X402_PAY_TO_ADDRESS=your_address
python app.py
```

## 3. FastAPI Integration

### Step 1: Install

```bash
pip install x402-connector[fastapi]
```

### Step 2: Create App

```python
# main.py
from fastapi import FastAPI
from x402_connector.fastapi import X402Middleware, require_payment
import os

app = FastAPI()

# Add middleware
app.add_middleware(
    X402Middleware,
    pay_to_address=os.getenv('X402_PAY_TO_ADDRESS'),
    price='$0.01',
    network='solana-devnet',
)

@app.get('/free')
async def free_endpoint():
    return {'data': 'free'}

@app.get('/premium')
@require_payment(price='$0.01')
async def premium_endpoint():
    return {'data': 'premium'}
```

### Step 3: Run

```bash
export X402_SIGNER_KEY=your_key
export X402_PAY_TO_ADDRESS=your_address
uvicorn main:app --reload
```

## Testing

### Test Free Endpoint

```bash
curl http://localhost:8000/free
# {"data": "free"}
```

### Test Paid Endpoint (No Payment)

```bash
curl -i http://localhost:8000/premium
# HTTP/1.1 402 Payment Required
# {
#   "status": 402,
#   "message": "Payment Required",
#   "accepts": [{
#     "network": "solana-devnet",
#     "asset": "USDC",
#     "amount": "10000",
#     "payTo": "YOUR_ADDRESS"
#   }]
# }
```

### Test Paid Endpoint (With Payment)

```bash
# 1. Sign payment with wallet (get signature)
# 2. Send request with payment
curl -H "X-PAYMENT: {payment_signature_json}" http://localhost:8000/premium
# HTTP/1.1 200 OK
# {"data": "premium"}
```

## Running the Example

The fastest way to see it working:

```bash
cd examples/django
./quickstart.sh
python manage.py runserver
```

Open browser to `http://localhost:8000` and click the buttons!

## Key Concepts

### 1. Decorators vs Middleware

**Middleware** - Protects paths by pattern:
```python
X402_CONFIG = {
    'protected_paths': ['/api/premium/*'],
}
```

**Decorator** - Protects specific views:
```python
@require_payment(price='$0.01')
def my_view(request):
    pass
```

Use both together for maximum flexibility!

### 2. Price Formats

All of these work:

```python
price='$0.01'          # USD amount
price='10000'          # Atomic units (0.01 USDC = 10000 units)
price='0.01 USDC'      # Explicit token
```

### 3. Networks

```python
'network': 'solana-mainnet'    # Production
'network': 'solana-devnet'     # Testing
'network': 'solana-testnet'    # Staging
```

### 4. Wallet Keys

**Two different keys:**

1. `PAY_TO_ADDRESS` - Where payments go (can be cold wallet)
2. `SIGNER_KEY` - Server's hot wallet for settlement (pays gas)

```bash
# Safe setup
X402_PAY_TO_ADDRESS=YourColdWallet     # Secure, offline
X402_SIGNER_KEY=ServerHotWallet        # Server only, minimal funds
```

## Next Steps

1. ✅ Follow this guide
2. 📖 Read [API Reference](API.md) for advanced features
3. 💻 Check [examples/](examples/) for complete code
4. 🧪 Test on devnet before mainnet
5. 🚀 Deploy to production!

## Troubleshooting

### "No module named 'x402_connector'"

```bash
pip install x402-connector
```

### "X402_SIGNER_KEY not found"

Set environment variable:
```bash
export X402_SIGNER_KEY=your_key
```

Or in code:
```python
X402_CONFIG = {
    'signer_key': 'your_key',  # Not recommended for production!
}
```

### "Payment verification failed"

Check:
1. Signature is valid
2. Payment amount matches
3. Payment destination matches
4. Network matches (devnet vs mainnet)

### "RPC error"

Provide custom RPC URL:
```python
X402_CONFIG = {
    'rpc_url': 'https://api.mainnet-beta.solana.com',
}
```

## Getting Help

- 📖 [API Reference](API.md)
- 💬 [GitHub Discussions](https://github.com/yourusername/x402-connector/discussions)
- 🐛 [GitHub Issues](https://github.com/yourusername/x402-connector/issues)
- 💼 [Examples](examples/)

---

Ready to build? Head to [API.md](API.md) for complete reference!
