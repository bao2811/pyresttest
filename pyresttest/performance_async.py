import asyncio
import time
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


async def run_async_performance(test, max_concurrency=None, retry_config=None):
    """
    Run async performance test with configurable concurrency and retry
    
    Args:
        test: Test object with performance configuration
        max_concurrency: Optional override for max concurrent requests
        retry_config: Optional RetryConfig for retry behavior
    
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
    semaphore = asyncio.Semaphore(concurrency)
    
    async def worker():
        async with semaphore:
            # Create session per worker to avoid sharing issues
            async with aiohttp.ClientSession(timeout=timeout) as session:
                return await async_single_request(test, session, retry_config)
    
    # Create all tasks
    tasks = [asyncio.create_task(worker()) for _ in range(repeat)]
    
    # Collect results as they complete
    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            results.append(result)
        except Exception as e:
            logger.error(f"Worker task failed: {e}")
            # Add failed result
            results.append(AsyncPerformanceResult("unknown", 0, 0, False, 0))
    
    return results


def execute_async_performance(test, max_concurrency=None, retry_config=None):
    """
    Entry point for async performance testing
    
    Args:
        test: Test object
        max_concurrency: Optional max concurrent requests
        retry_config: Optional RetryConfig
    
    Returns:
        List of AsyncPerformanceResult objects
    """
    return asyncio.run(run_async_performance(test, max_concurrency, retry_config))
