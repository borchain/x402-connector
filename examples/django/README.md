# Django x402-connector Example

A complete, working example of integrating x402 payment requirements into a Django application.

## 🎯 What This Demonstrates

This example shows:
- ✅ **Basic Integration** - Add x402 to existing Django app in 3 lines
- ✅ **Protected Endpoints** - Require payment for premium API routes
- ✅ **Multiple Price Tiers** - Different prices for different endpoints
- ✅ **Browser Paywall** - Automatic HTML paywall for browser requests
- ✅ **API 402 Responses** - JSON 402 responses for API clients
- ✅ **Payment Settlement** - Automatic on-chain settlement after successful requests

## 📁 Project Structure

```
django/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── manage.py             # Django management script
├── config/               # Project configuration
│   ├── __init__.py
│   ├── settings.py       # Django settings with x402 config
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI application
└── api/                  # Example API app
    ├── __init__.py
    ├── models.py        # Data models
    ├── views.py         # API views (some protected)
    └── urls.py          # API URL patterns
```

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install x402-connector with Django support
pip install -r requirements.txt

# Or install directly
pip install x402-connector[django]
```

### 2. Configure Environment Variables

Create a `.env` file (or export these):

```bash
# Required: Your payment recipient address
X402_PAY_TO_ADDRESS=0x1234567890123456789012345678901234567890

# Optional: Customize network and pricing
X402_NETWORK=base
X402_PRICE=$0.01

# For local facilitator mode (optional)
X402_SIGNER_KEY=0x...your_private_key...
X402_RPC_URL=https://mainnet.base.org
```

**⚠️ Security Note**: Never commit `.env` files with real private keys!

### 3. Run the Example

```bash
# Run database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

Server will start at `http://localhost:8000`

### 4. Test the Endpoints

#### **Free Endpoints** (No payment required)

```bash
# Public welcome endpoint
curl http://localhost:8000/

# Public API endpoint
curl http://localhost:8000/api/public/info
```

Expected: 200 OK with JSON response

#### **Premium Endpoints** (Payment required)

```bash
# Try accessing without payment
curl http://localhost:8000/api/premium/data

# Expected: 402 Payment Required
# {
#   "x402Version": 1,
#   "accepts": [{
#     "scheme": "exact",
#     "network": "base",
#     "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
#     "maxAmountRequired": "10000",
#     "payTo": "0x...",
#     ...
#   }],
#   "error": "No X-PAYMENT header provided"
# }
```

#### **Browser Requests**

Open in browser: `http://localhost:8000/api/premium/data`

You'll see a beautiful HTML paywall instead of JSON!

#### **With Valid Payment**

```bash
# With payment header (you need a valid x402 payment)
curl -H "X-Payment: <base64_encoded_payment>" \
     http://localhost:8000/api/premium/data

# Expected: 200 OK with data + X-PAYMENT-RESPONSE header
```

## 📖 How It Works

### Step 1: Add Middleware

In `config/settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ... other middleware ...
    'x402_connector.django.X402Middleware',  # ← Add this line
]
```

### Step 2: Configure x402

In `config/settings.py`:

```python
X402_CONFIG = {
    # Required
    'network': 'base',                    # Blockchain network
    'price': '$0.01',                     # Price per request
    'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS'),
    
    # Which paths to protect
    'protected_paths': [
        '/api/premium/*',                 # All /api/premium/ routes
        '/api/paid/*',                    # All /api/paid/ routes
    ],
    
    # Optional
    'description': 'Premium API Access',
    'facilitator_mode': 'local',          # or 'remote' or 'hybrid'
}
```

### Step 3: Write Your Views

Normal Django views - no changes needed!

```python
def premium_data(request):
    """This endpoint is automatically protected by x402."""
    return JsonResponse({
        'data': 'This is premium content!',
        'timestamp': timezone.now().isoformat(),
    })
```

That's it! The middleware handles everything else.

## 🎨 Use Cases Demonstrated

### 1. Simple Premium API

**File**: `api/views.py` → `premium_data()`

```python
# Protected endpoint - requires payment
def premium_data(request):
    return JsonResponse({'data': 'premium content'})
```

**Try it**:
```bash
curl http://localhost:8000/api/premium/data
# 402 Payment Required
```

### 2. AI Model Inference

**File**: `api/views.py` → `ai_inference()`

Charge per AI inference call:

```python
def ai_inference(request):
    prompt = request.GET.get('prompt', '')
    result = run_ai_model(prompt)  # Your AI logic
    return JsonResponse({'result': result})
```

**Try it**:
```bash
curl "http://localhost:8000/api/premium/ai?prompt=Hello"
# 402 Payment Required
```

### 3. Data Analytics

**File**: `api/views.py` → `analytics()`

Charge for expensive computations:

```python
def analytics(request):
    # Expensive computation
    results = compute_analytics()
    return JsonResponse(results)
```

### 4. Mixed Free/Paid Content

Some endpoints free, others paid:

