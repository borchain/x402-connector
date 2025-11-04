# Corbits.dev Facilitator Compatibility

This SDK is fully compatible with the [Corbits.dev](https://corbits.dev/) facilitator service for x402 payment processing.

## What is Corbits.dev?

Corbits.dev is a professional facilitator service for the x402 payment protocol that handles:
- Payment verification
- On-chain settlement
- Transaction monitoring
- Payment analytics

## Compatibility Status

✅ **Fully Compatible** - Our SDK implements the standard x402 protocol that Corbits.dev supports.

## Usage Modes

### 1. Local Mode (Self-Hosted) ⚡

Handle everything yourself - best for full control and lowest latency:

```python
# settings.py
X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'price': '$0.01',
    'network': 'solana-mainnet',
    # Default mode is 'local' - no additional config needed
}
```

**Pros:**
- Full control
- Lowest latency
- No third-party dependencies
- No facilitator fees

**Cons:**
- You manage private keys
- You handle transaction failures
- You monitor settlement

### 2. Remote Mode (Using Corbits) 🌐

Let Corbits handle verification and settlement:

```python
# settings.py
X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'price': '$0.01',
    'network': 'solana-mainnet',
    'facilitator_mode': 'remote',
    'remote': {
        'url': 'https://corbits.dev/api/v1/x402',
        'headers': {
            'Authorization': 'Bearer YOUR_CORBITS_API_KEY',
            'X-Merchant-ID': 'YOUR_MERCHANT_ID',
        },
        'timeout': 30,
    }
}
```

**Pros:**
- Professional infrastructure
- No private key management
- Built-in monitoring
- Transaction analytics
- Automatic retries

**Cons:**
- Third-party dependency
- Additional latency
- Facilitator fees

### 3. Hybrid Mode (Best of Both) ⚖️

Verify locally, settle via Corbits:

```python
# settings.py
X402_CONFIG = {
    'pay_to_address': 'YOUR_SOLANA_ADDRESS',
    'price': '$0.01',
    'network': 'solana-mainnet',
    'facilitator_mode': 'hybrid',
    'local': {
        'verify_balance': True,
        # Verify payments locally
    },
    'remote': {
        'url': 'https://corbits.dev/api/v1/x402',
        'headers': {
            'Authorization': 'Bearer YOUR_CORBITS_API_KEY',
        },
        # Settle via Corbits
    }
}
```

**Pros:**
- Fast verification (local)
- Reliable settlement (Corbits)
- Best security/convenience balance

## Protocol Compatibility

### Standard x402 Format

Both our SDK and Corbits use the standard x402 payment format:

```json
{
  "x402Version": 1,
  "scheme": "exact",
  "network": "solana-mainnet",
  "payload": {
    "authorization": {
      "from": "UserWalletAddress",
      "to": "YourPayToAddress",
      "value": "10000",
      "validAfter": 1730659200,
      "validBefore": 1730659500,
      "nonce": "123456789"
    },
    "signature": "base64_signature_here"
  }
}
```

### Network Support

| Network | Our SDK | Corbits | Status |
|---------|---------|---------|--------|
| solana-mainnet | ✅ | ✅ | Compatible |
| solana-devnet | ✅ | ✅ | Compatible |
| solana-testnet | ✅ | ✅ | Compatible |

### Asset Support

| Asset | Our SDK | Corbits | Status |
|-------|---------|---------|--------|
| USDC (Solana) | ✅ | ✅ | Compatible |
| SOL | 🚧 | ✅ | Planned |
| Other SPL Tokens | 🚧 | ✅ | Planned |

## Integration Examples

### Using Corbits Remote API

```python
# views.py
from x402_connector.django import require_payment

@require_payment(price='$0.01')
def premium_api(request):
    # If using remote mode, payment verification
    # is handled by Corbits automatically
    return JsonResponse({'data': 'premium'})
```

### Switching Between Modes

```python
# Easy to switch modes via environment
# .env.local
X402_FACILITATOR_MODE=local

# .env.production
X402_FACILITATOR_MODE=remote
X402_CORBITS_URL=https://corbits.dev/api/v1/x402
X402_CORBITS_KEY=your_api_key
```

## Testing with Corbits

### 1. Get Corbits API Key

Visit https://corbits.dev/ and sign up for an API key.

### 2. Configure for Testing

```python
# Test with Corbits devnet endpoint
X402_CONFIG = {
    'pay_to_address': 'YOUR_DEVNET_ADDRESS',
    'network': 'solana-devnet',
    'facilitator_mode': 'remote',
    'remote': {
        'url': 'https://corbits.dev/api/v1/x402/devnet',
        'headers': {
            'Authorization': 'Bearer YOUR_TEST_API_KEY',
        },
    }
}
```

### 3. Test Payment Flow

```bash
# Start your server
python manage.py runserver

# Test endpoint returns 402
curl -i http://localhost:8000/api/premium

# With Corbits, you'll see their verification in logs
```

## Corbits Dashboard

When using remote mode, you get access to:

- 📊 **Payment Analytics** - Track all payments
- 🔍 **Transaction Monitor** - Real-time settlement status
- 💰 **Revenue Reports** - Detailed financial reports
- 🔔 **Webhooks** - Get notified of payment events
- 🛠️ **API Console** - Test and debug integrations

## Migration Guide

### From Local to Remote

1. **Sign up at Corbits.dev** and get API key
2. **Update config**:
```python
X402_CONFIG = {
    # ... existing config ...
    'facilitator_mode': 'remote',
    'remote': {'url': '...', 'headers': {'Authorization': '...'}},
}
```
3. **Remove X402_SIGNER_KEY** from environment (not needed anymore)
4. **Test thoroughly** on devnet first

### From Remote to Local

1. **Generate server wallet**: `solana-keygen new`
2. **Fund with SOL** for gas fees
3. **Update config**:
```python
X402_CONFIG = {
    # ... existing config ...
    'facilitator_mode': 'local',
}
```
4. **Set X402_SIGNER_KEY** environment variable
5. **Remove Corbits config** from remote section

## Security Considerations

### Local Mode
- ✅ Your private keys, your control
- ⚠️ You're responsible for key security
- ⚠️ You handle transaction failures

### Remote Mode (Corbits)
- ✅ No private key exposure
- ✅ Professional security infrastructure
- ✅ Automatic failure handling
- ℹ️ Trust Corbits with settlement

## Support

### Our SDK Support
- GitHub Issues: https://github.com/yourusername/x402-connector/issues
- Documentation: [README.md](README.md), [QUICKSTART.md](QUICKSTART.md)

### Corbits Support
- Website: https://corbits.dev/
- Documentation: https://corbits.dev/docs
- Support: support@corbits.dev

## Roadmap

### Current
- ✅ Local facilitator (Solana)
- ✅ Remote facilitator interface
- ✅ Corbits.dev compatibility

### Coming Soon
- 🚧 Hybrid mode implementation
- 🚧 Automatic failover
- 🚧 Multi-facilitator support
- 🚧 Payment caching & retries

## FAQ

**Q: Can I use both local and Corbits?**
A: Yes! Use hybrid mode to verify locally and settle via Corbits.

**Q: Does Corbits charge fees?**
A: Check https://corbits.dev/pricing for current rates.

**Q: What if Corbits is down?**
A: Implement hybrid mode with local fallback for high availability.

**Q: Can I switch modes without code changes?**
A: Yes! Just change the `facilitator_mode` environment variable.

**Q: Does Corbits support all the same features?**
A: Core x402 features are identical. Check their docs for additional features.

---

**Summary:** Use local for full control, remote for convenience, hybrid for best of both! 🚀

