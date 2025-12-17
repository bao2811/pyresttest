# JSONPlaceholder Test Suite (PyRestTest)

This folder contains tests and examples for the JSONPlaceholder fake API (https://jsonplaceholder.typicode.com).

Files:

- `jsonplaceholder_tests.yaml` – functional tests for GET/POST/PUT/PATCH/DELETE and a small benchmark.
- `run_jsonplaceholder.py` – example script to run the suite (CLI-style and programmatic).

Quick commands:

Run all tests sequentially:

```bash
pyresttest --url https://jsonplaceholder.typicode.com --tests "examples/jsonplaceholder_tests.yaml" --log INFO
```

Run in parallel (2 workers):

```bash
pyresttest --url https://jsonplaceholder.typicode.com --tests "examples/jsonplaceholder_tests.yaml" --workers 2 --log INFO
```

Run benchmark only (uses the benchmark entry in the YAML):

```bash
pyresttest --url https://jsonplaceholder.typicode.com --tests "examples/jsonplaceholder_tests.yaml" --log INFO
# benchmark output is written to jsonplaceholder-get-posts-benchmark.json
```

Programmatic usage:

```bash
python examples/run_jsonplaceholder.py cli
```

Notes:

- The suite uses `compare` validators with `jsonpath_mini` to assert values.
- `POST` calls to JSONPlaceholder will return a created resource with `id` 101.
- Benchmark uses concurrency and will write output to `jsonplaceholder-get-posts-benchmark.json`.
