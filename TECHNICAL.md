# Technical Specification

## Project Structure

```
x402-connector/
├── src/
│   └── x402_connector/
│       ├── __init__.py                 # Public API exports
│       ├── core/                       # Framework-agnostic core
│       │   ├── __init__.py
│       │   ├── processor.py            # X402PaymentProcessor
│       │   ├── config.py               # Configuration management
│       │   ├── context.py              # RequestContext, ProcessingResult
│       │   ├── adapters.py             # BaseAdapter interface
│       │   ├── facilitators.py         # Facilitator implementations
│       │   └── utils.py                # Helpers (path matching, encoding)
│       ├── django/                     # Django integration
│       │   ├── __init__.py
│       │   ├── adapter.py              # DjangoAdapter
│       │   ├── middleware.py           # Django middleware
│       │   ├── views.py                # Facilitator endpoints
│       │   └── urls.py                 # URL patterns
│       ├── flask/                      # Flask integration
│       │   ├── __init__.py
│       │   ├── adapter.py              # FlaskAdapter
│       │   ├── extension.py            # X402Flask extension
│       │   └── decorators.py           # @require_payment
│       ├── fastapi/                    # FastAPI integration
│       │   ├── __init__.py
│       │   ├── adapter.py              # FastAPIAdapter
│       │   ├── middleware.py           # Starlette middleware
│       │   └── dependencies.py         # Dependency injection
│       └── types/                      # Shared types
│           ├── __init__.py
│           └── models.py               # PaymentRequirements, etc.
├── tests/
│   ├── core/                           # Core logic tests
│   ├── django/                         # Django adapter tests
│   ├── flask/                          # Flask adapter tests
│   ├── fastapi/                        # FastAPI adapter tests
│   └── integration/                    # End-to-end tests
├── examples/
│   ├── django_example/
│   ├── flask_example/
│   └── fastapi_example/
├── docs/
│   ├── getting-started.md
│   ├── configuration.md
│   └── api-reference.md
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md
├── TECHNICAL.md
└── LICENSE
```

## Core Components Implementation

### 1. RequestContext

**File**: `src/x402_connector/core/context.py`

```python
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any

@dataclass
class RequestContext:
    """Framework-agnostic request context."""
    
    path: str
    method: str
    headers: Dict[str, str]
    absolute_url: str
    payment_header: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RequestContext':
        """Create from dictionary (useful for testing)."""
        return cls(
            path=data['path'],
            method=data['method'],
            headers=data.get('headers', {}),
            absolute_url=data['absolute_url'],
            payment_header=data.get('payment_header')
        )


@dataclass
class ProcessingResult:
    """Result of payment processing."""
    
    action: str  # 'allow' or 'deny'
    payment_verified: bool = False
    requirements: Optional[List[Any]] = None
    error: Optional[str] = None
    payer_address: Optional[str] = None


@dataclass
class SettlementResult:
    """Result of payment settlement."""
    
    success: bool
    transaction_hash: Optional[str] = None
    encoded_response: Optional[str] = None
    error: Optional[str] = None
    receipt: Optional[Dict[str, Any]] = None
```

### 2. Configuration System

**File**: `src/x402_connector/core/config.py`

