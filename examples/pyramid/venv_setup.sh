#!/bin/bash
# Quick setup script for Pyramid example

echo "Setting up Pyramid example..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install x402-connector with Pyramid support from parent directory
echo "Installing x402-connector with Pyramid support..."
pip install -e "../../[pyramid,solana]"

# Copy env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp env.example .env
    echo "⚠️  Please edit .env with your Solana addresses!"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the Pyramid example:"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "Don't forget to configure .env with your Solana addresses!"

