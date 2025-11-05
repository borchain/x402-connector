# Flask x402 Quickstart

Get started with x402 payments in Flask in under 5 minutes!

## Installation

```bash
pip install x402-connector[flask]
```

## Basic Setup

### 1. Initialize Flask App

```python
from flask import Flask, jsonify
from x402_connector.flask import X402, require_payment

app = Flask(__name__)

# Configure x402
app.config['X402_CONFIG'] = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'price': '$0.01',
    'network': 'solana-devnet',
    'debug_mode': True,
}

# Initialize extension
x402 = X402(app)
```

### 2. Protect Routes

```python
# Free endpoint
@app.route('/api/free')
def free_data():
    return jsonify({'data': 'available to everyone'})

# Paid endpoint
@app.route('/api/premium')
@require_payment(price='$0.01')
def premium_data():
    return jsonify({'data': 'premium content'})
```

### 3. Run Server

```python
if __name__ == '__main__':
    app.run(port=5000)
```

That's it! Your API now requires payment for premium endpoints.

## Environment Variables

Create a `.env` file:

```bash
X402_PAY_TO_ADDRESS=your_solana_address
X402_SIGNER_KEY=your_private_key_base58
X402_NETWORK=solana-devnet
```

## Testing

### Free Endpoint

```bash
curl http://localhost:5000/api/free
# {"data": "available to everyone"}
```

### Premium Endpoint

```bash
curl http://localhost:5000/api/premium
# HTTP 402 Payment Required
# {
#   "x402Version": 1,
#   "accepts": [{...}]
# }
```

## Configuration Options

```python
app.config['X402_CONFIG'] = {
    # Required
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    
    # Optional
    'price': '$0.01',                      # Default price
    'network': 'solana-devnet',            # Network
    'protected_paths': [],                 # Empty = decorator-only mode
    'debug_mode': True,                    # Simulate transactions
    'rpc_url': None,                       # Custom RPC endpoint
    'description': 'API Access',           # Description
}
```

## Custom Pricing

```python
@app.route('/api/cheap')
@require_payment(price='$0.01')
def cheap_api():
    return jsonify({'data': 'cheap'})

@app.route('/api/expensive')
@require_payment(price='$1.00')
def expensive_api():
    return jsonify({'data': 'expensive'})

@app.route('/api/ai')
@require_payment(price='$0.10', description='AI Inference')
def ai_api():
    return jsonify({'result': 'AI output'})
```

## Factory Pattern

For application factories:

```python
from flask import Flask
from x402_connector.flask import X402

x402 = X402()

def create_app():
    app = Flask(__name__)
    app.config['X402_CONFIG'] = {...}
    
    x402.init_app(app)
    
    return app
```

## Complete Example

See `examples/flask/` for a full working example with:
- Interactive web UI
- Balance checking
- Phantom wallet integration
- Free and paid endpoints

## Next Steps

- [Full Documentation](../../README.md)
- [API Reference](../../API.md)
- [Complete Example](./README.md)

---

**Built for Flask developers** 🧪

