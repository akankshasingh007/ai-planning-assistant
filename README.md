# AI Planning Assistant 

A lightweight AI-powered daily planning assistant built for hackathons.
It helps users add tasks, get smart scheduling suggestions, and manage their day efficiently.

---

## Features
- Add tasks instantly
- Smart task scheduling
- Real-time updates
- Simple UI
- FastAPI backend + Streamlit frontend

---

##  Tech Stack
- Frontend: Streamlit
- Backend: FastAPI
- Language: Python

---

##  Project Structure
.
├── app.py
├── streamlit_app.py
├── planner.py
├── task_memory.py
├── requirements.txt
└── README.md

---

##  Setup Instructions

### 1. Clone the repository
git clone <repo-url>
cd <project-folder>

### 2. Create virtual environment
python -m venv .venv

Activate:
Windows:
.venv\Scripts\activate

Mac/Linux:
source .venv/bin/activate

### 3. Install dependencies
pip install -r requirements.txt

---

##  How to Run

### Start backend
uvicorn app:app --reload

Backend runs at:
http://127.0.0.1:8000

### Start frontend (new terminal)
streamlit run streamlit_app.py

---

## Usage
1. Open the Streamlit app
2. Add tasks
3. Get AI scheduling
4. Mark tasks complete

---

