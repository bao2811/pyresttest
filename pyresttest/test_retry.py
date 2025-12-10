"""
Unit tests for retry module
"""
import unittest
import time
from unittest.mock import Mock, patch
from pyresttest.retry import RetryConfig, should_retry, retry_sync


class TestRetryConfig(unittest.TestCase):
    """Test RetryConfig class"""
    
    def test_default_config(self):
        """Test default retry configuration"""
        config = RetryConfig()
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.backoff_base, 0.5)
        self.assertEqual(config.backoff_max, 30.0)
        self.assertEqual(config.retry_statuses, [500, 502, 503, 504])
    
    def test_custom_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_retries=5,
            backoff_base=1.0,
            backoff_max=60.0,
            retry_statuses=[500, 503]
        )
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.backoff_base, 1.0)
        self.assertEqual(config.backoff_max, 60.0)
        self.assertEqual(config.retry_statuses, [500, 503])
    
    def test_backoff_delay_calculation(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(backoff_base=1.0, backoff_max=10.0)
        
        # Attempt 0: 1.0 * 2^0 = 1.0
        self.assertEqual(config.get_backoff_delay(0), 1.0)
        
        # Attempt 1: 1.0 * 2^1 = 2.0
        self.assertEqual(config.get_backoff_delay(1), 2.0)
        
        # Attempt 2: 1.0 * 2^2 = 4.0
        self.assertEqual(config.get_backoff_delay(2), 4.0)
        
        # Attempt 3: 1.0 * 2^3 = 8.0
        self.assertEqual(config.get_backoff_delay(3), 8.0)
        
        # Attempt 4: 1.0 * 2^4 = 16.0, but capped at max 10.0
        self.assertEqual(config.get_backoff_delay(4), 10.0)
        
        # Attempt 10: Should still be capped at max
        self.assertEqual(config.get_backoff_delay(10), 10.0)


class TestShouldRetry(unittest.TestCase):
    """Test should_retry function"""
    
    def test_should_retry_on_500(self):
        """Test that 500 status triggers retry"""
        config = RetryConfig()
        self.assertTrue(should_retry(500, config))
    
    def test_should_retry_on_502(self):
        """Test that 502 status triggers retry"""
        config = RetryConfig()
        self.assertTrue(should_retry(502, config))
    
    def test_should_not_retry_on_200(self):
        """Test that 200 status does not trigger retry"""
        config = RetryConfig()
        self.assertFalse(should_retry(200, config))
    
    def test_should_not_retry_on_404(self):
        """Test that 404 status does not trigger retry"""
        config = RetryConfig()
        self.assertFalse(should_retry(404, config))
    
    def test_custom_retry_statuses(self):
        """Test custom retry status codes"""
        config = RetryConfig(retry_statuses=[429, 503])
        self.assertTrue(should_retry(429, config))
        self.assertTrue(should_retry(503, config))
        self.assertFalse(should_retry(500, config))


class TestRetrySyncFunction(unittest.TestCase):
    """Test retry_sync function"""
    
    def test_successful_first_attempt(self):
        """Test successful request on first attempt"""
        config = RetryConfig(max_retries=3)
        
        # Mock response with successful status
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Mock function that succeeds immediately
        mock_func = Mock(return_value=mock_response)
        
        result = retry_sync(mock_func, config)
        
        self.assertEqual(result.status_code, 200)
        self.assertEqual(mock_func.call_count, 1)
    
    def test_retry_on_500_then_success(self):
        """Test retry after 500 error, then success"""
        config = RetryConfig(max_retries=3, backoff_base=0.01)  # Fast backoff for testing
        
        # Mock responses: first attempt fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        
        mock_func = Mock(side_effect=[mock_response_fail, mock_response_success])
        
        start_time = time.time()
        result = retry_sync(mock_func, config)
        elapsed = time.time() - start_time
        
        self.assertEqual(result.status_code, 200)
        self.assertEqual(mock_func.call_count, 2)
        # Should have waited at least backoff_base seconds
        self.assertGreaterEqual(elapsed, 0.01)
    
    def test_max_retries_exhausted(self):
        """Test that retries stop after max_retries"""
        config = RetryConfig(max_retries=2, backoff_base=0.01)
        
        # Mock response that always fails with 500
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_func = Mock(return_value=mock_response)
        
        result = retry_sync(mock_func, config)
        
        # Should try: initial + 2 retries = 3 total attempts
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(result.status_code, 500)
    
    def test_no_retry_on_non_retryable_status(self):
        """Test that non-retryable statuses don't trigger retry"""
        config = RetryConfig(max_retries=3)
        
        # Mock response with 404 (not retryable)
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_func = Mock(return_value=mock_response)
        
        result = retry_sync(mock_func, config)
        
        self.assertEqual(result.status_code, 404)
        self.assertEqual(mock_func.call_count, 1)  # No retries
    
    def test_retry_on_exception(self):
        """Test retry on connection error"""
        config = RetryConfig(max_retries=2, backoff_base=0.01)
        
        # Mock function that raises exception first, then succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_func = Mock(side_effect=[ConnectionError("Network error"), mock_response])
        
        result = retry_sync(mock_func, config)
        
        self.assertEqual(result.status_code, 200)
        self.assertEqual(mock_func.call_count, 2)
    
    def test_exception_exhausts_retries(self):
        """Test that exceptions exhaust retries and raise"""
        config = RetryConfig(max_retries=2, backoff_base=0.01)
        
        # Mock function that always raises exception
        mock_func = Mock(side_effect=ConnectionError("Network error"))
        
        with self.assertRaises(ConnectionError):
            retry_sync(mock_func, config)
        
        # Should try: initial + 2 retries = 3 total attempts
        self.assertEqual(mock_func.call_count, 3)


if __name__ == '__main__':
    unittest.main()
