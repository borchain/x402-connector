# Installation Guide

## Quick Start

### For Development (Recommended)

Install the package in editable mode from the project root:

```bash
cd /Users/borker/coin_projects/x402-connector
source venv/bin/activate  # or create: python3 -m venv venv
pip install -e .
```

This allows you to make changes to the code and see them immediately without reinstalling.

### For Production

Install from PyPI (when published):

```bash
pip install x402-connector
```

## Installing with Framework Support

The package has optional dependencies for different frameworks. Choose the ones you need:

### Django

```bash
pip install -e ".[django]"
# or from PyPI:
# pip install "x402-connector[django]"
```

### Flask

```bash
pip install -e ".[flask]"
# or from PyPI:
# pip install "x402-connector[flask]"
```

### FastAPI

```bash
pip install -e ".[fastapi]"
# or from PyPI:
# pip install "x402-connector[fastapi]"
```

### Tornado

```bash
pip install -e ".[tornado]"
# or from PyPI:
# pip install "x402-connector[tornado]"
```

### Pyramid

```bash
pip install -e ".[pyramid]"
# or from PyPI:
# pip install "x402-connector[pyramid]"
```

### All Frameworks

```bash
pip install -e ".[all]"
# or from PyPI:
# pip install "x402-connector[all]"
```

### Solana Support (Blockchain)

```bash
pip install -e ".[solana]"
# or from PyPI:
# pip install "x402-connector[solana]"
```

### Development Tools

```bash
pip install -e ".[dev]"
# or from PyPI:
# pip install "x402-connector[dev]"
```

### Running Tests

```bash
pip install -e ".[tests]"
# or from PyPI:
# pip install "x402-connector[tests]"
```

## Zsh Users (macOS)

If you're using **zsh** (default on macOS), you need to **escape or quote** the square brackets:

### Option 1: Escape brackets
```bash
pip install -e .\[tornado\]
```

### Option 2: Quote the entire argument (Recommended)
```bash
pip install -e ".[tornado]"
```

### Option 3: Use single quotes
```bash
pip install -e '.[tornado]'
```

## Running Examples

After installation, you can run any example:

### Django Example
```bash
cd examples/django
cp env.example .env
# Edit .env with your configuration
python manage.py runserver
```

### Flask Example
```bash
cd examples/flask
cp env.example .env
# Edit .env with your configuration
python app.py
```

### FastAPI Example
```bash
cd examples/fastapi
cp env.example .env
# Edit .env with your configuration
uvicorn app:app --reload
```

### Tornado Example
```bash
cd examples/tornado
cp env.example .env
# Edit .env with your configuration
python app.py
```

### Pyramid Example
```bash
cd examples/pyramid
cp env.example .env
# Edit .env with your configuration
python app.py
```

## Verifying Installation

Test that x402-connector is properly installed:

```bash
python -c "import x402_connector; print(x402_connector.__version__)"
```

Test framework-specific imports:

```bash
# Django
python -c "from x402_connector.django import require_payment; print('Django OK')"

# Flask
python -c "from x402_connector.flask import require_payment; print('Flask OK')"

# FastAPI
python -c "from x402_connector.fastapi import require_payment; print('FastAPI OK')"

# Tornado
python -c "from x402_connector.tornado import require_payment; print('Tornado OK')"

# Pyramid
python -c "from x402_connector.pyramid import require_payment; print('Pyramid OK')"
```

## Troubleshooting

### ModuleNotFoundError: No module named 'x402_connector'

**Solution:** Install the package in editable mode:
```bash
cd /path/to/x402-connector
pip install -e .
```

### ModuleNotFoundError: No module named 'tornado' (or 'pyramid', etc.)

**Solution:** Install the framework-specific extras:
```bash
pip install -e ".[tornado]"  # for Tornado
pip install -e ".[pyramid]"  # for Pyramid
```

### zsh: no matches found: x402-connector[tornado]

**Solution:** Quote the argument in zsh:
```bash
pip install -e ".[tornado]"
# or escape:
pip install -e .\[tornado\]
```

### Import Error in Examples

**Solution:** Make sure you're in the virtual environment where x402-connector is installed:
```bash
source /path/to/venv/bin/activate
pip list | grep x402-connector
```

## Development Setup

For development with all tools:

```bash
cd x402-connector

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with all dev dependencies
pip install -e ".[dev,tests,all,solana]"

# Run tests
pytest

# Run with coverage
pytest --cov=x402_connector --cov-report=html

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Next Steps

- Read the [README.md](README.md) for usage examples
- Check out [QUICKSTART.md](QUICKSTART.md) for a quick tutorial
- See [API.md](API.md) for complete API documentation
- Browse [examples/](examples/) for framework-specific examples

