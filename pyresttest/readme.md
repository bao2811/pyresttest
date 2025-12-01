# PyRestTest - Performance & Async Extension

## Tổng quan

PyRestTest là công cụ kiểm thử REST API. Phiên bản mở rộng này hỗ trợ:

- **Performance Testing**: test tải cao với nhiều request đồng thời.
- **Async Testing**: sử dụng `aiohttp` để thực hiện nhiều request bất đồng bộ.
- **CLI nâng cấp**: cho phép chạy test performance/async trực tiếp từ dòng lệnh.

---

## 1. Cài đặt

Cài đặt các phụ thuộc:

```bash
pip install requests pyyaml aiohttp
```

Clone dự án PyRestTest:

```bash
git clone https://github.com/username/pyresttest.git
cd pyresttest
```

---

## 2. Cấu trúc dự án

```
pyresttest/
├─ resttest.py             # Core engine
├─ performance.py          # ThreadPool performance engine
├─ performance_async.py    # Async engine với aiohttp
├─ cli.py                  # CLI nâng cấp
└─ tests/                  # Folder chứa file YAML test
```

---

## 3. Cấu trúc YAML Test

### Ví dụ Test bình thường

```yaml
- test:
    name: "Basic GET Test"
    url: "https://httpbin.org/get"
    method: GET
    expected_status: [200]
```

### Ví dụ Test Performance Sync

```yaml
- test:
    name: "Sync Load Test"
    url: "https://httpbin.org/get"
    method: GET
    expected_status: [200]
    performance:
      repeat: 50
      concurrency: 10
      mode: sync
```

### Ví dụ Test Performance Async

```yaml
- test:
    name: "Async Load Test"
    url: "https://httpbin.org/get"
    method: GET
    expected_status: [200]
    performance:
      repeat: 100
      concurrency: 50
      mode: async
```

---

## 4. CLI Nâng cấp

### Cú pháp

```bash
python cli.py [testfile] [options]
```

### Options

| Option              | Mô tả                              |
| ------------------- | ---------------------------------- |
| `--perf`            | Bật chế độ performance             |
| `--async`           | Chọn engine async                  |
| `--repeat <n>`      | Ghi đè số lần lặp (override YAML)  |
| `--concurrency <n>` | Ghi đè concurrency (override YAML) |
| `--base-url <url>`  | Ghi đè base URL cho test           |

### Ví dụ

```bash
python cli.py tests/api_tests.yaml --perf --async --repeat 100 --concurrency 50
```

---

## 5. Cách hoạt động

1. CLI parse YAML test file và flag từ dòng lệnh.
2. Nếu bật performance (`--perf`), CLI gán `mytest.performance.mode` (`sync`/`async`) dựa trên flag `--async`.
3. `run_test()` sẽ kiểm tra `mytest.performance.mode`:

   - `sync` → ThreadPool engine
   - `async` → Async engine với aiohttp

4. Nếu không có `performance` → chạy test bình thường.
5. Kết quả in ra console, performance mode trả về **danh sách kết quả** của từng request.

---

## 6. Ví dụ kết quả

```
Test: Async Load Test
URL: https://httpbin.org/get, Status: 200, Passed: True, Time(ms): 35.12
URL: https://httpbin.org/get, Status: 200, Passed: True, Time(ms): 36.45
...
```

---

## 7. Lời khuyên sử dụng

- Sử dụng `--async` khi cần test **load lớn** để tiết kiệm thời gian.
- `--repeat` và `--concurrency` có thể điều chỉnh để mô phỏng số lượng request thực tế.
- Duy trì YAML tách biệt cho từng loại test (functional vs performance) để dễ quản lý.

---

## 8. Ghi chú

- Đảm bảo Python >= 3.7 khi dùng async.
- ThreadPool engine dùng `requests`, async engine dùng `aiohttp`.
- Có thể tích hợp vào pipeline CI/CD để tự động chạy test định kỳ.
