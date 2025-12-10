#!/bin/bash

# Demo script for PyRestTest retry and concurrency features
# This script demonstrates various usage patterns

set -e

echo "========================================="
echo "PyRestTest - Retry & Concurrency Demo"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pyresttest is available
if ! command -v python &> /dev/null; then
    echo "Error: Python not found"
    exit 1
fi

echo -e "${BLUE}Prerequisites check...${NC}"
echo "Python version: $(python --version)"
echo ""

# Demo 1: Basic retry
echo -e "${GREEN}=== Demo 1: Basic Retry ===${NC}"
echo "Command: pyresttest https://httpbin.org examples/github_api_smoketest.yaml --max-retries 2"
echo ""
echo "This will retry failed requests up to 2 times with exponential backoff."
echo "Press Enter to continue (or Ctrl+C to skip)..."
read -r

python pyresttest/resttest.py https://httpbin.org examples/github_api_smoketest.yaml --max-retries 2 --log info || true

echo ""
echo -e "${YELLOW}Demo 1 completed. Note the retry behavior in the logs.${NC}"
echo ""
read -p "Press Enter to continue..."

# Demo 2: Custom backoff
echo ""
echo -e "${GREEN}=== Demo 2: Custom Backoff Timing ===${NC}"
echo "Command: pyresttest https://httpbin.org examples/github_api_smoketest.yaml \\"
echo "    --max-retries 3 --retry-backoff-base 1.0 --retry-backoff-max 10"
echo ""
echo "This uses longer backoff delays: 1s, 2s, 4s, 8s, 10s (max)"
echo "Press Enter to continue (or Ctrl+C to skip)..."
read -r

python pyresttest/resttest.py https://httpbin.org examples/github_api_smoketest.yaml \
    --max-retries 3 --retry-backoff-base 1.0 --retry-backoff-max 10 --log info || true

echo ""
echo -e "${YELLOW}Demo 2 completed. Notice the longer delays between retries.${NC}"
echo ""
read -p "Press Enter to continue..."

# Demo 3: Performance with concurrency limit
echo ""
echo -e "${GREEN}=== Demo 3: Concurrency Control ===${NC}"
echo "This demo requires the test app to be running."
echo "Start the test app in another terminal with:"
echo "  cd pyresttest/testapp"
echo "  python manage.py runserver"
echo ""
echo "Command: pyresttest http://localhost:8000 examples/miniapp-benchmark.yaml \\"
echo "    --max-concurrency 5"
echo ""
echo "This limits concurrent requests to 5, preventing server overload."
read -p "Press Enter to run (or Ctrl+C to skip if app not running)..."

python pyresttest/resttest.py http://localhost:8000 examples/miniapp-benchmark.yaml \
    --max-concurrency 5 --log info || echo "Skipped (test app not running)"

echo ""
echo -e "${YELLOW}Demo 3 completed. Check the concurrency in performance summary.${NC}"
echo ""
read -p "Press Enter to continue..."

# Demo 4: Combined retry + concurrency
echo ""
echo -e "${GREEN}=== Demo 4: Combined Retry + Concurrency ===${NC}"
echo "Command: pyresttest http://localhost:8000 examples/miniapp-benchmark.yaml \\"
echo "    --max-concurrency 10 --max-retries 2 --log info"
echo ""
echo "This combines both features for resilient performance testing."
read -p "Press Enter to run (or Ctrl+C to skip if app not running)..."

python pyresttest/resttest.py http://localhost:8000 examples/miniapp-benchmark.yaml \
    --max-concurrency 10 --max-retries 2 --log info || echo "Skipped (test app not running)"

echo ""
echo -e "${YELLOW}Demo 4 completed. Notice retry statistics in summary.${NC}"
echo ""

# Summary
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Demo Summary${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "You've seen:"
echo "1. ✓ Basic retry with default settings"
echo "2. ✓ Custom backoff timing configuration"
echo "3. ✓ Concurrency limiting for performance tests"
echo "4. ✓ Combined retry + concurrency for resilient testing"
echo ""
echo "CLI Options Summary:"
echo "  --max-retries <num>              Maximum retry attempts (default: 0)"
echo "  --retry-backoff-base <seconds>   Base delay for backoff (default: 0.5)"
echo "  --retry-backoff-max <seconds>    Max delay between retries (default: 30)"
echo "  --max-concurrency <num>          Max concurrent requests"
echo ""
echo "For more details, see:"
echo "  - docs/retry_and_concurrency.md"
echo "  - IMPROVEMENTS_SUMMARY.md"
echo "  - examples/test-with-retry-concurrency.yaml"
echo ""
echo -e "${GREEN}Demo completed!${NC}"
