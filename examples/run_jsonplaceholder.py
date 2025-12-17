#!/usr/bin/env python3
"""
Example runner for JSONPlaceholder test suite.
Shows both CLI usage and programmatic API run.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyresttest import resttest

BASE_URL = 'https://jsonplaceholder.typicode.com'
YAML_FILE = os.path.join(os.path.dirname(__file__), 'jsonplaceholder_tests.yaml')


def run_cli_style():
    """Run using CLI-equivalent arguments programmatically"""
    args = [
        '--url', BASE_URL,
        '--tests', YAML_FILE,
        '--workers', '2',
        '--log', 'INFO'
    ]
    print('Running via resttest command_line_run (CLI-style args)')
    resttest.command_line_run(args)


def run_programmatic():
    """Run programmatically: read YAML, run tests sequentially with configuration"""
    print('Running programmatically: reading YAML and invoking run_test')
    tests_struct = resttest.read_test_file(YAML_FILE)

    # We assume resttest exposes helpers; fall back to command_line_run if not
    try:
        args = {
            'url': BASE_URL,
            'tests': YAML_FILE,
            'workers': 1,
            'log': 'INFO'
        }
        resttest.main(args)
    except Exception:
        print('Programmatic run path not available; use CLI style runner')


if __name__ == '__main__':
    # Default: print instructions only
    print('Examples:')
    print('1) CLI-style run: python run_jsonplaceholder.py cli')
    print('2) Programmatic run: python run_jsonplaceholder.py prog')

    if len(sys.argv) > 1 and sys.argv[1] == 'cli':
        run_cli_style()
    elif len(sys.argv) > 1 and sys.argv[1] == 'prog':
        run_programmatic()
    else:
        print('\nNo action specified. Exiting.')
