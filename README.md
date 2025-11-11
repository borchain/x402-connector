# x402-connector

[![PyPI version](https://badge.fury.io/py/x402-connector.svg)](https://badge.fury.io/py/x402-connector)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/x402-connector)](https://pypi.org/project/x402-connector/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/x402-connector)](https://pypi.org/project/x402-connector/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Solana](https://img.shields.io/badge/Solana-14F195?logo=solana&logoColor=white)
![Tests](https://img.shields.io/badge/tests-186%20passed-brightgreen)
![Django](https://img.shields.io/badge/Django-5.0%2B-092E20?logo=django)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask)
![Tornado](https://img.shields.io/badge/Tornado-6.0%2B-00A1E0)
![Pyramid](https://img.shields.io/badge/Pyramid-2.0%2B-EE3322)

**Python SDK for HTTP 402 Payment Required on Solana**

A lightweight, framework-agnostic SDK that adds micropayments to Python web applications using the x402 protocol on Solana blockchain.

## Why Solana?

- ⚡ **400ms finality** - Near-instant payment confirmation
- 💰 **$0.00001/tx** - Lowest transaction costs
- 🔒 **Native USDC** - Real stablecoins, not wrapped tokens
- 🚀 **High throughput** - 65,000 TPS capability

## Features

- 🎯 **Simple Integration** - Add `@require_payment` decorator to any endpoint
- 🌐 **Framework Agnostic** - Works with Django, Flask, FastAPI, Tornado, Pyramid
- 🔌 **Multiple Facilitators** - Local, PayAI, Corbits (protocol-compatible)
- ⚙️ **Zero Configuration** - Sensible defaults, configure only what you need
- 🔧 **Production Ready** - Comprehensive error handling and test coverage
- 📖 **Well Documented** - Clear examples and API reference

## Quick Start

### Installation

```bash
pip install x402-connector
```

### Usage Example

Add payment requirements to any endpoint with a single decorator:

```python
from flask import Flask, jsonify
from x402_connector.flask import X402, require_payment
import os

app = Flask(__name__)

# Initialize x402 (one-time setup)
x402 = X402(app, config={
    'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS'),
    'network': 'solana-mainnet',
    'price': '$0.01',
})

# Free endpoint - no payment required
@app.route('/free')
def free_endpoint():
    return jsonify({'data': 'free'})

# Premium endpoint - requires $0.01 payment
@app.route('/premium')
@require_payment(price='$0.01')
def premium_endpoint():
    return jsonify({'data': 'premium'})

if __name__ == '__main__':
    app.run(debug=True)
```

### Environment Setup

```bash
# Required: Your Solana address for receiving payments
export X402_PAY_TO_ADDRESS=your_solana_address_here

# Required: Private key for transaction settlement (hot wallet)
export X402_SIGNER_KEY=your_private_key_base58

# Optional: Network selection (defaults to solana-mainnet)
export X402_NETWORK=solana-mainnet
```

That's it! Your API now requires payment for premium endpoints.

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
    "network": "solana-mainnet",
    "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "assetSymbol": "USDC",
    "maxAmountRequired": "10000",
    "payTo": "YOUR_ADDRESS"
  }]
}
```

## Framework Integration

All frameworks use the same simple decorator pattern:

<details>
<summary><b>Django</b></summary>

```python
# settings.py
MIDDLEWARE = ['x402_connector.django.X402Middleware']

X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
}

# views.py
from x402_connector.django import require_payment

@require_payment(price='$0.01')
def premium_endpoint(request):
    return JsonResponse({'data': 'premium'})
```

[See Django example →](examples/django/)

</details>

<details>
<summary><b>Flask</b></summary>

```python
from flask import Flask
from x402_connector.flask import X402, require_payment

app = Flask(__name__)
x402 = X402(app, config={
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
})

@app.route('/premium')
@require_payment(price='$0.01')
def premium_endpoint():
    return {'data': 'premium'}
```

[See Flask example →](examples/flask/)

</details>

<details>
<summary><b>FastAPI</b></summary>

```python
from fastapi import FastAPI
from x402_connector.fastapi import X402Middleware, require_payment

app = FastAPI()
app.add_middleware(X402Middleware, 
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet'
)

@app.get('/premium')
@require_payment(price='$0.01')
async def premium_endpoint():
    return {'data': 'premium'}
```

[See FastAPI example →](examples/fastapi/)

</details>

<details>
<summary><b>Tornado</b></summary>

```python
from tornado import web, ioloop
from x402_connector.tornado import X402Middleware, require_payment

class PremiumHandler(web.RequestHandler):
    @require_payment(price='$0.01')
    async def get(self):
        self.write({'data': 'premium'})

app = web.Application([(r'/premium', PremiumHandler)])
X402Middleware(app, pay_to_address='YOUR_SOLANA_ADDRESS', network='solana-mainnet')
app.listen(8888)
```

[See Tornado example →](examples/tornado/)

</details>

<details>
<summary><b>Pyramid</b></summary>

```python
from pyramid.config import Configurator
from x402_connector.pyramid import require_payment

@require_payment(price='$0.01')
def premium_view(request):
    return {'data': 'premium'}

config = Configurator(settings={
    'x402.pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'x402.network': 'solana-mainnet',
})
config.include('x402_connector.pyramid')
```

[See Pyramid example →](examples/pyramid/)

</details>

## Facilitator Support

x402-connector supports multiple facilitator modes for payment processing:

| Facilitator | Status | Description |
|------------|--------|-------------|
| **Local** | ✅ Ready | Self-hosted verification and settlement |
| **PayAI** | ✅ Ready | Managed service at [payai.network](https://payai.network) |
| **Corbits** | ✅ Ready | Managed service at [corbits.dev](https://corbits.dev) |
| **Hybrid** | ✅ Ready | Local verification + remote settlement |

### Using PayAI Facilitator

```python
x402 = X402(app, config={
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
    'facilitator_mode': 'payai',
    'payai': {
        'facilitator_url': 'https://facilitator.payai.network',
    }
})
```

**Learn more:** [Facilitators Integration Guide →](FACILITATORS_INTEGRATION.md)

## Documentation

- 📘 **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes
- 📗 **[API Reference](API.md)** - Complete API documentation
- 📙 **[Facilitators Guide](FACILITATORS_INTEGRATION.md)** - PayAI, Corbits, local modes
- 💻 **[Examples](examples/)** - Working code for all frameworks
- 🔧 **[Installation Guide](INSTALLATION.md)** - Detailed installation instructions

## Configuration

Minimal required configuration:

```python
{
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',  # Required: where payments go
}
```

Common optional settings:

```python
{
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',              # Network selection
    'price': '$0.01',                         # Default price
    'facilitator_mode': 'local',              # 'local', 'payai', or 'corbits'
    'rpc_url': None,                          # Custom RPC endpoint
    'debug_mode': False,                      # Simulate transactions (testing)
}
```

**Learn more:** [API Reference →](API.md)

## Security Notes

- **Never commit private keys** - Use environment variables
- **Separate wallets** - Use different addresses for `pay_to_address` (cold) and `signer_key` (hot)
- **Test on devnet** - Thoroughly test before production deployment
- **Rate limiting** - Implement rate limiting to prevent abuse
- **Monitor transactions** - Keep track of payment activity

## Requirements

- Python 3.10+
- Solana wallet address
- USDC for payments (mainnet) or devnet SOL (testing)

## Framework Support

| Framework | Version | Status |
|-----------|---------|--------|
| Django    | 5.0+    | ✅ Full Support |
| Flask     | 3.0+    | ✅ Full Support |
| FastAPI   | 0.100+  | ✅ Full Support |
| Tornado   | 6.0+    | ✅ Full Support |
| Pyramid   | 2.0+    | ✅ Full Support |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=x402_connector

# Test specific framework
pytest tests/test_flask_adapter.py
```

## Examples

Complete working examples for each framework:

- **[Django Example](examples/django/)** - Full integration with Phantom wallet demo
- **[Flask Example](examples/flask/)** - Complete Flask setup with interactive UI
- **[FastAPI Example](examples/fastapi/)** - Async FastAPI integration
- **[Tornado Example](examples/tornado/)** - Async Tornado handlers
- **[Pyramid Example](examples/pyramid/)** - Pyramid views and tweens

## Resources

- **[x402 Protocol](https://github.com/coinbase/x402)** - Official protocol specification
- **[Solana Documentation](https://docs.solana.com)** - Solana blockchain docs
- **[PayAI Network](https://payai.network)** - Managed facilitator service
- **[Corbits Platform](https://corbits.dev/)** - API marketplace and facilitator
- **[GitHub Repository](https://github.com/borchain/x402-connector)** - Source code

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT License - see [LICENSE](LICENSE) for details

---

**Built with ❤️ for the Solana ecosystem**
