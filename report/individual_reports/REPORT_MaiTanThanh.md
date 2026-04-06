# Individual Report: Lab 3 — Chatbot vs ReAct Agent

- **Student Name**: Mai Tấn Thành
- **Student ID**: 2A202600127
- **Role**: Nhóm trưởng — Team 2
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

### Modules Implemented

| File | Mô tả |
|------|-------|
| `agent_v2/agent.py` | **Core ReAct Agent V2** — toàn bộ logic vòng lặp, prompt, parsing |
| `agent_v1/agent.py` | ReAct Agent V1 (baseline để so sánh) |
| `app.py` | Implement Streamlit app theo design của Nam: chat UI, 4 mode (Baseline/V1/V2/So sánh), stats bar, agent step logs |
| `report/group_report/GROUP_REPORT_TEAM2.md` | Group Report đầy đủ |
| `report/FLOWCHART.md` | Flowchart kiến trúc |

### Code Highlights — Agent V2

**1. JSON Action Format thay vì regex:**
```python
# V1 (dễ vỡ)
Action: get_coordinates("Hà Nội")

# V2 (structured, LLM không thể sai format)
Action: {"tool": "get_coordinates", "args": {"city_name": "Hà Nội"}}
```

**2. ARG_ALIASES — normalize tên tham số tự động:**
```python
ARG_ALIASES = {
    "lat": "latitude",  "lon": "longitude",
    "lng": "longitude", "temp": "temperature_c",
    "wind": "wind_speed_kmh", "code": "weather_code",
}

def normalize_args(tool_name: str, args: dict) -> dict:
    return {ARG_ALIASES.get(k, k): v for k, v in args.items()}
```
*Lý do*: LLM đôi khi gọi `lat` thay vì `latitude` — mà tool function chỉ nhận `latitude`. Nếu không có normalize, tool sẽ crash với `TypeError: missing required argument`.

**3. Few-Shot Example trong System Prompt:**

Thay vì mô tả format chung chung, tôi nhúng 1 example end-to-end hoàn chỉnh (query Bangkok → 5 steps) trực tiếp vào system prompt. Kết quả: parse error rate giảm từ **~28% → 0%** qua 8 test cases.

**4. Soft-error detection:**
```python
def is_tool_error(result: str) -> bool:
    try:
        data = json.loads(result)
        return data.get("status") == "error"
    except:
        return False
```
Khi tool trả về `{"status": "error"}`, agent không crash mà forward lỗi cho LLM — LLM tự quyết định bước tiếp theo (thử tên khác, hoặc trả lời gracefully).

### Interaction với ReAct Loop

```
User Query
  → [LLM] Thought + Action (JSON)
  → normalize_args() → validate_args()
  → execute tool() → Observation
  → if error: forward to LLM (không crash)
  → if risk=HIGH: escalate_to_human()
  → Final Answer
```

---

## II. Debugging Case Study (10 Points)

### Bug: Parameter Mismatch `lat/lon` → `latitude/longitude`

**Problem Description:**

Khi chạy V2 lần đầu, agent liên tục bị lỗi:

```
TypeError: get_weather() got an unexpected keyword argument 'lat'
```

LLM gọi `{"tool": "get_weather", "args": {"lat": 21.03, "lon": 105.85}}` nhưng function signature là `get_weather(latitude, longitude)`. Hai bên không khớp.

**Log Source:**
```json
{"event": "TOOL_CALL", "tool": "get_weather", "args": {"lat": 21.03, "lon": 105.85}}
{"event": "TOOL_ERROR", "error": "TypeError: unexpected keyword argument 'lat'"}
```

**Diagnosis:**

Nguyên nhân là **schema mismatch**: Tool schema trong system prompt mô tả `latitude/longitude`, nhưng few-shot example cũ dùng `lat/lon` làm shorthand. LLM học từ example ngắn hơn là từ schema chính thức.

**Solution:**

