import time
import json
import os
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
    for validator in (test.validators or []):
        if not validator.validate(response, context):
            passed = False
            break
    
    return {
        "status": response.status_code,
        "passed": passed,
        "elapsed_ms": elapsed_ms,
        "retries": retries_attempted
    }


def run_performance_test(test, test_config, context, max_concurrency=None, retry_config=None, verbose=True):
    """
    Run performance test with configurable concurrency and retry
    
    Args:
        test: Test object
        test_config: Test configuration
        context: Test context
        max_concurrency: Optional override for max concurrent requests
        retry_config: Optional RetryConfig for retry behavior
        verbose: Whether to print results to console (default True, False for warmup)
    
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
    
    # Track wall clock time
    wall_start = time.time()

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
    
    # Calculate wall clock time
    wall_elapsed_sec = time.time() - wall_start

    # Calculate statistics
    times = [r['elapsed_ms'] for r in results]
    total_retries = sum(r.get('retries', 0) for r in results)
    
    # Compute RPS. Default mode is 'wall' (requests / wall clock time).
    # If performance.rps_mode == 'response' then compute RPS as reciprocal of
    # average response time (1 / avg_response_time_seconds) which is equivalent
    # to total_requests / sum(response_times_seconds).
    rps_mode = perf.get('rps_mode', 'wall') if isinstance(perf, dict) else 'wall'
    if rps_mode == 'response':
        avg_ms = sum(times) / len(times) if times else 0
        rps = (1000.0 / avg_ms) if avg_ms > 0 else 0
    else:
        # RPS = total requests / wall clock time
        rps = repeat / wall_elapsed_sec if wall_elapsed_sec > 0 else 0

    summary = {
        "total": repeat,
        "passed": len([r for r in results if r['passed']]),
        "failed": len([r for r in results if not r['passed']]),
        "min_ms": min(times) if times else 0,
        "max_ms": max(times) if times else 0,
        "avg_ms": sum(times) / len(times) if times else 0,
        "wall_time_sec": wall_elapsed_sec,
        "rps": rps,
        "total_retries": total_retries,
        "avg_retries_per_request": total_retries / repeat if repeat > 0 else 0
    }

    if threshold:
        summary["threshold_exceeded"] = len([t for t in times if t > threshold])

    # Only print if verbose=True (skip for warmup runs)
    if verbose:
        test_name = getattr(test, 'name', 'Unnamed')
        print(f"\n{'='*60}")
        print(f"[SYNC MODE] Performance Test: {test_name}")
        print(f"{'='*60}")
        print(f"Total Requests    : {summary['total']}")
        print(f"Passed            : {summary['passed']}")
        print(f"Failed            : {summary['failed']}")
        print(f"Min Response Time : {summary['min_ms']:.2f} ms")
        print(f"Avg Response Time : {summary['avg_ms']:.2f} ms")
        print(f"Max Response Time : {summary['max_ms']:.2f} ms")
        print(f"Wall Clock Time   : {summary['wall_time_sec']:.2f} sec")
        print(f"Throughput (RPS)  : {summary['rps']:.2f} req/sec")
        if total_retries > 0:
            print(f"Total Retries     : {summary['total_retries']}")
            print(f"Avg Retries/Req   : {summary['avg_retries_per_request']:.2f}")
        print(f"{'='*60}\n")
    
    # Optional: add percentiles if requested
    metrics = perf.get('metrics', []) if isinstance(perf, dict) else []
    # metrics may be list of mappings, look for percentiles key
    percentiles = None
    for m in metrics:
        if isinstance(m, dict) and 'percentiles' in m:
            percentiles = m.get('percentiles')
            break
    if percentiles and times:
        def _percentile(sorted_times, p):
            k = (len(sorted_times)-1) * (p/100.0)
            f = int(k)
            c = min(f+1, len(sorted_times)-1)
            if f == c:
                return sorted_times[int(k)]
            d0 = sorted_times[f] * (c - k)
            d1 = sorted_times[c] * (k - f)
            return d0 + d1

        st = sorted(times)
        pct_vals = {f"p{int(p)}": _percentile(st, p) for p in percentiles}
        summary.update(pct_vals)

    # Write JSON output if requested
    out_file = perf.get('output_file') if isinstance(perf, dict) else None
    out_format = perf.get('output_format') if isinstance(perf, dict) else None
    if out_file and out_format and out_format.lower() == 'json':
        try:
            odir = os.path.dirname(out_file)
            if odir and not os.path.exists(odir):
                os.makedirs(odir)
            with open(out_file, 'w') as fh:
                json.dump(summary, fh, indent=2)
            logger.info(f"Wrote performance summary JSON to {out_file}")
        except Exception as e:
            logger.error(f"Failed to write performance output file {out_file}: {e}")

    return summary

