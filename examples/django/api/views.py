"""Example API views demonstrating x402 payment integration on Solana."""

import random
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from x402_connector.django import require_payment


# =============================================================================
# DEMO PAGE
# =============================================================================

def index(request):
    """Demo homepage with interactive buttons."""
    return render(request, 'index.html')


# =============================================================================
# RANDOM NUMBER API
# =============================================================================

@require_http_methods(["GET"])
def random_number(request):
    """Free random number generator (1-6).
    
    No payment required - publicly accessible.
    """
    number = random.randint(1, 6)
    
    return JsonResponse({
        'number': number,
        'range': '1-6',
        'type': 'free',
        'timestamp': timezone.now().isoformat(),
    })


@require_http_methods(["GET"])
@require_payment(price='$0.01')
def premium_random_number(request):
    """Premium random number generator (1000000-9999999).
    
    Requires payment via x402 protocol on Solana blockchain.
    Payment is handled automatically by the @require_payment decorator.
    """
    number = random.randint(1000000, 9999999)
    
    return JsonResponse({
        'number': number,
        'range': '1000000-9999999',
        'type': 'premium',
        'digits': 7,
        'timestamp': timezone.now().isoformat(),
        'note': 'This number required payment!',
    })