1. Sửa few-shot example để dùng đúng `latitude/longitude` thống nhất
2. Thêm `ARG_ALIASES` dictionary để normalize ngay cả khi LLM vẫn ra `lat/lon`:

```python
ARG_ALIASES = {"lat": "latitude", "lon": "longitude", ...}

def normalize_args(tool_name, args):
    return {ARG_ALIASES.get(k, k): v for k, v in args.items()}
```

Kết quả: Tool error rate **giảm từ 100% → 0%** cho parameter mismatch errors.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning — Thought block giúp gì?

Block `Thought:` buộc LLM phải **lập kế hoạch từng bước** trước khi hành động. Ví dụ với query *"Hải Phòng tối nay có nên đi xe máy không?"*, chatbot trả lời dựa trên kiến thức mùa vụ chung chung — trong khi agent thực sự gọi tool, lấy dữ liệu **37°C, gió 6.2 km/h, trời quang** và đưa ra lời khuyên cụ thể.

Quan sát thú vị: Trong test case #7 *(35°C nắng gắt, không có city)*, Agent V2 **bỏ qua `get_coordinates` và `get_weather`** — vì user đã cung cấp điều kiện, nên gọi thẳng `analyze_risk(35, 10, 1)`. Đây là biểu hiện của **contextual reasoning** thực sự, không phải chỉ follow script.

### 2. Reliability — Agent tệ hơn Chatbot khi nào?

Agent thực sự **kém hơn** trong 2 tình huống:

| Tình huống | Vấn đề |
|---|---|
| **Câu hỏi không có city** | V1 gặp parse fail, phải hỏi lại 2 lần (latency cao hơn chatbot) |
| **Latency đơn giản** | Chatbot trả lời ~10s; Agent V2 mất ~19s dù câu hỏi dễ |

→ Agent không phải là giải pháp cho mọi use case. Với câu hỏi kiến thức chung, chatbot vẫn nhanh hơn và đủ tốt.

### 3. Observation — Feedback từ environment ảnh hưởng thế nào?

Observation là **nguồn sự thật duy nhất** trong ReAct loop. Khi V1 tự bịa Observation (hallucinate), toàn bộ chuỗi lý luận tiếp theo bị sai — LLM tin vào dữ liệu giả mà không có gì kiểm tra. Đây là lỗi nguy hiểm nhất: **confident but wrong**.

V2 giải quyết bằng cách chặn LLM sau mỗi `Action`, chỉ append Observation sau khi tool thực sự chạy. Khi tool báo lỗi, LLM nhận được error message và tự điều chỉnh thay vì tiếp tục với dữ liệu sai.

---

## IV. Future Improvements (5 Points)

### Scalability
- **Parallel tool calls**: `get_coordinates` và một số operations độc lập có thể chạy song song với `asyncio.gather()` — giảm latency ~30-40%
- **Chuyển sang LangGraph**: Hỗ trợ branching phức tạp hơn (vd: multi-city comparison, conditional paths)

### Safety
- **Supervisor LLM**: Một LLM riêng audit action của agent trước khi execute — phát hiện prompt injection hoặc tool call bất thường
- **Input sanitization**: Hiện tại city name được truyền thẳng vào API — cần validate để tránh injection

### Performance
- **Response caching**: Cache kết quả `get_weather` theo (lat, lon, timestamp/hour) — tránh gọi API lặp lại trong cùng 1 session
- **Cost limit**: Hiện chỉ có `MAX_STEPS = 10` — cần thêm token budget limit để tránh overspend khi LLM loop
- **Streaming responses**: Hiển thị partial answer ngay khi LLM đang generate, thay vì đợi toàn bộ response

---

> [!NOTE]
> Codebase chính: `agent_v2/agent.py` — commit `dd6c2df` trên GitHub.
> Traces minh chứng: `traces/success/` (16 files từ 8 test cases).
> Kết quả so sánh: `results_20260406_141621.json`.
