
import os
import streamlit as st
import requests

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="AI Assistant", page_icon="🧭", layout="wide")
st.title("🧭 AI Productivity Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "text": "👋 Hi — I'm your AI assistant."}]
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "awaiting_time" not in st.session_state:
    st.session_state.awaiting_time = False
if "pending_task_id" not in st.session_state:
    st.session_state.pending_task_id = None
if "busy" not in st.session_state:
    st.session_state.busy = False
if "last_raw" not in st.session_state:
    st.session_state.last_raw = None
if "persona" not in st.session_state:
    st.session_state.persona = "default"
if "user_id_input" not in st.session_state:
    st.session_state.user_id_input = "demo_user"
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def fetch_tasks():
    try:
        r = requests.get(f"{API_BASE}/tasks", timeout=5)
        if r.status_code == 200:
            st.session_state.tasks = r.json().get("result", {}).get("tasks", [])
        else:
            st.session_state.tasks = []
    except Exception:
        st.session_state.tasks = []

def call_agent(user_id: str, goal: str, task_id: str = None, persona: str = None):
    payload = {"user_id": user_id, "goal": goal}
    if task_id:
        payload["task_id"] = task_id
    if persona:
        payload["persona"] = persona
    try:
        r = requests.post(f"{API_BASE}/mcp/act", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"result": {"message": f"Agent unreachable: {e}"}}

def complete_task_api(task_id: str):
    try:
        r = requests.post(f"{API_BASE}/tasks/{task_id}/complete", timeout=10)
        if r.status_code == 200:
            return r.json()
        return {"status": "error", "message": r.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def reflect_api(user_id: str):
    try:
        r = requests.get(f"{API_BASE}/mcp/reflect", params={"user_id": user_id}, timeout=10)
        if r.status_code == 200:
            return r.json()
        return {"status": "error", "message": r.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

left, right = st.columns([3,1])
with left:
    st.markdown("Enter commands below and press Enter to send. Examples: `add presentation prep`, `schedule meeting tomorrow 2pm`, `summarize my tasks`.")
with right:
    st.text_input("User ID", value=st.session_state.get("user_id_input", "demo_user"), key="user_id_input")
    st.selectbox("Persona", ["default", "developer", "product_manager", "team_lead"],
                 index=["default","developer","product_manager","team_lead"].index(st.session_state.get("persona", "default")),
                 key="persona")

for m in st.session_state.messages:
    if m["role"] == "assistant":
        st.markdown(f"> {m['text']}")
    else:
        st.markdown(f"**You:** {m['text']}")

def submit():
    user_msg = st.session_state.get("user_input", "").strip()
    user_id = st.session_state.get("user_id_input", "demo_user").strip() or "demo_user"
    persona = st.session_state.get("persona", "default")
    if not user_msg:
        return
    if st.session_state.get("busy"):
        return
    st.session_state.busy = True
    st.session_state.messages.append({"role": "user", "text": user_msg})

    if st.session_state.get("awaiting_time") and st.session_state.get("pending_task_id"):
        res = call_agent(user_id, user_msg, task_id=st.session_state.get("pending_task_id"), persona=persona)
       
        st.session_state.awaiting_time = False
        st.session_state.pending_task_id = None
    else:
        res = call_agent(user_id, user_msg, persona=persona)

    result = res.get("result", {}) if isinstance(res, dict) else {}
 
    if result.get("needs_time"):
        prompt = result.get("message") or f"When should I schedule '{result.get('title')}'?"
        st.session_state.messages.append({"role": "assistant", "text": prompt})
        st.session_state.awaiting_time = True
        st.session_state.pending_task_id = result.get("task_id")
    else:
        message = result.get("message") or res.get("message") or "Done."
        st.session_state.messages.append({"role": "assistant", "text": message})

    st.session_state.last_raw = res
    fetch_tasks()
    st.session_state.user_input = ""  
    st.session_state.busy = False

st.text_input("Your message", key="user_input", on_change=submit, placeholder="Type and press Enter (e.g. 'add presentation prep')")

st.markdown("---")

c1, c2 = st.columns(2)
with c1:
    if st.button("Reflect"):
        if not st.session_state.busy:
            st.session_state.busy = True
            res = reflect_api(st.session_state.get("user_id_input", "demo_user"))
            if res.get("status") == "ok":
                r = res["result"]
                st.session_state.messages.append({"role":"assistant","text": r.get("message")})
                st.info(f"Completed: {len(r.get('completed', []))}  •  Pending: {len(r.get('pending', []))}  •  Pending effort: {r.get('estimate', {}).get('total_minutes',0)} min")
                st.session_state.last_raw = res
            else:
                st.error(res.get("message", "Reflect failed"))
            st.session_state.busy = False
with c2:
    if st.button("Summarize tasks"):
        if not st.session_state.busy:
            st.session_state.busy = True
            res = call_agent(st.session_state.get("user_id_input", "demo_user"), "summarize my tasks", persona=st.session_state.get("persona", "default"))
            msg = res.get("result", {}).get("message", res.get("message", "No response"))
            st.session_state.messages.append({"role":"assistant","text": msg})
            st.session_state.last_raw = res
            st.session_state.busy = False

if st.button("Estimate pending effort"):
    if not st.session_state.busy:
        st.session_state.busy = True
        res = call_agent(st.session_state.get("user_id_input", "demo_user"), "estimate effort", persona=st.session_state.get("persona", "default"))
        msg = res.get("result", {}).get("message", res.get("message", "No response"))
        st.session_state.messages.append({"role":"assistant","text": msg})
        st.session_state.last_raw = res
        st.session_state.busy = False

st.markdown("---")
st.subheader("Tasks")
fetch_tasks()
if st.session_state.tasks:
    for t in st.session_state.tasks:
        title = t.get("title", "(untitled)")
        status = t.get("status", "pending")
        start = t.get("start") or ""
        cols = st.columns([10,1])
        cols[0].markdown(f"**{title}** — {status}{(' • ' + start) if start else ''}")
        
        if status != "done":
            if cols[1].button("✅", key=f"done-{t['id']}"):
                resp = complete_task_api(t["id"])
                if resp.get("status") == "ok" or resp.get("status") is None:
                    st.success("Task completed")
                    fetch_tasks()
                else:
                    st.error(resp.get("message", "Failed to complete task"))
else:
    st.write("No tasks yet.")

st.markdown("---")
st.write("Debug:")
st.json(st.session_state.last_raw or {"status": "no response yet"})