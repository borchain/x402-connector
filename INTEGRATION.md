# Implementation Plan

This document outlines the step-by-step plan to build the x402-connector SDK from scratch.

## Implementation Phases

### Phase 1: Core Foundation (Week 1)

Build the framework-agnostic core that all adapters will use.

#### 1.1 Project Setup

**Tasks:**
- [ ] Initialize project structure
- [ ] Create pyproject.toml with dependencies
- [ ] Set up GitHub Actions for CI/CD
- [ ] Configure linting (ruff, black, mypy)
- [ ] Create .gitignore

**Files to create:**
```
x402-connector/
├── src/x402_connector/
│   ├── __init__.py
│   └── core/
│       └── __init__.py
├── tests/
├── pyproject.toml
├── README.md
├── LICENSE
└── .github/workflows/
    ├── test.yml
    └── release.yml
```

**Acceptance criteria:**
- Project builds with `pip install -e .`
- Tests run with `pytest`
- Linting passes

#### 1.2 Core Data Models

**Files:**
- `src/x402_connector/core/context.py`
- `src/x402_connector/core/config.py`

**Tasks:**
- [ ] Implement `RequestContext` dataclass
- [ ] Implement `ProcessingResult` dataclass
- [ ] Implement `SettlementResult` dataclass
- [ ] Implement `X402Config` with validation
- [ ] Implement `LocalFacilitatorConfig`
- [ ] Implement `RemoteFacilitatorConfig`
- [ ] Add `from_dict()` and `from_env()` methods
- [ ] Write unit tests for all models

**Tests:**
```python
def test_request_context_creation():
    ctx = RequestContext(
        path='/api/test',
        method='GET',
        headers={'X-Payment': 'base64...'},
        absolute_url='https://example.com/api/test'
    )
    assert ctx.path == '/api/test'

def test_config_validation():
    # Should raise without required fields
    with pytest.raises(ValueError):
        X402Config(network='', price='', pay_to_address='')
    
    # Should work with valid config
    config = X402Config(
        network='base',
        price='$0.01',
        pay_to_address='0x123'
    )
    assert config.network == 'base'

def test_config_from_dict():
    config = X402Config.from_dict({
        'network': 'base',
        'price': '$0.01',
        'pay_to_address': '0x123',
        'local': {'verify_balance': True}
    })
    assert config.local.verify_balance is True
```

#### 1.3 Base Adapter Interface

**File:** `src/x402_connector/core/adapters.py`

**Tasks:**
- [ ] Define `BaseAdapter` abstract class
- [ ] Document all abstract methods
- [ ] Add type hints

**Tests:**
```python
def test_adapter_must_implement_all_methods():
    class IncompleteAdapter(BaseAdapter):
        pass
    
    with pytest.raises(TypeError):
        IncompleteAdapter()
```

#### 1.4 Facilitators (Port from django-x402)

**File:** `src/x402_connector/core/facilitators.py`

**Tasks:**
- [ ] Port `BaseFacilitator` interface
- [ ] Port `LocalFacilitator` (remove Django dependencies)
- [ ] Port `RemoteFacilitator`
- [ ] Port `HybridFacilitator`
- [ ] Add `get_facilitator()` factory function
- [ ] Update to use `X402Config` instead of Django settings
- [ ] Use `os.environ` instead of Django settings for env vars
- [ ] Write unit tests

**Changes from django-x402:**
```python
# OLD (Django-specific)
from django.conf import settings
private_key = getattr(settings, 'X402_SIGNER_KEY', None)

# NEW (Framework-agnostic)
import os
private_key = os.environ.get('X402_SIGNER_KEY')
```

**Tests:**
- Test local facilitator verification
- Test remote facilitator HTTP calls (mock with respx)
- Test hybrid fallback logic
- Test EIP-712 signature verification
- Test nonce tracking
- Test balance verification
- Test transaction simulation

#### 1.5 Core Payment Processor

**File:** `src/x402_connector/core/processor.py`

