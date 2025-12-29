# launch.py — Streamlit + FastAPI integration (safer for local runs)
import subprocess
import threading
import time
import webbrowser
import sys
import os

def start_fastapi():
    """Launch FastAPI backend in a thread (no --reload to avoid process forking races)."""
    # If you want automatic reload during development, run uvicorn manually:
    # uvicorn app:app --reload
    subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"])

def start_streamlit():
    """Launch Streamlit frontend."""
    subprocess.run(["streamlit", "run", "streamlit_app.py"])

def main():
    # Launch FastAPI backend in a separate thread
    backend_thread = threading.Thread(target=start_fastapi, daemon=True)
    backend_thread.start()

    # Give backend some time to start
    time.sleep(2)

    # Optionally open the frontend in browser automatically
    webbrowser.open("http://localhost:8501")

    # Launch Streamlit frontend (blocks)
    start_streamlit()

if __name__ == "__main__":
    main()