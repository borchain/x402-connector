# Architecture Overview

## Design Philosophy

The x402-connector SDK is built on three core principles:

1. **Framework Agnostic Core**: Business logic completely independent of web frameworks
2. **Minimal Integration Friction**: Single decorator/middleware to protect endpoints
3. **Progressive Enhancement**: Start simple, add complexity only when needed

## System Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  (User's Django/Flask/FastAPI/etc. application)             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                 FRAMEWORK ADAPTER LAYER                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Django   │  │  Flask   │  │ FastAPI  │  │  Others  │   │
│  │ Adapter  │  │ Adapter  │  │ Adapter  │  │ Adapters │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  Responsibilities:                                           │
│  - Extract request data (headers, path, method)             │
│  - Build payment requirements from config                   │
│  - Return 402 responses (HTML/JSON)                         │
│  - Inject payment response headers                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    CORE LOGIC LAYER                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │           X402PaymentProcessor                     │    │
│  │  - verify_payment()                                │    │
│  │  - settle_payment()                                │    │
│  │  - build_payment_requirements()                    │    │
│  │  - generate_402_response()                         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           ConfigurationManager                     │    │
│  │  - Load from env, dict, or config objects          │    │
│  │  - Validate configuration                          │    │
│  │  - Provide defaults                                │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           RequestContext (abstraction)             │    │
│  │  - path: str                                       │    │
│  │  - method: str                                     │    │
│  │  - headers: Dict[str, str]                         │    │
│  │  - payment_header: Optional[str]                   │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  FACILITATOR LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Local   │  │  Remote  │  │  Hybrid  │                  │
│  │Facilitatr│  │Facilitatr│  │Facilitatr│                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│                                                              │
│  Responsibilities:                                           │
│  - Payment verification (signatures, balances, nonces)      │
│  - Transaction settlement (EIP-3009)                        │
│  - Blockchain interaction (Web3)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│               BLOCKCHAIN SETTLEMENT LAYER                    │
│  (Solana, Base, Polygon, etc.)                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Framework Adapters

Each framework gets its own adapter that translates between framework-specific objects and our core abstractions.

**Key Responsibilities:**
- Convert framework requests to `RequestContext`
- Apply middleware/decorators to routes
- Generate framework-specific responses (HttpResponse, JSONResponse, etc.)
- Handle async/sync differences

**Interface:**
```python
class BaseAdapter(ABC):
    """Base adapter interface all frameworks must implement."""
    
    @abstractmethod
    def extract_request_context(self, request) -> RequestContext:
        """Extract framework-agnostic request context."""
        pass
    
    @abstractmethod
    def create_payment_required_response(
        self, 
        error: str, 
        requirements: List[PaymentRequirements],
        is_browser: bool
    ) -> Any:
        """Create 402 response in framework-specific format."""
        pass
    
    @abstractmethod
    def add_payment_response_header(self, response, header_value: str) -> Any:
        """Add X-PAYMENT-RESPONSE header to response."""
        pass
```

### 2. Core Payment Processor

The heart of the SDK - completely framework-agnostic.

```python
class X402PaymentProcessor:
    """Framework-agnostic x402 payment processing."""
    
    def __init__(self, config: X402Config, facilitator: BaseFacilitator):
        self.config = config
        self.facilitator = facilitator
    
    def process_request(self, context: RequestContext) -> ProcessingResult:
        """
        Main processing logic:
        1. Check if path is protected
        2. Verify payment if present
        3. Return allow/deny decision
        """
        if not self._is_protected_path(context.path):
            return ProcessingResult(action='allow')
        
        if not context.payment_header:
            return ProcessingResult(
                action='deny',
                requirements=self._build_requirements(context)
            )
        
        verification = self._verify_payment(context)
        if not verification.is_valid:
            return ProcessingResult(
                action='deny',
                error=verification.error
            )
        
        return ProcessingResult(action='allow', payment_verified=True)
    
    def settle_payment(self, context: RequestContext) -> SettlementResult:
        """Settle verified payment after successful response."""
        # Settlement logic
        pass
```

