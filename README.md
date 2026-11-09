# ✈️ TripMateAI: AI Multi-Agent Travel Planner

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.48%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange.svg)](https://
|---|---|---|
| **Destination Agent** | Groq (`openai/gpt-oss-20b`) | Analyzes user preferences and suggests a matching tech hub city. |
| **Review Node** | LangGraph `interrupt()` | Halts graph execution and yields control to the human traveler for approval. |
| **Itinerary Agent** | Tavily Search + Groq LLM | Fetches live culture/tech events and drafts a day-by-day bulleted itinerary. |
| **Budget Agent** | Groq LLlangchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Cloud-f55036.svg)](https://groq.com/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

**TripMateAI** is an autonomous multi-agent travel planning system built with **LangGraph**, **FastAPI**, and **Streamlit**. It coordinates specialized AI agents with **Human-in-the-Loop review**, real-time web search (Tavily), live flight data (AviationStack), and persistent storage in PostgreSQL.

---

## 🌟 Key Features

- 🤝 **Multi-Agent Orchestration**: Modular agent architecture powered by LangGraph `StateGraph` with state checkpointing (`MemorySaver`).
- ✋ **Human-in-the-Loop (HITL)**: Uses LangGraph's native `interrupt()` and `Command(resume=...)` to let travelers approve or revise AI-suggested destinations before generating expensive itineraries.
- 🔍 **Real-Time Web Search**: Integrates Tavily AI Search for up-to-date city attractions, cultural events, and hotel recommendations.
- 🛫 **Flight Route Intelligence**: Integrates AviationStack API with automatic fallback to LLM flight route and pricing estimation.
- 💰 **Budget Breakdown**: Computes realistic mid-range USD cost estimates tailored for 3-day visits.
- 💾 **Persistent Database Storage**: Saves finalized travel plans into PostgreSQL with async connection pooling (`asyncpg`).
- 🖥️ **Modern Streamlit Frontend**: User-friendly UI featuring travel presets, interactive approval cards, markdown/JSON export, and trip history browsing.

---

## 🏗️ Multi-Agent Architecture

```
                    [ 1. User Preferences ]
                               │
                               ▼
                 ┌───────────────────────────┐
                 │    Destination Agent      │ ── Groq LLM Suggestion
                 └─────────────┬─────────────┘
                               │
                               ▼  [ LangGraph interrupt() ]
                 ╔═══════════════════════════╗
                 ║   Human-in-the-Loop       ║
                 ║   Streamlit Review        ║ <── Approve or Enter Custom City
                 ╚═════════════╤═════════════╝
                               │ Command(resume=feedback)
                               ▼
                 ┌───────────────────────────┐
                 │      Itinerary Agent      │ ── Tavily Search + 3-Day Plan
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │       Budget Agent        │ ── Realistic USD Estimation
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │       Flight Agent        │ ── AviationStack API / Fallback
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │        Hotel Agent        │ ── Tavily Search + Hotel Details
                 └─────────────┬─────────────┘
                               │
                               ▼
                 ┌───────────────────────────┐
                 │    PostgreSQL Database    │ ── Persistent History via asyncpg
                 └───────────────────────────┘
```

---

## 🤖 The Agents

| Agent | Technology | Role |M | Calculates realistic accommodation, food, and local transit estimates. |
| **Flight Agent** | AviationStack API + Groq | Fetches live flights from origin airport (e.g. `BLR`), with fallback to LLM. |
| **Hotel Agent** | Tavily Search + Groq LLM | Searches and ranks top 3 mid-range hotels with ratings and nightly rates. |

---

## 📁 Project Structure

```text
TripMateAI-AI-Multi-Agent-Travel-Planner-with-LangGraph/
│
├── app/
│   ├── __init__.py           # Package marker
│   ├── config.py             # Environment configuration & variables
│   ├── db.py                 # Async PostgreSQL pool (asyncpg) & table init
│   ├── graph.py              # LangGraph StateGraph, Agents & MemorySaver
│   └── main.py               # FastAPI backend endpoints (/plan, /resume, /trips)
│
├── streamlit_app.py          # Interactive Streamlit frontend
├── requirements.txt          # Python project dependencies
├── .env.example              # Template for environment variables
├── .gitignore                # Git ignore patterns (includes .env)
└── README.md                 # Project documentation
```

---

## ⚙️ Prerequisites & Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/TripMateAI-AI-Multi-Agent-Travel-Planner-with-LangGraph.git
cd TripMateAI-AI-Multi-Agent-Travel-Planner-with-LangGraph
```

### 2. Create a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
# Groq LLM API Key (https://console.groq.com)
GROQ_API_KEY="your_groq_api_key"

# Tavily Search API Key (https://app.tavily.com)
TAVILY_API_KEY="your_tavily_api_key"

# AviationStack Flight API Key (https://aviationstack.com)
AVIATIONSTACK_API_KEY="your_aviationstack_api_key"

# Default Departure Airport IATA Code
DEFAULT_ORIGIN_IATA="BLR"

# PostgreSQL Connection String (Render / Neon / Local)
DATABASE_URL="postgresql://user:password@host/dbname"

# Optional LangSmith Tracing
LANGSMITH_TRACING="false"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your_langsmith_api_key"
LANGSMITH_PROJECT="TripMate-AI"
```

---

## 🚀 How to Run

Running TripMateAI requires two services: the **FastAPI Backend** and the **Streamlit Frontend**.

### 1️⃣ Start the FastAPI Backend
In your first terminal, run:
```bash
uvicorn app.main:app --reload --port 8000
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI Specification: `http://127.0.0.1:8000/openapi.json`

### 2️⃣ Start the Streamlit Frontend
In a second terminal, run:
```bash
streamlit run streamlit_app.py
```
- The frontend will open automatically in your browser at: **`http://localhost:8501`**
- Check the sidebar: A green **🟢 Backend Connected** badge confirms successful API communication.

---

## 🔌 API Endpoints Reference

### 1. `POST /plan`
Initiates a new multi-agent trip planning session. Runs the `destination` agent and pauses at human review.

- **Request Body**:
  ```json
  {
    "preferences": "Leading AI research hubs, robotics labs, cutting-edge tech museums and startup networking."
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "waiting",
    "suggested_destination": "San Francisco",
    "prompt": "AI suggests: San Francisco. Reply 'approve' or type a new city."
  }
  ```

---

### 2. `POST /resume/{thread_id}`
Resumes graph execution with the traveler's feedback (approval or custom city), runs all downstream agents, and saves the final result to PostgreSQL.

- **Request Body (Approve Suggestion)**:
  ```json
  {
    "feedback": "approve"
  }
  ```
- **Request Body (Override with Custom City)**:
  ```json
  {
    "feedback": "Tokyo"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "status": "completed",
    "trip": {
      "destination": "San Francisco",
      "itinerary": "- Day 1: Explore Silicon Valley...\n- Day 2: Visit AI labs...",
      "budget": "$1,200 USD",
      "flights": "- AI175 BLR to SFO: $850 USD",
      "hotels": "1. Hotel Nikko - $210/night, 4.4★\n2. CitizenM - $185/night, 4.5★"
    }
  }
  ```

---

### 3. `GET /trips?limit=10`
Retrieves past saved trips from the PostgreSQL database.

- **Query Parameters**: `limit` (int, default: 10)
- **Response (`200 OK`)**:
  ```json
  [
    {
      "id": 1,
      "destination": "San Francisco",
      "itinerary": "...",
      "budget": "$1,200 USD",
      "flights": "...",
      "hotels": "...",
      "created_at": "2026-11-09 10:30:15"
    }
  ]
  ```

---

## 🗄️ Database Schema

The system automatically initializes the `trips` table in PostgreSQL upon startup:

```sql
CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,
    destination TEXT,
    itinerary TEXT,
    budget TEXT,
    flights TEXT,
    hotels TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🖥️ Streamlit Frontend Walkthrough

1. **✈️ Trip Planner Tab**:
   - Quick one-click preference presets or custom preference input.
   - Live spinner during AI destination search.
   - Interactive human approval card displaying thread ID, suggested city, and options to approve or type a replacement destination.
   - Result dashboard featuring a 3-column layout (Itinerary, Flight routes, Hotel cards, and Budget metric).
   - One-click **Download Markdown** or **Export JSON** actions.
2. **📚 Saved Trips Database Tab**:
   - Browse through stored travel plans saved in PostgreSQL.
   - Expandable view for each trip with full itinerary details and timestamps.
3. **🧩 Architecture Flow Tab**:
   - Flow diagram and API contract references.

---

## 🛠️ Troubleshooting

- **FastAPI backend won't start (`ModuleNotFoundError`)**:
  Ensure you are running uvicorn from the project root:
  ```bash
  uvicorn app.main:app --reload --port 8000
  ```
- **Streamlit shows `🔴 Backend Offline`**:
  Make sure your FastAPI server is running on `http://127.0.0.1:8000`. You can also update the backend URL directly in the Streamlit sidebar.
- **Database connection error**:
  Check your `DATABASE_URL` in `.env`. Ensure it begins with `postgresql://` and that network access to your PostgreSQL host (e.g. Render/Neon) is allowed.
- **Groq API rate limits**:
  Verify your `GROQ_API_KEY` is active at [console.groq.com](https://console.groq.com/).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
