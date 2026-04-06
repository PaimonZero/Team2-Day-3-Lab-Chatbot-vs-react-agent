"""
app.py — Smart Weather Planner UI
Team 2 — Day 3 Lab: Chatbot vs ReAct Agent
"""

import streamlit as st
import sys
import io
import os
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from agent_v1.agent import run_agent as run_agent_v1
from agent_v2.agent import run_agent as run_agent_v2
from src.core.anthropic_provider import AnthropicProvider

_BASELINE_PROMPT = """You are a weather assistant chatbot. Answer in Vietnamese.
Rules:
- You DO NOT have access to real-time weather data or any tools.
- You MUST NOT pretend to know exact current weather conditions.
- Answer based on general weather patterns, seasons, knowledge — with uncertainty.
- Always clarify that you cannot check live weather.
- Still provide helpful, practical suggestions.
Style: Natural, helpful, concise. Vietnamese language."""

def chatbot_baseline(question: str) -> str:
    llm = AnthropicProvider(
        model_name=os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    return llm.generate(question, system_prompt=_BASELINE_PROMPT)["content"]

# ─── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Weather Planner — Team 2",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Light background */
    .stApp { background: linear-gradient(160deg, #e8f4fd 0%, #f0f7ff 60%, #e3f2fd 100%); }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #dde8f5;
    }

    /* Hero header */
    .hero-header {
        background: linear-gradient(135deg, #1565c0 0%, #1976d2 50%, #0288d1 100%);
        border-radius: 20px;
        padding: 32px 36px;
        margin-bottom: 24px;
        box-shadow: 0 4px 24px rgba(21,101,192,0.25);
    }
    .hero-header h1 { color: white; margin: 0; font-size: 1.9rem; font-weight: 700; }
    .hero-header p  { color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 0.92rem; }

    /* Stat cards */
    .stat-card {
        background: white;
        border: 1px solid #dde8f5;
        border-radius: 14px;
        padding: 18px 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(21,101,192,0.08);
    }
    .stat-number { font-size: 1.6rem; font-weight: 700; color: #1565c0; }
    .stat-label  { font-size: 0.75rem; color: #78909c; margin-top: 4px; font-weight: 500; }

    /* Agent step log */
    .step-log {
        background: #f8fafe;
        border-left: 3px solid #42a5f5;
        border-radius: 0 8px 8px 0;
        padding: 8px 14px;
        margin: 4px 0;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        color: #1565c0;
    }

    /* Mode badge */
    .mode-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .badge-baseline { background: #eceff1; color: #546e7a; }
    .badge-v1       { background: #e8f5e9; color: #2e7d32; }
    .badge-v2       { background: #e3f2fd; color: #1565c0; }
    .badge-compare  { background: #f3e5f5; color: #6a1b9a; }

    /* Compare header */
    .compare-header {
        text-align: center;
        font-weight: 700;
        font-size: 0.88rem;
        padding: 8px 12px;
        border-radius: 10px;
        margin-bottom: 10px;
    }

    /* Tip boxes */
    .tip-box {
        background: #fff8e1;
        border-left: 3px solid #ffb300;
        border-radius: 0 8px 8px 0;
        padding: 9px 12px;
        font-size: 0.82rem;
        color: #5d4037;
        margin: 5px 0;
        cursor: pointer;
    }

    /* Chat messages */
    .stChatMessage {
        background: white !important;
        border-radius: 14px !important;
        border: 1px solid #dde8f5 !important;
        box-shadow: 0 2px 8px rgba(21,101,192,0.06) !important;
        margin-bottom: 10px !important;
    }

    /* Input box */
    .stChatInputContainer {
        background: white !important;
        border-radius: 16px !important;
        border: 2px solid #90caf9 !important;
        box-shadow: 0 2px 12px rgba(21,101,192,0.1) !important;
    }

    /* Buttons */
    .stButton > button {
        background: #1565c0;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #0d47a1;
        box-shadow: 0 4px 12px rgba(21,101,192,0.3);
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)


# ─── Capture stdout ──────────────────────────────────────────
class StdoutCapture(io.StringIO):
    def __init__(self):
        super().__init__()
        self.lines = []

    def write(self, text):
        if text.strip():
            self.lines.append(text.strip())
        return len(text)


def run_with_capture(fn, query):
    """Chạy agent/chatbot, capture stdout, đo latency."""
    old_stdout = sys.stdout
    cap = StdoutCapture()
    sys.stdout = cap
    start = time.time()
    try:
        result = fn(query)
    except Exception as e:
        result = f"⚠️ Lỗi: {str(e)}"
    finally:
        sys.stdout = old_stdout
    latency = int((time.time() - start) * 1000)
    return result, cap.lines, latency


# ─── Header ──────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
  <h1>🌤️ Smart Weather Planner</h1>
  <p>Team 2 · Day 3 Lab · Chatbot Baseline vs ReAct Agent V1 & V2</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Chế độ")

    mode = st.radio(
        "Chọn model:",
        ["🤖 Chatbot Baseline", "⚡ Agent V1 (Basic)", "🚀 Agent V2 (Improved)", "📊 So sánh cả 3"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 📋 Mô tả từng mode")

    descriptions = {
        "🤖 Chatbot Baseline": ("badge-baseline", "Không có tools. Trả lời dựa trên kiến thức LLM — nhanh nhưng không có dữ liệu thực."),
        "⚡ Agent V1 (Basic)":  ("badge-v1",       "ReAct loop cơ bản, parse bằng regex. Đôi khi hallucinate Observation."),
        "🚀 Agent V2 (Improved)": ("badge-v2",     "JSON Action format, alias fallback, retry logic, exponential backoff — dữ liệu 100% thực."),
        "📊 So sánh cả 3":      ("badge-compare",  "Chạy cùng 1 query qua 3 model — so sánh trực tiếp chất lượng và latency."),
    }
    cls, desc = descriptions[mode]
    st.markdown(f'<div class="mode-badge {cls}">{mode}</div>', unsafe_allow_html=True)
    st.caption(desc)

    st.markdown("---")
    st.markdown("### 💡 Thử ngay")
    examples = [
        "Hà Nội hôm nay thời tiết như nào?",
        "Hôm nay Hà Nội có mưa không?",
        "Có nên đi xe máy ở Hải Phòng tối nay không?",
        "Thời tiết ở abcxyz hôm nay?",
        "Nếu trời 35°C nắng gắt thì nên làm gì?",
    ]
    for ex in examples:
        st.markdown(f'<div class="tip-box">💬 {ex}</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("🔧 Stack: Anthropic Claude · Open-Meteo API · Streamlit")
    st.caption("👥 Team 2 — Thành · Khoa · Tùng Anh · Phúc · Nam")


# ─── Session state ────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_queries" not in st.session_state:
    st.session_state.total_queries = 0
if "total_latency" not in st.session_state:
    st.session_state.total_latency = 0

# ─── Stats bar ───────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number">{st.session_state.total_queries}</div>
        <div class="stat-label">Queries</div></div>""", unsafe_allow_html=True)
with c2:
    avg = (st.session_state.total_latency // max(st.session_state.total_queries, 1))
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number">{avg:,}ms</div>
        <div class="stat-label">Avg Latency</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number">4</div>
        <div class="stat-label">Tools Available</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="stat-card">
        <div class="stat-number">Free</div>
        <div class="stat-label">Open-Meteo API</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Chat history ─────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("steps"):
            with st.expander(f"🔍 Agent Steps ({msg.get('latency', '?')}ms)", expanded=False):
                for line in msg["steps"]:
                    st.markdown(f'<div class="step-log">{line}</div>', unsafe_allow_html=True)


# ─── Chat input ───────────────────────────────────────────────
if user_input := st.chat_input("Hỏi về thời tiết hoặc kế hoạch du lịch..."):

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.total_queries += 1

    # ── So sánh cả 3 ──────────────────────────────────────────
    if mode == "📊 So sánh cả 3":
        with st.chat_message("assistant"):
            st.markdown("**So sánh 3 model — đang chạy...**")
            cols = st.columns(3)
            results = {}

            labels = [
                ("🤖 Baseline",  "baseline", chatbot_baseline),
                ("⚡ Agent V1",  "v1",       run_agent_v1),
                ("🚀 Agent V2",  "v2",       run_agent_v2),
            ]
            for i, (label, key, fn) in enumerate(labels):
                with cols[i]:
                    with st.spinner(f"Chạy {label}..."):
                        ans, steps, lat = run_with_capture(fn, user_input)
                    results[key] = (ans, steps, lat)
                    colors = {"baseline": "#546e7a", "v1": "#2e7d32", "v2": "#1565c0"}
                    st.markdown(
                        f'<div class="compare-header" style="background:{colors[key]}22;'
                        f'border:1px solid {colors[key]}66;color:white">{label} · {lat:,}ms</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(ans)
                    if steps:
                        with st.expander("Steps"):
                            for s in steps:
                                st.caption(s)

            fastest = min(results, key=lambda k: results[k][2])
            st.info(f"⚡ Nhanh nhất: **{fastest.upper()}** ({results[fastest][2]:,}ms)")

            summary = "\n\n".join([
                f"**{label}** ({results[key][2]:,}ms):\n{results[key][0]}"
                for label, key, _ in labels
            ])
            st.session_state.messages.append({
                "role": "assistant",
                "content": summary,
                "steps": [],
                "latency": max(r[2] for r in results.values()),
            })
            st.session_state.total_latency += sum(r[2] for r in results.values()) // 3

    # ── Single agent mode ─────────────────────────────────────
    else:
        fn_map = {
            "🤖 Chatbot Baseline":    chatbot_baseline,
            "⚡ Agent V1 (Basic)":    run_agent_v1,
            "🚀 Agent V2 (Improved)": run_agent_v2,
        }
        fn = fn_map[mode]

        with st.chat_message("assistant"):
            with st.spinner("Đang xử lý..."):
                answer, steps, latency = run_with_capture(fn, user_input)

            st.session_state.total_latency += latency

            # Hiển thị steps nếu là agent
            if steps:
                with st.expander(f"🔍 Agent Steps — {len([s for s in steps if 'Step' in s])} steps · {latency:,}ms", expanded=False):
                    for line in steps:
                        st.markdown(f'<div class="step-log">{line}</div>', unsafe_allow_html=True)

            # Final answer
            st.markdown(answer)

            # Latency badge
            color = "#2e7d32" if latency < 10000 else "#f57f17" if latency < 30000 else "#c62828"
            st.markdown(
                f'<span style="font-size:0.75rem;color:#888">⏱️ {latency:,}ms · {mode}</span>',
                unsafe_allow_html=True
            )

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "steps": steps,
                "latency": latency,
            })

    st.rerun()
