import asyncio
import time
import json
import os
import aiohttp
import logging
from .retry import RetryConfig, retry_async

logger = logging.getLogger('pyresttest.performance_async')


class AsyncPerformanceResult:
    def __init__(self, url, status, elapsed_ms, passed, retries=0):
        self.url = url
        self.status = status
        self.elapsed_ms = elapsed_ms
        self.passed = passed
        self.retries = retries


async def async_single_request(test, session, retry_config=None):
    """
    Execute a single async HTTP request with optional retry logic
    
    Args:
        test: Test object with method, url, headers, body, expected_status
        session: aiohttp ClientSession
        retry_config: Optional RetryConfig for retry behavior
    
    Returns:
        AsyncPerformanceResult with timing and status information
    """
    method = getattr(test, 'method', 'GET').upper()
    url = getattr(test, 'url', None)
    headers = getattr(test, 'headers', {})
    body = getattr(test, 'body', None)
    expected_status = getattr(test, 'expected_status', [200])
    
    retries_attempted = 0
    start = time.time()
    
    async def make_request():
        nonlocal retries_attempted
        try:
            async with session.request(method, url, headers=headers, data=body) as resp:
                await resp.text()  # Read response body
                return resp
        except Exception as e:
            logger.debug(f"Request to {url} failed: {e}")
            raise
    
    # Execute with retry if configured
    if retry_config and retry_config.max_retries > 0:
        for attempt in range(retry_config.max_retries + 1):
            try:
                resp = await make_request()
                elapsed_ms = (time.time() - start) * 1000
                
                # Check if status requires retry
                if resp.status in retry_config.retry_statuses and attempt < retry_config.max_retries:
                    delay = retry_config.get_backoff_delay(attempt)
                    logger.debug(f"Status {resp.status} on attempt {attempt + 1}, retrying in {delay}s")
                    retries_attempted += 1
                    await asyncio.sleep(delay)
                    start = time.time()  # Reset timer for retry
                    continue
                
                # Success or non-retryable
                passed = resp.status in expected_status
                return AsyncPerformanceResult(url, resp.status, elapsed_ms, passed, retries_attempted)
                
            except Exception as e:
                if attempt < retry_config.max_retries:
                    delay = retry_config.get_backoff_delay(attempt)
                    logger.debug(f"Exception {type(e).__name__} on attempt {attempt + 1}, retrying in {delay}s")
                    retries_attempted += 1
                    await asyncio.sleep(delay)
                    start = time.time()
                else:
                    # Final failure
                    elapsed_ms = (time.time() - start) * 1000
                    return AsyncPerformanceResult(url, 0, elapsed_ms, False, retries_attempted)
    else:
        # No retry configured, single attempt
        try:
            resp = await make_request()
            elapsed_ms = (time.time() - start) * 1000
            passed = resp.status in expected_status
            return AsyncPerformanceResult(url, resp.status, elapsed_ms, passed, 0)
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            logger.error(f"Request failed without retry: {e}")
            return AsyncPerformanceResult(url, 0, elapsed_ms, False, 0)