### 3. Configuration System

Flexible configuration that works across all frameworks.

```python
@dataclass
class X402Config:
    """Framework-agnostic configuration."""
    
    # Required
    network: str
    price: str
    pay_to_address: str
    
    # Optional
    protected_paths: List[str] = field(default_factory=lambda: ['*'])
    facilitator_mode: str = 'local'
    description: str = ''
    mime_type: str = 'application/json'
    max_timeout_seconds: int = 60
    
    # Facilitator configs
    local: Optional[LocalFacilitatorConfig] = None
    remote: Optional[RemoteFacilitatorConfig] = None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'X402Config':
        """Load from dictionary."""
        pass
    
    @classmethod
    def from_env(cls, prefix: str = 'X402_') -> 'X402Config':
        """Load from environment variables."""
        pass
```

## Framework Integration Patterns

### Pattern 1: Middleware (Django, FastAPI)

**Django:**
```python
class X402Middleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.processor = self._init_processor()
        self.adapter = DjangoAdapter()
    
    def __call__(self, request):
        context = self.adapter.extract_request_context(request)
        result = self.processor.process_request(context)
        
        if result.action == 'deny':
            return self.adapter.create_payment_required_response(
                error=result.error,
                requirements=result.requirements,
                is_browser=is_browser_request(context.headers)
            )
        
        response = self.get_response(request)
        
        if result.payment_verified and 200 <= response.status_code < 300:
            settlement = self.processor.settle_payment(context)
            if settlement.success:
                return self.adapter.add_payment_response_header(
                    response, 
                    settlement.encoded_response
                )
        
        return response
```

**FastAPI:**
```python
class X402Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        context = self.adapter.extract_request_context(request)
        result = await self.processor.process_request_async(context)
        
        if result.action == 'deny':
            return self.adapter.create_payment_required_response(...)
        
        response = await call_next(request)
        
        # Settlement logic
        return response
```

### Pattern 2: Decorator (Flask, Bottle)

**Flask:**
```python
class X402Flask:
    def __init__(self, app=None, config=None):
        if app:
            self.init_app(app, config)
    
    def require_payment(self, **kwargs):
        """Decorator to protect endpoints."""
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kw):
                context = self.adapter.extract_request_context(request)
                result = self.processor.process_request(context)
                
                if result.action == 'deny':
                    return self.adapter.create_payment_required_response(...)
                
                response = make_response(f(*args, **kw))
                
                if result.payment_verified:
                    settlement = self.processor.settle_payment(context)
                    if settlement.success:
                        response.headers['X-PAYMENT-RESPONSE'] = \
                            settlement.encoded_response
                
                return response
            return wrapped
        return decorator
```

## Data Flow

### Request Flow (Payment Verification)

```
1. Request arrives → Framework Adapter
                         ↓
2. Extract RequestContext (path, headers, method)
                         ↓
3. Pass to Core Processor → process_request()
                         ↓
4. Check if path is protected
                         ↓
5. If protected, check for payment header
                         ↓
6. If present, verify via Facilitator
                         ↓
7. Return ProcessingResult (allow/deny)
                         ↓
8. Adapter generates appropriate response
```

### Response Flow (Payment Settlement)

```
1. Protected endpoint returns 2xx → Framework Adapter
                         ↓
2. Pass RequestContext to Processor → settle_payment()
                         ↓
3. Processor calls Facilitator.settle()
                         ↓
4. Facilitator broadcasts transaction
                         ↓
5. Return SettlementResult
                         ↓
6. Adapter adds X-PAYMENT-RESPONSE header
                         ↓
7. Return modified response to client
```

## Key Design Decisions

### 1. Why Framework Adapters?

