"""
Django settings for x402-connector example project.

This demonstrates how to integrate x402 payment requirements
into a Django application.
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
# x402 Configuration - Payment Required Protocol
# ========================================================================

X402_CONFIG = {
    # ===== Required Settings =====
    
    # Blockchain network to use
    # Options: 'base', 'base-sepolia', 'polygon', 'ethereum'
    'network': os.getenv('X402_NETWORK', 'base-sepolia'),
    
    # Price per request
    # Formats: '$0.01', '10000' (atomic units), '0.01 USDC'
    'price': os.getenv('X402_PRICE', '$0.01'),
    
    # Your payment recipient address (Ethereum address)
    'pay_to_address': os.getenv(
        'X402_PAY_TO_ADDRESS',
        '0x0000000000000000000000000000000000000000'  # Change this!
    ),
    
    # ===== Protected Paths =====
    
    # Which URL paths require payment
    # Supports glob patterns: '*', '/api/premium/*', etc.
    'protected_paths': [
        '/api/random/premium',  # Premium random number (demo)
        '/api/premium/*',       # All premium API endpoints
        '/api/paid/*',          # All paid API endpoints
    ],
    
    # ===== Optional Settings =====
    
    # Human-readable description
    'description': 'Premium API Access - x402 Example',
    
    # Expected response content type
    'mime_type': 'application/json',
    
    # Maximum time for payment validity (seconds)
    'max_timeout_seconds': 60,
    
    # Whether to include in x402 discovery
    'discoverable': True,
    
    # ===== Facilitator Configuration =====
    
    # Facilitator mode: 'local', 'remote', or 'hybrid'
    # - local: Verify and settle payments yourself
    # - remote: Use external facilitator service
    # - hybrid: Verify locally, settle remotely
    'facilitator_mode': os.getenv('X402_FACILITATOR_MODE', 'local'),
    
    # Local facilitator settings (when mode='local' or 'hybrid')
    'local': {
        # Environment variable name for private key
        'private_key_env': 'X402_SIGNER_KEY',
        
        # Environment variable name for RPC URL
        'rpc_url_env': 'X402_RPC_URL',
        
        # Whether to verify payer has sufficient balance
        'verify_balance': False,  # Set to True for production
        
        # Whether to simulate transaction before broadcasting
        'simulate_before_send': True,
        
        # Whether to wait for transaction confirmation
        'wait_for_receipt': False,  # Set to True for production
    },
    
    # Remote facilitator settings (when mode='remote' or 'hybrid')
    # 'remote': {
    #     'url': 'https://facilitator.example.com',
    #     'headers': {'Authorization': 'Bearer your-token'},
    #     'timeout': 20,
    # },
    
    # ===== Settlement Policy =====
    
    # What to do if payment settlement fails:
    # - 'block-on-failure': Return 402 error
    # - 'log-and-continue': Log error but continue
    'settle_policy': 'block-on-failure',
    
    # Enable caching to prevent duplicate settlements
    'replay_cache_enabled': True,
}

# Validate required configuration
if X402_CONFIG['pay_to_address'] == '0x0000000000000000000000000000000000000000':
    print("⚠️  WARNING: X402_PAY_TO_ADDRESS is not configured!")
    print("   Set the X402_PAY_TO_ADDRESS environment variable")
    print("   or update config/settings.py")

