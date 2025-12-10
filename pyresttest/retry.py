"""
Retry logic with exponential backoff for HTTP requests
Supports both sync and async operations
"""
import time
import asyncio
import logging
from functools import wraps

logger = logging.getLogger('pyresttest.retry')


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(self, max_retries=3, backoff_base=0.5, backoff_max=30.0, 
                 retry_statuses=None, retry_exceptions=None):
        """
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_base: Base delay in seconds for exponential backoff (default: 0.5)
            backoff_max: Maximum delay in seconds between retries (default: 30.0)
            retry_statuses: HTTP status codes to retry on (default: [500, 502, 503, 504])
            retry_exceptions: Exception types to retry on (default: network-related exceptions)
        """
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.retry_statuses = retry_statuses or [500, 502, 503, 504]
        self.retry_exceptions = retry_exceptions or (ConnectionError, TimeoutError)

    def get_backoff_delay(self, attempt):
        """Calculate exponential backoff delay for given attempt number"""
        delay = self.backoff_base * (2 ** attempt)
        return min(delay, self.backoff_max)


def should_retry(status_code, config):
    """Check if a status code should trigger a retry"""
    return status_code in config.retry_statuses


def retry_sync(func, config, *args, **kwargs):
    """
    Synchronous retry wrapper for HTTP requests
    
    Args:
        func: Function to retry (should return response with status_code attribute)
        config: RetryConfig instance
        *args, **kwargs: Arguments to pass to func
        
    Returns:
        Response from successful call or last attempt
    """
    last_exception = None
    last_response = None
    
    for attempt in range(config.max_retries + 1):
        try:
            response = func(*args, **kwargs)
            last_response = response
            
            # Check if we should retry based on status code
            if hasattr(response, 'status_code'):
                if should_retry(response.status_code, config) and attempt < config.max_retries:
                    delay = config.get_backoff_delay(attempt)
                    logger.warning(f"Request failed with status {response.status_code}, "
                                 f"retrying in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries})")
                    time.sleep(delay)
                    continue
            
            # Success or non-retryable status
            return response
            
        except config.retry_exceptions as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = config.get_backoff_delay(attempt)
                logger.warning(f"Request failed with {type(e).__name__}: {e}, "
                             f"retrying in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries})")
                time.sleep(delay)
            else:
                logger.error(f"Request failed after {config.max_retries} retries")
                raise
    
    # Return last response or raise last exception
    if last_response is not None:
        return last_response
    if last_exception is not None:
        raise last_exception


async def retry_async(coro_func, config, *args, **kwargs):
    """
    Asynchronous retry wrapper for HTTP requests
    
    Args:
        coro_func: Async function to retry (should return response with status attribute)
        config: RetryConfig instance
        *args, **kwargs: Arguments to pass to coro_func
        
    Returns:
        Response from successful call or last attempt
    """
    last_exception = None
    last_response = None
    
    for attempt in range(config.max_retries + 1):
        try:
            response = await coro_func(*args, **kwargs)
            last_response = response
            
            # Check if we should retry based on status
            if hasattr(response, 'status'):
                if should_retry(response.status, config) and attempt < config.max_retries:
                    delay = config.get_backoff_delay(attempt)
                    logger.warning(f"Async request failed with status {response.status}, "
                                 f"retrying in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries})")
                    await asyncio.sleep(delay)
                    continue
            
            # Success or non-retryable status
            return response
            
        except config.retry_exceptions as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = config.get_backoff_delay(attempt)
                logger.warning(f"Async request failed with {type(e).__name__}: {e}, "
                             f"retrying in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Async request failed after {config.max_retries} retries")
                raise
    
    # Return last response or raise last exception
    if last_response is not None:
        return last_response
    if last_exception is not None:
        raise last_exception