```python
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class LocalFacilitatorConfig:
    """Configuration for local facilitator."""
    
    private_key_env: str = 'X402_SIGNER_KEY'
    rpc_url_env: str = 'X402_RPC_URL'
    verify_balance: bool = False
    simulate_before_send: bool = True
    wait_for_receipt: bool = False


@dataclass
class RemoteFacilitatorConfig:
    """Configuration for remote facilitator."""
    
    url: str
    headers: Optional[Dict[str, str]] = None
    timeout: int = 20


@dataclass
class X402Config:
    """Main x402 configuration."""
    
    # Required
    network: str
    price: str
    pay_to_address: str
    
    # Optional with defaults
    protected_paths: List[str] = field(default_factory=lambda: ['*'])
    facilitator_mode: str = 'local'
    description: str = ''
    mime_type: str = 'application/json'
    max_timeout_seconds: int = 60
    discoverable: bool = True
    
    # Facilitator configs
    local: Optional[LocalFacilitatorConfig] = None
    remote: Optional[RemoteFacilitatorConfig] = None
    
    # Advanced options
    settle_policy: str = 'block-on-failure'  # or 'log-and-continue'
    replay_cache_enabled: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
        self._set_defaults()
    
    def _validate(self):
        """Validate required fields."""
        if not self.network:
            raise ValueError("network is required")
        if not self.price:
            raise ValueError("price is required")
        if not self.pay_to_address:
            raise ValueError("pay_to_address is required")
        
        if self.facilitator_mode not in ('local', 'remote', 'hybrid'):
            raise ValueError(
                f"facilitator_mode must be 'local', 'remote', or 'hybrid', "
                f"got {self.facilitator_mode}"
            )
    
    def _set_defaults(self):
        """Set default facilitator configs if not provided."""
        if self.facilitator_mode == 'local' and self.local is None:
            self.local = LocalFacilitatorConfig()
        
        if self.facilitator_mode == 'remote' and self.remote is None:
            raise ValueError("remote facilitator config required when mode='remote'")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'X402Config':
        """Create configuration from dictionary."""
        # Extract nested configs
        local_config = config_dict.pop('local', None)
        remote_config = config_dict.pop('remote', None)
        
        # Create facilitator configs
        local = LocalFacilitatorConfig(**local_config) if local_config else None
        remote = RemoteFacilitatorConfig(**remote_config) if remote_config else None
        
        return cls(
            local=local,
            remote=remote,
            **config_dict
        )
    
    @classmethod
    def from_env(cls, prefix: str = 'X402_') -> 'X402Config':
        """Load configuration from environment variables."""
        network = os.getenv(f'{prefix}NETWORK')
        price = os.getenv(f'{prefix}PRICE')
        pay_to = os.getenv(f'{prefix}PAY_TO_ADDRESS')
        
        if not all([network, price, pay_to]):
            raise ValueError(
                f"Missing required env vars: {prefix}NETWORK, "
                f"{prefix}PRICE, {prefix}PAY_TO_ADDRESS"
            )
        
        return cls(
            network=network,
            price=price,
            pay_to_address=pay_to,
            protected_paths=os.getenv(f'{prefix}PROTECTED_PATHS', '*').split(','),
            facilitator_mode=os.getenv(f'{prefix}FACILITATOR_MODE', 'local'),
            description=os.getenv(f'{prefix}DESCRIPTION', ''),
        )
```

### 3. Base Adapter Interface

**File**: `src/x402_connector/core/adapters.py`

```python
from abc import ABC, abstractmethod
from typing import Any, List

from .context import RequestContext
from ..types.models import PaymentRequirements


class BaseAdapter(ABC):
    """Base adapter interface for framework integrations."""
    
    @abstractmethod
    def extract_request_context(self, request: Any) -> RequestContext:
        """
        Extract framework-agnostic request context from framework request.
        
        Args:
            request: Framework-specific request object
            
        Returns:
            RequestContext with path, method, headers, etc.
        """
        pass
    
    @abstractmethod
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[PaymentRequirements],
        is_browser: bool
    ) -> Any:
        """
        Create HTTP 402 response in framework-specific format.
        
        Args:
            error: Error message to display
            requirements: List of payment requirements
            is_browser: Whether request is from a browser
            
        Returns:
            Framework-specific response object with status 402
        """
        pass
    
    @abstractmethod
    def add_payment_response_header(self, response: Any, header_value: str) -> Any:
        """
        Add X-PAYMENT-RESPONSE header to response.
        
        Args:
            response: Framework-specific response object
            header_value: Base64-encoded payment response
            
        Returns:
            Modified response with header added
        """
        pass
    
    @abstractmethod
    def is_success_response(self, response: Any) -> bool:
        """
        Check if response status is 2xx.
        
        Args:
            response: Framework-specific response object
            
        Returns:
            True if status code is 200-299
        """
        pass
```

