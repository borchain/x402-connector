# Contributing to x402-connector

Thank you for your interest in contributing to x402-connector! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and professional. We're all here to build great software together.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/x402-connector/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version, framework version, OS
   - Minimal code example if possible

### Suggesting Features

1. Check if the feature has been requested in [Issues](https://github.com/yourusername/x402-connector/issues)
2. Create a new issue with:
   - Clear use case
   - Why this would be valuable
   - Proposed API/interface (if applicable)
   - Are you willing to implement it?

### Contributing Code

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/x402-connector.git
cd x402-connector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all extras
pip install -e ".[dev,tests,all]"

# Run tests to verify setup
pytest
```

#### Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code
   - Add tests
   - Update documentation
   - Follow code style guidelines

3. **Run quality checks**:
   ```bash
   # Format code
   black src/ tests/
   
   # Lint
   ruff check src/ tests/
   
   # Type check
   mypy src/
   
   # Run tests
   pytest -v --cov
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation only
   - `style:` - Formatting, missing semicolons, etc.
   - `refactor:` - Code change that neither fixes a bug nor adds a feature
   - `test:` - Adding missing tests
   - `chore:` - Updating build tasks, package manager configs, etc.

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

#### Pull Request Guidelines

- **One PR per feature/fix** - Keep PRs focused
- **Write clear descriptions** - Explain what and why
- **Add tests** - All new code should have tests
- **Update docs** - If you change APIs, update documentation
- **Pass CI checks** - All tests and linting must pass
- **Respond to feedback** - Be open to suggestions

## Code Style

### Python Style

- **Follow PEP 8** with 100 character line length
- **Use type hints** for all public APIs
- **Write docstrings** for all public functions/classes
- **Use black** for formatting
- **Use ruff** for linting

### Documentation Style

- **Clear and concise** - Get to the point
- **Examples** - Show, don't just tell
- **Complete** - Cover all parameters and return values
- **Accurate** - Keep docs in sync with code

Example:
```python
def process_payment(context: RequestContext) -> ProcessingResult:
    """Process payment for incoming request.
    
    Verifies payment signature, checks requirements, and determines
    whether to allow or deny the request.
    
    Args:
        context: Request context with path, headers, and payment info
        
    Returns:
        ProcessingResult with allow/deny decision and optional error
        
    Example:
        >>> result = processor.process_payment(context)
        >>> if result.action == 'allow':
        ...     print("Payment verified!")
    """
    pass
```

## Testing

### Test Organization

```
tests/
├── core/              # Core logic tests (no framework deps)
├── django/            # Django adapter tests
├── flask/             # Flask adapter tests
├── fastapi/           # FastAPI adapter tests
└── integration/       # End-to-end tests
```

### Writing Tests

- **Unit tests** - Test one thing at a time
- **Integration tests** - Test components working together
- **Use fixtures** - Share common test setup
- **Mock external deps** - Don't hit real APIs/blockchains in tests
- **Clear names** - Test names should describe what they test

Example:
```python
def test_config_validation_requires_network():
    """Test that X402Config raises error when network is missing."""
    with pytest.raises(ValueError, match='network is required'):
        X402Config(network='', price='$0.01', pay_to_address='0x123')
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_core_config.py

# Run specific test
pytest tests/test_core_config.py::test_minimal_config

# Run with coverage
pytest --cov=x402_connector --cov-report=html

# Run only fast tests (exclude integration)
pytest -m "not integration"
```

## Adding a New Framework Adapter

Want to add support for a new framework? Great! Here's the process:

1. **Check roadmap** - Make sure it's not already in progress
2. **Create issue** - Discuss the approach first
3. **Implement adapter**:
   ```
   src/x402_connector/
   └── your_framework/
       ├── __init__.py
       ├── adapter.py         # YourFrameworkAdapter(BaseAdapter)
       ├── middleware.py      # Framework integration
       └── decorators.py      # Optional decorator pattern
   ```

4. **Add tests**:
   ```
   tests/
   └── your_framework/
       ├── __init__.py
       ├── test_adapter.py
       └── test_middleware.py
   ```

5. **Create example**:
   ```
   examples/
   └── your_framework_example/
       ├── README.md
       ├── requirements.txt
       └── app.py
   ```

6. **Update docs**:
   - Add to README.md supported frameworks table
   - Create quickstart guide
   - Add to TECHNICAL.md

See [ARCHITECTURE.md](ARCHITECTURE.md) for design patterns.

## Project Structure

```
x402-connector/
├── src/x402_connector/     # Source code
│   ├── core/               # Framework-agnostic core
│   ├── django/             # Django adapter
│   ├── flask/              # Flask adapter
│   └── fastapi/            # FastAPI adapter
├── tests/                  # Test suite
├── examples/               # Working examples
├── docs/                   # Documentation
├── .github/workflows/      # CI/CD
└── pyproject.toml         # Package config
```

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will:
   - Run tests
   - Build package
   - Publish to PyPI
   - Create GitHub release

## Questions?

- **General questions** - Open a [Discussion](https://github.com/yourusername/x402-connector/discussions)
- **Bug reports** - Open an [Issue](https://github.com/yourusername/x402-connector/issues)
- **Security issues** - Email security@example.com (do not open public issue)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to x402-connector! 🎉

