# Quick Start Guide

Welcome to x402-connector! This guide will help you understand the project and start contributing.

## 🎯 What You Have

This repository contains a **complete architecture and skeleton** for a universal Python SDK for the x402 payment protocol. It supports multiple frameworks (Django, Flask, FastAPI) with a clean, framework-agnostic core.

## 📁 Project Structure

```
x402-connector/
├── README.md              # Main project README
├── OVERVIEW.md            # High-level vision and design
├── ARCHITECTURE.md        # Technical architecture deep-dive
├── TECHNICAL.md           # Implementation details
├── INTEGRATION.md         # Step-by-step implementation plan
├── PROJECT_SUMMARY.md     # Complete project summary
├── CONTRIBUTING.md        # Contribution guidelines
├── QUICKSTART.md          # This file
│
├── src/x402_connector/    # Source code
│   ├── __init__.py        # Package exports
│   └── core/              # Framework-agnostic core
│       ├── __init__.py
│       ├── config.py      # Configuration system ✅
│       ├── context.py     # Request/result abstractions ✅
│       ├── adapters.py    # Base adapter interface ✅
│       └── processor.py   # Core payment processor ✅
│
├── tests/                 # Test suite
│   ├── test_core_config.py    # Config tests ✅
│   └── test_core_context.py   # Context tests ✅
│
├── .github/workflows/     # CI/CD
│   └── test.yml          # GitHub Actions workflow ✅
│
├── pyproject.toml        # Package configuration ✅
├── .gitignore            # Git ignore patterns ✅
└── setup_dev.sh          # Development setup script ✅
```

## 🚀 Quick Setup (30 seconds)

```bash
# Clone if you haven't already
cd /Users/borker/coin_projects/x402-connector

# Run the setup script
./setup_dev.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,tests]"
pytest -v
```

## 📖 Documentation Reading Order

**For Understanding the Project:**
1. **README.md** (5 min) - Overview and quick examples
2. **OVERVIEW.md** (10 min) - Vision, use cases, comparison
3. **PROJECT_SUMMARY.md** (10 min) - What's done, what's next
4. **ARCHITECTURE.md** (20 min) - Technical design decisions
5. **TECHNICAL.md** (30 min) - Implementation details

**For Contributing:**
1. **INTEGRATION.md** - Step-by-step implementation roadmap
2. **CONTRIBUTING.md** - Code style, workflow, testing
3. Pick a task from INTEGRATION.md and start coding!

## ✅ What's Already Done

### Core Foundation (Phase 1 - Partially Complete)

- ✅ **Configuration System** (`core/config.py`)
  - `X402Config` with full validation
  - Support for dict, env vars, and framework configs
  - Local and remote facilitator configs

- ✅ **Context Abstractions** (`core/context.py`)
  - `RequestContext` - Framework-agnostic request
  - `ProcessingResult` - Payment verification result
  - `SettlementResult` - Settlement result

- ✅ **Base Adapter** (`core/adapters.py`)
  - Interface for all framework adapters
  - Clear contract and documentation

- ✅ **Core Processor** (`core/processor.py`)
  - Skeleton implementation
  - Path protection logic
  - Caching infrastructure

- ✅ **Tests** (`tests/`)
  - Configuration tests (15+ cases)
  - Context tests
  - Demonstrates testing patterns

- ✅ **Infrastructure**
  - Project structure
  - pyproject.toml with dependencies
  - GitHub Actions CI/CD
  - .gitignore
  - Development setup script

## 🚧 What Needs to Be Done

### Immediate (This Week)

1. **Complete Core Facilitator**
   - Port facilitator code from django-x402
   - Remove Django dependencies
   - Make it framework-agnostic
   - Add tests

2. **Complete Core Processor**
   - Implement payment verification
   - Implement settlement logic
   - Integrate with facilitators
   - Add comprehensive tests

3. **Achieve 90%+ Test Coverage**
   - Unit tests for all core functions
   - Edge case testing
   - Error handling tests

### Next (Weeks 2-4)

4. **Django Adapter** (Week 2)
5. **Flask Adapter** (Week 3)
6. **FastAPI Adapter** (Week 4)

See [INTEGRATION.md](INTEGRATION.md) for detailed roadmap.

## 🎓 Understanding the Architecture

### The Big Idea

Instead of building a Django-specific library (like django-x402), we're building:

```
┌──────────────────────────────────────────────────┐
│  Framework-Agnostic Core (One implementation)    │
│  • Configuration                                 │
│  • Payment verification                          │
│  • Settlement logic                              │
│  • Path protection                               │
└──────────────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────┐
│  Thin Framework Adapters (Simple translators)    │
│  • Django adapter                                │
│  • Flask adapter                                 │
│  • FastAPI adapter                               │
│  • ... more ...                                  │
└──────────────────────────────────────────────────┘
```

**Benefits:**
- Write payment logic once, use everywhere
- Easy to test (no framework overhead)
- Easy to add new frameworks
- Better code organization

### Key Abstractions