### 4. Core Payment Processor

**File**: `src/x402_connector/core/processor.py`

```python
import base64
import json
import logging
from typing import List, Optional

from x402.common import (
    process_price_to_atomic_amount,
    find_matching_payment_requirements,
)
from x402.encoding import safe_base64_decode
from x402.path import path_is_match
from x402.paywall import is_browser_request
from x402.types import PaymentPayload, PaymentRequirements

from .config import X402Config
from .context import RequestContext, ProcessingResult, SettlementResult
from .facilitators import BaseFacilitator, get_facilitator

logger = logging.getLogger(__name__)


class X402PaymentProcessor:
    """Framework-agnostic x402 payment processing engine."""
    
    def __init__(self, config: X402Config, facilitator: Optional[BaseFacilitator] = None):
        """
        Initialize payment processor.
        
        Args:
            config: X402 configuration
            facilitator: Optional custom facilitator (auto-created if None)
        """
        self.config = config
        self.facilitator = facilitator or get_facilitator(config)
        self._payment_cache: dict = {}  # For replay protection
    
    def process_request(self, context: RequestContext) -> ProcessingResult:
        """
        Process incoming request for payment verification.
        
        Args:
            context: Framework-agnostic request context
            
        Returns:
            ProcessingResult indicating allow/deny and requirements
        """
        # Check if path is protected
        if not self._is_protected_path(context.path):
            return ProcessingResult(action='allow')
        
        # Build payment requirements for this resource
        requirements = self._build_payment_requirements(context)
        
        # Check for payment header
        if not context.payment_header:
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='No X-PAYMENT header provided'
            )
        
        # Parse payment payload
        try:
            payment_dict = json.loads(safe_base64_decode(context.payment_header))
            payment = PaymentPayload(**payment_dict)
        except Exception as e:
            logger.warning(f"Failed to parse payment header: {e}")
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='Invalid payment header format'
            )
        
        # Find matching requirements
        selected_requirements = find_matching_payment_requirements(
            requirements, payment
        )
        
        if not selected_requirements:
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error='No matching payment requirements found'
            )
        
        # Verify payment
        verification = self.facilitator.verify(
            payment_dict,
            selected_requirements.model_dump(by_alias=True)
        )
        
        is_valid = verification.get('isValid') or verification.get('is_valid')
        if not is_valid:
            invalid_reason = verification.get('invalidReason') or \
                           verification.get('invalid_reason') or \
                           'Unknown error'
            return ProcessingResult(
                action='deny',
                requirements=requirements,
                error=f'Invalid payment: {invalid_reason}'
            )
        
        return ProcessingResult(
            action='allow',
            payment_verified=True,
            payer_address=verification.get('payer')
        )
    
    def settle_payment(self, context: RequestContext) -> SettlementResult:
        """
        Settle verified payment after successful response.
        
        Args:
            context: Request context with payment header
            
        Returns:
            SettlementResult with transaction details
        """
        # Check cache for idempotency
        if self.config.replay_cache_enabled:
            cached = self._get_cached_settlement(context.payment_header)
            if cached:
                logger.info("Using cached settlement result")
                return cached
        
        try:
            # Parse payment
            payment_dict = json.loads(safe_base64_decode(context.payment_header))
            requirements = self._build_payment_requirements(context)
            
            # Find matching requirements
            payment = PaymentPayload(**payment_dict)
            selected = find_matching_payment_requirements(requirements, payment)
            
            if not selected:
                return SettlementResult(
                    success=False,
                    error='No matching requirements for settlement'
                )
            
            # Settle via facilitator
            settlement = self.facilitator.settle(
                payment_dict,
                selected.model_dump(by_alias=True)
            )
            
            # Check success
            success = settlement.get('success', False)
            if not success:
                error = settlement.get('error', 'Settlement failed')
                logger.error(f"Settlement failed: {error}")
                return SettlementResult(success=False, error=error)
            
            # Encode response
            encoded = base64.b64encode(
                json.dumps(settlement).encode('utf-8')
            ).decode('ascii')
            
            result = SettlementResult(
                success=True,
                transaction_hash=settlement.get('transaction'),
                encoded_response=encoded,
                receipt=settlement.get('receipt')
            )
            
            # Cache result
            if self.config.replay_cache_enabled:
                self._cache_settlement(context.payment_header, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Settlement error: {e}", exc_info=True)
            return SettlementResult(success=False, error=str(e))
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path matches protected patterns."""
        return path_is_match(self.config.protected_paths, path)
    
    def _build_payment_requirements(
        self, 
        context: RequestContext
    ) -> List[PaymentRequirements]:
        """Build payment requirements for this request."""
        max_amount, asset, eip712_domain = process_price_to_atomic_amount(
            self.config.price,
            self.config.network
        )
        
        return [
            PaymentRequirements(
                scheme='exact',
                network=self.config.network,
                asset=asset,
                max_amount_required=max_amount,
                resource=context.absolute_url,
                description=self.config.description,
                mime_type=self.config.mime_type,
                pay_to=self.config.pay_to_address,
                max_timeout_seconds=self.config.max_timeout_seconds,
                output_schema={
                    'input': {
                        'type': 'http',
                        'method': context.method.upper(),
                        'discoverable': self.config.discoverable,
                    },
                    'output': {'type': self.config.mime_type},
                },
                extra=eip712_domain,
            )
        ]
    
    def _get_cached_settlement(self, payment_header: str) -> Optional[SettlementResult]:
        """Get cached settlement result."""
        return self._payment_cache.get(payment_header)
    
    def _cache_settlement(self, payment_header: str, result: SettlementResult):
        """Cache settlement result."""
        self._payment_cache[payment_header] = result
```

