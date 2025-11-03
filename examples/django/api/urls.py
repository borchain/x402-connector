"""URL configuration for the example x402 API."""

from django.urls import path
from . import views

urlpatterns = [
    # Demo page
    path('', views.index, name='index'),
    
    # API endpoints
    path('api/random', views.random_number, name='random'),
    path('api/premium/random', views.premium_random_number, name='premium_random'),
]
