"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

# Configure Django for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_settings')

# Setup Django
try:
    import django
    from django.conf import settings
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY='test-secret-key',
            ROOT_URLCONF='tests.test_django_middleware',
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
            ],
            MIDDLEWARE=[
                'django.middleware.common.CommonMiddleware',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            X402_CONFIG={
                'network': 'base-sepolia',
                'price': '$0.01',
                'pay_to_address': '0x1234567890123456789012345678901234567890',
                'protected_paths': ['/api/premium/*'],
            }
        )
        django.setup()
except ImportError:
    # Django not installed - skip Django tests
    pass

