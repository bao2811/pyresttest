# Retry and Concurrency Features

PyRestTest now supports advanced retry logic with exponential backoff and configurable concurrency limits for performance testing.

## Retry with Exponential Backoff

### Overview

The retry feature automatically retries failed HTTP requests with exponential backoff, making your tests more resilient to transient network failures and temporary server issues.

### CLI Options

- `--max-retries <number>`: Maximum number of retry attempts (default: 0, disabled)
- `--retry-backoff-base <seconds>`: Base delay in seconds for exponential backoff (default: 0.5)
- `--retry-backoff-max <seconds>`: Maximum delay in seconds between retries (default: 30)

### Example Usage

```bash
# Basic retry: retry up to 3 times with default backoff
python pyresttest/resttest.py http://localhost:8000 examples/miniapp-test.yaml --max-retries 3

# Custom backoff: 1 second base, max 60 seconds
python pyresttest/resttest.py http://localhost:8000 examples/miniapp-test.yaml \
    --max-retries 5 \
    --retry-backoff-base 1.0 \
    --retry-backoff-max 60.0
```

### Retry Behavior

By default, retries are triggered for:

- HTTP status codes: 500, 502, 503, 504 (server errors)
- Network exceptions: ConnectionError, TimeoutError

**Exponential Backoff Formula:**

```
delay = min(backoff_base * (2 ^ attempt), backoff_max)
```

**Example backoff sequence** (base=0.5s, max=30s):

- Attempt 0: 0.5s
- Attempt 1: 1.0s
- Attempt 2: 2.0s
- Attempt 3: 4.0s
- Attempt 4: 8.0s
- Attempt 5+: 16.0s, 30.0s (capped at max)

### Logging

Enable detailed retry logging:

```bash
python pyresttest/resttest.py http://localhost:8000 examples/test.yaml \
    --max-retries 3 \
    --log debug
```

## Concurrency Control

### Overview

Control the maximum number of concurrent requests in performance tests to avoid overwhelming the target server or your local system.

### CLI Option

- `--max-concurrency <number>`: Maximum concurrent requests for performance tests (overrides test-level config)

### Example Usage

```bash
# Limit to 10 concurrent requests globally
python pyresttest/resttest.py http://localhost:8000 examples/miniapp-benchmark.yaml \
    --max-concurrency 10

# Combined with retry
python pyresttest/resttest.py http://localhost:8000 examples/miniapp-benchmark.yaml \
    --max-concurrency 20 \
    --max-retries 3 \
    --log info
```

### YAML Configuration

You can also configure concurrency per-test in YAML:

```yaml
- test:
    - name: "Performance test with concurrency"
    - url: "/api/endpoint"
    - method: "GET"
    - performance:
        repeat: 100 # Total number of requests
        concurrency: 10 # Max concurrent requests
        mode: "sync" # or "async"
        threshold_ms: 500 # Alert if response > 500ms
```

### Sync vs Async Mode

**Sync mode** (default):

- Uses ThreadPoolExecutor
- Good for traditional HTTP/1.1 workloads
- Lower memory overhead

**Async mode**:

- Uses asyncio + aiohttp
- Better for high-concurrency scenarios
- Requires `aiohttp` package: `pip install aiohttp`

```yaml
- test:
    - name: "Async performance test"
    - url: "/api/endpoint"
    - performance:
        repeat: 1000
        concurrency: 100
        mode: "async"
        timeout: 30 # Total request timeout
        connect_timeout: 5 # Connection timeout
```

## Performance Metrics

Both sync and async modes now report retry statistics:

```
=== PERFORMANCE SUMMARY ===
total: 100
passed: 98
failed: 2
min_ms: 45.23
max_ms: 523.67
avg_ms: 123.45
total_retries: 5
avg_retries_per_request: 0.05
threshold_exceeded: 3
===========================
```

## Best Practices

### Retry Strategy

1. **Start conservative**: Begin with `--max-retries 2` or `3`
2. **Adjust backoff**: For flaky networks, increase `--retry-backoff-base`
3. **Set max delay**: Use `--retry-backoff-max` to prevent excessive waits
4. **Monitor logs**: Use `--log info` to see retry patterns

### Concurrency Tuning

1. **Baseline**: Start with low concurrency (5-10) to establish baseline
2. **Gradual increase**: Double concurrency until errors appear
3. **Server limits**: Respect target server's connection limits
4. **Local limits**: Watch system resources (file descriptors, memory)

### Combined Usage

```bash
# Robust performance testing with retries
python pyresttest/resttest.py http://api.example.com test.yaml \
    --max-retries 3 \
    --retry-backoff-base 0.5 \
    --retry-backoff-max 10 \
    --max-concurrency 20 \
    --log info
```

## Programmatic Usage

```python
from pyresttest.retry import RetryConfig
from pyresttest.performance import run_performance_test

# Create retry configuration
retry_config = RetryConfig(
    max_retries=3,
    backoff_base=0.5,
    backoff_max=30.0,
    retry_statuses=[500, 502, 503, 504, 429],  # Add 429 Too Many Requests
)

# Run performance test with retry and concurrency
result = run_performance_test(
    test=my_test,
    test_config=test_config,
    context=context,
    max_concurrency=10,
    retry_config=retry_config
)
```

## Troubleshooting

### Too Many Retries

**Symptom**: Tests take very long, many retry attempts
**Solution**:

- Reduce `--max-retries`
- Check if target server is actually down
- Verify network connectivity

### Concurrency Issues

**Symptom**: Connection errors, socket exhaustion
**Solution**:

- Lower `--max-concurrency`
- Check system limits: `ulimit -n`
- Use async mode for higher concurrency

### Async Mode Fails

**Symptom**: Import errors for aiohttp
**Solution**:

```bash
pip install aiohttp
```

## Future Enhancements

Planned features:

- Circuit breaker pattern
- Jitter for backoff (randomization)
- Per-status retry configuration
- Metrics export (Prometheus)
- Distributed tracing support

## See Also

- [Performance Testing Guide](performance_testing.md)
- [Advanced Guide](advanced_guide.md)
- [Examples](../examples/)
