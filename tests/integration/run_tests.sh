#!/bin/bash
# Quick test runner for FaceFusion API integration tests
# Usage: ./run_tests.sh [options]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${FACEFUSION_API_URL:-http://129.146.117.178:8000}"
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="${TEST_DIR}/../fixtures"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}FaceFusion API Integration Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found${NC}"
    echo -e "  Install: ${YELLOW}pip install pytest requests pillow${NC}"
    exit 1
fi

echo -e "${GREEN}✓ pytest found${NC}"

# Check if API server is running
echo -e "\n${BLUE}Checking API server...${NC}"
if curl -s "${API_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API server is running at ${API_URL}${NC}"
else
    echo -e "${RED}✗ API server not reachable at ${API_URL}${NC}"
    echo -e "  Start server: ${YELLOW}python facefusion.py api${NC}"
    exit 1
fi

# Check test fixtures
echo -e "\n${BLUE}Checking test fixtures...${NC}"
MISSING_FIXTURES=()

if [ ! -f "${FIXTURES_DIR}/source.jpg" ]; then
    MISSING_FIXTURES+=("source.jpg")
fi

if [ ! -f "${FIXTURES_DIR}/target.jpg" ]; then
    MISSING_FIXTURES+=("target.jpg")
fi

if [ ${#MISSING_FIXTURES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠ Missing fixtures:${NC}"
    for fixture in "${MISSING_FIXTURES[@]}"; do
        echo -e "    ${fixture}"
    done
    echo -e "  Add to: ${YELLOW}${FIXTURES_DIR}/${NC}"
    echo -e "  Tests requiring fixtures will be skipped"
else
    echo -e "${GREEN}✓ All required fixtures present${NC}"
fi

if [ ! -f "${FIXTURES_DIR}/target.mp4" ]; then
    echo -e "${YELLOW}ℹ Video fixture not found (video tests will be skipped)${NC}"
fi

# Parse command line arguments
TEST_ARGS=()
RUN_MODE="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            RUN_MODE="fast"
            shift
            ;;
        --slow)
            RUN_MODE="slow"
            shift
            ;;
        --smoke)
            RUN_MODE="smoke"
            shift
            ;;
        --health)
            RUN_MODE="health"
            shift
            ;;
        --image)
            RUN_MODE="image"
            shift
            ;;
        --video)
            RUN_MODE="video"
            shift
            ;;
        --jobs)
            RUN_MODE="jobs"
            shift
            ;;
        --files)
            RUN_MODE="files"
            shift
            ;;
        -v|--verbose)
            TEST_ARGS+=("-s")
            shift
            ;;
        -h|--help)
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --fast        Run only fast tests"
            echo "  --slow        Run only slow tests"
            echo "  --smoke       Run smoke tests only"
            echo "  --health      Run health endpoint tests only"
            echo "  --image       Run image processing tests only"
            echo "  --video       Run video processing tests only"
            echo "  --jobs        Run job management tests only"
            echo "  --files       Run file operations tests only"
            echo "  -v, --verbose Enable verbose output"
            echo "  -h, --help    Show this help message"
            echo ""
            echo "Environment:"
            echo "  FACEFUSION_API_URL  API server URL (default: http://localhost:8000)"
            echo ""
            exit 0
            ;;
        *)
            TEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Determine which tests to run
echo -e "\n${BLUE}Running tests...${NC}"
case $RUN_MODE in
    fast)
        echo -e "Mode: ${GREEN}Fast tests only${NC}"
        TEST_ARGS+=("-m" "fast")
        ;;
    slow)
        echo -e "Mode: ${YELLOW}Slow tests only${NC}"
        TEST_ARGS+=("-m" "slow")
        ;;
    smoke)
        echo -e "Mode: ${GREEN}Smoke tests${NC}"
        TEST_ARGS+=("-m" "smoke")
        ;;
    health)
        echo -e "Mode: ${GREEN}Health endpoint tests${NC}"
        TEST_ARGS+=("test_health.py")
        ;;
    image)
        echo -e "Mode: ${GREEN}Image processing tests${NC}"
        TEST_ARGS+=("test_image_processing.py")
        ;;
    video)
        echo -e "Mode: ${YELLOW}Video processing tests${NC}"
        TEST_ARGS+=("test_video_processing.py")
        ;;
    jobs)
        echo -e "Mode: ${GREEN}Job management tests${NC}"
        TEST_ARGS+=("test_jobs.py")
        ;;
    files)
        echo -e "Mode: ${GREEN}File operations tests${NC}"
        TEST_ARGS+=("test_file_operations.py")
        ;;
    all)
        echo -e "Mode: ${BLUE}All tests${NC}"
        ;;
esac

echo ""

# Run pytest
cd "${TEST_DIR}"
pytest "${TEST_ARGS[@]}"

EXIT_CODE=$?

# Summary
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${RED}========================================${NC}"
fi

exit $EXIT_CODE