**RequestContext** - Extracts what we need from any framework:
```python
RequestContext(
    path='/api/premium',
    method='GET',
    headers={'X-Payment': '...'},
    absolute_url='https://example.com/api/premium'
)
```

**BaseAdapter** - Contract for framework integrations:
```python
class DjangoAdapter(BaseAdapter):
    def extract_request_context(self, django_request):
        # Convert Django HttpRequest → RequestContext
        
    def create_payment_required_response(self, error, requirements, is_browser):
        # Return Django HttpResponse with 402
```

**X402PaymentProcessor** - Core logic:
```python
processor = X402PaymentProcessor(config)
result = processor.process_request(context)

if result.action == 'allow':
    # Continue to endpoint
elif result.action == 'deny':
    # Return 402
```

## 🛠️ Development Workflow

### 1. Pick a Task

See [INTEGRATION.md](INTEGRATION.md) for prioritized tasks.

Example: "Complete core facilitator implementation"

### 2. Create a Branch

```bash
git checkout -b feat/complete-core-facilitator
```

### 3. Implement

```bash
# Edit code
vim src/x402_connector/core/facilitators.py

# Run tests continuously
pytest tests/ -v --tb=short

# Check code quality
black src/ tests/
ruff check src/ tests/
mypy src/
```

### 4. Test

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_core_config.py -v

# Run with coverage
pytest --cov=x402_connector --cov-report=html
open htmlcov/index.html
```

### 5. Commit & Push

```bash
git add .
git commit -m "feat: complete core facilitator implementation"
git push origin feat/complete-core-facilitator
```

### 6. Create PR

Open Pull Request on GitHub with:
- Clear description
- What was changed
- How to test
- Link to issue

## 🧪 Testing Guidelines

### Test Organization

```
tests/
├── test_core_config.py      # Configuration tests
├── test_core_context.py     # Context tests
├── test_core_processor.py   # Processor tests (to be added)
└── test_core_facilitators.py # Facilitator tests (to be added)
```

### Writing Good Tests

```python
def test_descriptive_name_of_what_is_tested():
    """Test that X does Y when Z."""
    # Arrange
    config = X402Config(...)
    
    # Act
    result = do_something(config)
    
    # Assert
    assert result == expected
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_core_config.py

# Specific test
pytest tests/test_core_config.py::test_minimal_config

# With coverage
pytest --cov=x402_connector --cov-report=term-missing

# Watch mode (requires pytest-watch)
ptw
```

## 📚 Key Concepts

### Configuration

Load config from multiple sources:

```python
# From dict
config = X402Config.from_dict({
    'network': 'base',
    'price': '$0.01',
    'pay_to_address': '0x...'
})

# From environment
config = X402Config.from_env()

# Direct
config = X402Config(
    network='base',
    price='$0.01',
    pay_to_address='0x...'
)
```

### Request Processing Flow

```
1. Request arrives → Framework adapter
2. Extract RequestContext
3. Pass to core processor
4. Check if path protected
5. Verify payment if present
6. Return allow/deny
7. If allow, call endpoint
8. If 2xx, settle payment
9. Add payment response header
10. Return to client
```

### Facilitator Modes

- **local**: Self-hosted, verify and settle locally
- **remote**: Use external facilitator service
- **hybrid**: Verify locally, settle via service

## 🤔 Common Questions

**Q: Where do I start?**
A: Read OVERVIEW.md, then INTEGRATION.md. Start with completing the core facilitator.

**Q: Can I run the code now?**
A: The skeleton is there, but payment processing is not yet implemented. Tests run but some will fail/skip.

**Q: How does this compare to django-x402?**
A: We're taking the best parts (facilitator logic) and making it framework-agnostic with better architecture.

**Q: What if I want to add support for Framework X?**
A: Create an adapter that implements BaseAdapter. See CONTRIBUTING.md for details.

**Q: Where can I ask questions?**
A: Open a GitHub Discussion or Issue.

## 🎯 Next Actions

**If you want to understand the project:**
1. Read OVERVIEW.md
2. Read ARCHITECTURE.md
3. Explore the code in `src/x402_connector/core/`

**If you want to start coding:**
1. Read INTEGRATION.md
2. Pick a task from Phase 1
3. Read CONTRIBUTING.md
4. Start implementing and testing

**If you want to contribute:**
1. Fork the repository
2. Read CONTRIBUTING.md
3. Pick an issue or task
4. Submit a PR

## 📞 Getting Help

- **General questions**: GitHub Discussions
- **Bug reports**: GitHub Issues
- **Feature requests**: GitHub Issues
- **Security issues**: Email security@example.com

## 🎉 Welcome!

You now have everything you need to start building x402-connector. The architecture is sound, the skeleton is in place, and the roadmap is clear.

**Let's build something awesome!** 🚀

---

**Quick Links:**
- [Project Summary](PROJECT_SUMMARY.md)
- [Architecture](ARCHITECTURE.md)
- [Technical Spec](TECHNICAL.md)
- [Implementation Plan](INTEGRATION.md)
- [Contributing](CONTRIBUTING.md)

