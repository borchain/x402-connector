"""Tests for Flask middleware/extension."""

import pytest
from flask import Flask

from x402_connector.flask import X402


@pytest.fixture
def app():
    """Create Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def configured_app(app):
    """Create Flask app with x402 configuration."""
    # Use a valid Solana address format (base58, 32-44 chars)
    app.config['X402_CONFIG'] = {
        'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'price': '$0.01',
        'network': 'solana-devnet',
        'debug_mode': True,
    }
    return app


def test_x402_initialization(configured_app):
    """Test X402 extension initialization."""
    x402 = X402(configured_app)
    
    assert x402.enabled is True
    assert x402.processor is not None
    assert x402.config.pay_to_address == 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK'


def test_x402_initialization_without_config(app):
    """Test X402 extension without configuration."""
    x402 = X402(app)
    
    assert x402.enabled is False
    assert x402.processor is None


def test_x402_init_app_pattern(app):
    """Test X402 extension with factory pattern."""
    app.config['X402_CONFIG'] = {
        'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'price': '$0.01',
        'network': 'solana-devnet',
        'debug_mode': True,
    }
    
    x402 = X402()
    x402.init_app(app)
    
    assert x402.enabled is True
    assert x402.processor is not None


def test_x402_init_app_with_kwargs(app):
    """Test X402 extension with kwargs."""
    x402 = X402()
    x402.init_app(
        app,
        pay_to_address='DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        price='$0.05',
        network='solana-devnet',
        debug_mode=True
    )
    
    assert x402.enabled is True
    assert x402.config.pay_to_address == 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK'
    assert x402.config.price == '$0.05'


def test_x402_stored_in_extensions(configured_app):
    """Test X402 extension is stored in app.extensions."""
    x402 = X402(configured_app)
    
    assert hasattr(configured_app, 'extensions')
    assert 'x402' in configured_app.extensions
    assert configured_app.extensions['x402'] is x402


def test_free_endpoint_no_payment_required():
    """Test that free endpoints work without payment."""
    # Create a fresh app instance to avoid hook conflicts
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['X402_CONFIG'] = {
        'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'price': '$0.01',
        'network': 'solana-devnet',
        'debug_mode': True,
        'protected_paths': [],  # Empty - no paths protected
    }
    
    x402 = X402(app)
    
    @app.route('/free')
    def free_endpoint():
        return {'data': 'free'}
    
    client = app.test_client()
    response = client.get('/free')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['data'] == 'free'


def test_protected_endpoint_decorator(configured_app):
    """Test protected endpoint with @require_payment decorator."""
    from x402_connector.flask import require_payment
    
    x402 = X402(configured_app)
    
    @configured_app.route('/premium')
    @require_payment(price='$0.01')
    def premium_endpoint():
        return {'data': 'premium'}
    
    client = configured_app.test_client()
    
    # Request without payment should return 402
    response = client.get('/premium')
    assert response.status_code == 402
    
    data = response.get_json()
    assert 'x402Version' in data
    assert 'accepts' in data


def test_protected_endpoint_with_invalid_payment(configured_app):
    """Test protected endpoint with invalid payment."""
    from x402_connector.flask import require_payment
    
    x402 = X402(configured_app)
    
    @configured_app.route('/premium')
    @require_payment(price='$0.01')
    def premium_endpoint():
        return {'data': 'premium'}
    
    client = configured_app.test_client()
    
    # Request with invalid payment
    response = client.get(
        '/premium',
        headers={'X-Payment': '{"invalid": "payment"}'}
    )
    
    assert response.status_code == 402


def test_decorator_without_extension(app):
    """Test decorator returns error when extension not configured."""
    from x402_connector.flask import require_payment
    
    @app.route('/premium')
    @require_payment(price='$0.01')
    def premium_endpoint():
        return {'data': 'premium'}
    
    client = app.test_client()
    response = client.get('/premium')
    
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data
    assert 'not configured' in data['error']


def test_custom_price_in_decorator():
    """Test decorator with custom price."""
    from x402_connector.flask import require_payment
    
    # Create fresh app
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['X402_CONFIG'] = {
        'pay_to_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK',
        'price': '$0.01',  # Default price
        'network': 'solana-devnet',
        'debug_mode': True,
        'protected_paths': [],  # Don't let middleware interfere with decorator
    }
    
    x402 = X402(app)
    
    @app.route('/expensive')
    @require_payment(price='$1.00')  # Custom price
    def expensive_endpoint():
        return {'data': 'expensive'}
    
    client = app.test_client()
    response = client.get('/expensive')
    
    assert response.status_code == 402
    data = response.get_json()
    
    # Check that requirements reflect custom price
    assert 'accepts' in data
    # Price conversion: $1.00 = 1000000 atomic units (USDC has 6 decimals)
    assert data['accepts'][0]['maxAmountRequired'] == '1000000'


def test_custom_description_in_decorator(configured_app):
    """Test decorator with custom description."""
    from x402_connector.flask import require_payment
    
    x402 = X402(configured_app)
    
    @configured_app.route('/ai')
    @require_payment(price='$0.10', description='AI Inference')
    def ai_endpoint():
        return {'result': 'AI output'}
    
    client = configured_app.test_client()
    response = client.get('/ai')
    
    assert response.status_code == 402

