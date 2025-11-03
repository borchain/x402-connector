#!/bin/bash
# Development environment setup script for x402-connector

set -e

echo "🚀 Setting up x402-connector development environment..."

# Check Python version
echo "📍 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null

# Install package in development mode with all extras
echo "📥 Installing x402-connector with all dependencies..."
pip install -e ".[dev,tests,all]" > /dev/null 2>&1 || {
    echo "⚠️  Full installation failed (expected - some dependencies may not be available yet)"
    echo "   Installing core dependencies only..."
    pip install -e ".[dev,tests]" || {
        echo "❌ Installation failed. Installing minimal dependencies..."
        pip install -e "."
    }
}

# Run tests
echo ""
echo "🧪 Running tests..."
pytest -v --tb=short 2>&1 | head -20

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Start implementing following INTEGRATION.md"
echo ""
echo "  3. Run tests:"
echo "     pytest -v"
echo ""
echo "  4. Check code quality:"
echo "     black src/ tests/"
echo "     ruff check src/ tests/"
echo "     mypy src/"
echo ""
echo "📖 Read PROJECT_SUMMARY.md for an overview"
echo "📖 Read INTEGRATION.md for the implementation plan"
echo ""
echo "Happy coding! 🎉"

