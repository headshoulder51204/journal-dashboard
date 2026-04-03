# Analytica Log Intelligence Dashboard (LLM-Powered)

This project is a modern, high-performance log analysis dashboard that collects and visualizes AI-generated analysis results of system journal logs. It is designed with **iOS Design Principles** (Glassmorphism, clean typography, rounded corners) to provide a premium user experience.

## ✨ Features
- **AI Webhook Integration**: Accepts JSON payloads from LLM servers via `POST /api/webhook/analysis`.
- **90-Day Retention Policy**: Automatically cleans up logs older than 90 days to maintain database performance.
- **Detailed Insights**: Visualizes root cause, recommended actions, and error distribution for each trace.
- **Modern UI**: Clean, responsive dashboard with interactive charts and detailed log entries.

## 🛠 Tech Stack
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, SQLite.
- **Frontend**: Vanilla HTML5, CSS3 (Glassmorphism), JavaScript (Fetch & Chart.js).
- **Icons**: FontAwesome 6.

## 🚀 How to Run
1.  Ensure you have **Python** installed.
2.  Open the project folder in your terminal.
3.  Execute the [run.bat](run.bat) file:
    ```bash
    .\run.bat
    ```
4.  Open your browser and navigate to:
    - **Dashboard**: [http://localhost:8000](http://localhost:8000)
    - **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

## ☁️ Vercel Deployment
This project is pre-configured for Vercel deployment using `vercel.json`.

**Critial Step**:
1.  In your Vercel Project **Settings > General**, ensure **Root Directory** is set to the **Project Root** (empty or `.`), NOT the `backend` folder.
2.  Deploy by pushing to your main branch (Git integration) or using `vercel` CLI.
3.  Vercel will automatically:
    - Serve `frontend/` as static assets.
    - Serve `backend/main.py` as a serverless Python function mapped to `/api`.

## 📡 API Specification (Webhook)
To send a new log analysis to the dashboard:

**Endpoint**: `POST /api/webhook/analysis`
**Payload Example**:
```json
{
  "trace_id": "ALPHA-123",
  "status": "SUCCESS",
  "llm_model": "GPT-4o",
  "severity": "Critical",
  "root_cause": "The incident correlates with a 40% spike in Zombie Connections...",
  "recommendations": ["Action A", "Action B"],
  "anomaly_context": "92% of affected packets show corrupted header metadata...",
  "total_events": 142802,
  "duration": "18m 42s",
  "affected_nodes": 14,
  "error_distribution": { "Timeout Errors": 60, "Auth Failure": 30, "DNS Refusal": 10 },
  "log_entries": [
    {
      "timestamp": "2024-10-24 04:22:31",
      "source": "auth-svc-01",
      "status": "504 TIMEOUT",
      "message": "Upstream connection failed...",
      "stack_trace": "Error: Traceback at...",
      "metadata_info": { "node_id": "US-EAST-1A", "latency": "38s" }
    }
  ]
}
```

## 🛡 License
MIT License. Created by Antigravity AI.

---
**Repository**: [https://github.com/headshoulder51204/journal-dashboard.git](https://github.com/headshoulder51204/journal-dashboard.git)
<p align="center">
  <img src="https://img.shields.io/badge/Maintained%3F-yes-green.svg" alt="Maintained">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
</p>
