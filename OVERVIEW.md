# x402-connector: Overview

## What is x402-connector?

x402-connector is a **universal Python SDK** that brings the x402 "Payment Required" protocol to Python web applications. It provides a clean, framework-agnostic architecture with seamless integrations for the most popular Python web frameworks.

### The Problem

The HTTP 402 status code has existed since 1997 but was never implemented. With the rise of AI agents and micropayments, there's now a need for APIs to require payment before serving content. The x402 protocol activates this dormant status code for the modern web.

### Our Solution

A **single SDK** that works across multiple frameworks with:
- ✅ **One core library** - Framework-agnostic payment logic
- ✅ **Multiple adapters** - Django, Flask, FastAPI, and more
- ✅ **Simple integration** - Single decorator or middleware line
- ✅ **Production ready** - Spec-compliant, well-tested, secure

## Key Features

### 🎯 Framework Agnostic Core

Unlike the original `django-x402` which was tightly coupled to Django, x402-connector has a **completely framework-independent core**:

```
Core Logic (Framework-agnostic)
    ↓
Adapters (Framework-specific)
    ↓
Your Application (Django/Flask/FastAPI/etc.)
```

This architecture means:
- **One codebase** to maintain for payment logic
- **Easy testing** without framework overhead
- **Quick expansion** to new frameworks (just add adapter)

### 🚀 Dead Simple Integration

**Django:**
```python
# settings.py - One config block
MIDDLEWARE = ['x402_connector.django.X402Middleware']
X402_CONFIG = {
    'network': 'base',
    'price': '$0.01',
    'pay_to_address': '0xYourAddress',
}
```

**Flask:**
```python
# app.py - Two lines
from x402_connector.flask import X402Flask
x402 = X402Flask(app, config={...})

@app.route('/api/premium')
@x402.require_payment()  # One decorator
def premium():
    return {'data': 'premium'}
```

**FastAPI:**
```python
# main.py - One middleware line
from x402_connector.fastapi import X402Middleware
app.add_middleware(X402Middleware, config={...})
```

### 🔧 Flexible Configuration

Load configuration from:
- **Dictionaries** - Direct Python dicts
- **Environment variables** - 12-factor app style
- **Framework configs** - Django settings, Flask app.config, etc.

```python
# From dict
config = X402Config.from_dict({...})

# From environment
config = X402Config.from_env()

# Manual
config = X402Config(
    network='base',
    price='$0.01',
    pay_to_address='0x...'
)
```

### 🛡️ Production Ready

- **Spec compliant** - Follows x402 specification exactly
- **Security built-in** - Replay protection, nonce tracking, balance verification
- **Multiple facilitator modes**:
  - `local` - Self-hosted, full control
  - `remote` - Use external facilitator service
  - `hybrid` - Local verification, remote settlement
- **Comprehensive testing** - Unit, integration, and E2E tests
- **Type safe** - Full typing support for better DX

## Architecture Highlights

### Layered Design

```
┌─────────────────────────────────────────┐
│     Application Layer                   │
│  (Your Django/Flask/FastAPI app)        │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│     Framework Adapter Layer             │
│  • Converts framework requests          │
│  • Generates framework responses        │
│  • Handles async/sync differences       │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│     Core Logic Layer                    │
│  • Payment verification                 │
│  • Settlement processing                │
│  • Configuration management             │
│  • Path protection                      │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│     Facilitator Layer                   │
│  • Local: Direct blockchain access      │
│  • Remote: External facilitator API     │
│  • Hybrid: Best of both worlds          │
└─────────────────────────────────────────┘
```

### Request Flow

```
1. Request arrives
   ↓
2. Framework adapter extracts context
   ↓
3. Core processor checks if path protected
   ↓
4. If protected, verify payment via facilitator
   ↓
5. Return allow/deny decision
   ↓
6. If allowed, call endpoint
   ↓
7. If 2xx response, settle payment
   ↓
8. Add X-PAYMENT-RESPONSE header
   ↓
9. Return to client
```

## Comparison with django-x402

### What's Better?

| Aspect | django-x402 | x402-connector |
|--------|-------------|----------------|
| **Framework support** | Django only | Django, Flask, FastAPI, + more |
| **Architecture** | Monolithic | Layered, modular |
| **Testing** | Requires Django | Core testable standalone |
| **Integration** | Middleware only | Middleware + decorators |
| **Configuration** | Django settings only | Dict, env vars, framework configs |
| **Extensibility** | Limited | Easy to add frameworks/facilitators |

### What's Preserved?

- ✅ All facilitator logic (local, remote, hybrid)
- ✅ EIP-3009 TransferWithAuthorization support
- ✅ EIP-712 signature verification
- ✅ Nonce tracking and replay protection
- ✅ Balance verification
- ✅ Transaction simulation
- ✅ Spec compliance

