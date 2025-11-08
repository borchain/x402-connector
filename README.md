# x402-connector

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Solana](https://img.shields.io/badge/Solana-14F195?logo=solana&logoColor=white)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Django](https://img.shields.io/badge/Django-5.0%2B-092E20?logo=django)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask)
![Tornado](https://img.shields.io/badge/Tornado-6.0%2B-00A1E0)
![Pyramid](https://img.shields.io/badge/Pyramid-2.0%2B-EE3322)

**Python SDK for HTTP 402 Payment Required on Solana**

A lightweight, framework-agnostic SDK that adds micropayments to Python web applications using the x402 protocol on Solana blockchain. Fully compatible with [Corbits.dev](https://corbits.dev/) facilitator.

## Why Solana?

- ⚡ **400ms finality** - Near-instant payment confirmation
- 💰 **$0.00001/tx** - Lowest transaction costs
- 🔒 **Native USDC** - Real stablecoins, not wrapped tokens
- 🚀 **High throughput** - 65,000 TPS capability

## Features

- 🎯 **Simple Integration** - Add `@require_payment` decorator to any endpoint
- 🌐 **Framework Agnostic** - Works with Django, Flask, FastAPI, Tornado, Pyramid
- ⚙️ **Zero Configuration** - Sensible defaults, configure only what you need
- 🔧 **Production Ready** - Comprehensive error handling and test coverage
- 📖 **Well Documented** - Clear examples and API reference
- 🌍 **Corbits Compatible** - Works with https://corbits.dev/ facilitator

## Quick Start

### Installation

```bash
pip install x402-connector
```

### Django Example

```python
# settings.py
MIDDLEWARE = [
    'x402_connector.django.X402Middleware',
]

X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
}

# views.py
from x402_connector.django import require_payment

def free_endpoint(request):
    return JsonResponse({'data': 'free'})

@require_payment(price='$0.01')
def premium_endpoint(request):
    return JsonResponse({'data': 'premium'})
```

That's it! The `premium_endpoint` now requires payment.

### Flask Example

```python
from flask import Flask, jsonify
from x402_connector.flask import X402, require_payment

app = Flask(__name__)
x402 = X402(app, pay_to_address='YOUR_SOLANA_ADDRESS')

@app.route('/free')
def free_endpoint():
    return jsonify({'data': 'free'})

@app.route('/premium')
@require_payment(price='$0.01')
def premium_endpoint():
    return jsonify({'data': 'premium'})
```

### FastAPI Example

```python
from fastapi import FastAPI, Request
from x402_connector.fastapi import X402Middleware, require_payment

app = FastAPI()
app.add_middleware(X402Middleware, pay_to_address='YOUR_SOLANA_ADDRESS')

@app.get('/free')
async def free_endpoint():
    return {'data': 'free'}

@app.get('/premium')
@require_payment(price='$0.01')
async def premium_endpoint(request: Request):
    return {'data': 'premium'}
```

### Tornado Example

```python
from tornado import web, ioloop
from x402_connector.tornado import X402Middleware, require_payment

class PremiumHandler(web.RequestHandler):
    @require_payment(price='$0.01')
    async def get(self):
        self.write({'data': 'premium'})

app = web.Application([(r'/premium', PremiumHandler)])
X402Middleware(app, pay_to_address='YOUR_SOLANA_ADDRESS')

app.listen(8888)
ioloop.IOLoop.current().start()
```

### Pyramid Example

```python
from pyramid.config import Configurator
from pyramid.response import Response
from x402_connector.pyramid import require_payment

@require_payment(price='$0.01')
def premium_view(request):
    return Response(json.dumps({'data': 'premium'}))

config = Configurator(settings={
    'x402.pay_to_address': 'YOUR_SOLANA_ADDRESS',
})
config.include('x402_connector.pyramid')
config.add_route('premium', '/premium')
config.add_view(premium_view, route_name='premium')
app = config.make_wsgi_app()
```

## How It Works

1. **User requests protected endpoint** → `GET /premium`
2. **Server returns 402** with Solana payment instructions
3. **User signs payment** with wallet (Phantom, Solflare, etc.)
4. **User retries with payment** → `GET /premium` + `X-PAYMENT` header
5. **Server verifies & settles** → Returns 200 with content

```
GET /premium
←
402 Payment Required
{
  "accepts": [{
    "network": "solana-devnet",
    "asset": "USDC",
    "amount": "10000",
    "payTo": "YOUR_ADDRESS"
  }]
}
```

## Configuration

```python
X402_CONFIG = {
    # Required
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',  # Where you receive payments
    
    # Optional (sensible defaults)
    'price': '$0.01',                          # Default price
    'network': 'solana-mainnet',               # Network (mainnet/devnet/testnet)
    'rpc_url': None,                           # Custom RPC (uses public by default)
    'signer_key_env': 'X402_SIGNER_KEY',      # Env var for settlement key
}
```

## Environment Variables

```bash
# Required for settlement
X402_SIGNER_KEY=your_private_key_base58     # Server wallet for gas fees

# Optional overrides
X402_PAY_TO_ADDRESS=your_solana_address     # Payment recipient
X402_NETWORK=solana-devnet                  # Network override
X402_RPC_URL=https://api.mainnet-beta.solana.com  # Custom RPC
```

## Corbits.dev Compatibility

This SDK is fully compatible with the [Corbits.dev](https://corbits.dev/) facilitator service. You can use it in two modes:

### Local Mode (Self-hosted)
```python
X402_CONFIG = {
    'pay_to_address': 'YOUR_ADDRESS',
    # Handles verification and settlement locally
}
```

### Remote Mode (Using Corbits)
```python
X402_CONFIG = {
    'pay_to_address': 'YOUR_ADDRESS',
    'facilitator_mode': 'remote',
    'remote': {
        'url': 'https://corbits.dev/api',
        'headers': {'Authorization': 'Bearer YOUR_TOKEN'},
    }
}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=x402_connector

# Test specific framework
pytest tests/test_django_adapter.py
```

## Examples

See the `examples/` directory for complete working examples:

- [Django Example](examples/django/) - Full Django integration with Phantom wallet demo
- [Flask Example](examples/flask/) - Full Flask integration with Phantom wallet demo
- [FastAPI Example](examples/fastapi/) - Full FastAPI integration with Phantom wallet demo
- [Tornado Example](examples/tornado/) - Full Tornado integration with async support
- [Pyramid Example](examples/pyramid/) - Full Pyramid integration with tween middleware

## Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes
- [API Reference](API.md) - Complete API documentation
- [Examples](examples/) - Working code examples

## Security Notes

- **Never commit private keys** - Use environment variables
- **Separate wallets** - Use different addresses for `pay_to_address` (cold) and `signer_key` (hot)
- **Mainnet readiness** - Test thoroughly on devnet before production
- **Rate limiting** - Implement rate limiting to prevent abuse

## Requirements

- Python 3.10+
- Solana wallet
- USDC for payments (or devnet SOL for testing)

## Framework Support

| Framework | Version | Status |
|-----------|---------|--------|
| Django    | 5.0+    | ✅ Full Support |
| Flask     | 3.0+    | ✅ Full Support |
| FastAPI   | 0.100+  | ✅ Full Support |
| Tornado   | 6.0+    | ✅ Full Support |
| Pyramid   | 2.0+    | ✅ Full Support |

## License

MIT License - see [LICENSE](LICENSE) for details

## Links

- [x402 Protocol](https://github.com/coinbase/x402)
- [Solana Documentation](https://docs.solana.com)
- [Corbits Facilitator](https://corbits.dev/)
- [GitHub Issues](https://github.com/yourusername/x402-connector/issues)

## Contributing

Contributions welcome! Please open an issue or PR.

---

Built with ❤️ for the Solana ecosystem