### 5. Facilitators

**File**: `src/x402_connector/core/facilitators.py`

This can largely reuse the existing `django_x402/facilitators.py` implementation, but make it framework-agnostic by removing Django-specific imports.

Key changes:
- Remove `from django.conf import settings` - accept config directly
- Remove Django-specific environment variable lookups
- Make it a pure Python module

```python
# Reuse most of the existing facilitator code, but:
# - Accept config dict instead of Django settings
# - Use standard os.environ for env vars
# - Return plain dicts instead of Django responses

def get_facilitator(config: X402Config) -> BaseFacilitator:
    """
    Factory function to create facilitator based on config.
    
    Args:
        config: X402 configuration
        
    Returns:
        Appropriate facilitator instance
    """
    mode = config.facilitator_mode
    
    if mode == 'local':
        return LocalFacilitator(config.local)
    elif mode == 'remote':
        return RemoteFacilitator(
            url=config.remote.url,
            headers=config.remote.headers
        )
    elif mode == 'hybrid':
        local = LocalFacilitator(config.local)
        remote = RemoteFacilitator(
            url=config.remote.url,
            headers=config.remote.headers
        )
        return HybridFacilitator(local, remote)
    else:
        raise ValueError(f"Unknown facilitator mode: {mode}")
```

## Framework Adapter Implementations

### Django Adapter

**File**: `src/x402_connector/django/adapter.py`