### Migration Path

The Django adapter maintains **backward compatibility** with django-x402:

```python
# Old (django-x402)
from django_x402.middleware import X402Middleware

# New (x402-connector)
from x402_connector.django import X402Middleware

# Configuration format stays the same!
```

## Supported Frameworks

### Phase 1 (v0.1.0) - Core 3

| Framework | Status | Integration Pattern |
|-----------|--------|-------------------|
| **Django** | ✅ Planned | Middleware |
| **Flask** | ✅ Planned | Extension + Decorator |
| **FastAPI** | ✅ Planned | Middleware + Dependencies |

### Phase 2 (v0.2.0+) - Extended Support

| Framework | Status | Integration Pattern |
|-----------|--------|-------------------|
| Pyramid | 🚧 Planned | Tween + Decorator |
| Bottle | 🚧 Planned | Plugin + Decorator |
| Tornado | 🚧 Planned | Handler Mixin |
| Sanic | 🚧 Planned | Middleware |
| CherryPy | 🚧 Planned | Tool + Decorator |
| Dash | 🚧 Planned | Middleware Wrapper |
| Falcon | 🚧 Planned | Middleware |

## Use Cases

### 1. AI Agent API Monetization

```python
@app.route('/api/ai/inference')
@x402.require_payment(price='$0.001')
def ai_inference(prompt: str):
    """Charge per AI inference call."""
    return {'result': model.generate(prompt)}
```

### 2. Premium Content APIs

```python
# Protect all premium endpoints with one config
X402_CONFIG = {
    'protected_paths': ['/api/premium/*'],
    'price': '$0.01',
}
```

### 3. Per-Request Micropayments

```python
# Different prices for different endpoints
@app.route('/api/heavy-compute')
@x402.require_payment(price='$0.10')
def heavy_compute():
    pass

@app.route('/api/light-data')
@x402.require_payment(price='$0.001')
def light_data():
    pass
```

### 4. Multi-Chain Support

```python
# Accept payments on multiple networks
X402_CONFIG = {
    'accepts': [
        {'network': 'base', 'price': '$0.01'},
        {'network': 'polygon', 'price': '$0.01'},
        {'network': 'solana', 'price': '$0.01'},
    ]
}
```

## Design Philosophy

### 1. Separation of Concerns

**Core logic** knows nothing about frameworks. **Adapters** know nothing about payment logic. Each layer has a single responsibility.

### 2. Convention over Configuration

Sensible defaults for everything. Works out of the box with minimal config. Power users can customize everything.

### 3. Developer Experience First

- **Type hints** everywhere
- **Clear error messages**
- **Comprehensive documentation**
- **Working examples** for every framework
- **Test helpers** for your app

### 4. Production Ready

Not a toy. Built for real applications with real users:
- Security by default
- Performance optimized
- Well tested
- Battle-tested patterns

## What's Next?

### Immediate Roadmap (v0.1.0)

1. ✅ Core foundation (Week 1)
2. ✅ Django adapter (Week 2)
3. ✅ Flask adapter (Week 3)
4. ✅ FastAPI adapter (Week 4)
5. ✅ Documentation & release (Week 5)

### Future Plans

- **v0.2.0**: Additional frameworks (Pyramid, Bottle, Tornado, Sanic)
- **v0.3.0**: Advanced features (rate limiting, quotas, subscriptions)
- **v0.4.0**: Observability (metrics, tracing, monitoring hooks)
- **v1.0.0**: Production hardening, performance optimization

## Getting Started

1. **Install:**
   ```bash
   pip install x402-connector[django]  # or flask, fastapi
   ```

2. **Configure:**
   ```python
   X402_CONFIG = {
       'network': 'base',
       'price': '$0.01',
       'pay_to_address': '0xYourAddress',
   }
   ```

3. **Integrate:**
   - Django: Add middleware
   - Flask: Add decorator
   - FastAPI: Add middleware

4. **Test:**
   ```bash
   pytest
   ```

5. **Deploy:**
   Works everywhere Python works!

## Learn More

- **[Architecture](ARCHITECTURE.md)** - Deep dive into design
- **[Technical Spec](TECHNICAL.md)** - Implementation details
- **[Integration Plan](INTEGRATION.md)** - Step-by-step roadmap
- **[Examples](examples/)** - Working code for each framework

## Contributing

We welcome contributions! Whether it's:
- 🐛 Bug reports
- 💡 Feature requests
- 📖 Documentation improvements
- 🔧 New framework adapters
- ✅ Test coverage
- 🎨 Examples and tutorials

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ by the x402 community**

Questions? Open an issue or discussion on GitHub!

