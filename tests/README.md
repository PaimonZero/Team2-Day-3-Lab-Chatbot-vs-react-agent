# Tests — 5 Test Cases

**Người làm: Thành viên C**

## Nhiệm vụ
Viết `test_weather.py` với **5 test cases** dùng `pytest`, so sánh kết quả Chatbot vs Agent.

## 5 Test Cases cần có

| # | Input | Mục tiêu |
|---|---|---|
| 1 | "Thời tiết Tokyo?" | Agent gọi API, chatbot đoán mò |
| 2 | "Đi London mang gì?" | Agent dùng real-time, chatbot generic |
| 3 | "Thời tiết Hà Nội?" | Kiểm tra city tiếng Việt |
| 4 | "Thời tiết ở Narnia?" | Fallback path — city không tồn tại |
| 5 | City có gió > 90km/h | Human Escalation trigger |

## Cách chạy
```bash
pytest tests/test_weather.py -v
```

## Cũng cần viết: run_comparison.py
Script chạy cả 5 queries qua chatbot và agent, in ra bảng so sánh metrics.
