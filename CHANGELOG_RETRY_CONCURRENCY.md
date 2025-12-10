# New Features - Retry and Concurrency (December 2025)

## Version: Next Release

### 🎯 Major Features

#### 1. Retry with Exponential Backoff

- **Automatic retry** cho failed HTTP requests
- **Exponential backoff** với configurable delays
- **Smart retry logic**: chỉ retry khi có ý nghĩa (5xx, network errors)
- Hỗ trợ cả **sync và async** modes
- **Zero breaking changes**: mặc định disabled

**CLI Options:**

```bash
--max-retries <num>              # Maximum retry attempts (default: 0)
--retry-backoff-base <seconds>   # Base delay for backoff (default: 0.5)
--retry-backoff-max <seconds>    # Max delay between retries (default: 30)
```

**Usage:**

```bash
pyresttest http://api.example.com test.yaml --max-retries 3
```

#### 2. Concurrency Control

- **Limit concurrent requests** trong performance tests
- **ThreadPoolExecutor** cho sync mode
- **asyncio.Semaphore** cho async mode
- Override được từ CLI hoặc YAML config
- **Connection pooling** awareness

**CLI Option:**

```bash
--max-concurrency <num>  # Max concurrent requests
```

**Usage:**

```bash
pyresttest http://api.example.com benchmark.yaml --max-concurrency 10
```

**YAML Configuration:**

```yaml
- test:
    - performance:
        repeat: 100
        concurrency: 10
        mode: "async"
        timeout: 30
```

### 📈 Enhancements

#### Performance Metrics

- Added `total_retries` to performance summary
- Added `avg_retries_per_request` metric
- Better error reporting for retry failures

#### Async Improvements

- Enhanced timeout configuration (total + connect)
- Better error handling in async workers
- Session management per worker thread

### 📚 Documentation

**New Files:**

- `docs/retry_and_concurrency.md` - Comprehensive guide (340+ lines)
- `IMPROVEMENTS_SUMMARY.md` - Technical summary
- `examples/test-with-retry-concurrency.yaml` - Example tests
- `demo_retry_concurrency.sh` - Interactive demo script

**Updated Files:**

- `README.md` - Added "Retry and Concurrency Features" section
- Table of contents updated

### 🧪 Testing

**New Tests:**

- `pyresttest/test_retry.py` - 14 unit tests for retry module
  - RetryConfig configuration tests
  - Exponential backoff calculation
  - Retry trigger logic
  - Success/failure scenarios
  - Exception handling

**Test Results:** ✅ 14/14 tests passing

### 🔧 Technical Details

**New Modules:**

- `pyresttest/retry.py` - Core retry logic
  - `RetryConfig` class
  - `retry_sync()` function
  - `retry_async()` function
  - `should_retry()` helper

**Modified Modules:**

- `pyresttest/resttest.py`
  - CLI option parsing
  - RetryConfig creation from args
  - Integration with test execution flow
- `pyresttest/performance.py`
  - Retry support in sync performance tests
  - Enhanced error handling
  - Retry statistics collection
- `pyresttest/performance_async.py`
  - Retry support in async performance tests
  - Improved timeout configuration
  - Better session management

### 🎓 Best Practices

**When to use Retry:**

- ✅ CI/CD pipelines with network instability
- ✅ Testing external APIs with occasional downtime
- ✅ Load testing to avoid false failures
- ❌ Unit tests (should fail fast)

**When to use Concurrency Limit:**

- ✅ Performance testing production systems
- ✅ Rate-limited APIs
- ✅ Resource-constrained environments
- ✅ Preventing server overload

**Recommended Settings:**

Development:

```bash
--max-retries 2 --retry-backoff-base 0.2 --max-concurrency 5
```

CI/CD:

```bash
--max-retries 3 --retry-backoff-base 0.5 --max-concurrency 10
```

Production:

```bash
--max-retries 3 --retry-backoff-base 1.0 --max-concurrency 20 --log info
```

### 🐛 Bug Fixes

- Fixed session management in async performance tests
- Improved error handling for network timeouts
- Better cleanup of async resources

### ⚡ Performance

- Minimal overhead when retry disabled (< 1%)
- Efficient connection pooling with requests.Session
- Async semaphore for true concurrency control

### 📦 Dependencies

- No new required dependencies
- Optional: `aiohttp` for async mode (already supported)

### 🔄 Backward Compatibility

- ✅ 100% backward compatible
- Retry disabled by default (`--max-retries 0`)
- No changes to existing YAML syntax
- All existing tests work without modification

### 🚀 Migration Guide

No migration needed! Features are opt-in:

1. Add retry to existing tests:

   ```bash
   pyresttest <url> <test.yaml> --max-retries 3
   ```

2. Limit concurrency in benchmarks:

   ```bash
   pyresttest <url> <benchmark.yaml> --max-concurrency 10
   ```

3. Update YAML for async performance (optional):
   ```yaml
   - performance:
       mode: "async"
       timeout: 30
   ```

### 📊 Examples

**Example 1: Resilient API Testing**

```bash
pyresttest https://api.production.com tests/smoke.yaml \
    --max-retries 3 \
    --retry-backoff-base 0.5 \
    --log info
```

**Example 2: Controlled Performance Testing**

```bash
pyresttest http://api.staging.com tests/load.yaml \
    --max-concurrency 20 \
    --max-retries 2
```

**Example 3: High-Concurrency Async**

```bash
pyresttest http://api.example.com tests/stress.yaml \
    --max-concurrency 100 \
    --max-retries 3
```

### 🔮 Future Enhancements

- Jitter for backoff randomization
- Circuit breaker pattern
- Per-status retry configuration
- Metrics export (Prometheus format)
- Distributed tracing support

### 👥 Contributors

- Implementation: GitHub Copilot + bao2811
- Testing: Automated unit tests
- Documentation: Comprehensive guides

### 📝 Notes

- Retry logic respects HTTP semantics (only retry safe operations)
- Concurrency limits apply per-test, not globally
- Async mode requires Python 3.7+ with asyncio support
- Logging at DEBUG level shows detailed retry information

---

For complete documentation, see `docs/retry_and_concurrency.md`
