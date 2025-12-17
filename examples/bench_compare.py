    #!/usr/bin/env python3
    """
    Simple sync vs async benchmark comparison for JSONPlaceholder /posts

    Sends N requests sequentially (sync) and N requests concurrently (async)
    and prints + saves summary statistics (min/avg/max/p50/p95/p99/throughput).

    Run with the project's virtualenv python: .venv/bin/python examples/bench_compare.py
    """
    import asyncio
    import json
    import math
    import time
    from collections import Counter

    import requests
    import aiohttp
    from concurrent.futures import ThreadPoolExecutor, as_completed

    TARGET_BASE = "https://jsonplaceholder.typicode.com"
    ENDPOINT = "/posts"
    DEFAULT_N_REQUESTS = 200
    DEFAULT_ASYNC_CONCURRENCY = 50
    DEFAULT_REPEAT = 1


    def percentile(sorted_list, p):
        if not sorted_list:
            return None
        k = (len(sorted_list) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        d0 = sorted_list[int(f)] * (c - k)
        d1 = sorted_list[int(c)] * (k - f)
        return d0 + d1


    def summarize(times_ms, statuses, errors, name):
        times_sorted = sorted(times_ms)
        total = len(times_ms)
        passed = sum(1 for s in statuses if 200 <= s < 300)
        failed = total - passed
        summary = {
            "name": name,
            "total_requests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "min_ms": min(times_sorted) if times_sorted else None,
            "max_ms": max(times_sorted) if times_sorted else None,
            "avg_ms": (sum(times_sorted) / len(times_sorted)) if times_sorted else None,
            "p50_ms": percentile(times_sorted, 50),
            "p95_ms": percentile(times_sorted, 95),
            "p99_ms": percentile(times_sorted, 99),
        }
        return summary


    def run_sync(url, n):
        times = []
        statuses = []
        errors = []
        start = time.time()
        for i in range(n):
            t0 = time.time()
            try:
                r = requests.get(url, timeout=30)
                elapsed_ms = (time.time() - t0) * 1000.0
                times.append(elapsed_ms)
                statuses.append(r.status_code)
            except Exception as e:
                elapsed_ms = (time.time() - t0) * 1000.0
                times.append(elapsed_ms)
                statuses.append(0)
                errors.append(str(e))
        total_elapsed = time.time() - start
        summary = summarize(times, statuses, errors, "sync-sequential")
        summary["total_wall_seconds"] = total_elapsed
        summary["throughput_rps"] = summary["total_requests"] / total_elapsed if total_elapsed > 0 else None
        summary["status_counts"] = dict(Counter(statuses))
        return summary


    def run_sync_concurrent(url, n, concurrency):
        """Run n requests using ThreadPoolExecutor and requests (sync HTTP but concurrent threads)."""
        times = []
        statuses = []
        errors = []

        def _do(i):
            t0 = time.time()
            try:
                r = requests.get(url, timeout=30)
                elapsed_ms = (time.time() - t0) * 1000.0
                return elapsed_ms, r.status_code, None
            except Exception as e:
                elapsed_ms = (time.time() - t0) * 1000.0
                return elapsed_ms, 0, str(e)

        start = time.time()
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [ex.submit(_do, i) for i in range(n)]
            for fut in as_completed(futures):
                elapsed_ms, status, err = fut.result()
                times.append(elapsed_ms)
                statuses.append(status)
                if err:
                    errors.append(err)

        total_elapsed = time.time() - start
        summary = summarize(times, statuses, errors, f"sync-concurrent-{concurrency}")
        summary["total_wall_seconds"] = total_elapsed
        summary["throughput_rps"] = summary["total_requests"] / total_elapsed if total_elapsed > 0 else None
        summary["status_counts"] = dict(Counter(statuses))
        return summary


    async def _aio_get(session, url, sem, times, statuses, errors, idx):
        async with sem:
            t0 = time.time()
            try:
                async with session.get(url, timeout=30) as resp:
                    await resp.text()
                    elapsed_ms = (time.time() - t0) * 1000.0
                    times.append(elapsed_ms)
                    statuses.append(resp.status)
            except Exception as e:
                elapsed_ms = (time.time() - t0) * 1000.0
                times.append(elapsed_ms)
                statuses.append(0)
                errors.append(str(e))


    async def run_async(url, n, concurrency):
        times = []
        statuses = []
        errors = []
        sem = asyncio.Semaphore(concurrency)
        start = time.time()
        connector = aiohttp.TCPConnector(limit=0)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [asyncio.create_task(_aio_get(session, url, sem, times, statuses, errors, i)) for i in range(n)]
            await asyncio.gather(*tasks)
        total_elapsed = time.time() - start
        summary = summarize(times, statuses, errors, f"async-concurrent-{concurrency}")
        summary["total_wall_seconds"] = total_elapsed
        summary["throughput_rps"] = summary["total_requests"] / total_elapsed if total_elapsed > 0 else None
        summary["status_counts"] = dict(Counter(statuses))
        return summary


    def save_json(obj, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)


    def print_summary(s):
        print("\n=== {} ===".format(s.get("name")))
        print(f"Total requests: {s.get('total_requests')}")
        print(f"Passed: {s.get('passed')}, Failed: {s.get('failed')}")
        print(f"Wall sec: {s.get('total_wall_seconds'):.3f}, Throughput rps: {s.get('throughput_rps'):.2f}")
        print(f"min/avg/max ms: {s.get('min_ms'):.2f}/{s.get('avg_ms'):.2f}/{s.get('max_ms'):.2f}")
        print(f"p50/p95/p99 ms: {s.get('p50_ms'):.2f}/{s.get('p95_ms'):.2f}/{s.get('p99_ms'):.2f}")
        print(f"Status counts: {s.get('status_counts')}\n")


    def main():
        import argparse
        parser = argparse.ArgumentParser(description="Bench compare sync vs async")
        parser.add_argument("--requests", "-n", type=int, default=DEFAULT_N_REQUESTS, help="Number of requests per run")
        parser.add_argument("--concurrency", "-c", type=int, default=DEFAULT_ASYNC_CONCURRENCY, help="Async concurrency")
        parser.add_argument("--repeat", "-r", type=int, default=DEFAULT_REPEAT, help="Repeat runs")
        parser.add_argument("--outdir", default="examples/bench_results", help="Directory to save results")
        parser.add_argument("--prefix", default="bench", help="Filename prefix for saved results")
        args = parser.parse_args()

        url = TARGET_BASE + ENDPOINT
        n = args.requests
        import os
        os.makedirs(args.outdir, exist_ok=True)

        all_runs = []
        for i in range(1, args.repeat + 1):
            print(f"Run {i}/{args.repeat}: sync sequential {n} requests against {url}")
            sync_summary = run_sync(url, n)
            sync_path = f"{args.outdir}/{args.prefix}_sync_run{i}.json"
            save_json(sync_summary, sync_path)
            print_summary(sync_summary)

            print(f"Run {i}/{args.repeat}: sync concurrent {n} requests against {url} with concurrency {args.concurrency}")
            syncc_summary = run_sync_concurrent(url, n, args.concurrency)
            syncc_path = f"{args.outdir}/{args.prefix}_syncc_c{args.concurrency}_run{i}.json"
            save_json(syncc_summary, syncc_path)
            print_summary(syncc_summary)

            print(f"Run {i}/{args.repeat}: async concurrent {n} requests against {url} with concurrency {args.concurrency}")
            async_summary = asyncio.run(run_async(url, n, args.concurrency))
            async_path = f"{args.outdir}/{args.prefix}_async_c{args.concurrency}_run{i}.json"
            save_json(async_summary, async_path)
            print_summary(async_summary)

            all_runs.append({
                "sync": sync_summary,
                "sync_concurrent": syncc_summary,
                "async": async_summary,
                "sync_path": sync_path,
                "syncc_path": syncc_path,
                "async_path": async_path,
            })

        # Combined summary
        combo = {"runs": all_runs}
        combo_path = f"{args.outdir}/{args.prefix}_combined.json"
        save_json(combo, combo_path)
        print(f"Saved combined summary to {combo_path}")


    if __name__ == '__main__':
        main()