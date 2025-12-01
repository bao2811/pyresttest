# import argparse
# import yaml
# from pyresttest.resttest import run_test


# def main():
#     parser = argparse.ArgumentParser(description='PyRestTest CLI with performance/async support')

#     parser.add_argument('testfile', help='YAML file containing tests')

#     # Performance flags
#     parser.add_argument("--perf", choices=["sync", "async"], help="Performance mode")
#     parser.add_argument("--repeat", type=int, default=None, help="Override repeat count")
#     parser.add_argument("--concurrency", type=int, default=None, help="Override concurrency")

#     # Base URL override
#     parser.add_argument("--base-url", help="Base URL for tests")

#     args = parser.parse_args()

#     # Load YAML tests
#     with open(args.testfile, 'r', encoding='utf-8') as f:
#         tests = yaml.safe_load(f)

#     for t in tests:
#         test_data = t.get('test')
#         if not test_data:
#             continue

#         # --- Override base url if specified ---
#         if args.base_url:
#             if "url" in test_data:
#                 test_data["url"] = args.base_url.rstrip("/") + "/" + test_data["url"].lstrip("/")

#         # --- Override performance config ---
#         if args.perf:
#             perf = test_data.setdefault("performance", {})
#             perf["mode"] = args.perf

#             if args.repeat is not None:
#                 perf["repeat"] = args.repeat
#             if args.concurrency is not None:
#                 perf["concurrency"] = args.concurrency

#         print(f"\n=== Running Test: {test_data.get('name', 'Unnamed Test')} ===")

#         # --- Execute test ---
#         result = run_test(test_data)

#         # --- Print performance or normal results ---
#         if isinstance(result, list):
#             # Performance returns list of result objects
#             for r in result:
#                 print(f"- URL: {r.url}, "
#                       f"Status: {r.status_code}, "
#                       f"Passed: {r.passed}, "
#                       f"Time(ms): {r.elapsed_ms:.2f}")
#         else:
#             # Normal test result (InternalTest TestResponse object)
#             print(result)


# if __name__ == '__main__':
#     main()

# #!/usr/bin/env python3
# import argparse
# import yaml
# import json
# import time
# import statistics
# import asyncio
# import httpx
# from urllib.parse import urljoin

# # ===== ANSI colors =====
# class C:
#     GREEN = "\033[92m"
#     RED = "\033[91m"
#     CYAN = "\033[96m"
#     YELLOW = "\033[93m"
#     BOLD = "\033[1m"
#     END = "\033[0m"

# def print_color(text, color):
#     print(color + text + C.END)

# def compute_stats(times):
#     if not times:
#         return {}
#     return {
#         "count": len(times),
#         "avg_ms": sum(times)/len(times),
#         "min_ms": min(times),
#         "max_ms": max(times),
#         "p95_ms": statistics.quantiles(times, n=100)[94],
#         "p99_ms": statistics.quantiles(times, n=100)[98],
#     }

# # ===== Sync test runner =====
# import requests

# def run_single_test(test):
#     url = test.get("url")
#     method = test.get("method", "GET").upper()
#     headers = test.get("headers")
#     body = test.get("body")
#     expected_status = test.get("expected_status", [200])
#     result = {
#         "url": url,
#         "method": method,
#         "passed": False,
#         "status_code": None,
#         "elapsed_ms": 0,
#     }
#     start = time.time()
#     try:
#         resp = requests.request(method, url, headers=headers, data=body, timeout=10)
#         result["status_code"] = resp.status_code
#         result["passed"] = resp.status_code in expected_status
#     except Exception as e:
#         result["error"] = str(e)
#     finally:
#         end = time.time()
#         result["elapsed_ms"] = (end - start)*1000
#     return result

