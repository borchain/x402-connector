#!/bin/bash
# Quick start script for Django x402-connector example

set -e

echo "🚀 Django x402-connector Example - Quick Start"
echo "=============================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "   Creating from env.example..."
    cp env.example .env
    echo ""
    echo "✅ Created .env file"
    echo "⚠️  IMPORTANT: Edit .env and set your X402_PAY_TO_ADDRESS!"
    echo ""
fi

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate --no-input

# Check environment
echo ""
echo "🔍 Checking configuration..."
python manage.py check

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Edit .env and set your X402_PAY_TO_ADDRESS"
echo "   2. Run: python manage.py runserver"
echo "   3. Visit: http://localhost:8000"
echo ""
echo "📖 Read README.md for more information"
echo ""
echo "🧪 Test endpoints:"
echo "   Free:    curl http://localhost:8000/api/public/info"
echo "   Premium: curl http://localhost:8000/api/premium/data"
echo "   Browser: Open http://localhost:8000/api/premium/data"
echo ""
echo "Ready to start? Run: python manage.py runserver"
echo ""