```python
from typing import Any, Dict, List
from django.http import HttpRequest, HttpResponse, JsonResponse

from x402.paywall import get_paywall_html
from x402.common import x402_VERSION
from x402.types import PaymentRequirements, x402PaymentRequiredResponse

from ..core.adapters import BaseAdapter
from ..core.context import RequestContext


class DjangoAdapter(BaseAdapter):
    """Django framework adapter."""
    
    def extract_request_context(self, request: HttpRequest) -> RequestContext:
        """Extract request context from Django HttpRequest."""
        return RequestContext(
            path=request.path,
            method=request.method,
            headers=dict(request.headers),
            absolute_url=request.build_absolute_uri(),
            payment_header=request.META.get('HTTP_X_PAYMENT')
        )
    
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[PaymentRequirements],
        is_browser: bool
    ) -> HttpResponse:
        """Create Django HTTP 402 response."""
        if is_browser:
            html_content = get_paywall_html(error, requirements, None)
            return HttpResponse(
                html_content,
                status=402,
                content_type='text/html; charset=utf-8'
            )
        
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=requirements,
            error=error,
        ).model_dump(by_alias=True)
        
        return JsonResponse(response_data, status=402)
    
    def add_payment_response_header(
        self, 
        response: HttpResponse, 
        header_value: str
    ) -> HttpResponse:
        """Add payment response header to Django response."""
        response['X-PAYMENT-RESPONSE'] = header_value
        return response
    
    def is_success_response(self, response: HttpResponse) -> bool:
        """Check if Django response is 2xx."""
        return 200 <= response.status_code < 300
```

**File**: `src/x402_connector/django/middleware.py`

```python
from django.conf import settings
from django.http import HttpRequest, HttpResponse

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import DjangoAdapter
from x402.paywall import is_browser_request


class X402Middleware:
    """Django middleware for x402 payment processing."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Load configuration from Django settings
        config_dict = getattr(settings, 'X402_CONFIG', None) or \
                     getattr(settings, 'X402', {})
        
        self.config = X402Config.from_dict(config_dict)
        self.processor = X402PaymentProcessor(self.config)
        self.adapter = DjangoAdapter()
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request through x402 payment gate."""
        # Extract context
        context = self.adapter.extract_request_context(request)
        
        # Process payment
        result = self.processor.process_request(context)
        
        if result.action == 'deny':
            # Return 402 response
            is_browser = is_browser_request(context.headers)
            return self.adapter.create_payment_required_response(
                error=result.error or 'Payment required',
                requirements=result.requirements or [],
                is_browser=is_browser
            )
        
        # Call view
        response = self.get_response(request)
        
        # Settle payment if verified and successful response
        if result.payment_verified and self.adapter.is_success_response(response):
            settlement = self.processor.settle_payment(context)
            
            if settlement.success:
                response = self.adapter.add_payment_response_header(
                    response,
                    settlement.encoded_response
                )
            elif self.config.settle_policy == 'block-on-failure':
                # Return 402 on settlement failure
                return self.adapter.create_payment_required_response(
                    error='Settlement failed',
                    requirements=result.requirements or [],
                    is_browser=False
                )
        
        return response
```

### Flask Adapter

**File**: `src/x402_connector/flask/adapter.py`

```python
from typing import Any, Dict, List
from flask import Request, Response, jsonify, make_response

from x402.paywall import get_paywall_html
from x402.common import x402_VERSION
from x402.types import PaymentRequirements, x402PaymentRequiredResponse

from ..core.adapters import BaseAdapter
from ..core.context import RequestContext


class FlaskAdapter(BaseAdapter):
    """Flask framework adapter."""
    
    def extract_request_context(self, request: Request) -> RequestContext:
        """Extract request context from Flask Request."""
        return RequestContext(
            path=request.path,
            method=request.method,
            headers=dict(request.headers),
            absolute_url=request.url,
            payment_header=request.headers.get('X-Payment')
        )
    
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[PaymentRequirements],
        is_browser: bool
    ) -> Response:
        """Create Flask HTTP 402 response."""
        if is_browser:
            html_content = get_paywall_html(error, requirements, None)
            return make_response(html_content, 402, {
                'Content-Type': 'text/html; charset=utf-8'
            })
        
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=requirements,
            error=error,
        ).model_dump(by_alias=True)
        
        response = jsonify(response_data)
        response.status_code = 402
        return response
    
    def add_payment_response_header(
        self, 
        response: Response, 
        header_value: str
    ) -> Response:
        """Add payment response header to Flask response."""
        response.headers['X-PAYMENT-RESPONSE'] = header_value
        return response
    
    def is_success_response(self, response: Response) -> bool:
        """Check if Flask response is 2xx."""
        return 200 <= response.status_code < 300
```

