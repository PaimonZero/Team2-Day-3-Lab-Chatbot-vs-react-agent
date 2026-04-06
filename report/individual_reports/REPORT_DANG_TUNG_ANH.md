# Individual Report: Lab 3 - Chatbot vs ReAct Agent 

- **Student Name**: Đặng Tùng Anh
- **Student ID**: 2A202600026
- **Date**: April 6, 2026

---

## I. Technical Contribution (15 Points)

I developed the **Risk & Escalation Tools** module, which provided the safety layer for the the team's ReAct Agent. My tools were critical in interpreting raw weather data and translating it into actionable travel advice and professional incident reports.

- **Modules Implemented**: 
  - `agent_v1/tools/risk_tools.py`: Rule-based safety logic.
  - `agent_v2/tools/risk_tools.py`: Granular 4-level risk assessment and escalation logging.
- **Evidence from Logs**:
  In the evaluation of Case 8 (Hải Phòng), the Agent V2 correctly identified a high-risk situation (wind gusts of 68 km/h). My tool generated a professional incident report:
  > **Observation**: `{"status": "escalated", "incident_id": "INC-20487", "message": "[HỆ THỐNG CẢNH BÁO V2]: Sự cố mã INC-20487 tại Hải Phòng đã được ghi nhận..."}`
- **Documentation**: My `analyze_risk` tool interprets WMO weather codes (e.g., 95, 96 for storms) into human-readable warnings. This prevents the LLM from having to "guess" the danger level of a numerical code, ensuring deterministic safety logic.

---

## II. Debugging Case Study (10 Points)

During the evaluation of Agent V1, we encountered a significant failure mode documented in `traces/failure/trace_v1_parse_error.json`.

- **Problem Description**: The V1 Regex Parser crashed when the LLM included "Inner Dialogue" within the `Action` line.
- **Log Source**: `trace_v1_parse_error.json` -> `Action: Let me check if there is an alternate spelling — get_coordinates(city = 'Xanadu')`.
- **Diagnosis**: The Agent V1 expected a rigid `Action: tool_name(args)` format. However, the LLM felt compelled to explain its reasoning *inside* the instruction line. The Regex parser was not robust enough to handle the leading explanatory text, causing a `No Action found` error.
- **Solution**: In Agent V2, my team leader implemented a JSON-based Action format. From my side, I added **Input Validation** to all my tools to ensure that even if the Parser partially failed or passed "cluttered" data, my functions would return a graceful "UNKNOWN" status instead of a raw Python traceback.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: In Case 8 (Hải Phòng), the Chatbot baseline gave generic advice because it had no real-time data. The ReAct Agent successfully deduced that "Hải Phòng" (accented) failed our geocoding tool, and its **Thought** was: *"I see Hải Phòng was not found. I'll try 'Hai Phong' instead."* This adaptive reasoning is impossible in a standard Chatbot.
2.  **Reliability (Latency Tradeoff)**: Based on `results_20260406_141621.json`, the Baseline Chatbot returned in **~12s**, while Agent V2 took **~26s**. This **116% increase in latency** is a significant tradeoff for the Agent's improved reliability and safety reporting.
3.  **Observation**: Environment feedback is the "anchor" of the agent. In the success traces, the Observation of `windspeed=45` from the weather tool was what triggered the Agent's next Thought to call my `analyze_risk` tool, proving that the Agent doesn't just guess; it reacts to specific data points.

---

## IV. Future Improvements (5 Points)

- **Scalability**: For a production system, `risk_tools` should support historical data to predict safety trends (e.g., "Usually storms here every Monday in Oct").
- **Fuzzy Matching for Tools**: A major pain point was the "Hải Phòng" vs "Hai Phong" confusion. We should integrate fuzzy matching (Levenshtein distance) directly into the geocoding tool or the Agent's string pre-processor to reduce redundant reasoning steps and save tokens/latency.
- **Audit Mode**: Implement a shadow `risk_check` that runs for every user query, even if the Agent doesn't think it needs a weather check, as a final "Safe Guard" before any travel recommendation.

---


