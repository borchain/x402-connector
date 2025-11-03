"""URL configuration for x402-connector Django example."""

from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone


def index(request):
    """Welcome page - publicly accessible."""
    return JsonResponse({
        'message': 'Welcome to x402-connector Django Example!',
        'timestamp': timezone.now().isoformat(),
        'endpoints': {
            'public': {
                '/': 'This welcome page',
                '/api/public/info': 'Public API information',
                '/api/public/status': 'Service status',
            },
            'premium': {
                '/api/premium/data': 'Premium data (requires payment)',
                '/api/premium/ai': 'AI inference (requires payment)',
                '/api/premium/analytics': 'Analytics (requires payment)',
            },
            'paid': {
                '/api/paid/content': 'Paid content (requires payment)',
            },
        },
        'instructions': {
            'test_free': 'curl http://localhost:8000/api/public/info',
            'test_premium': 'curl http://localhost:8000/api/premium/data',
            'see_paywall': 'Open http://localhost:8000/api/premium/data in browser',
        },
    })


urlpatterns = [
    path('', index, name='index'),
    path('api/', include('api.urls')),
]

