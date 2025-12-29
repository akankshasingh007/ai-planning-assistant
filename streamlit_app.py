import streamlit as st
import requests
from datetime import datetime

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Planning Assistant", page_icon="🧭", layout="wide")

st.markdown("""
<style>
.assistant-box { background:#0f1720; color:#e6eef8; padding:14px; border-radius:12px; margin-bottom:8px; }
.user-box { background:#071029; color:#cfe9ff; padding:12px; border-radius:12px; margin-bottom:8px; text-align:right; }
.panel { background:#0b1220; padding:14px; border-radius:12px; margin-bottom:8px; }
.task-title { font-weight:600; }
</style>""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state: st.session_state.messages = [{"role":"assistant","text":"👋 Hi — I'm your AI assistant."}]
if "tasks" not in st.session_state: st.session_state.tasks = []
if "awaiting_time" not in st.session_state: st.session_state.awaiting_time = False
if "pending_task_title" not in st.session_state: st.session_state.pending_task_title = None
if "last_raw" not in st.session_state: st.session_state.last_raw = None

# Helpers
def fetch_tasks():
    try:
        r = requests.get(f"{API_BASE}/tasks", timeout=5)
        if r.status_code == 200:
            st.session_state.tasks = r.json().get("result", {}).get("tasks", [])
        else:
            st.session_state.tasks = []
            st.session_state.last_raw = {"http_status": r.status_code, "text": r.text}
    except Exception as e:
        st.session_state.tasks = []
        st.session_state.last_raw = {"error": str(e)}

def call_agent(user_id: str, goal: str):
    """
    Improved call to backend that returns rich debug info on non-200 or non-JSON responses.
    """
    try:
        r = requests.post(f"{API_BASE}/mcp/act", json={"user_id": user_id, "goal": goal}, timeout=30)
        # Try to parse JSON body if possible
        try:
            body = r.json()
        except Exception:
            body = None

        if r.status_code != 200:
            # Return helpful debug details so the UI can show them
            return {"result": {"message": f"⚠️ Backend returned HTTP {r.status_code}: {r.text}", "http_status": r.status_code, "raw_text": r.text, "body": body}} 

        if not r.text.strip():
            return {"result": {"message": "⚠️ Backend returned empty response."}}

        return body or {"result": {"message": "⚠️ Backend returned non-JSON response.", "raw_text": r.text}}
    except Exception as e:
        return {"result": {"message": f"🚨 Agent unreachable: {e}"}}

def complete_task(task_id): 
    call_agent(user_id, f"complete task {task_id}")
    fetch_tasks()

# Header
h1,h2 = st.columns([3,1])
with h1:
    st.title("🧭 AI Personal Productivity Assistant")
    st.caption("Talk naturally. Tasks appear on the right.")
with h2:
    user_id = st.text_input("User ID", value="demo_user", label_visibility="collapsed")

if not st.session_state.tasks: fetch_tasks()

# Layout
left,right = st.columns([3,1])

with left:
    for m in st.session_state.messages:
        box_class = "assistant-box" if m["role"]=="assistant" else "user-box"
        st.markdown(f"<div class='{box_class}'>{m['text']}</div>", unsafe_allow_html=True)
    st.markdown("---")

    user_msg = st.text_input("Say something", key="input")
    if st.button("Send"):
        if not user_msg: st.stop()
        st.session_state.messages.append({"role":"user","text":user_msg})

        if st.session_state.awaiting_time:
            data = call_agent(user_id, user_msg)
            st.session_state.last_raw = data
            st.session_state.awaiting_time = False
            st.session_state.pending_task_title = None
            st.session_state.messages.append({"role":"assistant","text":"✅ Scheduled. Anything else?"})
            fetch_tasks()
        else:
            data = call_agent(user_id, user_msg)
            st.session_state.last_raw = data
            result = data.get("result", {})
            if result.get("needs_time"):
                st.session_state.awaiting_time = True
                st.session_state.pending_task_title = result.get("title")
                st.session_state.messages.append({"role":"assistant","text":"⏰ When should I schedule this?"})
            else:
                assistant_text = result.get("message") or "🤖 All set. What’s next?"
                st.session_state.messages.append({"role": "assistant", "text": assistant_text})
            fetch_tasks()

with right:
    st.subheader("Tasks")
    if st.session_state.tasks:
        for t in st.session_state.tasks:
            title = t.get("title","(untitled)")
            status = t.get("status","pending")
            start = t.get("start","")
            st.markdown(f"<div class='panel'><div class='task-title'>{title}</div><div>Status: {status}{(' • ' + start) if start else ''}</div></div>", unsafe_allow_html=True)
            if status != "done" and st.button("✅ Mark done", key=t["id"]):
                complete_task(t["id"])
    else:
        st.write("No tasks yet.")

    st.markdown("---")
    st.caption(f"Local time: {datetime.now().isoformat()}")
    with st.expander("Debug: last assistant JSON"):
        st.json(st.session_state.last_raw)