**Tasks:**
- [ ] Implement `X402PaymentProcessor` class
- [ ] Implement `process_request()` method
- [ ] Implement `settle_payment()` method
- [ ] Implement `_is_protected_path()` helper
- [ ] Implement `_build_payment_requirements()` helper
- [ ] Add caching for replay protection
- [ ] Write comprehensive unit tests

**Tests:**
```python
def test_unprotected_path_allows_through():
    config = X402Config(
        network='base',
        price='$0.01',
        pay_to_address='0x123',
        protected_paths=['/api/premium/*']
    )
    processor = X402PaymentProcessor(config)
    
    context = RequestContext(
        path='/public/free',
        method='GET',
        headers={},
        absolute_url='https://example.com/public/free'
    )
    
    result = processor.process_request(context)
    assert result.action == 'allow'

def test_protected_path_without_payment_denies():
    config = X402Config(
        network='base',
        price='$0.01',
        pay_to_address='0x123',
        protected_paths=['/api/premium/*']
    )
    processor = X402PaymentProcessor(config)
    
    context = RequestContext(
        path='/api/premium/data',
        method='GET',
        headers={},
        absolute_url='https://example.com/api/premium/data'
    )
    
    result = processor.process_request(context)
    assert result.action == 'deny'
    assert result.requirements is not None

def test_valid_payment_allows():
    # Mock facilitator to return valid
    # Test full flow
    pass
```

**Milestone:** Core foundation complete - all tests passing, no framework dependencies

---

### Phase 2: Django Adapter (Week 2)

Build the Django integration on top of the core.

#### 2.1 Django Adapter

**File:** `src/x402_connector/django/adapter.py`

**Tasks:**
- [ ] Implement `DjangoAdapter(BaseAdapter)`
- [ ] Implement `extract_request_context()`
- [ ] Implement `create_payment_required_response()`
- [ ] Implement `add_payment_response_header()`
- [ ] Implement `is_success_response()`
- [ ] Write unit tests (no Django test client needed)

**Tests:**
```python
from django.http import HttpRequest

def test_django_adapter_extracts_context():
    request = HttpRequest()
    request.path = '/api/test'
    request.method = 'GET'
    request.META['HTTP_X_PAYMENT'] = 'base64...'
    
    adapter = DjangoAdapter()
    context = adapter.extract_request_context(request)
    
    assert context.path == '/api/test'
    assert context.method == 'GET'
    assert context.payment_header == 'base64...'
```

#### 2.2 Django Middleware

**File:** `src/x402_connector/django/middleware.py`

**Tasks:**
- [ ] Implement `X402Middleware`
- [ ] Load config from Django settings
- [ ] Integrate with core processor
- [ ] Handle sync Django views
- [ ] Write integration tests with Django test client

**Tests:**
```python
from django.test import RequestFactory, Client

def test_middleware_blocks_without_payment(client):
    response = client.get('/api/premium/data')
    assert response.status_code == 402
    assert 'x402Version' in response.json()

def test_middleware_allows_with_valid_payment(client, monkeypatch):
    # Mock facilitator
    # Make request with payment header
    # Assert 200 response
    pass
```

#### 2.3 Django Views & URLs

**Files:**
- `src/x402_connector/django/views.py`
- `src/x402_connector/django/urls.py`

**Tasks:**
- [ ] Port facilitator verification endpoint
- [ ] Port facilitator settlement endpoint
- [ ] Port discovery endpoint
- [ ] Create URL patterns
- [ ] Write tests

#### 2.4 Django Documentation & Examples

**Tasks:**
- [ ] Create Django quickstart guide
- [ ] Create complete Django example app
- [ ] Document Django-specific configuration
- [ ] Add to main README

**Milestone:** Django adapter complete - backward compatible with django-x402

---

### Phase 3: Flask Adapter (Week 3)

#### 3.1 Flask Adapter

**File:** `src/x402_connector/flask/adapter.py`

