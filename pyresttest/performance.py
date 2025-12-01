import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

session = requests.Session()

def run_single_http_test(test, context):
    method = test.method.upper()
    url = test.url
    headers = test.headers or {}
    body = test.body or None

    start = time.time()
    response = session.request(method, url, headers=headers, data=body)
    elapsed_ms = (time.time() - start) * 1000

    passed = True

    # validator của PyRestTest nằm trong test.validators
    for validator in test.validators:
        if not validator.validate(response, context):
            passed = False

    return {
        "status": response.status_code,
        "passed": passed,
        "elapsed_ms": elapsed_ms
    }


def run_performance_test(test, test_config, context):
    perf = test.performance
    repeat = perf.get('repeat', 1)
    concurrency = perf.get('concurrency', 1)
    threshold = perf.get('threshold_ms', None)
    mode = perf.get('mode', 'sync')

    if mode == 'async':
        from .performance_async import run_async_perf
        return run_async_perf(test)

    results = []

    def worker(_):
        return run_single_http_test(test, context)

    with ThreadPoolExecutor(max_workers=concurrency) as exec:
        futures = [exec.submit(worker, i) for i in range(repeat)]
        for f in as_completed(futures):
            results.append(f.result())

    # thống kê
    times = [r['elapsed_ms'] for r in results]

    summary = {
        "total": repeat,
        "passed": len([r for r in results if r['passed']]),
        "failed": len([r for r in results if not r['passed']]),
        "min_ms": min(times),
        "max_ms": max(times),
        "avg_ms": sum(times)/len(times),
    }

    if threshold:
        summary["threshold_exceeded"] = len([t for t in times if t > threshold])

    print("=== PERFORMANCE SUMMARY ===")
    print(summary)
    print("===========================")

    return summary
