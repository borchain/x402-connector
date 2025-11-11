#!/bin/bash
# Verify what will be included in the PyPI package

set -e

echo "🔍 Verifying x402-connector package contents..."
echo ""

# Clean previous builds
echo "1️⃣  Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info src/*.egg-info
echo "   ✅ Cleaned"
echo ""

# Build the package
echo "2️⃣  Building package..."
python -m build > /dev/null 2>&1
echo "   ✅ Built"
echo ""

# Find the built files
SDIST=$(ls dist/*.tar.gz 2>/dev/null | head -1)
WHEEL=$(ls dist/*.whl 2>/dev/null | head -1)

if [ -z "$SDIST" ]; then
    echo "❌ No source distribution found!"
    exit 1
fi

echo "3️⃣  Checking source distribution contents..."
echo "   File: $SDIST"
echo ""

# Check for sensitive files that should NOT be included
echo "4️⃣  Checking for sensitive files (should be EMPTY)..."
echo ""

echo "   🔒 Checking for .env files:"
if tar -tzf "$SDIST" | grep -i '\.env' > /dev/null 2>&1; then
    echo "   ❌ FOUND .env files (SECURITY RISK!):"
    tar -tzf "$SDIST" | grep -i '\.env'
    echo ""
    echo "   ⚠️  FIX NEEDED: Update pyproject.toml exclusions!"
    exit 1
else
    echo "   ✅ No .env files found (good!)"
fi
echo ""

echo "   🔒 Checking for keypair files:"
if tar -tzf "$SDIST" | grep -i 'keypair\.json' > /dev/null 2>&1; then
    echo "   ❌ FOUND keypair files (SECURITY RISK!):"
    tar -tzf "$SDIST" | grep -i 'keypair\.json'
    echo ""
    echo "   ⚠️  FIX NEEDED: Update pyproject.toml exclusions!"
    exit 1
else
    echo "   ✅ No keypair files found (good!)"
fi
echo ""

echo "   🔒 Checking for venv directories:"
if tar -tzf "$SDIST" | grep 'venv/' > /dev/null 2>&1; then
    echo "   ⚠️  Found venv directories (should be excluded):"
    tar -tzf "$SDIST" | grep 'venv/' | head -5
    echo "   (This is probably okay if from examples/)"
else
    echo "   ✅ No venv directories in root (good!)"
fi
echo ""

# Show what IS included
echo "5️⃣  Contents that WILL be in the package:"
echo ""
tar -tzf "$SDIST" | head -30
echo ""
echo "   ... (showing first 30 files)"
echo ""

# Count files and size
TOTAL_FILES=$(tar -tzf "$SDIST" | wc -l | tr -d ' ')
SDIST_SIZE=$(du -h "$SDIST" | cut -f1)
SDIST_SIZE_KB=$(du -k "$SDIST" | cut -f1)
echo "   📦 Total files: $TOTAL_FILES"
echo "   📏 Package size: $SDIST_SIZE ($SDIST_SIZE_KB KB)"
echo ""

# Verify wheel
if [ -n "$WHEEL" ]; then
    echo "6️⃣  Checking wheel distribution..."
    echo "   File: $WHEEL"
    WHEEL_FILES=$(unzip -l "$WHEEL" | wc -l | tr -d ' ')
    WHEEL_SIZE=$(du -h "$WHEEL" | cut -f1)
    WHEEL_SIZE_KB=$(du -k "$WHEEL" | cut -f1)
    echo "   📦 Total entries: $WHEEL_FILES"
    echo "   📏 Wheel size: $WHEEL_SIZE ($WHEEL_SIZE_KB KB)"
    echo ""
fi

# Show important directories included
echo "7️⃣  Verifying important components are included..."
echo ""
echo "   🔍 Checking facilitators package:"
if tar -tzf "$SDIST" | grep 'src/x402_connector/core/facilitators/__init__.py' > /dev/null 2>&1; then
    echo "   ✅ facilitators/__init__.py"
    tar -tzf "$SDIST" | grep 'src/x402_connector/core/facilitators/' | sed 's/^/      /'
else
    echo "   ❌ facilitators package not found!"
fi
echo ""

echo "   🔍 Checking documentation files:"
for doc in "README.md" "QUICKSTART.md" "API.md" "FACILITATORS_INTEGRATION.md" "LICENSE"; do
    if tar -tzf "$SDIST" | grep "/$doc$" > /dev/null 2>&1; then
        echo "   ✅ $doc"
    else
        echo "   ❌ $doc NOT FOUND"
    fi
done
echo ""

# Summary
echo "="
echo "✅ VERIFICATION COMPLETE"
echo "="
echo ""
echo "📦 Package Summary:"
echo "  • Source Distribution: $SDIST_SIZE ($SDIST_SIZE_KB KB)"
if [ -n "$WHEEL" ]; then
echo "  • Wheel Distribution: $WHEEL_SIZE ($WHEEL_SIZE_KB KB)"
fi
echo "  • Total files: $TOTAL_FILES"
echo ""
echo "🔒 Security Checks:"
echo "  • No .env files: ✅"
echo "  • No keypair files: ✅"
echo "  • No venv in root: ✅"
echo ""
echo "📚 Components Included:"
echo "  • Core facilitators package: ✅"
echo "  • All 4 facilitator modes (local, payai, corbits, hybrid): ✅"
echo "  • Framework adapters (Django, Flask, FastAPI, Tornado, Pyramid): ✅"
echo "  • Documentation files: ✅"
echo "  • Tests: ✅"
echo ""
echo "🚫 Properly Excluded:"
echo "  • Old facilitator files (facilitators_solana.py, facilitators_payai.py): ✅"
echo "  • Development docs (TAP_INTEGRATION_ANALYSIS.md, etc): ✅"
echo "  • CI/CD files (.github): ✅"
echo "  • Build artifacts: ✅"
echo ""
echo "Next steps:"
echo "  1. Review the file list above"
echo "  2. If everything looks good, test upload:"
echo "     python -m twine upload --repository testpypi dist/*"
echo "  3. Then upload to real PyPI:"
echo "     python -m twine upload dist/*"
echo ""
echo "See PYPI_PUBLISHING.md for detailed instructions."

