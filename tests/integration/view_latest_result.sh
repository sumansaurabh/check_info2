#!/bin/bash
# Quick script to view the latest generated test image

TEST_OUTPUTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/test_outputs"

if [ ! -d "$TEST_OUTPUTS" ]; then
    echo "❌ No test_outputs directory found"
    echo "   Run tests first: ./run_tests.sh --image"
    exit 1
fi

IMAGE_COUNT=$(find "$TEST_OUTPUTS" -name "*.jpg" -o -name "*.png" 2>/dev/null | wc -l | tr -d ' ')

if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo "❌ No images found in $TEST_OUTPUTS"
    echo "   Run tests to generate images: ./run_tests.sh --image"
    exit 1
fi

echo "🖼️  Found $IMAGE_COUNT image(s) in test outputs"
echo ""

# List all images with details
ls -lht "$TEST_OUTPUTS"/*.{jpg,png} 2>/dev/null | head -10

echo ""
echo "Opening latest image..."

# Find and open the most recent image
LATEST_IMAGE=$(ls -t "$TEST_OUTPUTS"/*.{jpg,png} 2>/dev/null | head -1)

if [ -n "$LATEST_IMAGE" ]; then
    echo "📂 $LATEST_IMAGE"

    # Open based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$LATEST_IMAGE"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$LATEST_IMAGE" 2>/dev/null || echo "   Please open manually: $LATEST_IMAGE"
    else
        echo "   Please open manually: $LATEST_IMAGE"
    fi
else
    echo "❌ Could not find latest image"
fi