**Tasks:**
- [ ] Implement `FlaskAdapter(BaseAdapter)`
- [ ] Implement all required methods
- [ ] Write unit tests

#### 3.2 Flask Extension

**File:** `src/x402_connector/flask/extension.py`

**Tasks:**
- [ ] Implement `X402Flask` extension class
- [ ] Implement `init_app()` method
- [ ] Implement `require_payment()` decorator
- [ ] Support both app factory and direct initialization
- [ ] Write integration tests with Flask test client

**Tests:**
```python
from flask import Flask

def test_flask_decorator_blocks_without_payment():
    app = Flask(__name__)
    x402 = X402Flask(app, config={...})
    
    @app.route('/api/premium')
    @x402.require_payment()
    def premium():
        return {'data': 'premium'}
    
    with app.test_client() as client:
        response = client.get('/api/premium')
        assert response.status_code == 402
```

#### 3.3 Flask Documentation & Examples

**Tasks:**
- [ ] Create Flask quickstart guide
- [ ] Create complete Flask example app
- [ ] Document Flask-specific patterns
- [ ] Add to main README

**Milestone:** Flask adapter complete

---

### Phase 4: FastAPI Adapter (Week 4)

#### 4.1 FastAPI Adapter

**File:** `src/x402_connector/fastapi/adapter.py`

**Tasks:**
- [ ] Implement `FastAPIAdapter(BaseAdapter)`
- [ ] Handle async operations
- [ ] Implement all required methods
- [ ] Write unit tests

#### 4.2 FastAPI Middleware

**File:** `src/x402_connector/fastapi/middleware.py`

**Tasks:**
- [ ] Implement `X402Middleware(BaseHTTPMiddleware)`
- [ ] Handle async request processing
- [ ] Integrate with core processor
- [ ] Write async tests with httpx AsyncClient

**Tests:**
```python
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_fastapi_middleware_blocks_without_payment():
    app = FastAPI()
    app.add_middleware(X402Middleware, config={...})
    
    @app.get('/api/premium')
    async def premium():
        return {'data': 'premium'}
    
    async with AsyncClient(app=app, base_url='http://test') as client:
        response = await client.get('/api/premium')
        assert response.status_code == 402
```

#### 4.3 FastAPI Dependencies (Optional)

**File:** `src/x402_connector/fastapi/dependencies.py`

**Tasks:**
- [ ] Create dependency injection helpers
- [ ] Allow per-endpoint payment requirements
- [ ] Document advanced patterns

**Example:**
```python
from fastapi import Depends
from x402_connector.fastapi import verify_payment

@app.get('/api/premium')
async def premium(payer: str = Depends(verify_payment)):
    return {'data': 'premium', 'payer': payer}
```

#### 4.4 FastAPI Documentation & Examples

**Tasks:**
- [ ] Create FastAPI quickstart guide
- [ ] Create complete FastAPI example app
- [ ] Document async patterns
- [ ] Add to main README

**Milestone:** FastAPI adapter complete - Core 3 frameworks done

---

### Phase 5: Polish & Documentation (Week 5)

#### 5.1 Comprehensive Documentation

**Tasks:**
- [ ] Complete API reference
- [ ] Add architecture diagrams
- [ ] Create migration guide from django-x402
- [ ] Document all configuration options
- [ ] Add troubleshooting guide
- [ ] Create contributing guide

#### 5.2 Examples

**Tasks:**
- [ ] Create example for each framework
- [ ] Add Docker Compose setup for examples
- [ ] Include frontend payment UI examples
- [ ] Document local development setup

#### 5.3 Testing & Quality

**Tasks:**
- [ ] Achieve >90% code coverage
- [ ] Add integration tests with real blockchain (Anvil)
- [ ] Performance benchmarks
- [ ] Memory leak tests
- [ ] Thread safety tests

#### 5.4 Package & Release

**Tasks:**
- [ ] Configure PyPI publishing
- [ ] Create GitHub releases
- [ ] Set up documentation hosting (Read the Docs)
- [ ] Create release checklist
- [ ] Tag v0.1.0

