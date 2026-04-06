import streamlit as st
import sys
import io
import os
from dotenv import load_dotenv

# Ensure right path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.anthropic_provider import AnthropicProvider
from agent_v1.agent import run_agent as run_agent_v1
from agent_v2.agent import run_agent as run_agent_v2

load_dotenv()

st.set_page_config(page_title="Smart Weather Planner", page_icon="🌤️", layout="wide")

# Custom Stdout to capture print statements and stream them to Streamlit
class StreamlitCapture(io.StringIO):
    def __init__(self, st_container):
        super().__init__()
        self.st_container = st_container
        self.logs = []

    def write(self, text):
        if text.strip():
            self.logs.append(text.strip())
            # We don't update live continuously here to avoid UI flicker,
            # but we save to display at the end.
        return len(text)

st.title("🌤️ Smart Weather Planner AI")
st.markdown("**(Team 2) Chatbot Baseline vs. ReAct Agent Simulation**")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Agent Settings")
    
    agent_mode = st.radio(
        "Choose Mode:",
        ["Baseline Chatbot", "ReAct Agent V1 (Basic)", "ReAct Agent V2 (Improved)"]
    )
    
    st.markdown("---")
    st.markdown("### 💡 Example Queries:")
    st.code("Is it safe to travel to Hanoi today?")
    st.code("What is the weather like in Xanadu City right now?")
    st.code("Should I bring a jacket to Tokyo?")

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "trace" in msg and msg["trace"]:
            with st.expander("🔍 View Agent Internal Steps"):
                st.code(msg["trace"])

# User Input
if prompt := st.chat_input("Ask about weather travel safety..."):
    # Add to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Setup capture
        trace_expander = st.expander("⚙️ Agent is executing... (Live Logs)", expanded=True)
        log_placeholder = trace_expander.empty()
        
        # Override stdout to capture prints
        old_stdout = sys.stdout
        capture = StreamlitCapture(log_placeholder)
        sys.stdout = capture
        
        final_answer = ""
        
        try:
            with st.spinner("Processing..."):
                if agent_mode == "Baseline Chatbot":
                    # Chatbot mode (no tools)
                    provider = AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))
                    sys_prompt = "You are a travel assistant that helps users with weather-related travel advice. Answer based on your general knowledge about weather patterns and seasons. Be helpful but honest if you don't have real-time data."
                    
                    history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages[:-1]])
                    full_prompt = f"{history_text}\nUser: {prompt}" if history_text else prompt
                    
                    print("Connecting to LLM (No tools available)...")
                    result = provider.generate(full_prompt, system_prompt=sys_prompt)
                    final_answer = result["content"]
                    print("\nResponse ready.")
                    
                elif agent_mode == "ReAct Agent V1 (Basic)":
                    final_answer = run_agent_v1(prompt)
                    
                elif agent_mode == "ReAct Agent V2 (Improved)":
                    final_answer = run_agent_v2(prompt)
        except Exception as e:
            final_answer = f"⚠️ System Error: {str(e)}"
        finally:
            sys.stdout = old_stdout # Restore
            
        full_trace = "\n".join(capture.logs)
        log_placeholder.code(full_trace, language="text")
        trace_expander.expanded = False # Collapse when done
        
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer, "trace": full_trace})
