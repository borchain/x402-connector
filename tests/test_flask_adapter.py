"""Tests for Flask adapter."""

import pytest
from flask import Flask, Request
from werkzeug.test import EnvironBuilder

from x402_connector.flask.adapter import FlaskAdapter
from x402_connector.core.context import RequestContext


@pytest.fixture
def adapter():
    """Create FlaskAdapter instance."""
    return FlaskAdapter()


@pytest.fixture
def flask_app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_extract_request_context(adapter, flask_app):
    """Test extracting request context from Flask Request."""
    with flask_app.test_request_context(
        '/api/test',
        method='POST',
        headers={'X-Payment': 'test_payment', 'User-Agent': 'test'}
    ):
        from flask import request
        context = adapter.extract_request_context(request)
        
        assert isinstance(context, RequestContext)
        assert context.path == '/api/test'
        assert context.method == 'POST'
        assert context.payment_header == 'test_payment'
        assert 'User-Agent' in context.headers
        assert context.headers['User-Agent'] == 'test'


def test_extract_request_context_no_payment(adapter, flask_app):
    """Test extracting context without payment header."""
    with flask_app.test_request_context('/api/test'):
        from flask import request
        context = adapter.extract_request_context(request)
        
        assert context.payment_header is None


def test_create_payment_required_response_json(adapter, flask_app):
    """Test creating JSON 402 response."""
    requirements = [
        {
            'network': 'solana-devnet',
            'asset': 'USDC',
            'maxAmountRequired': '10000'
        }
    ]
    
    with flask_app.app_context():
        response = adapter.create_payment_required_response(
            error='Payment required',
            requirements=requirements,
            is_browser=False
        )
        
        assert response.status_code == 402
        assert response.is_json
        
        data = response.get_json()
        assert data['x402Version'] == 1
        assert data['error'] == 'Payment required'
        assert len(data['accepts']) == 1
        assert data['accepts'][0]['network'] == 'solana-devnet'


def test_create_payment_required_response_html(adapter, flask_app):
    """Test creating HTML 402 response for browsers."""
    requirements = [
        {
            'network': 'solana-devnet',
            'asset': 'USDC',
            'maxAmountRequired': '10000'
        }
    ]
    
    with flask_app.app_context():
        response = adapter.create_payment_required_response(
            error='Payment required',
            requirements=requirements,
            is_browser=True
        )
        
        assert response.status_code == 402
        assert response.mimetype == 'text/html'
        assert b'402' in response.data
        assert b'Payment Required' in response.data
        assert b'Payment required' in response.data


def test_add_payment_response_header(adapter, flask_app):
    """Test adding X-PAYMENT-RESPONSE header."""
    with flask_app.test_request_context():
        from flask import make_response
        response = make_response('test content')
        
        modified = adapter.add_payment_response_header(
            response,
            'test_settlement_data'
        )
        
        assert 'X-PAYMENT-RESPONSE' in modified.headers
        assert modified.headers['X-PAYMENT-RESPONSE'] == 'test_settlement_data'


def test_is_success_response(adapter, flask_app):
    """Test checking if response is successful."""
    with flask_app.test_request_context():
        from flask import make_response
        
        # Test 200 OK
        response_200 = make_response('ok')
        response_200.status_code = 200
        assert adapter.is_success_response(response_200) is True
        
        # Test 201 Created
        response_201 = make_response('created')
        response_201.status_code = 201
        assert adapter.is_success_response(response_201) is True
        
        # Test 404 Not Found
        response_404 = make_response('not found')
        response_404.status_code = 404
        assert adapter.is_success_response(response_404) is False
        
        # Test 500 Internal Server Error
        response_500 = make_response('error')
        response_500.status_code = 500
        assert adapter.is_success_response(response_500) is False


def test_absolute_url_extraction(adapter, flask_app):
    """Test that absolute URL is properly extracted."""
    with flask_app.test_request_context(
        'http://example.com/api/test?param=value',
        method='GET'
    ):
        from flask import request
        context = adapter.extract_request_context(request)
        
        assert 'example.com' in context.absolute_url
        assert '/api/test' in context.absolute_url

