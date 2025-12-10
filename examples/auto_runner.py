#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-configured test runner for PyRestTest
Đọc config từ JSON/YAML và tự động chạy tests
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add pyresttest to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyresttest.tests import Test
from pyresttest.resttest import TestConfig, run_test
from pyresttest.binding import Context
from pyresttest.retry import RetryConfig


class ConfiguredTestRunner:
    """Test runner với auto-configuration từ JSON/YAML"""
    
    def __init__(self, config_file, environment='development'):
        """
        Initialize runner với config file
        
        Args:
            config_file: Path đến JSON config file
            environment: Environment để chạy (development, staging, production)
        """
        self.config_file = config_file
        self.environment = environment
        self.config = self.load_config()
        self.results = []
        
    def load_config(self):
        """Load configuration từ JSON file"""
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        # Merge environment-specific config
        if self.environment in config.get('environments', {}):
            env_config = config['environments'][self.environment]
            
            # Override base_url
            if 'base_url' in env_config:
                config['global_settings']['base_url'] = env_config['base_url']
            
            # Merge retry settings
            if 'retry' in env_config:
                config['global_settings']['retry'].update(env_config['retry'])
            
            # Merge concurrency settings
            if 'concurrency' in env_config:
                config['global_settings']['concurrency'].update(env_config['concurrency'])
        
        return config
    
    def create_retry_config(self):
        """Tạo RetryConfig từ global settings"""
        retry_settings = self.config['global_settings'].get('retry', {})
        
        return RetryConfig(
            max_retries=retry_settings.get('max_retries', 0),
            backoff_base=retry_settings.get('backoff_base', 0.5),
            backoff_max=retry_settings.get('backoff_max', 30.0),
            retry_statuses=retry_settings.get('retry_on_statuses', [500, 502, 503, 504])
        )
    
    def create_test_from_dict(self, test_dict, base_url):
        """
        Tạo Test object từ dictionary config
        
        Args:
            test_dict: Test configuration dict
            base_url: Base URL cho API
            
        Returns:
            Test object
        """
        test = Test()
        test.name = test_dict['name']
        test.url = base_url + test_dict['path']
        test.method = test_dict['method']
        test.expected_status = test_dict.get('expected_status', [200])
        
        # Headers
        if 'headers' in test_dict:
            test.headers = test_dict['headers']
        
        # Body
        if 'body' in test_dict:
            body = test_dict['body']
            if isinstance(body, dict):
                test.body = json.dumps(body)
            else:
                test.body = body
        
        # Performance config
        if 'performance' in test_dict:
            test.performance = test_dict['performance']
        
        return test
    
    def run_test_suite(self, suite):
        """
        Chạy một test suite
        
        Args:
            suite: Test suite configuration dict
            
        Returns:
            Tuple (passed_count, failed_count)
        """
        suite_name = suite['name']
        
        if not suite.get('enabled', True):
            print(f"⏭️  Skipping suite: {suite_name} (disabled)")
            return (0, 0)
        
        print(f"\n{'='*60}")
        print(f"📦 Test Suite: {suite_name}")
        if 'description' in suite:
            print(f"   {suite['description']}")
        print(f"{'='*60}\n")
        
        base_url = self.config['global_settings']['base_url']
        retry_config = self.create_retry_config()
        max_concurrency = self.config['global_settings']['concurrency'].get('max_concurrent', None)
        
        context = Context()
        test_config = TestConfig()
        
        # Logging settings
        logging_settings = self.config['global_settings'].get('logging', {})
        test_config.print_bodies = logging_settings.get('print_bodies', False)
        test_config.print_headers = logging_settings.get('print_headers', False)
        
        passed = 0
        failed = 0
        
        for test_dict in suite['tests']:
            test = self.create_test_from_dict(test_dict, base_url)
            
            print(f"🧪 Running: {test.name}")
            print(f"   {test.method} {test.url}")
            
            try:
                result = run_test(
                    test,
                    test_config=test_config,
                    context=context,
                    retry_config=retry_config,
                    max_concurrency=max_concurrency
                )
                
                # Check if performance test (result might be dict)
                if isinstance(result, dict):
                    # Performance test result
                    test_passed = result.get('failed', 0) == 0
                    status_code = 'N/A (Performance)'
                else:
                    # Regular test result
                    test_passed = result.passed
                    status_code = result.response_code
                
                if test_passed:
                    print(f"   ✅ PASSED (Status: {status_code})")
                    passed += 1
                else:
                    print(f"   ❌ FAILED (Status: {status_code})")
                    failed += 1
                
                # Store result
                self.results.append({
                    'suite': suite_name,
                    'test': test.name,
                    'passed': test_passed,
                    'status': status_code,
                    'url': test.url
                })
                
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                failed += 1
                self.results.append({
                    'suite': suite_name,
                    'test': test.name,
                    'passed': False,
                    'error': str(e),
                    'url': test.url
                })
            
            print()
        
        return (passed, failed)
    
    def run_all(self):
        """Chạy tất cả test suites"""
        print("\n" + "="*60)
        print(f"🚀 {self.config['project_name']}")
        print(f"   Environment: {self.environment}")
        print(f"   Base URL: {self.config['global_settings']['base_url']}")
        print("="*60)
        
        retry_cfg = self.config['global_settings']['retry']
        print(f"\n⚙️  Configuration:")
        print(f"   Retry: {retry_cfg['max_retries']} attempts")
        print(f"   Backoff: {retry_cfg['backoff_base']}s base, {retry_cfg['backoff_max']}s max")
        print(f"   Concurrency: {self.config['global_settings']['concurrency']['max_concurrent']}")
        
        total_passed = 0
        total_failed = 0
        start_time = datetime.now()
        
        for suite in self.config['test_suites']:
            passed, failed = self.run_test_suite(suite)
            total_passed += passed
            total_failed += failed
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Summary
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        print(f"Total Tests: {total_passed + total_failed}")
        print(f"✅ Passed: {total_passed}")
        print(f"❌ Failed: {total_failed}")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"📅 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Save results if configured
        self.save_results()
        
        return total_failed == 0
    
    def save_results(self):
        """Save test results to JSON file"""
        reporting = self.config.get('reporting', {})
        
        if 'json' in reporting.get('formats', []):
            output_dir = reporting.get('output_dir', './test-results')
            json_file = reporting.get('json_file', 'results.json')
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, json_file)
            
            results_data = {
                'project': self.config['project_name'],
                'environment': self.environment,
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'base_url': self.config['global_settings']['base_url'],
                    'retry': self.config['global_settings']['retry'],
                    'concurrency': self.config['global_settings']['concurrency']
                },
                'results': self.results,
                'summary': {
                    'total': len(self.results),
                    'passed': sum(1 for r in self.results if r['passed']),
                    'failed': sum(1 for r in self.results if not r['passed'])
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            print(f"💾 Results saved to: {output_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Auto-configured PyRestTest runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default environment (development)
  python auto_runner.py --config test_config.json
  
  # Run with specific environment
  python auto_runner.py --config test_config.json --env production
  
  # Run with custom config
  python auto_runner.py --config my_tests.json --env staging
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to JSON config file'
    )
    
    parser.add_argument(
        '--env', '-e',
        default='development',
        choices=['development', 'staging', 'production'],
        help='Environment to run tests against (default: development)'
    )
    
    parser.add_argument(
        '--suite', '-s',
        help='Run only specific test suite by name'
    )
    
    args = parser.parse_args()
    
    # Check config file exists
    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)
    
    # Create runner and execute
    runner = ConfiguredTestRunner(args.config, args.env)
    
    # Run specific suite or all
    if args.suite:
        # Find and run specific suite
        suite = next((s for s in runner.config['test_suites'] if s['name'] == args.suite), None)
        if suite:
            passed, failed = runner.run_test_suite(suite)
            success = failed == 0
        else:
            print(f"Error: Suite '{args.suite}' not found")
            sys.exit(1)
    else:
        # Run all suites
        success = runner.run_all()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
