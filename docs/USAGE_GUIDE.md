# PyRestTest - Hướng Dẫn Sử Dụng Đa Năng

## 📖 Mục Lục

1. [Sử dụng qua CLI](#1-sử-dụng-qua-cli)
2. [Sử dụng qua Python Script](#2-sử-dụng-qua-python-script)
3. [Auto-configured Runner](#3-auto-configured-runner)
4. [Tích hợp vào CI/CD](#4-tích-hợp-vào-cicd)
5. [Best Practices](#5-best-practices)

---

## 1. Sử dụng qua CLI

### 1.1. Basic Usage

```bash
# Test đơn giản
pyresttest http://api.example.com tests/smoke.yaml

# Với retry
pyresttest http://api.example.com tests/api.yaml --max-retries 3

# Với concurrency limit
pyresttest http://api.example.com tests/load.yaml --max-concurrency 10

# Kết hợp tất cả
pyresttest http://api.example.com tests/full.yaml \
    --max-retries 3 \
    --retry-backoff-base 0.5 \
    --retry-backoff-max 30 \
    --max-concurrency 20 \
    --log info
```

### 1.2. CLI Options Summary

```bash
# URL và test file
pyresttest <base_url> <test_file.yaml>

# Retry options
--max-retries <num>              # Số lần retry tối đa (default: 0)
--retry-backoff-base <seconds>   # Delay base cho backoff (default: 0.5)
--retry-backoff-max <seconds>    # Max delay giữa retries (default: 30)

# Concurrency
--max-concurrency <num>          # Max concurrent requests

# Output
--log <level>                    # debug, info, warning, error, critical
--print-bodies                   # In response bodies
--print-headers                  # In response headers

# Other
--interactive                    # Interactive mode
--absolute-urls                  # Sử dụng absolute URLs
```

### 1.3. YAML Test File Format

```yaml
---
# Test configuration
- config:
    - testset: "My Test Suite"
    - timeout: 30

# Simple test
- test:
    - name: "GET request"
    - url: "/api/users"
    - method: "GET"
    - expected_status: [200]

# Test with headers and body
- test:
    - name: "POST request"
    - url: "/api/users"
    - method: "POST"
    - headers:
        Content-Type: "application/json"
    - body: '{"name": "John", "email": "john@example.com"}'
    - expected_status: [201]

# Performance test
- test:
    - name: "Load test"
    - url: "/api/search"
    - method: "GET"
    - expected_status: [200]
    - performance:
        repeat: 100
        concurrency: 10
        mode: "sync"
        threshold_ms: 500
```

---

## 2. Sử dụng qua Python Script

### 2.1. Programmatic Usage

Xem file: `examples/programmatic_usage.py`

**Chạy examples:**

```bash
cd examples
python programmatic_usage.py
```

**8 ví dụ có sẵn:**

1. Simple Test - Test cơ bản từ code
2. Test with Retry - Test với retry config
3. Run from YAML - Load và chạy từ YAML
4. Performance Test - Performance với concurrency
5. Custom Config - Config từ dictionary
6. Advanced Usage - Với validators
7. Load Config from File - Từ JSON/YAML
8. CLI Equivalent - Code tương đương CLI

### 2.2. Code Examples

#### Example 1: Simple Test

```python
from pyresttest import resttest
from pyresttest.tests import Test
from pyresttest.binding import Context

# Tạo test
test = Test()
test.name = "My Test"
test.url = "https://api.example.com/users"
test.method = "GET"
test.expected_status = [200]

# Chạy test
context = Context()
test_config = resttest.TestConfig()
result = resttest.run_test(test, test_config=test_config, context=context)

print(f"Passed: {result.passed}")
print(f"Status: {result.response_code}")
```

#### Example 2: Test with Retry

```python
from pyresttest.retry import RetryConfig

# Tạo retry config
retry_config = RetryConfig(
    max_retries=3,
    backoff_base=0.5,
    backoff_max=30.0
)

# Chạy với retry
result = resttest.run_test(
    test,
    test_config=test_config,
    context=context,
    retry_config=retry_config
)
```

#### Example 3: Performance Test

```python
# Config performance
test.performance = {
    'repeat': 100,
    'concurrency': 10,
    'mode': 'sync',
    'threshold_ms': 500
}

# Chạy
result = resttest.run_test(
    test,
    test_config=test_config,
    context=context,
    retry_config=retry_config,
    max_concurrency=10
)
```

#### Example 4: Load from YAML

```python
# Đọc YAML
test_structure = resttest.read_test_file('tests.yaml')
base_url = "https://api.example.com"

# Parse tests
tests = resttest.parse_testsets(
    base_url,
    test_structure,
    working_directory='.'
)

# Chạy tất cả
failures = resttest.run_testsets(
    tests,
    retry_config=retry_config,
    max_concurrency=10
)
```

---

## 3. Auto-configured Runner

### 3.1. Giới thiệu

File: `examples/auto_runner.py` - Tự động đọc config và chạy tests

**Features:**

- ✅ Load config từ JSON
- ✅ Multiple environments (dev, staging, prod)
- ✅ Auto retry & concurrency
- ✅ Test suites management
- ✅ Results export to JSON
- ✅ Beautiful console output

### 3.2. Config File

Xem: `examples/test_config.json`

**Cấu trúc:**

```json
{
  "project_name": "My API Tests",
  "global_settings": {
    "base_url": "https://api.example.com",
    "retry": {
      "max_retries": 3,
      "backoff_base": 0.5
    },
    "concurrency": {
      "max_concurrent": 10
    }
  },
  "environments": {
    "development": { "base_url": "http://localhost:8000" },
    "production": { "base_url": "https://api.example.com" }
  },
  "test_suites": [
    {
      "name": "Smoke Tests",
      "tests": [
        {
          "name": "Health Check",
          "path": "/health",
          "method": "GET",
          "expected_status": [200]
        }
      ]
    }
  ]
}
```

### 3.3. Cách sử dụng

```bash
cd examples

# Run với development environment (default)
python auto_runner.py --config test_config.json

# Run với production environment
python auto_runner.py --config test_config.json --env production

# Run specific test suite
python auto_runner.py --config test_config.json --suite "Smoke Tests"

# Show help
python auto_runner.py --help
```

### 3.4. Output

```
============================================================
🚀 My API Testing Project
   Environment: production
   Base URL: https://api.example.com
============================================================

⚙️  Configuration:
   Retry: 3 attempts
   Backoff: 0.5s base, 30.0s max
   Concurrency: 10

============================================================
📦 Test Suite: Smoke Tests
   Basic health checks
============================================================

🧪 Running: Health Check
   GET https://api.example.com/health
   ✅ PASSED (Status: 200)

============================================================
📊 Test Summary
============================================================
Total Tests: 10
✅ Passed: 10
❌ Failed: 0
⏱️  Duration: 3.45s
📅 Completed: 2025-12-10 15:30:00
============================================================

💾 Results saved to: ./test-results/results.json
```

---

## 4. Tích hợp vào CI/CD

### 4.1. GitHub Actions

```yaml
# .github/workflows/api-tests.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.9"

      - name: Install dependencies
        run: |
          pip install pycurl pyyaml requests
          pip install aiohttp  # For async mode

      - name: Run API tests
        run: |
          cd examples
          python auto_runner.py \
            --config test_config.json \
            --env staging

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: examples/test-results/
```

### 4.2. GitLab CI

```yaml
# .gitlab-ci.yml
api-tests:
  stage: test
  image: python:3.9

  before_script:
    - pip install pycurl pyyaml requests aiohttp

  script:
    - cd examples
    - python auto_runner.py --config test_config.json --env staging

  artifacts:
    when: always
    paths:
      - examples/test-results/
    reports:
      junit: examples/test-results/results.json
```

### 4.3. Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'pip install pycurl pyyaml requests aiohttp'
            }
        }

        stage('API Tests') {
            steps {
                dir('examples') {
                    sh '''
                        python auto_runner.py \
                            --config test_config.json \
                            --env ${ENVIRONMENT}
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'examples/test-results/**/*'
        }
    }
}
```

### 4.4. Docker

```dockerfile
# Dockerfile.tests
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y python3-pycurl && \
    pip install pyyaml requests aiohttp

# Copy project
COPY . .

# Run tests
CMD ["python", "examples/auto_runner.py", \
     "--config", "examples/test_config.json", \
     "--env", "production"]
```

**Build và chạy:**

```bash
# Build image
docker build -f Dockerfile.tests -t my-api-tests .

# Run tests
docker run --rm my-api-tests

# Run với custom environment
docker run --rm -e ENV=staging my-api-tests \
    python examples/auto_runner.py \
    --config examples/test_config.json \
    --env staging
```

---

## 5. Best Practices

### 5.1. Project Structure

```
my-project/
├── tests/
│   ├── smoke/
│   │   ├── health.yaml
│   │   └── version.yaml
│   ├── api/
│   │   ├── users.yaml
│   │   └── products.yaml
│   └── performance/
│       └── load.yaml
├── config/
│   ├── dev.json
│   ├── staging.json
│   └── prod.json
├── scripts/
│   ├── run_tests.py
│   └── generate_report.py
└── results/
    └── .gitkeep
```

### 5.2. Naming Conventions

```yaml
# Good
- test:
    - name: "GET /users - List all users"
    - name: "POST /users - Create new user"
    - name: "PUT /users/:id - Update user"

# Bad
- test:
    - name: "test1"
    - name: "another test"
```

### 5.3. Test Organization

```json
{
  "test_suites": [
    {
      "name": "Smoke Tests",
      "enabled": true,
      "tests": [
        /* critical tests */
      ]
    },
    {
      "name": "Regression Tests",
      "enabled": true,
      "tests": [
        /* all features */
      ]
    },
    {
      "name": "Performance Tests",
      "enabled": false, // Run manually
      "tests": [
        /* load tests */
      ]
    }
  ]
}
```

### 5.4. Environment Configuration

```json
{
  "environments": {
    "development": {
      "base_url": "http://localhost:8000",
      "retry": { "max_retries": 1 },
      "concurrency": { "max_concurrent": 5 }
    },
    "staging": {
      "base_url": "https://staging.api.example.com",
      "retry": { "max_retries": 2 },
      "concurrency": { "max_concurrent": 10 }
    },
    "production": {
      "base_url": "https://api.example.com",
      "retry": { "max_retries": 3 },
      "concurrency": { "max_concurrent": 20 }
    }
  }
}
```

### 5.5. Retry Strategy

```python
# Development: Fast fail
RetryConfig(max_retries=1, backoff_base=0.1)

# Staging: Moderate
RetryConfig(max_retries=2, backoff_base=0.5)

# Production: Resilient
RetryConfig(max_retries=3, backoff_base=1.0, backoff_max=60)

# Load Testing: Minimal retry
RetryConfig(max_retries=1, backoff_base=0.2)
```

### 5.6. Concurrency Guidelines

```python
# Development: Low concurrency
max_concurrency = 5

# Staging: Medium
max_concurrency = 10

# Production Smoke Tests: Low (don't overload)
max_concurrency = 5

# Load Testing: High
max_concurrency = 50-100

# Stress Testing: Very high (with rate limiting)
max_concurrency = 100-500
```

---

## 6. Troubleshooting

### 6.1. Common Issues

**Issue: Import errors**

```bash
# Solution: Ensure pyresttest is in PYTHONPATH
export PYTHONPATH=/path/to/pyresttest:$PYTHONPATH
python auto_runner.py --config test_config.json
```

**Issue: aiohttp not found (async mode)**

```bash
# Solution: Install aiohttp
pip install aiohttp
```

**Issue: Too many retries**

```json
// Reduce retry attempts in config
"retry": {
  "max_retries": 1,
  "backoff_base": 0.2
}
```

### 6.2. Debug Mode

```bash
# Enable debug logging
python auto_runner.py --config test_config.json --env dev

# Or in config:
{
  "global_settings": {
    "logging": {
      "level": "debug",
      "print_bodies": true,
      "print_headers": true
    }
  }
}
```

---

## 7. Examples Summary

| Use Case        | Method    | Command/File                               |
| --------------- | --------- | ------------------------------------------ |
| Quick CLI test  | CLI       | `pyresttest http://api.com test.yaml`      |
| With retry      | CLI       | `pyresttest ... --max-retries 3`           |
| Programmatic    | Python    | `programmatic_usage.py`                    |
| Auto-configured | Script    | `auto_runner.py --config test_config.json` |
| CI/CD           | Pipeline  | GitHub Actions / GitLab CI                 |
| Docker          | Container | `docker run my-api-tests`                  |

---

## 8. Resources

- **Main Docs**: `docs/retry_and_concurrency.md`
- **Examples**: `examples/` folder
- **Tests**: `pyresttest/test_*.py`
- **Changelog**: `CHANGELOG_RETRY_CONCURRENCY.md`

Happy Testing! 🚀
