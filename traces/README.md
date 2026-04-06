# Traces — Smart Weather Planner Agent

Folder này chứa các **execution traces** được chọn lọc từ quá trình chạy thử agent.

## Cấu trúc

```
traces/
├── success/
│   ├── trace_v1_hanoi_success.json     ← Agent V1 chạy thành công
│   └── trace_v2_tokyo_success.json     ← Agent V2 chạy thành công
└── failure/
    ├── trace_v1_parse_error.json       ← V1 fail do parse Action sai
    ├── trace_v1_unknown_city.json      ← V1 fail do city không tồn tại
    └── trace_v2_retry_recovery.json    ← V2 fail nhưng tự recover
```

## Cách đọc trace

Mỗi trace file là một JSON array chứa các bước của agent:

```json
[
  { "step": 1, "type": "THOUGHT", "content": "..." },
  { "step": 2, "type": "ACTION",  "tool": "get_coordinates", "args": ["Hanoi"] },
  { "step": 3, "type": "OBSERVATION", "result": { "lat": 21.03, "lon": 105.85 } },
  ...
  { "step": N, "type": "FINAL_ANSWER", "content": "..." }
]
```

## Mục đích

Theo rubric **Trace Quality (9 điểm)**:
- Phải có ít nhất 1 **success trace** (agent hoàn thành đúng)
- Phải có ít nhất 1 **failure trace** (agent fail + giải thích tại sao)
- Failure trace của V1 → là lý do để cải tiến V2
