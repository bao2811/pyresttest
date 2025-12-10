# PyRestTest Examples

Thư mục này chứa các ví dụ về cách sử dụng PyRestTest theo nhiều cách khác nhau.

## 📁 Files

### 1. Test Files (YAML)

| File                               | Mô tả                    | Sử dụng      |
| ---------------------------------- | ------------------------ | ------------ |
| `github_api_test.yaml`             | Test GitHub API          | CLI basic    |
| `github_api_smoketest.yaml`        | GitHub smoke test        | CI/CD        |
| `miniapp-test.yaml`                | Test ứng dụng mẫu        | Local dev    |
| `miniapp-benchmark.yaml`           | Performance test         | Load testing |
| `test-with-retry-concurrency.yaml` | Demo retry & concurrency | Learning     |

### 2. Python Scripts

| File                    | Mô tả                  | Cách chạy                                         |
| ----------------------- | ---------------------- | ------------------------------------------------- |
| `auto_runner.py` ⭐     | Auto-configured runner | `python auto_runner.py --config test_config.json` |
| `programmatic_usage.py` | 8 ví dụ programmatic   | `python programmatic_usage.py`                    |

### 3. Configuration Files

| File               | Mô tả                       |
| ------------------ | --------------------------- |
| `test_config.json` | JSON config cho auto_runner |

## 🚀 Quick Start

### Cách 1: CLI (Đơn giản nhất)

```bash
# Test cơ bản
pyresttest https://api.github.com github_api_smoketest.yaml

# Với retry
pyresttest https://api.github.com github_api_test.yaml --max-retries 3

# Với concurrency
pyresttest http://localhost:8000 miniapp-benchmark.yaml --max-concurrency 10
```

### Cách 2: Auto Runner (Khuyến nghị)

```bash
# Default environment (development)
python auto_runner.py --config test_config.json

# Production environment
python auto_runner.py --config test_config.json --env production

# Specific test suite
python auto_runner.py --config test_config.json --suite "Smoke Tests"
```

### Cách 3: Programmatic (Tùy biến cao)

```bash
# Interactive examples
python programmatic_usage.py

# Chọn example cụ thể
python programmatic_usage.py
# Chọn số 1-8
```

## 📖 Chi tiết từng ví dụ

### auto_runner.py ⭐

**Tự động runner với JSON config**

Features:

- ✅ Multi-environment support
- ✅ Auto retry & concurrency
- ✅ Test suites management
- ✅ JSON results export
- ✅ Beautiful console output

**Usage:**

```bash
python auto_runner.py --help

python auto_runner.py \
    --config test_config.json \
    --env production \
    --suite "Smoke Tests"
```

**Config structure:**

```json
{
  "project_name": "My Tests",
  "environments": {
    "dev": { "base_url": "http://localhost:8000" },
    "prod": { "base_url": "https://api.example.com" }
  },
  "test_suites": [
    {
      "name": "Suite 1",
      "tests": [
        /* ... */
      ]
    }
  ]
}
```

### programmatic_usage.py

**8 ví dụ code Python**

1. **Simple Test** - Test cơ bản từ code
2. **Test with Retry** - Thêm retry config
3. **Run from YAML** - Load tests từ YAML
4. **Performance Test** - Performance với concurrency
5. **Custom Config** - Config từ dictionary
6. **Advanced Usage** - Validators và extractors
7. **Load Config from File** - Từ JSON/YAML
8. **CLI Equivalent** - Code tương đương CLI

**Usage:**

```bash
python programmatic_usage.py
# Chọn 'y' để chạy tất cả hoặc chọn số 1-8
```

### test_config.json

**Sample configuration file**

Chứa:

- Project settings
- Environments (dev/staging/prod)
- Global retry & concurrency config
- Test suites definition
- Reporting config

**Customize:**

1. Copy file: `cp test_config.json my_config.json`
2. Edit với project của bạn
3. Run: `python auto_runner.py --config my_config.json`

## 🎯 Use Cases

### Use Case 1: CI/CD Pipeline

```bash
# GitHub Actions / GitLab CI
python auto_runner.py \
    --config ci_tests.json \
    --env staging
```

### Use Case 2: Local Development

```bash
# Quick smoke test
pyresttest http://localhost:8000 miniapp-test.yaml

# Full test với retry
python auto_runner.py --config test_config.json --env development
```

### Use Case 3: Load Testing

```bash
# Performance benchmark
pyresttest http://api.example.com miniapp-benchmark.yaml \
    --max-concurrency 50 \
    --max-retries 2
```

### Use Case 4: Production Monitoring

```bash
# Scheduled health checks
python auto_runner.py \
    --config prod_health.json \
    --env production \
    --suite "Health Checks"
```

## 🔧 Customization

### Tạo test YAML mới

```yaml
---
- config:
    - testset: "Your Test Suite"

- test:
    - name: "Your test name"
    - url: "/api/endpoint"
    - method: "GET"
    - expected_status: [200]
    - performance:
        repeat: 100
        concurrency: 10
```

### Tạo config JSON mới

```json
{
  "project_name": "Your Project",
  "global_settings": {
    "base_url": "https://your-api.com",
    "retry": {
      "max_retries": 3,
      "backoff_base": 0.5
    }
  },
  "test_suites": [
    {
      "name": "Your Suite",
      "tests": [
        /* ... */
      ]
    }
  ]
}
```

### Extend auto_runner.py

```python
# Add custom validators
class MyValidator:
    def validate(self, response, context):
        # Your validation logic
        return True

# Add custom hooks
def before_test(test):
    print(f"Running: {test.name}")

# Integrate vào runner
runner = ConfiguredTestRunner('config.json', 'prod')
runner.add_validator(MyValidator())
runner.add_hook('before_each', before_test)
runner.run_all()
```

## 📚 Tài liệu

- **Usage Guide**: `../docs/USAGE_GUIDE.md` - Hướng dẫn đầy đủ
- **Retry & Concurrency**: `../docs/retry_and_concurrency.md` - Chi tiết features
- **Main README**: `../README.md` - Overview

## 💡 Tips

1. **Start simple**: Dùng CLI trước
2. **Scale up**: Chuyển sang auto_runner khi cần automation
3. **Customize**: Extend programmatic_usage.py cho needs riêng
4. **Environment**: Luôn tách config cho dev/staging/prod
5. **CI/CD**: Sử dụng auto_runner trong pipelines

## 🐛 Troubleshooting

**Import errors:**

```bash
export PYTHONPATH=/path/to/pyresttest:$PYTHONPATH
```

**Test app not running:**

```bash
cd ../pyresttest/testapp
python manage.py runserver
```

**Missing dependencies:**

```bash
pip install pycurl pyyaml requests aiohttp
```

## 🤝 Contributing

Muốn thêm examples?

1. Create new .yaml hoặc .py file
2. Add documentation ở đây
3. Test thoroughly
4. Submit PR

---

Happy Testing! 🚀
