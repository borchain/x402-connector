"""Framework-agnostic context and result types for x402 payment processing."""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any


@dataclass
class RequestContext:
    """Framework-agnostic representation of an HTTP request.
    
    This abstraction allows the core payment processor to work with any
    web framework without depending on framework-specific request objects.
    
    Attributes:
        path: Request path (e.g., '/api/premium/data')
        method: HTTP method (e.g., 'GET', 'POST')
        headers: Request headers as dict
        absolute_url: Full URL including scheme and host
        payment_header: Optional X-PAYMENT header value (base64-encoded)
    """
    
    path: str
    method: str
    headers: Dict[str, str]
    absolute_url: str
    payment_header: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RequestContext':
        """Create RequestContext from dictionary.
        
        Useful for testing and serialization.
        
        Args:
            data: Dictionary with request data
            
        Returns:
            RequestContext instance
            
        Example:
            >>> ctx = RequestContext.from_dict({
            ...     'path': '/api/test',
            ...     'method': 'GET',
            ...     'headers': {},
            ...     'absolute_url': 'https://example.com/api/test'
            ... })
        """
        return cls(
            path=data['path'],
            method=data['method'],
            headers=data.get('headers', {}),
            absolute_url=data['absolute_url'],
            payment_header=data.get('payment_header')
        )


@dataclass
class ProcessingResult:
    """Result of payment verification and processing.
    
    Attributes:
        action: 'allow' or 'deny' - whether to allow request to proceed
        payment_verified: Whether payment was present and valid
        requirements: Payment requirements to send in 402 response (if denying)
        error: Error message if payment was invalid
        payer_address: Ethereum address of the payer (if payment verified)
    """
    
    action: str  # 'allow' or 'deny'
    payment_verified: bool = False
    requirements: Optional[List[Any]] = None
    error: Optional[str] = None
    payer_address: Optional[str] = None
    
    def __post_init__(self):
        """Validate action value."""
        if self.action not in ('allow', 'deny'):
            raise ValueError(f"action must be 'allow' or 'deny', got {self.action}")


@dataclass
class SettlementResult:
    """Result of payment settlement on blockchain.
    
    Attributes:
        success: Whether settlement was successful
        transaction_hash: Blockchain transaction hash (if successful)
        encoded_response: Base64-encoded settlement response for X-PAYMENT-RESPONSE header
        error: Error message if settlement failed
        receipt: Transaction receipt from blockchain (if available)
    """
    
    success: bool
    transaction_hash: Optional[str] = None
    encoded_response: Optional[str] = None
    error: Optional[str] = None
    receipt: Optional[Dict[str, Any]] = None

