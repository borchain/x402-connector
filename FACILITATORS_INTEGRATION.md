# Facilitators Integration Guide

Comprehensive guide for configuring and using x402-connector with different facilitator services for payment verification and settlement.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Supported Facilitators](#supported-facilitators)
  - [Local Mode](#local-mode)
  - [PayAI Network](#payai-network)
  - [Corbits Platform](#corbits-platform)
  - [Hybrid Mode](#hybrid-mode)
- [Configuration Guide](#configuration-guide)
- [Framework Integration Examples](#framework-integration-examples)
- [Environment Variables Reference](#environment-variables-reference)
- [Choosing the Right Facilitator](#choosing-the-right-facilitator)
- [Testing Guide](#testing-guide)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Resources](#resources)

---

## Overview

A **facilitator** handles the payment verification and settlement process for x402 payments on Solana blockchain. The x402-connector SDK provides four production-ready facilitator modes, each designed for different use cases and deployment scenarios.

### What is a Facilitator?

Facilitators manage:
- **Payment Verification**: Validating signatures and payment requirements
- **Transaction Settlement**: Broadcasting payments to Solana blockchain
- **Nonce Management**: Handling replay protection and durable nonces
- **Error Handling**: Managing transaction failures and retries

### Available Modes

- **Local**: Self-hosted verification and settlement on your server
- **PayAI**: Managed service by PayAI Network
- **Corbits**: Managed service with marketplace integration
- **Hybrid**: Local verification combined with remote settlement

---

## Architecture

### Directory Structure

```
src/x402_connector/core/facilitators/
├── __init__.py          # Factory function and exports
├── local.py             # Self-hosted Solana facilitator
├── payai.py             # PayAI Network facilitator
├── corbits.py           # Corbits platform facilitator
└── hybrid.py            # Hybrid mode facilitator
```

### Common Interface

All facilitators implement a consistent interface:

```python
class Facilitator:
    def verify(payment: Dict, requirements: Dict) -> Dict:
        """Verify payment signature and requirements"""
        
    def settle(payment: Dict, requirements: Dict) -> Dict:
        """Settle payment on Solana blockchain"""
        
    def get_durable_nonce_info() -> Optional[Dict]:
        """Get durable nonce information (optional)"""
```

### Payment Flow

```
1. Client Request (No Payment)
   ↓
2. Server Returns 402 with Requirements
   ↓
3. Client Signs Payment
   ↓
4. Client Retries with X-PAYMENT Header
   ↓
5. Facilitator.verify() → Validates Payment
   ↓
6. Server Processes Request (2xx Response)
   ↓
7. Facilitator.settle() → Broadcasts to Solana
   ↓
8. Server Returns Response + X-PAYMENT-RESPONSE Header
```

---

## Supported Facilitators

### Local Mode

**Status:** ✅ Production Ready

Self-hosted payment processing without external dependencies.

#### Features

- Full control over verification and settlement
- Direct Solana RPC communication
- Durable transaction nonces support
- Zero facilitator fees
- Maximum privacy
- Lowest external latency

#### Requirements

- Solana RPC endpoint access
- Hot wallet private key (for settlement)
- Server manages transaction monitoring

#### Configuration

```python
from x402_connector.core import X402Config

config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='local',
    local={
        'private_key_env': 'X402_SIGNER_KEY',
        'rpc_url': 'https://api.mainnet-beta.solana.com',
        'verify_balance': False,
        'wait_for_confirmation': False,
        'use_durable_nonce': False,
        'debug_mode': False,  # Set True for testing
    }
)
```

#### Environment Variables

```bash
# Required for settlement
X402_SIGNER_KEY=your_base58_private_key

# Optional overrides
X402_RPC_URL=https://api.mainnet-beta.solana.com
X402_NETWORK=solana-mainnet
X402_DEBUG_MODE=false
X402_USE_DURABLE_NONCE=false
X402_NONCE_ACCOUNT=your_nonce_account_address
```

#### Best For

- Self-sovereign applications
- Maximum control requirements
- Zero external fees needed
- High-security deployments
- Custom transaction logic

---

### PayAI Network

**Status:** ✅ Production Ready

Managed facilitator service by [PayAI Network](https://payai.network).

#### Features

- No hot wallet management required
- Professional transaction handling
- Built-in monitoring and analytics
- Multiple network support (mainnet, devnet, testnet)
- Automatic retry logic
- RESTful API integration

#### Requirements

- Internet connection to facilitator
- Optional API key for authenticated endpoints
- PayAI account (for analytics dashboard)

#### Configuration

```python
from x402_connector.core import X402Config

config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='payai',
    payai={
        'facilitator_url': 'https://facilitator.payai.network',
        'api_key_env': 'PAYAI_API_KEY',  # Optional
        'timeout': 30,
    }
)
```

#### Environment Variables

```bash
# Optional: for authenticated endpoints
PAYAI_API_KEY=your_payai_api_key

# Optional: override facilitator URL
PAYAI_FACILITATOR_URL=https://facilitator.payai.network
```

#### API Endpoints

- **Verify**: `POST /verify`
- **Settle**: `POST /settle`
- **Nonce**: `GET /nonce`

#### Best For

- Quick deployment
- Managed infrastructure
- No DevOps overhead
- Built-in analytics needs
- Professional support

#### Resources

- Documentation: https://docs.payai.network/
- Facilitator: https://facilitator.payai.network
- Dashboard: https://payai.network

---

### Corbits Platform

**Status:** ✅ Production Ready

Managed facilitator with marketplace integration by [Corbits](https://corbits.dev).

#### Features

- Professional API marketplace integration
- Built-in analytics dashboard
- Transaction monitoring
- Multiple network support
- API discovery and visibility
- RESTful API integration

#### Requirements

- Corbits API key (required)
- Internet connection to facilitator
- Corbits account for marketplace features

#### Configuration

```python
from x402_connector.core import X402Config

config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='corbits',
    corbits={
        'facilitator_url': 'https://api.corbits.dev',
        'api_key_env': 'CORBITS_API_KEY',
        'timeout': 30,
    }
)
```

#### Environment Variables

```bash
# Required
CORBITS_API_KEY=your_corbits_api_key

# Optional: override facilitator URL
CORBITS_FACILITATOR_URL=https://api.corbits.dev
```

#### API Endpoints

- **Verify**: `POST /v1/payments/verify`
- **Settle**: `POST /v1/payments/settle`
- **Nonce**: `GET /v1/nonce`

#### Best For

- API marketplace visibility
- Professional analytics dashboard
- API discovery needs
- Managed infrastructure
- Marketplace integration

#### Resources

- Documentation: https://docs.corbits.dev/
- Platform: https://corbits.dev/
- Marketplace: https://corbits.dev/marketplace

---

### Hybrid Mode

**Status:** ✅ Production Ready

Combines local verification with remote settlement for optimal performance and security.

#### Features

- Lowest latency verification (local, no external calls)
- No hot wallet management (remote settlement)
- Maximum privacy for verification
- Professional settlement infrastructure
- Fallback capability between PayAI and Corbits
- Best of both worlds

#### Requirements

- Local: Solana RPC endpoint access
- Remote: PayAI or Corbits API access
- No hot wallet private key needed

#### Architecture

```
┌─────────────────────────────────────────┐
│ Request with Payment                     │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ LOCAL Verification                       │
│ - Fast (no external API)                │
│ - Private (local RPC only)              │
│ - Immediate response                    │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│ REMOTE Settlement (PayAI or Corbits)    │
│ - Managed keys                          │
│ - Professional infrastructure           │
│ - No hot wallet exposure                │
└─────────────────────────────────────────┘
```

#### Configuration with PayAI

```python
from x402_connector.core import X402Config

config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='hybrid',
    local={
        'rpc_url': 'https://api.mainnet-beta.solana.com',
        'verify_balance': False,
    },
    payai={
        'facilitator_url': 'https://facilitator.payai.network',
        'api_key_env': 'PAYAI_API_KEY',
    }
)
```

#### Configuration with Corbits

```python
from x402_connector.core import X402Config

config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='hybrid',
    local={
        'rpc_url': 'https://api.mainnet-beta.solana.com',
        'verify_balance': False,
    },
    corbits={
        'facilitator_url': 'https://api.corbits.dev',
        'api_key_env': 'CORBITS_API_KEY',
    }
)
```

#### Environment Variables

```bash
# For PayAI settlement
PAYAI_API_KEY=your_payai_api_key

# OR for Corbits settlement
CORBITS_API_KEY=your_corbits_api_key

# Optional: Custom RPC for local verification
X402_RPC_URL=https://api.mainnet-beta.solana.com
```

#### Best For

- Production deployments
- Performance-critical applications
- Privacy-conscious implementations
- Managed settlement without hot wallets
- Maximum uptime requirements

---

## Configuration Guide

### Basic Configuration

All facilitators use the same base configuration:

```python
from x402_connector.core import X402Config

config = X402Config(
    # Required
    pay_to_address='YOUR_SOLANA_ADDRESS',
    
    # Optional (with defaults)
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='local',  # or 'payai', 'corbits', 'hybrid'
    
    # Mode-specific configuration
    local={...},    # For local mode
    payai={...},    # For payai mode
    corbits={...},  # For corbits mode
)
```

### Switching Between Facilitators

Use environment variables for easy switching:

```python
import os
from x402_connector.core import X402Config

# Determine mode from environment
facilitator_mode = os.getenv('X402_FACILITATOR_MODE', 'local')

config_dict = {
    'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS'),
    'network': 'solana-mainnet',
    'facilitator_mode': facilitator_mode,
}

# Add mode-specific config
if facilitator_mode == 'payai':
    config_dict['payai'] = {
        'facilitator_url': 'https://facilitator.payai.network',
    }
elif facilitator_mode == 'corbits':
    config_dict['corbits'] = {
        'facilitator_url': 'https://api.corbits.dev',
    }
elif facilitator_mode == 'hybrid':
    config_dict['local'] = {
        'rpc_url': 'https://api.mainnet-beta.solana.com',
    }
    config_dict['payai'] = {
        'facilitator_url': 'https://facilitator.payai.network',
    }

config = X402Config.from_dict(config_dict)
```

### Network Configuration

All facilitators support multiple Solana networks:

```python
# Mainnet (production)
config = X402Config(
    pay_to_address='YOUR_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='local',
)

# Devnet (testing)
config = X402Config(
    pay_to_address='YOUR_ADDRESS',
    network='solana-devnet',
    facilitator_mode='local',
)

# Testnet (staging)
config = X402Config(
    pay_to_address='YOUR_ADDRESS',
    network='solana-testnet',
    facilitator_mode='local',
)
```

---

## Framework Integration Examples

### Django

```python
# settings.py

X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
    'price': '$0.01',
    'facilitator_mode': 'payai',
    'payai': {
        'facilitator_url': 'https://facilitator.payai.network',
    }
}

MIDDLEWARE = [
    'x402_connector.django.X402Middleware',
    # ... other middleware
]
```

### Flask

```python
from flask import Flask
from x402_connector.flask import X402

app = Flask(__name__)

x402 = X402(app, config={
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
    'facilitator_mode': 'corbits',
    'corbits': {
        'facilitator_url': 'https://api.corbits.dev',
    }
})
```

### FastAPI

```python
from fastapi import FastAPI
from x402_connector.fastapi import X402Middleware

app = FastAPI()

app.add_middleware(
    X402Middleware,
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='hybrid',
    local={'rpc_url': 'https://api.mainnet-beta.solana.com'},
    payai={'facilitator_url': 'https://facilitator.payai.network'},
)
```

### Tornado

```python
from tornado import web
from x402_connector.tornado import X402Middleware

app = web.Application(routes)

X402Middleware(app, 
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='local',
)
```

### Pyramid

```python
from pyramid.config import Configurator

config = Configurator(settings={
    'x402.pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'x402.network': 'solana-mainnet',
    'x402.facilitator_mode': 'payai',
    'x402.payai.facilitator_url': 'https://facilitator.payai.network',
})

config.include('x402_connector.pyramid')
app = config.make_wsgi_app()
```

---

## Environment Variables Reference

### General

```bash
X402_PAY_TO_ADDRESS=your_solana_address
X402_NETWORK=solana-mainnet
X402_FACILITATOR_MODE=local
X402_PRICE=$0.01
```

### Local Mode

```bash
X402_SIGNER_KEY=your_base58_private_key  # Required
X402_RPC_URL=https://api.mainnet-beta.solana.com
X402_VERIFY_BALANCE=false
X402_WAIT_FOR_CONFIRMATION=false
X402_DEBUG_MODE=false
X402_USE_DURABLE_NONCE=false
X402_NONCE_ACCOUNT=your_nonce_account_address
```

### PayAI Mode

```bash
PAYAI_API_KEY=your_payai_api_key  # Optional
PAYAI_FACILITATOR_URL=https://facilitator.payai.network
```

### Corbits Mode

```bash
CORBITS_API_KEY=your_corbits_api_key  # Required
CORBITS_FACILITATOR_URL=https://api.corbits.dev
```

### Hybrid Mode

```bash
# Choose one for settlement
PAYAI_API_KEY=your_payai_api_key
# OR
CORBITS_API_KEY=your_corbits_api_key

# Optional for local verification
X402_RPC_URL=https://api.mainnet-beta.solana.com
```

---

## Choosing the Right Facilitator

### Comparison Matrix

| Feature | Local | PayAI | Corbits | Hybrid |
|---------|-------|-------|---------|--------|
| **Status** | ✅ Ready | ✅ Ready | ✅ Ready | ✅ Ready |
| **Key Management** | Self-hosted | Managed | Managed | Hybrid |
| **Verification Latency** | Lowest | Low | Low | Lowest |
| **Settlement Latency** | Low | Low | Low | Low |
| **Setup Complexity** | Medium | Easy | Easy | Medium |
| **Privacy** | Maximum | Standard | Standard | High |
| **Facilitator Fees** | None | Possible | Possible | Possible |
| **Analytics** | DIY | Built-in | Built-in | Mixed |
| **Hot Wallet Required** | Yes | No | No | No |
| **External Dependencies** | RPC only | Full | Full | Partial |
| **Marketplace Integration** | No | No | Yes | No |

### Recommendations

**Choose Local Mode if:**
- You need maximum control and privacy
- You want zero facilitator fees
- You can manage hot wallets securely
- You have DevOps resources
- Self-sovereignty is critical

**Choose PayAI Mode if:**
- You want quick deployment
- You prefer managed infrastructure
- You don't want to manage hot wallets
- You need built-in analytics
- Professional support is important

**Choose Corbits Mode if:**
- You want marketplace visibility
- API discovery is important
- You need professional analytics
- Marketplace integration matters
- You want managed infrastructure

**Choose Hybrid Mode if:**
- You need maximum performance
- Privacy for verification is critical
- You want professional settlement
- You don't want to manage hot wallets
- Production-grade uptime is required

---

## Testing Guide

### Testing Locally

```bash
# Set test environment
export X402_NETWORK=solana-devnet
export X402_DEBUG_MODE=true
export X402_PAY_TO_ADDRESS=your_devnet_address

# Run your application
python app.py
```

### Testing with Different Facilitators

```bash
# Local mode
X402_FACILITATOR_MODE=local python app.py

# PayAI mode
X402_FACILITATOR_MODE=payai PAYAI_API_KEY=xxx python app.py

# Corbits mode
X402_FACILITATOR_MODE=corbits CORBITS_API_KEY=xxx python app.py

# Hybrid mode
X402_FACILITATOR_MODE=hybrid PAYAI_API_KEY=xxx python app.py
```

### Test Endpoints

```bash
# Test free endpoint
curl http://localhost:5000/free
# Expected: 200 OK with content

# Test premium endpoint without payment
curl -i http://localhost:5000/premium
# Expected: 402 Payment Required with payment requirements

# Test premium endpoint with payment
curl -H "X-PAYMENT: {payment_json}" http://localhost:5000/premium
# Expected: 200 OK with content + X-PAYMENT-RESPONSE header
```

---

## Security Considerations

### Local Mode

- ✅ Secure `X402_SIGNER_KEY` environment variable
- ✅ Use separate wallets for receiving (cold) and signing (hot)
- ✅ Monitor transaction activity regularly
- ✅ Implement rate limiting
- ✅ Rotate hot wallet keys periodically
- ✅ Keep hot wallet balance minimal

### Remote Modes (PayAI/Corbits)

- ✅ Secure API keys as environment variables
- ✅ Use HTTPS for all facilitator communication
- ✅ Verify facilitator SSL certificates
- ✅ Monitor API usage and costs
- ✅ Implement timeout and retry logic
- ✅ Log all facilitator interactions

### Hybrid Mode

- ✅ Follow local mode security for verification
- ✅ Follow remote mode security for settlement
- ✅ Monitor both local and remote operations
- ✅ Implement fallback mechanisms

### General Best Practices

- Never commit private keys or API keys to git
- Use `.env` files for local development
- Use secret management systems in production
- Implement comprehensive logging
- Monitor all payment transactions
- Set up alerts for unusual activity
- Test thoroughly on devnet before mainnet
- Implement proper error handling

---

## Troubleshooting

### Common Issues

#### "Facilitator timeout"

**Cause:** Remote facilitator not responding  
**Solution:** 
- Check network connectivity
- Verify facilitator URL is correct
- Increase timeout value in configuration
- Check facilitator status page

#### "Invalid facilitator mode"

**Cause:** Unsupported mode specified  
**Solution:** Use 'local', 'payai', 'corbits', or 'hybrid' (case-insensitive)

#### "PayAI verification failed"

**Cause:** PayAI service issue or misconfiguration  
**Solution:**
- Check PAYAI_API_KEY if using authenticated endpoints
- Verify network settings match
- Check PayAI status at https://status.payai.network
- Review logs for detailed error messages

#### "Corbits verification failed"

**Cause:** Corbits service issue or missing API key  
**Solution:**
- Ensure CORBITS_API_KEY is set correctly
- Verify account is active on corbits.dev
- Check network settings
- Review API quota limits

#### "X402_SIGNER_KEY not set" (Local Mode)

**Cause:** Missing private key for settlement  
**Solution:**
- Set `X402_SIGNER_KEY` environment variable
- Use base58-encoded Solana private key
- Ensure key has sufficient SOL for gas fees

#### "Payment verification failed"

**Cause:** Invalid payment signature or requirements  
**Solution:**
- Verify signature format is correct
- Check amount matches requirements
- Ensure network matches (devnet vs mainnet)
- Verify payment hasn't expired
- Check recipient address matches

#### "Settlement failed"

**Cause:** Transaction broadcast error  
**Solution:**
- Check signer has sufficient SOL for fees
- Verify RPC endpoint is responding
- Check transaction wasn't already settled
- Review Solana network status

---

## API Reference

### Factory Function

```python
from x402_connector.core.facilitators import get_facilitator

facilitator = get_facilitator(config)
```

**Returns:** Appropriate facilitator instance based on `config.facilitator_mode`

### Facilitator Interface

#### `verify(payment: Dict, requirements: Dict) -> Dict`

Verifies payment signature and requirements.

**Parameters:**
- `payment`: Payment payload from X-PAYMENT header
- `requirements`: Payment requirements from 402 response

**Returns:**
```python
{
    'isValid': bool,           # True if payment is valid
    'invalidReason': str,      # Reason if invalid
    'payer': str,              # Payer's Solana address
}
```

#### `settle(payment: Dict, requirements: Dict) -> Dict`

Settles payment on Solana blockchain.

**Parameters:**
- `payment`: Verified payment payload
- `requirements`: Payment requirements

**Returns:**
```python
{
    'success': bool,           # True if settlement succeeded
    'transaction': str,        # Solana transaction signature
    'error': str,              # Error message if failed
    'receipt': dict,           # Optional transaction receipt
}
```

#### `get_durable_nonce_info() -> Optional[Dict]`

Gets durable nonce information (if supported).

**Returns:**
```python
{
    'account': str,            # Nonce account address
    'nonce': str,              # Current nonce value
    'authorizedPubkey': str,   # Authority public key
}
```

### Protocol Compatibility

All facilitators implement the x402 protocol specification:

**Payment Requirements (402 Response):**
```json
{
  "x402Version": 1,
  "accepts": [{
    "scheme": "exact",
    "network": "solana-mainnet",
    "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "assetSymbol": "USDC",
    "maxAmountRequired": "10000",
    "payTo": "YOUR_SOLANA_ADDRESS",
    "resource": "https://your-api.com/premium",
    "timeout": 60
  }]
}
```

**Payment Header (X-PAYMENT):**
```json
{
  "x402Version": 1,
  "scheme": "exact",
  "network": "solana-mainnet",
  "payload": {
    "authorization": {
      "from": "PAYER_ADDRESS",
      "to": "RECIPIENT_ADDRESS",
      "value": "10000",
      "validAfter": 1234567890,
      "validBefore": 1234567950,
      "nonce": "unique_nonce"
    },
    "signature": "base64_signature",
    "signedTransaction": "base64_transaction"
  }
}
```

---

## Resources

### Documentation

- **x402 Protocol**: https://github.com/coinbase/x402
- **Solana Docs**: https://docs.solana.com
- **PayAI Docs**: https://docs.payai.network/
- **Corbits Docs**: https://docs.corbits.dev/
- **SDK Documentation**: [README.md](README.md)
- **API Reference**: [API.md](API.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)

### Services

- **PayAI Network**: https://payai.network
- **PayAI Facilitator**: https://facilitator.payai.network
- **Corbits Platform**: https://corbits.dev/
- **Corbits Marketplace**: https://corbits.dev/marketplace

### Support

- **GitHub Issues**: https://github.com/borchain/x402-connector/issues
- **PayAI Discord**: https://discord.gg/payai
- **Corbits Discord**: https://discord.gg/corbits
- **Solana Discord**: https://discord.gg/solana

---

**x402-connector** - Production-ready facilitator integration for Solana micropayments