**File**: `src/x402_connector/flask/extension.py`

```python
from functools import wraps
from flask import Flask, request, make_response
from typing import Optional, Dict, Any, Callable

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import FlaskAdapter
from x402.paywall import is_browser_request


class X402Flask:
    """Flask extension for x402 payment processing."""
    
    def __init__(self, app: Optional[Flask] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Flask extension.
        
        Args:
            app: Flask application (optional, can use init_app later)
            config: X402 configuration dict
        """
        self.processor = None
        self.adapter = FlaskAdapter()
        
        if app is not None:
            self.init_app(app, config)
    
    def init_app(self, app: Flask, config: Optional[Dict[str, Any]] = None):
        """
        Initialize extension with Flask app.
        
        Args:
            app: Flask application
            config: X402 configuration dict (overrides app.config)
        """
        # Load config from app.config or provided dict
        config_dict = config or app.config.get('X402_CONFIG', {})
        
        if not config_dict:
            raise ValueError("X402 configuration required")
        
        x402_config = X402Config.from_dict(config_dict)
        self.processor = X402PaymentProcessor(x402_config)
        
        # Store on app for access in routes
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['x402'] = self
    
    def require_payment(self, **options) -> Callable:
        """
        Decorator to protect Flask routes with payment requirement.
        
        Usage:
            @app.route('/api/premium')
            @x402.require_payment()
            def premium_view():
                return {'data': 'premium'}
        
        Args:
            **options: Override options for this specific route
            
        Returns:
            Decorator function
        """
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Extract context
                context = self.adapter.extract_request_context(request)
                
                # Process payment
                result = self.processor.process_request(context)
                
                if result.action == 'deny':
                    # Return 402
                    is_browser = is_browser_request(context.headers)
                    return self.adapter.create_payment_required_response(
                        error=result.error or 'Payment required',
                        requirements=result.requirements or [],
                        is_browser=is_browser
                    )
                
                # Call original view
                response = make_response(f(*args, **kwargs))
                
                # Settle payment
                if result.payment_verified and self.adapter.is_success_response(response):
                    settlement = self.processor.settle_payment(context)
                    
                    if settlement.success:
                        response = self.adapter.add_payment_response_header(
                            response,
                            settlement.encoded_response
                        )
                    elif self.processor.config.settle_policy == 'block-on-failure':
                        return self.adapter.create_payment_required_response(
                            error='Settlement failed',
                            requirements=result.requirements or [],
                            is_browser=False
                        )
                
                return response
            
            return wrapped
        return decorator
```

### FastAPI Adapter

**File**: `src/x402_connector/fastapi/adapter.py`

```python
from typing import Any, Dict, List
from fastapi import Request
from starlette.responses import Response, HTMLResponse, JSONResponse

from x402.paywall import get_paywall_html
from x402.common import x402_VERSION
from x402.types import PaymentRequirements, x402PaymentRequiredResponse

from ..core.adapters import BaseAdapter
from ..core.context import RequestContext


class FastAPIAdapter(BaseAdapter):
    """FastAPI/Starlette framework adapter."""
    
    def extract_request_context(self, request: Request) -> RequestContext:
        """Extract request context from FastAPI Request."""
        return RequestContext(
            path=request.url.path,
            method=request.method,
            headers=dict(request.headers),
            absolute_url=str(request.url),
            payment_header=request.headers.get('X-Payment')
        )
    
    def create_payment_required_response(
        self,
        error: str,
        requirements: List[PaymentRequirements],
        is_browser: bool
    ) -> Response:
        """Create FastAPI HTTP 402 response."""
        if is_browser:
            html_content = get_paywall_html(error, requirements, None)
            return HTMLResponse(
                content=html_content,
                status_code=402
            )
        
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=requirements,
            error=error,
        ).model_dump(by_alias=True)
        
        return JSONResponse(
            content=response_data,
            status_code=402
        )
    
    def add_payment_response_header(
        self, 
        response: Response, 
        header_value: str
    ) -> Response:
        """Add payment response header to FastAPI response."""
        response.headers['X-PAYMENT-RESPONSE'] = header_value
        return response
    
    def is_success_response(self, response: Response) -> bool:
        """Check if FastAPI response is 2xx."""
        return 200 <= response.status_code < 300
```

