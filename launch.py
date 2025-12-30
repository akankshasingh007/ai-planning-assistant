
import subprocess
import threading
import time
import webbrowser
import sys
import os

def start_fastapi():
    subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"])

def start_streamlit():
    subprocess.run(["streamlit", "run", "streamlit_app.py"])

def main():
    backend_thread = threading.Thread(target=start_fastapi, daemon=True)
    backend_thread.start()

    time.sleep(2)
    webbrowser.open("http://localhost:8501")

    start_streamlit()

if __name__ == "__main__":
    main()