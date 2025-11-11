# Facilitators Integration Guide

This guide explains how to configure x402-connector with different facilitator services for payment verification and settlement.

## What is a Facilitator?

A **facilitator** handles the payment verification and settlement process for x402 payments. It can operate in different modes:

- **Local** - Self-hosted verification and settlement on your server
- **Remote** - Delegated to a third-party service (PayAI, Corbits)
- **Hybrid** - Local verification, remote settlement

## Supported Facilitators

### 🏠 Local Mode (Default)

**Status:** ✅ Fully Supported

Handle all payment processing on your own server using Solana RPC.

**Pros:**
- Full control and ownership
- No third-party dependencies
- Lowest latency
- No facilitator fees
- Maximum privacy

**Cons:**
- You manage hot wallet private keys
- You handle transaction monitoring
- You implement your own analytics

**Configuration:**

```python
from x402_connector.core import X402Config

config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    price='$0.01',
    facilitator_mode='local',  # Default
)
```

**Environment Variables:**

```bash
# Required for settlement
X402_SIGNER_KEY=your_private_key_base58

# Optional
X402_RPC_URL=https://api.mainnet-beta.solana.com
```

---

### 🚀 PayAI Network

**Status:** ✅ Fully Supported

[PayAI](https://payai.network) provides a managed facilitator service for x402 payments on Solana.

**Pros:**
- No hot wallet management needed
- Professional transaction handling
- Built-in monitoring and analytics
- Multiple network support (mainnet, devnet, testnet)

**Cons:**
- Requires internet connection to facilitator
- Third-party dependency
- May have service fees

**Configuration:**

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

**Environment Variables:**

```bash
# Optional: for authenticated endpoints
PAYAI_API_KEY=your_payai_api_key

# Optional: override facilitator URL
PAYAI_FACILITATOR_URL=https://facilitator.payai.network
```

**Resources:**
- Documentation: https://docs.payai.network/
- Facilitator URL: https://facilitator.payai.network

---

### 🔷 Corbits.dev

**Status:** 🚧 Planned (Future Release)

[Corbits](https://corbits.dev/) provides facilitator services and a marketplace for paywalled APIs.

**Note:** Direct integration with Corbits facilitator is planned for a future release. Currently, you can use **local mode** and remain **protocol-compatible** with Corbits clients.

**Protocol Compatibility:**

Corbits' JavaScript SDK clients can already call your API when using local mode:

```python
# Your Python API (x402-connector in local mode)
config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='local',  # Protocol-compatible with Corbits clients
)
```

**Future Configuration** (when available):

```python
config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='corbits',
    corbits={
        'facilitator_url': 'https://api.corbits.dev',
        'api_key_env': 'CORBITS_API_KEY',
        'timeout': 30,
    }
)
```

**Resources:**
- Documentation: https://docs.corbits.dev/
- Platform: https://corbits.dev/

---

### 🔄 Hybrid Mode

**Status:** 🚧 Planned (Future Release)

Hybrid mode combines local verification with remote settlement:
- Verify payments locally (fast, no external calls)
- Settle via remote facilitator (delegated key management)

**Future Configuration:**

```python
config = X402Config(
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='hybrid',
    local={
        'verify_only': True,
    },
    payai={
        'facilitator_url': 'https://facilitator.payai.network',
        'settlement_only': True,
    }
)
```

---

## Configuration Examples

### Django with PayAI

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

### Flask with Local Mode

```python
# app.py
from flask import Flask
from x402_connector.flask import X402

app = Flask(__name__)

x402 = X402(app, config={
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'network': 'solana-mainnet',
    'facilitator_mode': 'local',  # Default
})
```

### FastAPI with PayAI

```python
# main.py
from fastapi import FastAPI
from x402_connector.fastapi import X402Middleware

app = FastAPI()

app.add_middleware(
    X402Middleware,
    pay_to_address='YOUR_SOLANA_ADDRESS',
    network='solana-mainnet',
    facilitator_mode='payai',
    payai={
        'facilitator_url': 'https://facilitator.payai.network',
    }
)
```

---

## Switching Between Facilitators

You can easily switch between facilitators by changing the configuration:

```python
import os

# Determine facilitator from environment
facilitator_mode = os.getenv('X402_FACILITATOR_MODE', 'local')

config = {
    'pay_to_address': os.getenv('X402_PAY_TO_ADDRESS'),
    'network': 'solana-mainnet',
    'facilitator_mode': facilitator_mode,
}

# Add mode-specific config
if facilitator_mode == 'payai':
    config['payai'] = {
        'facilitator_url': 'https://facilitator.payai.network',
    }

# Use in your framework
x402 = X402(app, config=config)
```

---

## Protocol Compatibility

All facilitators implement the same **x402 protocol specification**:

### Payment Requirements Format (HTTP 402 Response)

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

### Payment Header Format (X-PAYMENT Header)

```json
{
  "x402Version": 1,
  "scheme": "exact",
  "network": "solana-mainnet",
  "payload": {
    "authorization": {
      "from": "PAYER_ADDRESS",
      "to": "YOUR_ADDRESS",
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

This means:
- ✅ Clients using any x402-compatible SDK can call your API
- ✅ You can switch facilitators without breaking clients
- ✅ Mix and match: PayAI client → your local server, or vice versa

---

## Choosing a Facilitator

| Feature | Local | PayAI | Corbits | Hybrid |
|---------|-------|-------|---------|--------|
| **Status** | ✅ Ready | ✅ Ready | 🚧 Future | 🚧 Future |
| **Key Management** | Self-hosted | Managed | Managed | Hybrid |
| **Latency** | Lowest | Low | Low | Medium |
| **Setup Complexity** | Medium | Easy | Easy | Easy |
| **Privacy** | Maximum | Standard | Standard | High |
| **Fees** | None | Possible | Possible | Possible |
| **Analytics** | DIY | Built-in | Built-in | Mixed |

**Recommendations:**

- **Local Mode**: Best for self-sovereign applications, maximum control
- **PayAI**: Best for quick setup, managed infrastructure
- **Corbits**: Best for marketplace visibility (when available)
- **Hybrid**: Best for balancing speed and convenience (when available)

---

## Testing

### Test with Local Mode

```bash
# Start your server with local mode
X402_FACILITATOR_MODE=local python app.py

# Test payment endpoint
curl http://localhost:5000/premium
# Returns 402 with payment requirements
```

### Test with PayAI

```bash
# Start your server with PayAI mode
X402_FACILITATOR_MODE=payai python app.py

# Test payment endpoint
curl http://localhost:5000/premium
# Returns 402 with payment requirements
```

---

## Environment Variables Reference

### Local Mode

```bash
X402_SIGNER_KEY=your_private_key_base58  # Required for settlement
X402_RPC_URL=https://api.mainnet-beta.solana.com  # Optional
X402_VERIFY_BALANCE=false  # Optional
X402_WAIT_FOR_CONFIRMATION=false  # Optional
```

### PayAI Mode

```bash
PAYAI_API_KEY=your_api_key  # Optional
PAYAI_FACILITATOR_URL=https://facilitator.payai.network  # Optional
```

### General

```bash
X402_PAY_TO_ADDRESS=your_solana_address  # Where payments go
X402_NETWORK=solana-mainnet  # Network selection
X402_FACILITATOR_MODE=local  # Facilitator mode
```

---

## Security Considerations

### Local Mode

- ✅ Keep `X402_SIGNER_KEY` secure (hot wallet)
- ✅ Use separate wallets for `pay_to_address` (cold) and `signer_key` (hot)
- ✅ Monitor transaction activity
- ✅ Implement rate limiting

### Remote Mode (PayAI/Corbits)

- ✅ Secure API keys as environment variables
- ✅ Use HTTPS for all facilitator communication
- ✅ Verify facilitator SSL certificates
- ✅ Monitor API usage and costs

---

## Troubleshooting

### "Facilitator timeout"

**Cause:** Remote facilitator not responding
**Solution:** Check network connectivity, verify facilitator URL, increase timeout

### "Invalid facilitator mode"

**Cause:** Unsupported mode specified
**Solution:** Use 'local', 'payai', 'corbits', or 'hybrid'

### "PayAI verification failed"

**Cause:** PayAI service issue or misconfiguration
**Solution:** Check API key, verify network settings, check PayAI status

### "X402_SIGNER_KEY not set" (Local Mode)

**Cause:** Missing private key for settlement
**Solution:** Set environment variable with your Solana private key (base58)

---

## Additional Resources

- **x402 Protocol**: https://github.com/coinbase/x402
- **PayAI Documentation**: https://docs.payai.network/
- **Corbits Documentation**: https://docs.corbits.dev/
- **Solana Documentation**: https://docs.solana.com
- **SDK Documentation**: [README.md](README.md)
- **API Reference**: [API.md](API.md)

---

**Built for the x402 ecosystem** 🚀

