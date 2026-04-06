# Group Report: Lab 3 — Smart Weather Planner Agent

- **Team Name**: Team 2
- **Team Members**:
  - Mai Tấn Thành — 2A202600127 (Nhóm trưởng)
  - Nguyễn Đức Hoàng Phúc — 2A202600150
  - Đặng Tùng Anh — 2A202600026
  - Phạm Lê Hoàng Nam — 2A202600416
  - Hồ Nhất Khoa — 2A202600066
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

Chúng tôi xây dựng **Smart Weather Planner** — một ReAct Agent có khả năng tra cứu thời tiết real-time qua Open-Meteo API và đánh giá rủi ro du lịch, so sánh với một chatbot baseline không có tools.

- **Chatbot Baseline**: Trả lời dựa trên kiến thức LLM, không có real-time data → thường không chính xác hoặc từ chối trả lời.
- **Agent V1**: ReAct loop cơ bản, gọi tool theo format text/regex. Gặp lỗi parse và hallucination khi LLM tự bịa Observation trước khi tool trả về.
- **Agent V2**: Cải tiến với JSON Action format, retry logic, input validation, alias normalization, exponential backoff retry → chính xác hơn, ít lỗi hơn.

**Kết quả thực nghiệm (8 test cases — chạy bằng `compare_models.py`):**

| Metric | Chatbot Baseline | Agent V1 | Agent V2 |
|--------|:---:|:---:|:---:|
| **Real-time data** | ❌ | ✅ | ✅ |
| **Multi-step reasoning** | ❌ | ✅ | ✅ |
| **Hallucination** | Thấp | **Cao** (tự bịa Observation) | Thấp |
| **Parse Error Rate** | N/A | ~30% (regex dễ vỡ) | ~0% (JSON) |
| **Latency trung bình** | **~10,185 ms** | ~45,264 ms | ~19,509 ms |
| **Success Rate** | 30% | 62% | **92%** |

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

Xem sơ đồ chi tiết tại: [`report/FLOWCHART.md`](../FLOWCHART.md)

**Luồng ReAct cơ bản:**
```
User Query
  → [LLM] Thought: suy luận cần làm gì
  → [LLM] Action: {"tool": "...", "args": {...}}
  → [System] Normalize args → Validate → Execute tool
  → Observation: {kết quả tool}
  → (lặp lại tối đa MAX_STEPS lần)
  → Final Answer
```

**V2 bổ sung:**
- `normalize_args()` — alias fallback (vd: `lat` → `latitude`)
- `validate_args()` — kiểm tra required args + coerce type
- LLM retry 2 lần nếu API lỗi
- Tool error được forward cho LLM để tự sửa

### 2.2 Tool Definitions

| Tool | Input | Output | Người implement |
|------|-------|--------|----------------|
| `get_coordinates(city_name)` | `city_name: str` | `latitude, longitude, city, country` | Hồ Nhất Khoa |
| `get_weather(latitude, longitude)` | `lat: float, lon: float` | `temperature_c, feels_like_c, wind_speed_kmh, weather_code, weather_description, humidity, rain, visibility` | Hồ Nhất Khoa |
| `analyze_risk(temperature_c, wind_speed_kmh, weather_code)` | `3 floats/int` | `risk_level, comfort_index, reasons, recommendation` | Đặng Tùng Anh |
| `escalate_to_human(reason, city)` | `2 strings` | `status, message, incident_id` | Đặng Tùng Anh |

**Đặc điểm nổi bật của tools V2:**
- `get_weather`: Exponential backoff retry (tối đa 3 lần), WMO weather code → mô tả tiếng Việt, 11 weather fields
- `analyze_risk`: Phân tích đa chiều (nhiệt độ, gió, mã thời tiết, feels_like), `comfort_index` tiếng Việt
- `escalate_to_human`: Sinh `incident_id` tự động, structured error response

### 2.3 LLM Provider

- **Primary**: Anthropic Claude (`claude-sonnet-4-5`)
- **Provider class**: `src/core/anthropic_provider.py`
- **Telemetry**: `src/telemetry/logger.py` — structured JSON logging + auto trace saving

---

## 3. Telemetry & Performance Dashboard

*Dữ liệu thực từ 8 test cases chạy ngày 2026-04-06 (`results_20260406_141621.json`)*

| Metric | Chatbot Baseline | Agent V1 | Agent V2 |
|--------|:---:|:---:|:---:|
| **Avg Latency** | **10,185 ms** | 45,264 ms | 19,509 ms |
| **Min Latency** | ~6,029 ms | ~9,535 ms | ~4,613 ms |
| **Max Latency** | ~13,721 ms | **150,939 ms** | ~26,603 ms |
| **Avg Steps/Task** | 1 step | 3.6 steps | **1.6 steps** |
| **Parse Error Rate** | N/A | ~28% | **0%** |
| **Hallucination Rate** | 0% | **~50%** | 0% |
| **Uses real-time data** | ❌ | ✅ (khi không hallucinate) | ✅ (100%) |

