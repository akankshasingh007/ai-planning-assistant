# ai-planning-assistant
AI Personal Productivity Assistant
A smart AI assistant that helps you plan your day, manage tasks, and stay productive. Talk naturally, and let the AI handle scheduling, task management, and self-reflection.

 #Features

Add Tasks – Quickly add tasks by typing what you need to do.
Schedule Tasks – AI suggests optimal times and integrates your tasks into a schedule.
Complete Tasks – Mark tasks as done directly from the interface.
Task Overview – See pending and completed tasks at a glance.
Self-Reflection – Get a summary of your productivity and focus next steps.
Fast Response – Uses background scheduling for instant feedback while planning.

 #Tech Stack

Backend: FastAPI for AI task management and scheduling.
Frontend: Streamlit for a user-friendly interface.
AI: Lightweight agent using NLP for task parsing and intent recognition.
Memory: JSON-based local task memory.
Scheduler: Background scheduling with planner integration.

#How It Works

User sends a command (e.g., “Add a meeting tomorrow at 10am”).
AI parses the input, determines intent, and decides whether to:
Add a task immediately
Ask for missing time information
Schedule the task in the background

Running the App

Start the FastAPI backend:
        uvicorn app:app --reload
Open the Streamlit frontend:
     streamlit run streamlit_app.py

Tasks are stored in memory and displayed in the Streamlit app.

AI can also perform self-reflection to summarize completed vs. pending tasks.
