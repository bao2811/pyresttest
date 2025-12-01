import asyncio
import time
import aiohttp

class AsyncPerformanceResult:
    def __init__(self, url, status, elapsed_ms, passed):
        self.url = url
        self.status = status
        self.elapsed_ms = elapsed_ms
        self.passed = passed

async def async_single_request(test, session):
    method = getattr(test, 'method', 'GET').upper()
    url = getattr(test, 'url', None)
    headers = getattr(test, 'headers', {})
    body = getattr(test, 'body', None)
    expected_status = getattr(test, 'expected_status', [200])

    start = time.time()
    async with session.request(method, url, headers=headers, data=body) as resp:
        text = await resp.text()
        elapsed_ms = (time.time() - start) * 1000
        passed = resp.status in expected_status
        return AsyncPerformanceResult(url, resp.status, elapsed_ms, passed)

async def run_async_performance(test):
    perf = getattr(test, 'performance', {})
    repeat = perf.get('repeat', 1)
    concurrency = perf.get('concurrency', 1)

    results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def worker():
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                return await async_single_request(test, session)

    tasks = [asyncio.create_task(worker()) for _ in range(repeat)]
    for coro in asyncio.as_completed(tasks):
        results.append(await coro)

    return results

def execute_async_performance(test):
    return asyncio.run(run_async_performance(test))