**Problem**: Each framework has different request/response objects, middleware systems, and async patterns.

**Solution**: Thin adapter layer that translates between framework specifics and our core abstractions. Core logic never touches framework objects.

**Benefits**:
- Core logic is testable without framework overhead
- Easy to add new frameworks
- Changes to core don't break framework integrations

### 2. Why RequestContext Abstraction?

**Problem**: Different frameworks represent requests differently (Django's HttpRequest, Flask's Request, FastAPI's Request, etc.)

**Solution**: Extract only what we need into a simple dataclass.

```python
@dataclass
class RequestContext:
    path: str
    method: str
    headers: Dict[str, str]
    payment_header: Optional[str]
    absolute_url: str
```

**Benefits**:
- Core logic has no framework dependencies
- Easy to mock for testing
- Clear contract for what data is needed

### 3. Why Both Middleware and Decorators?

**Problem**: Different frameworks have different conventions.

**Solution**: Provide both patterns, let users choose what fits their framework/style.

- **Middleware**: Good for protecting many routes with one configuration (Django, FastAPI)
- **Decorators**: Good for per-endpoint control and explicit marking (Flask, Bottle)

### 4. Facilitator Reuse

**Decision**: Keep the existing facilitator architecture from django-x402.

**Reason**: It's already well-designed and framework-agnostic. No need to reinvent.

## Extension Points

### Adding a New Framework

1. Create adapter in `x402_connector/<framework>/`
2. Implement `BaseAdapter` interface
3. Create middleware/decorator wrapper
4. Add tests
5. Add to documentation

Example structure:
```
x402_connector/
  pyramid/
    __init__.py
    adapter.py      # PyramidAdapter(BaseAdapter)
    middleware.py   # Pyramid tween
    decorators.py   # @require_payment decorator
```

### Custom Facilitators

Users can provide their own facilitator implementations:

```python
class CustomFacilitator(BaseFacilitator):
    def verify(self, payment, requirements):
        # Custom verification logic
        pass
    
    def settle(self, payment, requirements):
        # Custom settlement logic
        pass

# Use it
config = X402Config(facilitator=CustomFacilitator())
```

## Performance Considerations

### 1. Caching

- **Nonce tracking**: In-memory cache prevents replay attacks
- **Settlement caching**: Idempotent settlement results cached by payment header
- **Configuration**: Loaded once at startup, not per-request

### 2. Async Support

- Core processor has both sync and async methods
- Async facilitator operations use `httpx` (async HTTP)
- Framework adapters handle async/sync bridge

### 3. Request Path Matching

- Glob patterns compiled once at startup
- Fast path matching using `fnmatch` or regex
- Protected paths checked before payment verification

## Security Considerations

### 1. Replay Protection

- Nonce tracking prevents reuse of payment signatures
- Optional persistence backend for distributed systems

### 2. Balance Verification

- Optional ERC-20 balance checks before accepting payment
- Prevents accepting payments that will fail settlement

### 3. Transaction Simulation

- Simulate transactions before broadcasting
- Catch errors early, save gas fees

### 4. Environment Variables

- Private keys always from environment, never hardcoded
- Configuration validation at startup
- Clear error messages for missing/invalid config

## Testing Strategy

### Unit Tests

- Core logic tested without framework dependencies
- Mock facilitators for fast tests
- Test all payment verification edge cases

### Integration Tests

- Each framework adapter tested with real framework
- Test decorators/middleware with actual HTTP requests
- Mock blockchain calls, test against test networks

### End-to-End Tests

- Optional: Test against local blockchain (Anvil)
- Test complete payment flow
- Verify actual settlement transactions

## Migration Path

For users of `django-x402`:

1. Install `x402-connector[django]`
2. Change imports from `django_x402` to `x402_connector.django`
3. Update configuration (backward compatible)
4. Run tests
5. Deploy

The Django adapter maintains API compatibility with django-x402.

