# Chatbot Baseline

**Người làm: Thành viên C**

## Nhiệm vụ
Viết file `chatbot.py` — một chatbot đơn giản dùng Claude để tư vấn thời tiết, **KHÔNG dùng tools**.

## Yêu cầu
- Nhận input từ user (tên thành phố)
- Gọi Claude API để trả lời
- Chatbot sẽ trả lời dựa trên kiến thức sẵn có (không biết real-time) → đây là điểm yếu cần highlight
- Lưu log ra `logs/`

## Cách chạy
```bash
python chatbot_baseline/chatbot.py
```

## Provider dùng
```python
from src.core.anthropic_provider import AnthropicProvider
```
