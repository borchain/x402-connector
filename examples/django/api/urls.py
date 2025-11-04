"""URL configuration for the example x402 API."""

from django.urls import path
from . import views

urlpatterns = [
    # API endpoints (no 'api/' prefix since it's already in config/urls.py)
    path('random', views.random_number, name='random'),
    path('premium/random', views.premium_random_number, name='premium_random'),
    path('balances', views.check_balances, name='balances'),
]
