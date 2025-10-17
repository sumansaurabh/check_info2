#!/bin/bash
# Integration Test Setup Verification Script

echo "========================================="
echo "FaceFusion Integration Tests - Setup Check"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SUCCESS=0

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python not found${NC}"
    SUCCESS=1
fi

# Check pytest
echo -n "Checking pytest... "
if command -v pytest &> /dev/null; then
    PYTEST_VERSION=$(pytest --version 2>&1 | head -n1 | awk '{print $2}')
    echo -e "${GREEN}✓ pytest $PYTEST_VERSION${NC}"
else
    echo -e "${RED}✗ pytest not found${NC}"
    echo "  Install: pip install pytest"
    SUCCESS=1
fi

# Check requests
echo -n "Checking requests library... "
if python3 -c "import requests" 2>/dev/null; then
    REQUESTS_VERSION=$(python3 -c "import requests; print(requests.__version__)")
    echo -e "${GREEN}✓ requests $REQUESTS_VERSION${NC}"
else
    echo -e "${RED}✗ requests not found${NC}"
    echo "  Install: pip install requests"
    SUCCESS=1
fi

# Check PIL/Pillow
echo -n "Checking Pillow library... "
if python3 -c "import PIL" 2>/dev/null; then
    PILLOW_VERSION=$(python3 -c "from PIL import Image; print(Image.__version__ if hasattr(Image, '__version__') else 'installed')")
    echo -e "${GREEN}✓ Pillow $PILLOW_VERSION${NC}"
else
    echo -e "${RED}✗ Pillow not found${NC}"
    echo "  Install: pip install Pillow"
    SUCCESS=1
fi

echo ""
echo "Checking test structure..."

# Check test files
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILES=(
    "conftest.py"
    "test_health.py"
    "test_image_processing.py"
    "test_video_processing.py"
    "test_jobs.py"
    "test_file_operations.py"
    "pytest.ini"
    "run_tests.sh"
)

for file in "${TEST_FILES[@]}"; do
    echo -n "  $file... "
    if [ -f "$TEST_DIR/$file" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        SUCCESS=1
    fi
done

# Check fixtures
echo ""
echo "Checking test fixtures..."
FIXTURES_DIR="$TEST_DIR/../fixtures"

echo -n "  source.jpg... "
if [ -f "$FIXTURES_DIR/source.jpg" ]; then
    SIZE=$(stat -f%z "$FIXTURES_DIR/source.jpg" 2>/dev/null || stat -c%s "$FIXTURES_DIR/source.jpg" 2>/dev/null)
    echo -e "${GREEN}✓ (${SIZE} bytes)${NC}"
else
    echo -e "${YELLOW}⚠ Missing (will use placeholder)${NC}"
fi

echo -n "  target.jpg... "
if [ -f "$FIXTURES_DIR/target.jpg" ]; then
    SIZE=$(stat -f%z "$FIXTURES_DIR/target.jpg" 2>/dev/null || stat -c%s "$FIXTURES_DIR/target.jpg" 2>/dev/null)
    echo -e "${GREEN}✓ (${SIZE} bytes)${NC}"
else
    echo -e "${YELLOW}⚠ Missing (will use placeholder)${NC}"
fi

echo -n "  target.mp4... "
if [ -f "$FIXTURES_DIR/target.mp4" ]; then
    SIZE=$(stat -f%z "$FIXTURES_DIR/target.mp4" 2>/dev/null || stat -c%s "$FIXTURES_DIR/target.mp4" 2>/dev/null)
    echo -e "${GREEN}✓ (${SIZE} bytes)${NC}"
else
    echo -e "${YELLOW}ℹ Optional (video tests will be skipped)${NC}"
fi

# Check API server
echo ""
echo "Checking API server..."
API_URL="${FACEFUSION_API_URL:-http://localhost:8000}"
echo -n "  Connecting to $API_URL... "

if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}⚠ Not running${NC}"
    echo "  Start with: python facefusion.py api"
fi

# Test collection
echo ""
echo "Checking pytest test collection..."
cd "$TEST_DIR"
COLLECTED=$(pytest --collect-only -q 2>/dev/null | grep "test" | wc -l | tr -d ' ')
if [ "$COLLECTED" -gt 0 ]; then
    echo -e "  ${GREEN}✓ $COLLECTED tests collected${NC}"
else
    echo -e "  ${RED}✗ No tests collected${NC}"
    SUCCESS=1
fi

echo ""
echo "========================================="
if [ $SUCCESS -eq 0 ]; then
    echo -e "${GREEN}✓ Setup complete! Ready to run tests.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Ensure API server is running"
    echo "  2. Replace placeholder images with real faces"
    echo "  3. Run: ./run_tests.sh"
else
    echo -e "${RED}✗ Setup incomplete. Please fix issues above.${NC}"
fi
echo "========================================="

exit $SUCCESS