# # ===== Async test runner =====
# async def run_single_test_async(test):
#     url = test.get("url")
#     method = test.get("method", "GET").upper()
#     headers = test.get("headers")
#     body = test.get("body")
#     expected_status = test.get("expected_status", [200])
#     result = {
#         "url": url,
#         "method": method,
#         "passed": False,
#         "status_code": None,
#         "elapsed_ms": 0,
#     }
#     start = time.time()
#     async with httpx.AsyncClient(timeout=10) as client:
#         try:
#             resp = await client.request(method, url, headers=headers, content=body)
#             result["status_code"] = resp.status_code
#             result["passed"] = resp.status_code in expected_status
#         except Exception as e:
#             result["error"] = str(e)
#         finally:
#             end = time.time()
#             result["elapsed_ms"] = (end - start)*1000
#     return result

# async def run_test_async(test, repeat=1, concurrency=1):
#     tasks = []
#     results = []
#     semaphore = asyncio.Semaphore(concurrency)

#     async def run_with_semaphore():
#         async with semaphore:
#             res = await run_single_test_async(test)
#             results.append(res)

#     for _ in range(repeat):
#         tasks.append(asyncio.create_task(run_with_semaphore()))
#     await asyncio.gather(*tasks)
#     return results

# # ===== Main CLI =====
# def main():
#     parser = argparse.ArgumentParser(description="CLI API Test Runner")
#     parser.add_argument("testfile", help="YAML file with tests")
#     parser.add_argument("--perf", choices=["sync", "async"], help="Performance mode")
#     parser.add_argument("--repeat", type=int, default=1)
#     parser.add_argument("--concurrency", type=int, default=1)
#     parser.add_argument("--base-url", help="Override base URL")
#     parser.add_argument("--json", action="store_true", help="Output JSON results")
#     args = parser.parse_args()

#     # Load YAML
#     with open(args.testfile, "r", encoding="utf-8") as f:
#         data = yaml.safe_load(f)

#     # Normalize tests list
#     tests_list = []
#     for block in data:
#         if "test" in block:
#             test = block["test"]
#             # Apply base_url override
#             if args.base_url:
#                 test["url"] = urljoin(args.base_url, test.get("url", ""))
#             tests_list.append(test)

#     all_results = []

#     for test in tests_list:
#         name = test.get("name", "Unnamed")
#         print_color(f"\n=== Running Test: {name} ===", C.BOLD)

#         perf = test.get("performance", {})
#         mode = args.perf or perf.get("mode")
#         repeat = args.repeat or perf.get("repeat", 1)
#         concurrency = args.concurrency or perf.get("concurrency", 1)

#         if mode == "async":
#             results = asyncio.run(run_test_async(test, repeat=repeat, concurrency=concurrency))
#         else:
#             results = [run_single_test(test) for _ in range(repeat)]

#         # Print results
#         for r in results:
#             color = C.GREEN if r.get("passed") else C.RED
#             print_color(
#                 f"{r.get('method')} {r.get('url')} | Status: {r.get('status_code')} | "
#                 f"Passed: {r.get('passed')} | Time(ms): {r.get('elapsed_ms'):.2f}",
#                 color
#             )
#         # Collect for summary
#         all_results.extend(results)

#     # Summary
#     times = [r["elapsed_ms"] for r in all_results]
#     stats = compute_stats(times)
#     if stats:
#         print_color("\n===== PERFORMANCE SUMMARY =====", C.BOLD)
#         print(f"Total Requests : {stats['count']}")
#         print(f"Average (ms)   : {stats['avg_ms']:.2f}")
#         print(f"Min (ms)       : {stats['min_ms']:.2f}")
#         print(f"Max (ms)       : {stats['max_ms']:.2f}")
#         print(f"P95 (ms)       : {stats['p95_ms']:.2f}")
#         print(f"P99 (ms)       : {stats['p99_ms']:.2f}")

#     # JSON output
#     if args.json:
#         print(json.dumps(all_results, indent=2))

# if __name__ == "__main__":
#     main()


#!/usr/bin/env python3
# import argparse
# import yaml
# from .resttest import run_test, TestConfig
# from .resttest import Test

