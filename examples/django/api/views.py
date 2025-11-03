"""Example API views demonstrating x402 payment integration.

This module shows different use cases:
- Public endpoints (no payment required)
- Premium endpoints (payment required via path matching)
- Different types of paid content (data, AI, analytics)
- Random number generator demo (free vs paid)
"""

import random
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods


# =============================================================================
# DEMO PAGE
# =============================================================================

def index(request):
    """Demo homepage with interactive buttons."""
    return render(request, 'index.html')


# =============================================================================
# RANDOM NUMBER GENERATOR DEMO
# =============================================================================

@require_http_methods(["GET"])
def random_free(request):
    """Free random number generator (1-6 digits).
    
    No payment required - publicly accessible.
    """
    min_val = 1
    max_val = 6
    number = random.randint(min_val, max_val)
    
    return JsonResponse({
        'number': number,
        'min': min_val,
        'max': max_val,
        'type': 'free',
        'timestamp': timezone.now().isoformat(),
    })


@require_http_methods(["GET"])
def random_premium(request):
    """Premium random number generator (7+ digits).
    
    Requires payment - protected by x402 middleware.
    Path matches '/api/random/premium' which is in protected_paths.
    """
    min_val = 1000000
    max_val = 9999999
    number = random.randint(min_val, max_val)
    
    return JsonResponse({
        'number': number,
        'min': min_val,
        'max': max_val,
        'type': 'premium',
        'digits': len(str(number)),
        'timestamp': timezone.now().isoformat(),
        'note': 'This number required payment to generate!',
    })


# =============================================================================
# PUBLIC ENDPOINTS - No payment required
# =============================================================================

@require_http_methods(["GET"])
def public_info(request):
    """Public API information - accessible without payment."""
    return JsonResponse({
        'service': 'x402-connector Django Example',
        'version': '1.0.0',
        'description': 'Demonstrating HTTP 402 Payment Required',
        'timestamp': timezone.now().isoformat(),
        'endpoints': {
            'free': [
                '/api/public/info',
                '/api/public/status',
            ],
            'paid': [
                '/api/premium/data',
                '/api/premium/ai',
                '/api/premium/analytics',
                '/api/paid/content',
            ],
        },
        'x402': {
            'enabled': True,
            'network': 'base',
            'price': '$0.01',
        },
    })


@require_http_methods(["GET"])
def public_status(request):
    """Service status - accessible without payment."""
    return JsonResponse({
        'status': 'operational',
        'timestamp': timezone.now().isoformat(),
        'uptime': '99.9%',
        'message': 'All systems operational',
    })


# =============================================================================
# PREMIUM ENDPOINTS - Payment required (matched by path /api/premium/*)
# =============================================================================

@require_http_methods(["GET"])
def premium_data(request):
    """Premium data endpoint - requires payment.
    
    This endpoint is automatically protected by x402 middleware because
    its path matches '/api/premium/*' in the protected_paths configuration.
    
    No code changes needed - just configure the path pattern!
    """
    return JsonResponse({
        'type': 'premium',
        'data': {
            'market_data': {
                'btc_price': 45000 + random.randint(-1000, 1000),
                'eth_price': 3000 + random.randint(-100, 100),
                'sol_price': 100 + random.randint(-10, 10),
            },
            'predictions': {
                'trend': random.choice(['bullish', 'bearish', 'neutral']),
                'confidence': random.uniform(0.7, 0.95),
            },
            'exclusive_insights': [
                'Market sentiment is shifting',
                'Watch for key resistance levels',
                'Volume indicators suggest momentum',
            ],
        },
        'timestamp': timezone.now().isoformat(),
        'note': 'This data required payment to access',
    })


@require_http_methods(["GET", "POST"])
def ai_inference(request):
    """AI inference endpoint - requires payment per request.
    
    Demonstrates charging for expensive AI computations.
    Each inference costs $0.01 (or whatever price configured).
    """
    if request.method == 'POST':
        # In real app, parse JSON body
        prompt = request.POST.get('prompt', 'Hello')
    else:
        prompt = request.GET.get('prompt', 'Hello')
    
    # Simulate AI inference (in real app, call your AI model)
    responses = [
        f"The answer to '{prompt}' is quite interesting...",
        f"Based on '{prompt}', I would suggest...",
        f"Regarding '{prompt}', the key insight is...",
        f"In response to '{prompt}', consider this...",
    ]
    
    return JsonResponse({
        'type': 'ai_inference',
        'prompt': prompt,
        'response': random.choice(responses),
        'model': 'gpt-4-mini',
        'tokens_used': random.randint(50, 200),
        'inference_time_ms': random.randint(100, 500),
        'timestamp': timezone.now().isoformat(),
        'note': 'This inference required payment',
    })


@require_http_methods(["GET"])
def analytics(request):
    """Analytics endpoint - requires payment.
    
    Demonstrates charging for expensive analytical computations.
    """
    # Simulate expensive computation
    dataset = request.GET.get('dataset', 'default')
    
    return JsonResponse({
        'type': 'analytics',
        'dataset': dataset,
        'results': {
            'total_records': random.randint(10000, 100000),
            'mean': round(random.uniform(100, 1000), 2),
            'median': round(random.uniform(100, 1000), 2),
            'std_dev': round(random.uniform(10, 100), 2),
            'correlation': round(random.uniform(-1, 1), 3),
        },
        'insights': [
            'Strong correlation detected',
            'Outliers identified and removed',
            'Trend analysis complete',
        ],
        'computation_time_ms': random.randint(500, 2000),
        'timestamp': timezone.now().isoformat(),
        'note': 'This analysis required payment',
    })


# =============================================================================
# PAID CONTENT - Payment required (matched by path /api/paid/*)
# =============================================================================

@require_http_methods(["GET"])
def paid_content(request):
    """Paid content endpoint - requires payment.
    
    Demonstrates simple paid content delivery.
    """
    content_id = request.GET.get('id', '1')
    
    return JsonResponse({
        'type': 'paid_content',
        'content_id': content_id,
        'title': f'Premium Article #{content_id}',
        'body': 'This is exclusive premium content that requires payment to access. ' * 10,
        'author': 'Premium Author',
        'published': timezone.now().isoformat(),
        'word_count': 250,
        'reading_time_minutes': 5,
        'note': 'This content required payment to access',
    })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

def custom_404(request, exception=None):
    """Custom 404 handler."""
    return JsonResponse({
        'error': 'Not Found',
        'status_code': 404,
        'path': request.path,
        'message': 'The requested endpoint does not exist',
    }, status=404)


def custom_500(request):
    """Custom 500 handler."""
    return JsonResponse({
        'error': 'Internal Server Error',
        'status_code': 500,
        'message': 'An unexpected error occurred',
    }, status=500)

