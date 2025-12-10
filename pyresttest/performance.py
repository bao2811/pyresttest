import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import logging
from .retry import RetryConfig, retry_sync

logger = logging.getLogger('pyresttest.performance')

# Global session for connection pooling
session = requests.Session()


def run_single_http_test(test, context, retry_config=None):
    """
    Execute a single HTTP test with optional retry logic
    
    Args:
        test: Test object with method, url, headers, body, validators
        context: Test context
        retry_config: Optional RetryConfig for retry behavior
    
    Returns:
        Dict with status, passed, elapsed_ms, retries
    """
    method = test.method.upper()
    url = test.url
    headers = test.headers or {}
    body = test.body or None
    
    retries_attempted = 0
    start = time.time()
    
    def make_request():
        return session.request(method, url, headers=headers, data=body, 
                             timeout=getattr(test, 'timeout', 30))
    
    # Execute with retry if configured
    if retry_config and retry_config.max_retries > 0:
        for attempt in range(retry_config.max_retries + 1):
            try:
                response = make_request()
                
                # Check if status requires retry
                if response.status_code in retry_config.retry_statuses and attempt < retry_config.max_retries:
                    delay = retry_config.get_backoff_delay(attempt)
                    logger.debug(f"Status {response.status_code} on attempt {attempt + 1}, retrying in {delay}s")
                    retries_attempted += 1
                    time.sleep(delay)
                    start = time.time()  # Reset timer
                    continue
                
                # Success or non-retryable, validate
                break
                
            except requests.exceptions.RequestException as e:
                if attempt < retry_config.max_retries:
                    delay = retry_config.get_backoff_delay(attempt)
                    logger.debug(f"Exception {type(e).__name__} on attempt {attempt + 1}, retrying in {delay}s")
                    retries_attempted += 1
                    time.sleep(delay)
                    start = time.time()
                else:
                    logger.error(f"Request failed after {retry_config.max_retries} retries: {e}")
                    raise
    else:
        # No retry, single attempt
        response = make_request()
    
    elapsed_ms = (time.time() - start) * 1000
    
    # Run validators
    passed = True
    for validator in test.validators:
        if not validator.validate(response, context):
            passed = False
            break
    
    return {
        "status": response.status_code,
        "passed": passed,
        "elapsed_ms": elapsed_ms,
        "retries": retries_attempted
    }


def run_performance_test(test, test_config, context, max_concurrency=None, retry_config=None):
    """
    Run performance test with configurable concurrency and retry
    
    Args:
        test: Test object
        test_config: Test configuration
        context: Test context
        max_concurrency: Optional override for max concurrent requests
        retry_config: Optional RetryConfig for retry behavior
    
    Returns:
        Summary dict with performance statistics
    """
    perf = test.performance
    repeat = perf.get('repeat', 1)
    concurrency = max_concurrency or perf.get('concurrency', 1)
    threshold = perf.get('threshold_ms', None)
    mode = perf.get('mode', 'sync')

    if mode == 'async':
        from .performance_async import execute_async_performance
        return execute_async_performance(test, max_concurrency, retry_config)

    results = []

    def worker(_):
        try:
            return run_single_http_test(test, context, retry_config)
        except Exception as e:
            logger.error(f"Worker failed: {e}")
            return {
                "status": 0,
                "passed": False,
                "elapsed_ms": 0,
                "retries": 0
            }

    with ThreadPoolExecutor(max_workers=concurrency) as exec:
        futures = [exec.submit(worker, i) for i in range(repeat)]
        for f in as_completed(futures):
            results.append(f.result())

    # Calculate statistics
    times = [r['elapsed_ms'] for r in results]
    total_retries = sum(r.get('retries', 0) for r in results)

    summary = {
        "total": repeat,
        "passed": len([r for r in results if r['passed']]),
        "failed": len([r for r in results if not r['passed']]),
        "min_ms": min(times) if times else 0,
        "max_ms": max(times) if times else 0,
        "avg_ms": sum(times) / len(times) if times else 0,
        "total_retries": total_retries,
        "avg_retries_per_request": total_retries / repeat if repeat > 0 else 0
    }

    if threshold:
        summary["threshold_exceeded"] = len([t for t in times if t > threshold])

    print("=== PERFORMANCE SUMMARY ===")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    print("===========================")

    return summary