**File**: `src/x402_connector/fastapi/middleware.py`

```python
from typing import Dict, Any
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..core.config import X402Config
from ..core.processor import X402PaymentProcessor
from .adapter import FastAPIAdapter
from x402.paywall import is_browser_request


class X402Middleware(BaseHTTPMiddleware):
    """FastAPI middleware for x402 payment processing."""
    
    def __init__(self, app: FastAPI, config: Dict[str, Any]):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            config: X402 configuration dict
        """
        super().__init__(app)
        
        self.config = X402Config.from_dict(config)
        self.processor = X402PaymentProcessor(self.config)
        self.adapter = FastAPIAdapter()
    
    async def dispatch(self, request: Request, call_next):
        """Process request through x402 payment gate."""
        # Extract context
        context = self.adapter.extract_request_context(request)
        
        # Process payment
        result = self.processor.process_request(context)
        
        if result.action == 'deny':
            # Return 402 response
            is_browser = is_browser_request(context.headers)
            return self.adapter.create_payment_required_response(
                error=result.error or 'Payment required',
                requirements=result.requirements or [],
                is_browser=is_browser
            )
        
        # Call endpoint
        response = await call_next(request)
        
        # Settle payment if verified and successful response
        if result.payment_verified and self.adapter.is_success_response(response):
            settlement = self.processor.settle_payment(context)
            
            if settlement.success:
                response = self.adapter.add_payment_response_header(
                    response,
                    settlement.encoded_response
                )
            elif self.config.settle_policy == 'block-on-failure':
                # Return 402 on settlement failure
                return self.adapter.create_payment_required_response(
                    error='Settlement failed',
                    requirements=result.requirements or [],
                    is_browser=False
                )
        
        return response
```

## Dependencies

**File**: `pyproject.toml`

```toml
[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"

[project]
name = "x402-connector"
version = "0.1.0"
description = "Universal Python SDK for the x402 Payment Required protocol"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [
  { name = "x402 Contributors" }
]
keywords = ["x402", "payments", "web3", "solana", "base", "http402"]
classifiers = [
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Development Status :: 4 - Beta",
  "Intended Audience :: Developers",
  "Topic :: Software Development :: Libraries :: Python Modules",
]

# Core dependencies (framework-agnostic)
dependencies = [
  "httpx>=0.27.0",
  "x402>=0.1.0",
  "eth-account>=0.13.4",
  "web3>=6.20.0",
]

[project.optional-dependencies]
# Framework-specific extras
django = [
  "Django>=5.0",
]
flask = [
  "Flask>=3.0",
]
fastapi = [
  "fastapi>=0.100.0",
  "uvicorn>=0.24.0",
]

# Development dependencies
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23.0",
  "pytest-cov>=4.1.0",
  "black>=23.0",
  "ruff>=0.1.0",
  "mypy>=1.7",
]

# Testing dependencies
tests = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23.0",
  "pytest-django>=4.8.0",
  "respx>=0.21.1",
  "anyio>=4.0.0",
  "hexbytes>=0.3.1",
]

# All frameworks
all = [
  "x402-connector[django,flask,fastapi]",
]

[project.urls]
Homepage = "https://github.com/yourusername/x402-connector"
Documentation = "https://x402-connector.readthedocs.io"
Repository = "https://github.com/yourusername/x402-connector"
Issues = "https://github.com/yourusername/x402-connector/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/x402_connector"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-ra -v --cov=x402_connector --cov-report=term-missing"
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.black]
line-length = 100
target-version = ["py310", "py311", "py312"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
```

## Testing Strategy

See next section for comprehensive testing plan...