**Milestone:** v0.1.0 release ready

---

### Phase 6: Additional Frameworks (Week 6+)

After the core 3 frameworks are stable, add support for additional frameworks:

#### 6.1 Pyramid

**Tasks:**
- [ ] Create Pyramid adapter
- [ ] Create tween for middleware
- [ ] Create decorator
- [ ] Write tests
- [ ] Document

#### 6.2 Bottle

**Tasks:**
- [ ] Create Bottle adapter
- [ ] Create plugin
- [ ] Create decorator
- [ ] Write tests
- [ ] Document

#### 6.3 Tornado

**Tasks:**
- [ ] Create Tornado adapter
- [ ] Create request handler mixin
- [ ] Handle async patterns
- [ ] Write tests
- [ ] Document

#### 6.4 Sanic

**Tasks:**
- [ ] Create Sanic adapter
- [ ] Create middleware
- [ ] Handle async patterns
- [ ] Write tests
- [ ] Document

---

## Development Guidelines

### Code Quality Standards

1. **Type Hints**: All public APIs must have full type hints
2. **Documentation**: All public functions/classes must have docstrings
3. **Tests**: Minimum 90% code coverage
4. **Formatting**: Use black with 100 character line length
5. **Linting**: Pass ruff checks
6. **Type Checking**: Pass mypy checks

### Testing Strategy

**Unit Tests:**
- Test core logic in isolation
- Mock all external dependencies
- Fast (<1ms per test)

**Integration Tests:**
- Test framework adapters with real framework test clients
- Mock blockchain calls
- Medium speed (~10-100ms per test)

**End-to-End Tests:**
- Optional: Test against local blockchain
- Test complete payment flow
- Slow (>1s per test)

### Git Workflow

1. Create feature branch from `main`
2. Implement feature with tests
3. Run full test suite locally
4. Open PR with description
5. Address review comments
6. Squash and merge

### Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create GitHub release with tag
4. CI automatically publishes to PyPI
5. Update documentation

---

## Critical Path

The critical path for the first release (v0.1.0) is:

```
Week 1: Core Foundation
  ↓
Week 2: Django Adapter (backward compatibility)
  ↓
Week 3: Flask Adapter (expand ecosystem)
  ↓
Week 4: FastAPI Adapter (complete core 3)
  ↓
Week 5: Polish & Release
```

**Total estimated time:** 5-6 weeks for v0.1.0

Additional frameworks can be added incrementally in v0.2.0, v0.3.0, etc.

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Framework compatibility issues | Early testing with multiple framework versions |
| Async/sync complexity | Clear separation in adapters, comprehensive async tests |
| Breaking changes in dependencies | Pin versions, monitor upstream changes |
| Performance overhead | Benchmarking, profiling, optimization |

### Project Risks

| Risk | Mitigation |
|------|------------|
| Scope creep | Focus on core 3 frameworks first |
| Insufficient testing | Require 90% coverage, automated CI |
| Poor documentation | Write docs alongside code, examples first |
| Adoption barriers | Migration guide, backward compatibility |

---

## Success Metrics

For v0.1.0 to be considered successful:

- [ ] All core 3 frameworks (Django, Flask, FastAPI) fully supported
- [ ] >90% test coverage
- [ ] All tests passing on Python 3.10, 3.11, 3.12, 3.13
- [ ] Complete documentation published
- [ ] At least 3 working examples
- [ ] Published to PyPI
- [ ] GitHub Actions CI/CD working
- [ ] At least 1 external user successfully integrates

---

## Next Steps

To start implementation:

1. **Day 1-2**: Set up project structure and CI/CD
2. **Day 3-5**: Implement core data models and tests
3. **Day 6-7**: Port facilitators from django-x402
4. **Day 8-10**: Implement core processor
5. **Week 2**: Begin Django adapter

Start with `pyproject.toml`, project structure, and basic tests to establish the foundation.

