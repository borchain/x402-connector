"""Django settings for x402-connector example project.

This demonstrates how to integrate x402 payment requirements
into a Django application using Solana blockchain.
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-example-key-change-in-production'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'api',  # Our example API app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ✨ x402 Payment Middleware - Add this line to enable x402
    'x402_connector.django.X402Middleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'x402_connector': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ========================================================================
# x402 Configuration - Solana Payment Required
# ========================================================================

X402_CONFIG = {
    # Required: Your Solana address for receiving payments
    'pay_to_address': os.getenv(
        'X402_PAY_TO_ADDRESS',
        'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK'  # Example address
    ),
    
    # Optional: Price per request (default: '$0.01')
    'price': os.getenv('X402_PRICE', '$0.01'),
    
    # Optional: Solana network (default: 'solana-mainnet')
    # Options: 'solana-mainnet', 'solana-devnet', 'solana-testnet'
    'network': os.getenv('X402_NETWORK', 'solana-devnet'),
    
    # Optional: Custom RPC URL (uses public RPC if not specified)
    # 'rpc_url': 'https://api.devnet.solana.com',
    
    # Optional: Description
    'description': 'Premium Random Number API',
}

# Display current configuration
print("=" * 70)
print("x402-connector - Solana Payment SDK")
print("=" * 70)
print(f"Network:        {X402_CONFIG.get('network')}")
print(f"Pay To:         {X402_CONFIG.get('pay_to_address')}")
print(f"Default Price:  {X402_CONFIG.get('price')}")
print("=" * 70)

# Validate configuration
pay_to = X402_CONFIG.get('pay_to_address', '')
if not pay_to or len(pay_to) < 32:
    print("⚠️  WARNING: X402_PAY_TO_ADDRESS is not properly configured!")
    print("   Set a valid Solana address (base58 format)")
    print("   Example: DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK")
    print("=" * 70)
