# Agent V1 — ReAct Agent (Basic)

**Người làm:**
- `agent.py` → **Mai Tấn Thành - 2A202600127 (nhóm trưởng)**
- `tools/weather_tools.py` → **Thành viên A**
- `tools/risk_tools.py` → **Thành viên B**

## Cấu trúc
```
agent_v1/
├── agent.py              ← ReAct loop cơ bản (Thought → Action → Observation)
└── tools/
    ├── weather_tools.py  ← Tool gọi Open-Meteo API
    └── risk_tools.py     ← Tool phân tích rủi ro + escalation
```

## Thành viên A — weather_tools.py
Implement 2 functions:
- `get_coordinates(city: str)` → gọi https://geocoding-api.open-meteo.com/v1/search
- `get_weather(lat: float, lon: float)` → gọi https://api.open-meteo.com/v1/forecast

## Thành viên B — risk_tools.py
Implement 2 functions:
- `analyze_risk(temperature_c, wind_speed_kmh, weather_code)` → trả về risk level + khuyến nghị
- `escalate_to_human(reason: str, city: str)` → simulate notify travel agent
