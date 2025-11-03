# x402-connector

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

**Universal Python SDK for the x402 "Payment Required" protocol.**

A framework-agnostic SDK that brings HTTP 402 payments to Python web applications with seamless integration across Django, Flask, FastAPI, and more.

## 🚀 Features

- **Framework Agnostic**: One core library, multiple framework adapters
- **Simple Integration**: Single decorator or middleware to protect endpoints
- **Flexible Configuration**: Environment variables, dicts, or config objects
- **Multiple Facilitator Modes**: Local, remote, or hybrid settlement
- **Type Safe**: Full typing support for better developer experience
- **Production Ready**: Comprehensive test coverage and battle-tested patterns

## 📦 Installation

```bash
# Core library
pip install x402-connector

# With framework-specific extras
pip install x402-connector[django]
pip install x402-connector[flask]
pip install x402-connector[fastapi]

# Install all frameworks
pip install x402-connector[all]
```

## 🎯 Quick Start

### Django

```python
# settings.py
MIDDLEWARE = [
    'x402_connector.django.X402Middleware',
]

X402_CONFIG = {
    'protected_paths': ['/api/premium/*'],
    'network': 'base',
    'price': '$0.01',
    'pay_to_address': '0xYourAddress',
}
```

### Flask

```python
from flask import Flask
from x402_connector.flask import X402Flask

app = Flask(__name__)
x402 = X402Flask(app, {
    'network': 'base',
    'price': '$0.01',
    'pay_to_address': '0xYourAddress',
})

@app.route('/api/premium')
@x402.require_payment()
def premium_endpoint():
    return {'data': 'premium content'}
```

### FastAPI

```python
from fastapi import FastAPI
from x402_connector.fastapi import X402Middleware

app = FastAPI()
app.add_middleware(X402Middleware, config={
    'protected_paths': ['/api/premium'],
    'network': 'base',
    'price': '$0.01',
    'pay_to_address': '0xYourAddress',
})

@app.get('/api/premium')
async def premium_endpoint():
    return {'data': 'premium content'}
```

## 🏗️ Architecture

The SDK follows a layered architecture:

```
Framework Adapters (Django, Flask, FastAPI, etc.)
    ↓
Core x402 Logic (Framework-agnostic)
    ↓
Facilitators (Local, Remote, Hybrid)
    ↓
Blockchain Settlement Layer
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

## 📚 Documentation

- [Architecture Overview](ARCHITECTURE.md) - System design and patterns
- [Technical Specification](TECHNICAL.md) - Implementation details
- [Integration Guide](INTEGRATION.md) - Step-by-step implementation plan

## 📚 Examples

Complete, working examples for each framework:

### Django Example (✅ COMPLETE)

```bash
cd examples/django_basic
./quickstart.sh
python manage.py runserver
```

Visit `http://localhost:8000` to see it in action!

See [Django Example README](examples/django_basic/README.md) for detailed documentation.

### Flask Example (🚧 Coming Soon)

```bash
cd examples/flask_basic
./quickstart.sh
flask run
```

### FastAPI Example (🚧 Coming Soon)

```bash
cd examples/fastapi_basic
./quickstart.sh
uvicorn main:app
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Test specific framework
pytest tests/test_django.py
pytest tests/test_flask.py
pytest tests/test_fastapi.py

# Test core logic only
pytest tests/test_core.py
```

## 🔧 Configuration

All configuration options with descriptions:

```python
config = {
    # Required
    'network': 'base',              # Blockchain network
    'price': '$0.01',               # Price per request
    'pay_to_address': '0x...',      # Payment recipient
    
    # Optional
    'protected_paths': ['*'],       # Paths to protect (glob patterns)
    'facilitator_mode': 'local',    # 'local' | 'remote' | 'hybrid'
    'description': 'API access',    # Payment description
    'mime_type': 'application/json', # Response content type
    'max_timeout_seconds': 60,      # Payment validity window
    
    # Local facilitator options
    'local': {
        'private_key_env': 'X402_SIGNER_KEY',
        'rpc_url_env': 'X402_RPC_URL',
        'verify_balance': True,
        'simulate_before_send': True,
    },
    
    # Remote facilitator options
    'remote': {
        'url': 'https://facilitator.example.com',
        'headers': {'Authorization': 'Bearer token'},
    },
}
```

## 🌐 Supported Frameworks

| Framework | Status | Version |
|-----------|--------|---------|
| Django    | ✅ Supported | 5.0+ |
| Flask     | ✅ Supported | 3.0+ |
| FastAPI   | ✅ Supported | 0.100+ |
| Pyramid   | 🚧 Planned | - |
| Bottle    | 🚧 Planned | - |
| Tornado   | 🚧 Planned | - |
| Sanic     | 🚧 Planned | - |

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [x402 Protocol Specification](https://github.com/coinbase/x402)
- [Solana x402 Overview](https://solana.com/x402/what-is-x402)
- [Coinbase x402 Documentation](https://www.coinbase.com/developer-platform/products/x402)

## 💡 Examples

See the [examples/](examples/) directory for complete integration examples:

- [Django Example](examples/django_example/)
- [Flask Example](examples/flask_example/)
- [FastAPI Example](examples/fastapi_example/)

