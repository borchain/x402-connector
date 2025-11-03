"""URL patterns for the example API."""

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Public endpoints (no payment required)
    path('public/info', views.public_info, name='public_info'),
    path('public/status', views.public_status, name='public_status'),
    
    # Premium endpoints (payment required - matched by /api/premium/*)
    path('premium/data', views.premium_data, name='premium_data'),
    path('premium/ai', views.ai_inference, name='ai_inference'),
    path('premium/analytics', views.analytics, name='analytics'),
    
    # Paid content (payment required - matched by /api/paid/*)
    path('paid/content', views.paid_content, name='paid_content'),
]

