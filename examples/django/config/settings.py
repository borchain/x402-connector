"""Django settings for x402-connector example project.

This demonstrates how to integrate x402 payment requirements
into a Django application using Solana blockchain.
"""

import os
from pathlib import Path

# Load environment variables from .env file
print("=" * 70)
print("Loading .env file...")
print("=" * 70)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env'
    
    if env_path.exists():
        print(f"✅ Found .env file at: {env_path}")
        load_dotenv(env_path)
        print("✅ .env file loaded successfully")
        
        # Check if X402_SIGNER_KEY is loaded
        signer_key = os.getenv('X402_SIGNER_KEY', '')
        if signer_key and len(signer_key) > 10:
            print(f"🔑 X402_SIGNER_KEY: Loaded ({len(signer_key)} chars)")
            print(f"   Preview: {signer_key[:20]}...{signer_key[-8:]}")
            print("   Status: ✅ REAL MODE (transactions will be broadcast)")
        else:
            print("⚠️  X402_SIGNER_KEY: NOT SET")
            print("   Status: ⚠️  DEMO MODE (signatures verified, no real transactions)")
            print("   To enable: Set X402_SIGNER_KEY in .env file")
    else:
        print(f"⚠️  No .env file found at: {env_path}")
        print("   Copy env.example to .env and configure your keys")
except ImportError:
    print("⚠️  python-dotenv not installed")
    print("   Install with: pip install python-dotenv")
print("=" * 70)
print()

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
        'REPLACE_WITH_YOUR_SOLANA_ADDRESS_44_CHARS'  # Change this!
    ),
    
    # Optional: Default price (used if endpoint doesn't specify)
    # Most endpoints use @require_payment(price='$0.01') instead
    'price': os.getenv('X402_PRICE', '$0.01'),
    
    # Optional: Solana network
    'network': os.getenv('X402_NETWORK', 'solana-devnet'),
    
    # Protected paths - empty by default, use @require_payment() decorator instead
    'protected_paths': [],
    
    # Optional: Description
    'description': 'Premium Random Number API',
    
    # Debug mode (True = simulated, False = requires pre-signed transactions)
    # Keep True for now - full SPL transfer implementation requires additional client-side setup
    'debug_mode': os.getenv('X402_DEBUG_MODE', 'True').lower() == 'true',
    
    # Optional: Custom RPC URL (if not set, uses public RPC based on network)
    'rpc_url': os.getenv('X402_RPC_URL'),
    
    # Optional: Durable nonce (solves blockhash expiry issue!)
    'use_durable_nonce': os.getenv('X402_USE_DURABLE_NONCE', 'False').lower() == 'true',
    'nonce_account_env': 'X402_NONCE_ACCOUNT',
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
if not pay_to or len(pay_to) < 32 or pay_to.startswith('REPLACE'):
    print("⚠️  WARNING: X402_PAY_TO_ADDRESS is not properly configured!")
    print("   Set a valid Solana address (base58 format, 32-44 chars)")
    print("   Set environment variable: X402_PAY_TO_ADDRESS=YourAddress")
    print("=" * 70)
