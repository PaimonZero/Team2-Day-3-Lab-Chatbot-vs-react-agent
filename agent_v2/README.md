# Agent V2 — ReAct Agent (Improved)

**Người làm:**
- `agent.py` → **Mai Tấn Thành - 2A202600127 (nhóm trưởng)** — cải tiến từ v1 dựa trên failure traces
- `tools/weather_tools.py` → **Thành viên A** — cải tiến v1
- `tools/risk_tools.py` → **Thành viên B** — cải tiến v1

## Điểm khác so với V1

| Vấn đề V1 | Fix V2 |
|---|---|
| Prompt đơn giản, không có ví dụ | Thêm few-shot examples |
| Parse Action dễ fail | Dùng JSON format, robust hơn |
| Không retry khi lỗi | Retry tối đa 2 lần |
| Không validate tool input | Validate trước khi gọi |
| Không có fallback | Fallback khi city không tồn tại |

## Thành viên A — weather_tools.py (v2)
Copy từ v1 rồi cải tiến thêm:
- Retry khi API fail
- Trả về thêm thông tin (humidity, feels_like)
- Error message rõ ràng hơn

## Thành viên B — risk_tools.py (v2)
Copy từ v1 rồi cải tiến thêm:
- Risk level chi tiết hơn (LOW/MEDIUM/HIGH/CRITICAL)
- Thêm comfort index
- Escalation message chuyên nghiệp hơn
