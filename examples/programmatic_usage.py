#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ví dụ sử dụng PyRestTest từ Python script
Có thể tự config và chạy tests programmatically
"""

import sys
import os

# Add pyresttest to path nếu chưa install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyresttest import resttest
from pyresttest.binding import Context
from pyresttest.tests import Test
from pyresttest.benchmarks import Benchmark
from pyresttest.retry import RetryConfig
import yaml


def example_1_simple_test():
    """Ví dụ 1: Chạy test đơn giản từ code"""
    print("=" * 60)
    print("Example 1: Simple Test")
    print("=" * 60)
    
    # Tạo test object
    test = Test()
    test.name = "Test GET request"
    test.url = "https://httpbin.org/get"
    test.method = "GET"
    test.expected_status = [200]
    
    # Tạo context
    context = Context()
    
    # Chạy test
    from pyresttest.resttest import TestConfig
    test_config = TestConfig()
    
    result = resttest.run_test(test, test_config=test_config, context=context)
    
    print(f"Test passed: {result.passed}")
    print(f"Status code: {result.response_code}")
    print()


def example_2_test_with_retry():
    """Ví dụ 2: Test với retry configuration"""
    print("=" * 60)
    print("Example 2: Test with Retry")
    print("=" * 60)
    
    # Tạo retry config
    retry_config = RetryConfig(
        max_retries=3,
        backoff_base=0.5,
        backoff_max=10.0,
        retry_statuses=[500, 502, 503, 504, 429]  # Thêm 429 Too Many Requests
    )
    
    # Tạo test
    test = Test()
    test.name = "Test with retry"
    test.url = "https://httpbin.org/status/200"
    test.method = "GET"
    test.expected_status = [200]
    
    # Chạy test với retry
    from pyresttest.resttest import TestConfig
    context = Context()
    test_config = TestConfig()
    
    result = resttest.run_test(
        test, 
        test_config=test_config, 
        context=context,
        retry_config=retry_config
    )
    
    print(f"Test passed: {result.passed}")
    print(f"Status code: {result.response_code}")
    print(f"Retry config: max_retries={retry_config.max_retries}, backoff_base={retry_config.backoff_base}s")
    print()


def example_3_run_from_yaml():
    """Ví dụ 3: Load và chạy tests từ YAML file"""
    print("=" * 60)
    print("Example 3: Run from YAML")
    print("=" * 60)
    
    # Đọc YAML file
    yaml_file = os.path.join(
        os.path.dirname(__file__), 
        'github_api_smoketest.yaml'
    )
    
    if not os.path.exists(yaml_file):
        print(f"YAML file not found: {yaml_file}")
        return
    
    # Parse tests từ YAML
    test_structure = resttest.read_test_file(yaml_file)
    base_url = "https://api.github.com"
    
    tests = resttest.parse_testsets(
        base_url, 
        test_structure,
        working_directory=os.path.dirname(yaml_file)
    )
    
    # Tạo retry config (optional)
    retry_config = RetryConfig(max_retries=2, backoff_base=0.5)
    
    # Chạy testsets
    print(f"Running {len(tests)} testset(s)...")
    failures = resttest.run_testsets(
        tests, 
        retry_config=retry_config,
        max_concurrency=5
    )
    
    print(f"Total failures: {failures}")
    print()


def example_4_performance_test():
    """Ví dụ 4: Performance test với concurrency"""
    print("=" * 60)
    print("Example 4: Performance Test with Concurrency")
    print("=" * 60)
    
    # Tạo test với performance config
    test = Test()
    test.name = "Performance test"
    test.url = "https://httpbin.org/delay/0"
    test.method = "GET"
    test.expected_status = [200]
    
    # Config performance
    test.performance = {
        'repeat': 20,
        'concurrency': 5,
        'mode': 'sync',  # hoặc 'async'
        'threshold_ms': 1000
    }
    
    # Tạo retry config
    retry_config = RetryConfig(max_retries=2, backoff_base=0.3)
    
    # Chạy performance test
    from pyresttest.resttest import TestConfig
    context = Context()
    test_config = TestConfig()
    
    print("Running performance test (20 requests, 5 concurrent)...")
    result = resttest.run_test(
        test,
        test_config=test_config,
        context=context,
        retry_config=retry_config,
        max_concurrency=5
    )
    
    print("Performance test completed!")
    print()


def example_5_custom_config():
    """Ví dụ 5: Custom configuration từ dict/JSON"""
    print("=" * 60)
    print("Example 5: Custom Configuration")
    print("=" * 60)
    
    # Config từ dictionary (có thể load từ JSON/env vars)
    config = {
        'base_url': 'https://httpbin.org',
        'retry': {
            'max_retries': 3,
            'backoff_base': 1.0,
            'backoff_max': 30.0
        },
        'concurrency': 10,
        'tests': [
            {
                'name': 'Test 1: GET',
                'url': '/get',
                'method': 'GET',
                'expected_status': [200]
            },
            {
                'name': 'Test 2: POST',
                'url': '/post',
                'method': 'POST',
                'body': '{"key": "value"}',
                'expected_status': [200]
            }
        ]
    }
    
    # Tạo retry config từ dict
    retry_config = RetryConfig(
        max_retries=config['retry']['max_retries'],
        backoff_base=config['retry']['backoff_base'],
        backoff_max=config['retry']['backoff_max']
    )
    
    # Chạy tests từ config
    from pyresttest.resttest import TestConfig
    context = Context()
    test_config = TestConfig()
    
    for test_dict in config['tests']:
        test = Test()
        test.name = test_dict['name']
        test.url = config['base_url'] + test_dict['url']
        test.method = test_dict['method']
        test.expected_status = test_dict['expected_status']
        if 'body' in test_dict:
            test.body = test_dict['body']
        
        print(f"Running: {test.name}")
        result = resttest.run_test(
            test,
            test_config=test_config,
            context=context,
            retry_config=retry_config
        )
        print(f"  Result: {'PASS' if result.passed else 'FAIL'} (Status: {result.response_code})")
    
    print()


def example_6_advanced_usage():
    """Ví dụ 6: Advanced usage với validators và extractors"""
    print("=" * 60)
    print("Example 6: Advanced Usage")
    print("=" * 60)
    
    # Tạo test với validators
    test = Test()
    test.name = "Advanced test with validation"
    test.url = "https://httpbin.org/json"
    test.method = "GET"
    test.expected_status = [200]
    
    # Thêm validators
    from pyresttest.validators import ComparatorValidator
    from pyresttest import validators
    
    # Validate response contains specific field
    # (Cần parse response để validate, ở đây là ví dụ đơn giản)
    
    # Chạy test
    from pyresttest.resttest import TestConfig
    context = Context()
    test_config = TestConfig()
    
    retry_config = RetryConfig(max_retries=2)
    
    result = resttest.run_test(
        test,
        test_config=test_config,
        context=context,
        retry_config=retry_config
    )
    
    print(f"Test: {test.name}")
    print(f"Passed: {result.passed}")
    print(f"Status: {result.response_code}")
    
    if result.body:
        print(f"Response length: {len(result.body)} bytes")
    
    print()


def example_7_load_config_from_file():
    """Ví dụ 7: Load config từ file JSON/YAML"""
    print("=" * 60)
    print("Example 7: Load Config from File")
    print("=" * 60)
    
    # Ví dụ config file (JSON format)
    config_example = {
        "project_name": "My API Tests",
        "base_url": "https://httpbin.org",
        "global_settings": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 0.5,
                "backoff_max": 30
            },
            "concurrency": 10,
            "timeout": 30
        },
        "test_suites": [
            {
                "name": "Smoke Tests",
                "tests": [
                    {
                        "name": "Health Check",
                        "path": "/status/200",
                        "method": "GET",
                        "expected_status": [200]
                    }
                ]
            }
        ]
    }
    
    print("Example config structure:")
    print(yaml.dump(config_example, default_flow_style=False))
    print()
    
    # Load và execute
    retry_config = RetryConfig(
        max_retries=config_example['global_settings']['retry']['max_retries'],
        backoff_base=config_example['global_settings']['retry']['backoff_base'],
        backoff_max=config_example['global_settings']['retry']['backoff_max']
    )
    
    print(f"Project: {config_example['project_name']}")
    print(f"Retry Config: {retry_config.max_retries} retries, {retry_config.backoff_base}s base")
    print()


def example_8_cli_equivalent():
    """Ví dụ 8: Tương đương với CLI command"""
    print("=" * 60)
    print("Example 8: CLI Equivalent")
    print("=" * 60)
    
    # CLI command:
    # pyresttest http://api.example.com test.yaml --max-retries 3 --max-concurrency 10
    
    # Equivalent code:
    cli_args = {
        'url': 'https://httpbin.org',
        'test': os.path.join(os.path.dirname(__file__), 'github_api_smoketest.yaml'),
        'max_retries': 3,
        'retry_backoff_base': 0.5,
        'retry_backoff_max': 30.0,
        'max_concurrency': 10,
        'log': 'info',
        'cwd': os.getcwd()
    }
    
    print("CLI equivalent args:")
    for key, value in cli_args.items():
        print(f"  {key}: {value}")
    print()
    
    # Có thể gọi resttest.main(cli_args) để chạy như CLI
    # (comment out để không chạy thật)
    # resttest.main(cli_args)
    
    print("To run via CLI:")
    print(f"pyresttest {cli_args['url']} {os.path.basename(cli_args['test'])} \\")
    print(f"    --max-retries {cli_args['max_retries']} \\")
    print(f"    --max-concurrency {cli_args['max_concurrency']} \\")
    print(f"    --log {cli_args['log']}")
    print()


def main():
    """Main function - chạy tất cả examples"""
    print("\n" + "=" * 60)
    print("PyRestTest - Programmatic Usage Examples")
    print("=" * 60 + "\n")
    
    examples = [
        ("Simple Test", example_1_simple_test),
        ("Test with Retry", example_2_test_with_retry),
        ("Run from YAML", example_3_run_from_yaml),
        ("Performance Test", example_4_performance_test),
        ("Custom Config", example_5_custom_config),
        ("Advanced Usage", example_6_advanced_usage),
        ("Load Config from File", example_7_load_config_from_file),
        ("CLI Equivalent", example_8_cli_equivalent),
    ]
    
    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print()
    
    # Chạy từng example (hoặc chọn specific example)
    run_all = input("Run all examples? (y/n): ").lower().strip() == 'y'
    
    if run_all:
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"Error in {name}: {e}")
                import traceback
                traceback.print_exc()
                print()
    else:
        choice = input("Enter example number to run (1-8): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                examples[idx][1]()
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