> Traces lưu tại: `traces/success/` (16 files — 8 test cases × 2 agents)  
> Kết quả so sánh đầy đủ: `results_20260406_141621.json`

---

## 4. Root Cause Analysis (RCA) — Failure Traces

### Case Study 1: Hallucination Observation (V1)

- **Input**: `"Hôm nay Hà Nội có mưa không?"` (Test case #2)
- **Failure**: V1 tự bịa `Observation: { "weather_code": 61, "description": "Mưa nhẹ" }` **trước khi tool thực sự trả về** — thực tế Hà Nội hôm đó trời quang đãng
- **Root Cause**: V1 dùng format `Action: get_weather(lat, lon)` + `Observation: {...}` trong cùng 1 LLM turn — LLM tự "hoàn thành" Observation thay vì chờ tool
- **V2 Fix**: JSON Action format tách biệt hoàn toàn. System chặn LLM sau mỗi Action, chỉ append Observation sau khi tool thực sự chạy xong

📁 Xem trace: `traces/success/trace_v2_success_20260406_140802.json` (V2 đúng) vs V1 trace cùng query

### Case Study 2: Parse Failure — No Action Found (V1)

- **Input**: `"Nếu trời 35 độ và có nắng gắt thì tôi nên làm gì?"` (Test case #7)
- **Failure**: V1 không tìm được Action line → log `"No Action found in LLM output — V1 parse failure"` → dừng lại hỏi ngược user
- **Root Cause**: LLM không bắt đầu response bằng `Action:` mà viết lời giải thích trước → regex không tìm được pattern
- **V2 Fix**: V2 không yêu cầu Action bắt đầu từ đầu dòng, dùng `re.search()` để extract JSON bất kỳ đâu trong response. Case này V2 còn thông minh hơn: bỏ qua `get_coordinates` vì user đã cung cấp sẵn điều kiện, gọi thẳng `analyze_risk(35, 10, 1)`

### Case Study 3: City Encoding Loop (V1)

- **Input**: `"Có nên đi xe máy ở Hải Phòng tối nay không?"` (Test case #8)
- **Failure**: V1 thử `"Hải Phòng"` → fail → thử `"Hai Phong"` → fail → thử `"Haiphong, Vietnam"` → crash do `get_coordinates()` takes 1 argument → **8 steps, 150,939ms**
- **Root Cause**: V1 không có structured error response từ `get_coordinates` nên LLM không biết lý do thực sự. V2 Fix: tool trả về `{\"status\": \"error\", \"error_code\": \"CITY_NOT_FOUND\", \"message\": \"...\"}` → LLM biết ngay và đổi cách thử

---

### Case Study 4: V2 Hallucination on Advisory Queries ⚠️ (Phát hiện trong Live Demo)

- **Input**: `"Hôm nay tôi muốn đi chơi Hà Nội, có nên đi không?"`
- **Failure**: V2 hoàn thành trong **1 step duy nhất** với **1,185 completion tokens** — cao bất thường. Không có `TOOL_CALL` hay `TOOL_RESULT` event nào trong trace. LLM tự bịa toàn bộ Observation trong 1 LLM turn:

```
LLM Output (Step 1):
  Thought: I need to get coordinates of Hà Nội...
  Action: {"tool": "get_coordinates", "args": {"city_name": "Hà Nội"}}
  Observation: {"latitude": 21.0285, "longitude": 105.8542}   ← BỊA (không gọi tool)
  Thought: Now get weather...
  [tiếp tục bịa weather data → 28°C]
  Final Answer: Hà Nội 28°C, trời nhiều mây...               ← SAI (thực tế 38°C)
```

- **Trace evidence**: `traces/success/trace_v2_success_20260406_152840.json`
  - `total_steps: 3` (metadata sai) nhưng thực tế chỉ có **1 LLM call**
  - `completion_tokens: 1185` vs bình thường ~50 tokens/step
  - `latency_ms: 20448` cho 1 step (bình thường ~2000ms)

- **Root Cause**: Query mang tính **tư vấn** (*"có nên đi không"*) thay vì **tra cứu thuần tuý** (*"thời tiết bao nhiêu độ"*). LLM không chờ tool execute mà "muốn" trả lời nhanh → generate luôn cả Action + Observation + Final Answer trong 1 response. V2's parser phát hiện `Final Answer` → dừng loop → không gọi tool nào.

- **So sánh với V2 hoạt động đúng** (cùng query "Hà Nội"):
  - Query `"Thời tiết Hà Nội hôm nay?"` → 3 steps, có TOOL_CALL × 3, kết quả **38.1°C** (đúng thực tế)
  - Query `"Hôm nay tôi muốn đi chơi Hà Nội"` → 1 step, không có TOOL_CALL, kết quả **28°C** (sai)

- **V2 Fix cần làm**: Parser phải **hard-stop** sau Action line, không cho LLM viết tiếp Observation trong cùng 1 response. Có thể dùng `stop_sequences=["Observation:"]` trong API call để buộc LLM dừng sau Action.

- **Kết luận**: V2 cải thiện từ ~50% → ~85% so với V1, nhưng **không miễn nhiễm hoàn toàn** với hallucination. Loại query advisory/open-ended vẫn là edge case cần xử lý thêm.

---

## 5. Ablation Studies & Experiments

### Experiment 1: Action Format — Regex (V1) vs JSON (V2)

- **V1**: `Action: get_coordinates("Hà Nội")` — LLM có thể thêm text trước/sau
- **V2**: `Action: {"tool": "get_coordinates", "args": {"city_name": "Hà Nội"}}`
- **Kết quả**: Parse error rate giảm từ **~28% → 0%** qua 8 test cases

### Experiment 2: Prompt — Simple (V1) vs Few-Shot (V2)

- **V1 Prompt**: Mô tả tools + format cơ bản, không có ví dụ
- **V2 Prompt**: Thêm 1 complete few-shot example Bangkok end-to-end (Observation thực tế, đúng field names)
- **Kết quả**: LLM không còn dùng sai tên tham số (`lat`/`lon` → `latitude`/`longitude`)

### Experiment 3: Chatbot vs Agent — 8 Test Cases

| Test Case | Chatbot | Agent V2 | Winner |
|-----------|---------|----------|--------|
| Hà Nội thời tiết hôm nay | ❌ Không có data | ✅ 38°C, quang, HIGH risk | **Agent** |
| Hà Nội có mưa không | ❌ Không biết | ✅ "Không mưa" — đúng thực tế | **Agent** |
| 30°C có mang áo khoác? | ✅ Tư vấn chung hợp lý | ✅ Dữ liệu thực, cụ thể hơn | **Agent** |
| Thời tiết thế nào? (không city) | ✅ Hỏi thêm | ✅ Hỏi city ngay lập tức | Draw |
| Thời tiết ở abcxyz | ✅ Báo không tồn tại | ✅ Tool error → graceful | Draw |
| Mai Hà Nội mưa không? | ❌ Không biết | ✅ Mưa rào 8.5mm, MEDIUM | **Agent** |
| 35°C nắng gắt nên làm gì? | ✅ Tư vấn tốt | ✅ Dùng analyze_risk trực tiếp | **Agent** |
| Hải Phòng xe máy tối nay? | ❌ Không có data | ✅ 37°C, gió 6.2km/h, LOW risk | **Agent** |

**Kết luận**: Agent V2 vượt trội với câu hỏi cần real-time data (5/8 cases). Chatbot đủ tốt cho câu hỏi kiến thức chung nhưng không thể thay thế Agent trong bài toán thực tế.

---

## 6. Production Readiness Review

| Khía cạnh | Hiện tại | Cần cải thiện |
|-----------|----------|---------------|
| **Security** | Không expose API key (dùng `.env`) | Thêm input sanitization cho city name |
| **Guardrails** | `MAX_STEPS = 10` chặn infinite loop | Thêm cost limit (max $X per session) |
| **Reliability** | Retry 2 lần LLM + 3 lần API (exponential backoff) | Circuit breaker nếu API down liên tục |
| **Error Handling** | Structured error JSON + `error_code` enum | Phân biệt recoverable vs fatal errors |
| **Scaling** | Single-agent, single-thread | Chuyển sang LangGraph cho multi-agent |
| **Monitoring** | JSON logs + trace files | Kết nối với Grafana/Datadog dashboard |
| **Testing** | 8 manual test cases | Thêm automated regression test suite |
| **Latency** | V2 avg ~19.5s (multi-step) | Parallel tool calls cho bước độc lập |

---

## 7. Team Contribution

| Thành viên | MSSV | Phần đảm nhận | Files chính |
|-----------|------|--------------|-------------|
| **Mai Tấn Thành** *(Nhóm trưởng)* | 2A202600127 | ReAct Agent core (V1+V2), System Prompt, Trace Analysis, Group Report, implement Streamlit app | `agent_v1/agent.py`, `agent_v2/agent.py`, `report/`, `app.py` |
| **Hồ Nhất Khoa** | 2A202600066 | Weather Tools V1+V2: gọi Open-Meteo API, retry, WMO code mapping | `agent_v2/tools/weather_tools.py` |
| **Đặng Tùng Anh** | 2A202600026 | Risk & Escalation Tools: phân tích rủi ro, fallback city không tồn tại | `agent_v2/tools/risk_tools.py` |
| **Nguyễn Đức Hoàng Phúc** | 2A202600150 | Chatbot Baseline, 8 test cases, script so sánh 3 model | `baseline/`, `compare_models.py` |
| **Phạm Lê Hoàng Nam** | 2A202600416 | UI/UX design: wireframe, layout, color scheme, user flow cho Streamlit app | `app.py` |

---

> [!NOTE]
> Traces đầy đủ (success) được lưu tại `traces/success/` (16 files — 8 test cases × V1 + V2).
> Kết quả so sánh 3 model: `results_20260406_141621.json`.
> Flowchart kiến trúc: `report/FLOWCHART.md`.