# # Chuyển dict YAML thành object giống PyRestTest
# def dict_to_test(test_dict):
#     class InternalTest:
#         pass
#     test_obj = InternalTest()
#     for k, v in test_dict.items():
#         setattr(test_obj, k, v)
#     return test_obj

# # Chạy tất cả test trong YAML
# def run_tests(yaml_file, base_url=None):
#     with open(yaml_file, "r", encoding="utf-8") as f:
#         docs = yaml.safe_load(f)

#     config = TestConfig()
#     config.timeout = 10
#     config.print_bodies = True

#     for block in docs:
#         if "test" not in block:
#             continue
#         test_dict = block["test"]

#         if base_url:
#             test_dict["url"] = base_url + test_dict.get("url", "")

#         # Chuyển dict thành object
#         class InternalTest:
#             pass
#         mytest = InternalTest()
#         for k, v in test_dict.items():
#             setattr(mytest, k, v)

#         # Gọi run_test
#         result = run_test(mytest, test_config=config)

#         print(f"\n=== Running Test: {mytest.name} ===")

#         # Nếu là performance mode async, result là list
#         if isinstance(result, list):
#             total = len(result)
#             passed = sum(1 for r in result if getattr(r, "passed", False))
#             for r in result:
#                 status = getattr(r, "response_code", None)
#                 print(f"URL: {r.url}, Status: {status}, Passed: {r.passed}, Time(ms): {r.elapsed_ms:.2f}")
#             print(f"Performance Summary: {passed}/{total} requests passed")
#         else:
#             status = getattr(result, "response_code", None)
#             print(f"URL: {mytest.url} | Passed: {result.passed} | Status: {status}")


# # CLI
# def main():
#     parser = argparse.ArgumentParser(description="Run PyRestTest YAML tests")
#     parser.add_argument("yaml_file", help="YAML file containing tests")
#     parser.add_argument("--base-url", help="Override base URL for all tests")
#     args = parser.parse_args()
#     run_tests(args.yaml_file, base_url=args.base_url)

# if __name__ == "__main__":
#     main()

import argparse
import yaml
from .resttest import run_test, TestConfig, Test

# Chạy tất cả test trong YAML
def run_tests(yaml_file, base_url=None):
    with open(yaml_file, "r", encoding="utf-8") as f:
        docs = yaml.safe_load(f)

    config = TestConfig()
    config.timeout = 10
    config.print_bodies = True

    for block in docs:
        if "test" not in block:
            continue
        test_dict = block["test"]

        url = test_dict.get("url", "")
        if base_url:
            url = base_url + url

        # Khởi tạo Test rỗng
        mytest = Test()

        # Gán các thuộc tính từ dict
        mytest.name = test_dict.get("name", "Unnamed")
        mytest.url = url
        mytest.method = test_dict.get("method", "GET")
        mytest.headers = test_dict.get("headers", {})
        mytest.body = test_dict.get("body")
        mytest.validators = test_dict.get("validators", [])
        mytest.performance = test_dict.get("performance")  # Nếu có

        print(f"\n=== Running Test: {mytest.name} ===")
        result = run_test(mytest, test_config=config)

        # Nếu là performance mode async, result là list
        if isinstance(result, list):
            total = len(result)
            passed = sum(1 for r in result if getattr(r, "passed", False))
            for r in result:
                status = getattr(r, "response_code", None)
                print(f"URL: {r.url}, Status: {status}, Passed: {r.passed}, Time(ms): {r.elapsed_ms:.2f}")
            print(f"Performance Summary: {passed}/{total} requests passed")
        else:
            status = getattr(result, "response_code", None)
            print(f"URL: {mytest.url} | Passed: {result.passed} | Status: {status}")


# CLI
def main():
    parser = argparse.ArgumentParser(description="Run PyRestTest YAML tests")
    parser.add_argument("yaml_file", help="YAML file containing tests")
    parser.add_argument("--base-url", help="Override base URL for all tests")
    args = parser.parse_args()
    run_tests(args.yaml_file, base_url=args.base_url)


if __name__ == "__main__":
    main()