```python
# Free
def public_info(request):
    return JsonResponse({'info': 'public'})

# Paid (path matches /api/premium/*)
def premium_data(request):
    return JsonResponse({'data': 'premium'})
```

## ⚙️ Configuration Options

### Basic Configuration

```python
X402_CONFIG = {
    'network': 'base',              # Required
    'price': '$0.01',               # Required
    'pay_to_address': '0x...',      # Required
    'protected_paths': ['*'],       # Default: protect all
}
```

### Advanced Configuration

```python
X402_CONFIG = {
    # Basic
    'network': 'base',
    'price': '$0.01',
    'pay_to_address': '0x...',
    'protected_paths': ['/api/premium/*'],
    
    # Facilitator Mode
    'facilitator_mode': 'local',    # 'local' | 'remote' | 'hybrid'
    
    # Local Facilitator Options
    'local': {
        'private_key_env': 'X402_SIGNER_KEY',
        'rpc_url_env': 'X402_RPC_URL',
        'verify_balance': True,      # Check payer has funds
        'simulate_before_send': True, # Simulate tx before broadcast
        'wait_for_receipt': False,   # Wait for confirmation
    },
    
    # Remote Facilitator Options
    'remote': {
        'url': 'https://facilitator.example.com',
        'headers': {'Authorization': 'Bearer token'},
    },
    
    # Settlement Policy
    'settle_policy': 'block-on-failure',  # or 'log-and-continue'
    
    # Caching
    'replay_cache_enabled': True,  # Prevent duplicate settlements
}
```

### Path Protection Patterns

```python
X402_CONFIG = {
    ...
    'protected_paths': [
        '*',                      # Protect everything
        '/api/premium/*',         # All /api/premium/ routes
        '/api/*/paid',           # Any route ending in /paid
        '/specific-endpoint',     # Exact match
    ],
}
```

## 🧪 Testing

### Run Django Tests

```bash
python manage.py test
```

### Manual Testing

```bash
# Test without payment
curl -i http://localhost:8000/api/premium/data

# Test with invalid payment
curl -i -H "X-Payment: invalid" \
     http://localhost:8000/api/premium/data

# Test browser request
curl -i -H "Accept: text/html" \
        -H "User-Agent: Mozilla/5.0" \
        http://localhost:8000/api/premium/data
```

## 🔒 Security Best Practices

### 1. Environment Variables

```python
# ✅ Good: Load from environment
'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS')

# ❌ Bad: Hardcoded
'pay_to_address': '0x1234...'
```

### 2. Private Keys

```bash
# ✅ Good: Separate .env file (in .gitignore)
echo "X402_SIGNER_KEY=0x..." >> .env

# ❌ Bad: In settings.py or version control
```

### 3. Network Configuration

```python
# ✅ Good: Use environment-specific config
if DEBUG:
    X402_CONFIG['network'] = 'base-sepolia'  # Testnet
else:
    X402_CONFIG['network'] = 'base'          # Mainnet
```

## 📚 Next Steps

### Integrate into Your Existing Django App

1. **Install x402-connector**:
   ```bash
   pip install x402-connector[django]
   ```

2. **Add middleware** to `settings.py`:
   ```python
   MIDDLEWARE = [
       ...
       'x402_connector.django.X402Middleware',
   ]
   ```

3. **Configure**:
   ```python
   X402_CONFIG = {
       'network': 'base',
       'price': '$0.01',
       'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS'),
       'protected_paths': ['/api/premium/*'],
   }
   ```

4. **Done!** Your premium endpoints are now protected.

### Customize

- **Different prices per endpoint**: Use path patterns
- **Dynamic pricing**: Implement custom facilitator
- **Complex authorization**: Combine with Django permissions
- **Monitoring**: Add logging and metrics

## 🐛 Troubleshooting

### "No X402_CONFIG found in Django settings"

**Solution**: Add `X402_CONFIG` dictionary to `settings.py`

### "network is required"

**Solution**: Ensure `X402_CONFIG` has `network`, `price`, and `pay_to_address`

### Payments not settling

**Solution**: Check `X402_SIGNER_KEY` and `X402_RPC_URL` environment variables

### Still seeing 402 with valid payment

**Solution**: Check logs for verification errors:
```bash
python manage.py runserver --verbosity=2
```

## 📖 Learn More

- [x402 Protocol Specification](https://github.com/coinbase/x402)
- [x402-connector Documentation](https://github.com/borchain/x402-connector)
- [Django Documentation](https://docs.djangoproject.com/)

## 💡 Example Projects

Check other examples in the `examples/` directory:
- `django/` - This example (simple API)
- `django_ai/` - AI inference marketplace
- `django_analytics/` - Data analytics API
- `django_content/` - Content paywall

## 🤝 Contributing

Found a bug or have a suggestion? Open an issue!

## 📄 License

MIT License - see LICENSE file for details

---

**Happy coding with x402!** 🚀

Questions? Open an issue at https://github.com/borchain/x402-connector/issues

