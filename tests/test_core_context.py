"""Tests for core context classes."""

import pytest
from x402_connector.core.context import (
    RequestContext,
    ProcessingResult,
    SettlementResult,
)


class TestRequestContext:
    """Tests for RequestContext."""
    
    def test_basic_creation(self):
        """Test creating a basic request context."""
        ctx = RequestContext(
            path='/api/test',
            method='GET',
            headers={'X-Payment': 'encoded_payment'},
            absolute_url='https://example.com/api/test'
        )
        
        assert ctx.path == '/api/test'
        assert ctx.method == 'GET'
        assert ctx.headers == {'X-Payment': 'encoded_payment'}
        assert ctx.absolute_url == 'https://example.com/api/test'
        assert ctx.payment_header is None
    
    def test_with_payment_header(self):
        """Test creating context with payment header."""
        ctx = RequestContext(
            path='/api/premium',
            method='POST',
            headers={},
            absolute_url='https://example.com/api/premium',
            payment_header='base64_encoded_payment'
        )
        
        assert ctx.payment_header == 'base64_encoded_payment'
    
    def test_from_dict(self):
        """Test creating context from dictionary."""
        ctx = RequestContext.from_dict({
            'path': '/api/test',
            'method': 'GET',
            'headers': {'User-Agent': 'test'},
            'absolute_url': 'https://example.com/api/test',
            'payment_header': 'payment123'
        })
        
        assert ctx.path == '/api/test'
        assert ctx.method == 'GET'
        assert ctx.headers == {'User-Agent': 'test'}
        assert ctx.payment_header == 'payment123'
    
    def test_from_dict_without_optional_fields(self):
        """Test creating context from dict without optional fields."""
        ctx = RequestContext.from_dict({
            'path': '/api/test',
            'method': 'GET',
            'absolute_url': 'https://example.com/api/test'
        })
        
        assert ctx.headers == {}
        assert ctx.payment_header is None


class TestProcessingResult:
    """Tests for ProcessingResult."""
    
    def test_allow_result(self):
        """Test creating an allow result."""
        result = ProcessingResult(action='allow')
        
        assert result.action == 'allow'
        assert result.payment_verified is False
        assert result.requirements is None
        assert result.error is None
        assert result.payer_address is None
    
    def test_deny_result_with_requirements(self):
        """Test creating a deny result with requirements."""
        requirements = [{'network': 'base', 'price': '$0.01'}]
        
        result = ProcessingResult(
            action='deny',
            requirements=requirements,
            error='No payment provided'
        )
        
        assert result.action == 'deny'
        assert result.requirements == requirements
        assert result.error == 'No payment provided'
    
    def test_allow_with_verified_payment(self):
        """Test allow result with verified payment."""
        result = ProcessingResult(
            action='allow',
            payment_verified=True,
            payer_address='TestSolanaAddress1234567890123456789012'
        )
        
        assert result.action == 'allow'
        assert result.payment_verified is True
        assert result.payer_address == 'TestSolanaAddress1234567890123456789012'
    
    def test_invalid_action_raises_error(self):
        """Test that invalid action raises ValueError."""
        with pytest.raises(ValueError, match='action must be'):
            ProcessingResult(action='invalid')


class TestSettlementResult:
    """Tests for SettlementResult."""
    
    def test_successful_settlement(self):
        """Test creating a successful settlement result."""
        result = SettlementResult(
            success=True,
            transaction_hash='0xabc123',
            encoded_response='base64_encoded_response'
        )
        
        assert result.success is True
        assert result.transaction_hash == '0xabc123'
        assert result.encoded_response == 'base64_encoded_response'
        assert result.error is None
        assert result.receipt is None
    
    def test_failed_settlement(self):
        """Test creating a failed settlement result."""
        result = SettlementResult(
            success=False,
            error='Insufficient gas'
        )
        
        assert result.success is False
        assert result.error == 'Insufficient gas'
        assert result.transaction_hash is None
        assert result.encoded_response is None
    
    def test_settlement_with_receipt(self):
        """Test settlement result with transaction receipt."""
        receipt = {
            'blockNumber': 12345,
            'gasUsed': 21000,
            'status': 1
        }
        
        result = SettlementResult(
            success=True,
            transaction_hash='0xdef456',
            encoded_response='encoded',
            receipt=receipt
        )
        
        assert result.receipt == receipt
        assert result.receipt['blockNumber'] == 12345

