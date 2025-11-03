"""URL configuration for x402-connector Django example."""

from django.urls import path, include
from api.views import index


urlpatterns = [
    path('', index, name='index'),
    path('api/', include('api.urls')),
]

