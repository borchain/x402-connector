# API Reference

Complete API documentation for x402-connector.

## Table of Contents

- [Decorators](#decorators)
- [Middleware](#middleware)
- [Configuration](#configuration)
- [Response Format](#response-format)
- [Payment Flow](#payment-flow)

## Decorators

### `@require_payment(price=None, description=None)`

Decorator to protect individual endpoints with payment requirement.

**Parameters:**
- `price` (str, optional): Payment amount. Formats: `'$0.01'`, `'10000'`, `'0.01 USDC'`. Defaults to config default.
- `description` (str, optional): Human-readable description for this endpoint.

**Example:**

```python
from x402_connector.django import require_payment

@require_payment(price='$0.01')
def premium_api(request):
    return JsonResponse({'data': 'premium'})

@require_payment(price='$0.10', description='AI Inference')
def ai_endpoint(request):
    return JsonResponse({'result': 'AI response'})

@require_payment()  # Uses default price from config
def default_price_endpoint(request):
    return JsonResponse({'data': 'content'})
```

**Returns:**
- On success: Your view's response
- On failure: 402 Payment Required response

**Behavior:**
1. If no payment header → Return 402 with payment instructions
2. If invalid payment → Return 402 with error
3. If valid payment → Call your view
4. On 2xx response → Settle payment on-chain
5. Add `X-PAYMENT-SETTLED` header to response

## Middleware

### Django Middleware

#### `X402Middleware`

Django middleware class for path-based protection.

**Configuration:**

```python
# settings.py
MIDDLEWARE = [
    'x402_connector.django.X402Middleware',
]

X402_CONFIG = {
    'pay_to_address': 'YOUR_ADDRESS',
    'price': '$0.01',
    'protected_paths': ['/api/premium/*'],
    # ... other options
}
```

**Protected Paths:**

Supports glob patterns:
- `'*'` - All paths (default)
- `'/api/premium/*'` - All paths starting with `/api/premium/`
- `'/specific/path'` - Exact path match
- `['/api/paid/*', '/api/premium/*']` - Multiple patterns

### Flask Middleware

#### `X402(app, config=None)`

Flask extension for x402 integration.

**Usage:**

```python
from flask import Flask
from x402_connector.flask import X402

app = Flask(__name__)
x402 = X402(app, config={
    'pay_to_address': 'YOUR_ADDRESS',
    'price': '$0.01',
})

# Or initialize later
x402 = X402()
x402.init_app(app, config={...})
```

**Methods:**
- `init_app(app, config)` - Initialize with Flask app
- `require_payment(price=None)` - Decorator factory

### FastAPI Middleware

#### `X402Middleware`

FastAPI middleware for x402 integration.

**Usage:**

```python
from fastapi import FastAPI
from x402_connector.fastapi import X402Middleware

app = FastAPI()
app.add_middleware(
    X402Middleware,
    pay_to_address='YOUR_ADDRESS',
    price='$0.01',
    protected_paths=['/api/premium/*'],
)
```

## Configuration

### `X402Config`

Configuration object for x402-connector.

**Required Parameters:**
- `pay_to_address` (str): Solana address where payments are received

**Optional Parameters:**
- `price` (str): Default price. Default: `'$0.01'`
- `network` (str): Solana network. Default: `'solana-mainnet'`
  - Options: `'solana-mainnet'`, `'solana-devnet'`, `'solana-testnet'`
- `protected_paths` (list): Paths requiring payment. Default: `['*']`
- `description` (str): Payment description. Default: `'API Access'`
- `rpc_url` (str): Custom RPC URL. Default: Uses public RPC
- `signer_key_env` (str): Environment variable for signer key. Default: `'X402_SIGNER_KEY'`
- `max_timeout_seconds` (int): Payment validity window. Default: `60`
- `verify_balance` (bool): Verify sender has funds. Default: `False`
- `wait_for_confirmation` (bool): Wait for transaction confirmation. Default: `False`

**Example:**

```python
config = {
    'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
    'price': '$0.01',
    'network': 'solana-devnet',
    'protected_paths': ['/api/premium/*'],
    'description': 'Premium API Access',
    'rpc_url': 'https://api.devnet.solana.com',
    'max_timeout_seconds': 120,
}
```

### Environment Variables

The SDK checks these environment variables:

**Required for Settlement:**
- `X402_SIGNER_KEY` - Base58 private key for transaction signing

**Optional Overrides:**
- `X402_PAY_TO_ADDRESS` - Override pay_to_address
- `X402_NETWORK` - Override network
- `X402_RPC_URL` - Override rpc_url
- `X402_PRICE` - Override default price

**Example `.env`:**

```bash
X402_SIGNER_KEY=5GxZ8VJqQBGmHeQPV6hkNeZJV3qN5KqxPr7XfJL8mA3Q...
X402_PAY_TO_ADDRESS=DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK
X402_NETWORK=solana-devnet
X402_RPC_URL=https://api.devnet.solana.com
```

## Response Format

### 402 Payment Required Response

When payment is required, the response follows this format:

```json
{
  "status": 402,
  "message": "Payment Required",
  "accepts": [
    {
      "network": "solana-devnet",
      "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "assetSymbol": "USDC",
      "maxAmountRequired": "10000",
      "payTo": "DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK",
      "timeout": 60,
      "description": "Premium API Access"
    }
  ]
}
```

**Fields:**
- `status` - HTTP status code (402)
- `message` - Human-readable message
- `accepts` - Array of acceptable payment methods
  - `network` - Blockchain network
  - `asset` - Token mint address (USDC)
  - `assetSymbol` - Token symbol
  - `maxAmountRequired` - Amount in atomic units (1 USDC = 1,000,000 units)
  - `payTo` - Recipient address
  - `timeout` - Seconds until payment expires
  - `description` - What the payment is for

### 200 Success Response

After successful payment, your endpoint's response is returned with additional header:

```
HTTP/1.1 200 OK
X-Payment-Settled: txhash_abc123
Content-Type: application/json

{
  "data": "your response here"
}
```

The `X-Payment-Settled` header contains the Solana transaction hash.

## Payment Flow

### Client Side

1. **Initial Request (No Payment)**

```bash
curl -i http://localhost:8000/api/premium
```

Response:
```
HTTP/1.1 402 Payment Required
{
  "accepts": [{
    "network": "solana-devnet",
    "maxAmountRequired": "10000",
    "payTo": "..."
  }]
}
```

2. **Sign Payment with Wallet**

```javascript
// Using Solana Web3.js
const payment = await wallet.signTransaction({
  from: userWallet,
  to: payToAddress,
  amount: amount,
  token: usdcMint,
});
```

3. **Retry with Payment**

```bash
curl -i http://localhost:8000/api/premium \
  -H "X-PAYMENT: {\"signature\":\"...\",\"transaction\":\"...\"}"
```

Response:
```
HTTP/1.1 200 OK
X-Payment-Settled: txhash_abc123
{
  "data": "premium content"
}
```

### Server Side (Automatic)

The middleware/decorator handles:

1. ✅ Detect missing payment → Return 402
2. ✅ Parse `X-PAYMENT` header
3. ✅ Verify signature
4. ✅ Check payment amount
5. ✅ Check payment destination
6. ✅ Check payment validity
7. ✅ Call your endpoint
8. ✅ Settle payment on-chain
9. ✅ Add `X-Payment-Settled` header
10. ✅ Return response

You don't need to write any payment logic!

## Price Formats

The SDK accepts multiple price formats:

### USD Format

```python
price='$0.01'   # $0.01 USD
price='$1.00'   # $1.00 USD
price='$10'     # $10.00 USD
```

Converted to USDC automatically (assumes $1 USDC = $1 USD).

### Atomic Units

```python
price='10000'      # 10000 atomic units = $0.01 USDC (6 decimals)
price='1000000'    # 1000000 atomic units = $1.00 USDC
```

USDC has 6 decimals, so 1 USDC = 1,000,000 atomic units.

### Explicit Token

```python
price='0.01 USDC'  # 0.01 USDC tokens
price='1 USDC'     # 1 USDC token
```

## Error Handling

### Payment Errors

```python
try:
    # Your protected endpoint
    return response
except PaymentError as e:
    # Payment verification failed
    return JsonResponse({
        'error': str(e),
        'code': e.code,
    }, status=402)
```

### Network Errors

```python
try:
    # Settlement
    result = settle_payment(...)
except NetworkError as e:
    # Blockchain RPC error
    logger.error(f'Settlement failed: {e}')
    # Continue or abort based on config
```

### Common Error Codes

- `PAYMENT_MISSING` - No X-PAYMENT header
- `PAYMENT_INVALID` - Invalid payment format
- `AMOUNT_INSUFFICIENT` - Payment amount too low
- `SIGNATURE_INVALID` - Invalid signature
- `PAYMENT_EXPIRED` - Payment validity timeout
- `NETWORK_MISMATCH` - Wrong blockchain network
- `SETTLEMENT_FAILED` - On-chain settlement failed

## Advanced Usage

### Custom Settlement Logic

```python
from x402_connector.core.facilitators_solana import SolanaFacilitator

# Create custom facilitator
facilitator = SolanaFacilitator(
    rpc_url='https://api.mainnet-beta.solana.com',
    signer_key=your_key,
    verify_balance=True,
)

# Manual settlement
result = facilitator.settle_payment(
    payment_data=payment,
    amount=10000,
    recipient=pay_to_address,
)

if result.success:
    print(f'Settled: {result.transaction_hash}')
```

### Custom Verification

```python
from x402_connector.core.processor import X402PaymentProcessor

processor = X402PaymentProcessor(config)

# Verify payment
context = RequestContext(
    path='/api/premium',
    headers={'X-Payment': payment_json},
)

result = processor.verify_payment(context)
if result.valid:
    # Proceed
    pass
```

### Caching

Prevent replay attacks:

```python
config = {
    'replay_cache_enabled': True,  # Default: True
    'cache_ttl': 300,  # 5 minutes
}
```

## Framework-Specific Details

### Django

Access payment info in views:

```python
def my_view(request):
    # Access payment metadata
    payment_hash = request.META.get('HTTP_X_PAYMENT_SETTLED')
    return JsonResponse({'tx': payment_hash})
```

### Flask

Access payment via `g` object:

```python
from flask import g

@app.route('/premium')
@require_payment()
def premium():
    payment_hash = g.get('x402_payment_hash')
    return jsonify({'tx': payment_hash})
```

### FastAPI

Access via dependency injection:

```python
from x402_connector.fastapi import get_payment_info

@app.get('/premium')
async def premium(payment_info = Depends(get_payment_info)):
    return {'tx': payment_info.transaction_hash}
```

## Testing

### Mock Payments

```python
# tests/test_views.py
def test_premium_endpoint(client):
    # Without payment
    response = client.get('/premium')
    assert response.status_code == 402
    
    # With payment (mocked)
    response = client.get('/premium', headers={
        'X-PAYMENT': mock_payment_signature(),
    })
    assert response.status_code == 200
```

### Disable Verification

For testing, disable actual blockchain verification:

```python
# test_settings.py
X402_CONFIG = {
    'verify_payment': False,  # Skip verification
    'settle_payment': False,  # Skip settlement
}
```

---

## Complete Example

```python
# Django views.py
from django.http import JsonResponse
from x402_connector.django import require_payment

# Free endpoint
def public_data(request):
    return JsonResponse({'data': 'public'})

# Single paid endpoint
@require_payment(price='$0.01')
def premium_data(request):
    return JsonResponse({'data': 'premium'})

# Variable pricing
@require_payment(price='$0.10')
def expensive_api(request):
    # Heavy computation
    result = expensive_operation()
    return JsonResponse({'result': result})

# Access payment info
@require_payment(price='$0.01')
def with_payment_info(request):
    tx_hash = request.META.get('HTTP_X_PAYMENT_SETTLED')
    return JsonResponse({
        'data': 'premium',
        'payment_tx': tx_hash,
    })
```

---

For more examples, see the [examples/](examples/) directory.