async def run_async_performance(test, max_concurrency=None, retry_config=None, verbose=True):
    """
    Run async performance test with configurable concurrency and retry
    
    Args:
        test: Test object with performance configuration
        max_concurrency: Optional override for max concurrent requests
        retry_config: Optional RetryConfig for retry behavior
        verbose: Whether to print results to console (default True, False for warmup)
    
    Returns:
        List of AsyncPerformanceResult objects
    """
    perf = getattr(test, 'performance', {})
    repeat = perf.get('repeat', 1)
    concurrency = max_concurrency or perf.get('concurrency', 10)
    
    # Create timeout configuration
    timeout = aiohttp.ClientTimeout(
        total=perf.get('timeout', 300),  # Total timeout for request
        connect=perf.get('connect_timeout', 10)  # Connection timeout
    )
    
    results = []

    # Use a single ClientSession with a TCPConnector so connections are reused.
    # Creating a session per request is expensive (TLS handshake, new TCP socket)
    # and can make async runs slower than sync. Reuse the session and limit
    # the connector to the desired concurrency.
    connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    # Track wall clock time
    wall_start = time.time()

    async def worker(session):
        async with semaphore:
            return await async_single_request(test, session, retry_config)

    # Create a single session and launch tasks that reuse it
    session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    try:
        tasks = [asyncio.create_task(worker(session)) for _ in range(repeat)]

        # Collect results as they complete
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
            except Exception as e:
                logger.error(f"Worker task failed: {e}")
                # Add failed result
                results.append(AsyncPerformanceResult("unknown", 0, 0, False, 0))
    finally:
        # Ensure session is closed
        await session.close()

    # Calculate wall clock time
    wall_elapsed_sec = time.time() - wall_start

    # Compute summary similar to sync runner
    times = [r.elapsed_ms for r in results]
    total_retries = sum(r.retries for r in results)
    passed = len([r for r in results if r.passed])
    failed = len([r for r in results if not r.passed])
    
    # Calculate throughput. Default mode uses wall clock time. If the test
    # requests response-time-based RPS, compute reciprocal of average
    # response time.
    perf = getattr(test, 'performance', {})
    rps_mode = perf.get('rps_mode', 'wall') if isinstance(perf, dict) else 'wall'
    if rps_mode == 'response':
        avg_ms = (sum(times) / len(times)) if times else 0
        rps = (1000.0 / avg_ms) if avg_ms > 0 else 0
    else:
        # RPS based on wall-clock time
        rps = len(results) / wall_elapsed_sec if wall_elapsed_sec > 0 else 0
    
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "min_ms": min(times) if times else 0,
        "max_ms": max(times) if times else 0,
        "avg_ms": (sum(times) / len(times)) if times else 0,
        "wall_time_sec": wall_elapsed_sec,
        "rps": rps,
        "total_retries": total_retries,
        "avg_retries_per_request": (total_retries / len(results)) if results else 0
    }

    # Percentiles support if requested
    perf = getattr(test, 'performance', {})
    percentiles = None
    metrics = perf.get('metrics') if isinstance(perf, dict) else None
    if isinstance(metrics, list):
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
        for p in percentiles:
            summary[f"p{int(p)}"] = _percentile(st, p)

    # Only print summary if verbose=True (skip for warmup runs)
    if verbose:
        test_name = getattr(test, 'name', 'Unnamed')
        print(f"\n{'='*60}")
        print(f"[ASYNC MODE] Performance Test: {test_name}")
        print(f"{'='*60}")
        print(f"Total Requests    : {summary['total']}")
        print(f"Passed            : {summary['passed']}")
        print(f"Failed            : {summary['failed']}")
        print(f"Min Response Time : {summary['min_ms']:.2f} ms")
        print(f"Avg Response Time : {summary['avg_ms']:.2f} ms")
        print(f"Max Response Time : {summary['max_ms']:.2f} ms")
        print(f"Wall Clock Time   : {summary['wall_time_sec']:.2f} sec")
        print(f"Throughput (RPS)  : {summary['rps']:.2f} req/sec")
        if summary['total_retries'] > 0:
            print(f"Total Retries     : {summary['total_retries']}")
            print(f"Avg Retries/Req   : {summary['avg_retries_per_request']:.2f}")
        print(f"{'='*60}\n")

    # Optionally write JSON output
    out_file = perf.get('output_file') if isinstance(perf, dict) else None
    out_format = perf.get('output_format') if isinstance(perf, dict) else None
    if out_file and out_format and out_format.lower() == 'json':
        try:
            odir = os.path.dirname(out_file)
            if odir and not os.path.exists(odir):
                os.makedirs(odir)
            with open(out_file, 'w') as fh:
                json.dump(summary, fh, indent=2)
            logger.info(f"Wrote async performance summary JSON to {out_file}")
        except Exception as e:
            logger.error(f"Failed to write async performance output file {out_file}: {e}")

    return results


def execute_async_performance(test, max_concurrency=None, retry_config=None, verbose=True):
    """
    Entry point for async performance testing
    
    Args:
        test: Test object
        max_concurrency: Optional max concurrent requests
        retry_config: Optional RetryConfig
        verbose: Whether to print results to console (default True, False for warmup)
    
    Returns:
        List of AsyncPerformanceResult objects
    """
    return asyncio.run(run_async_performance(test, max_concurrency, retry_config, verbose))
