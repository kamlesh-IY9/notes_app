# 🤖 AI Phone Notes Generator Pipeline

A robust, end-to-end pipeline designed to generate high-quality, AI-detection-resistant training datasets consisting of phone notes. The application automatically generates authentic, fragmented, human-like text and renders pixel-perfect screenshots mirroring native device note apps.

## 🎯 Target Categories

This generator is strictly tuned and optimized for two core note variants:
- 🧑‍🤝‍🧑 **People & Relationships (P&R) Notes:** Informal thoughts, venting, updates, reminders, or relationship observations about friends, partners, family members, and colleagues.
- 📇 **Contact Notes:** Name-drops, situational context, professional contacts, saved business details, or brief interactions with service workers and acquaintances.

## ✨ Core Features

- **Multi-LLM Asynchronous Generation:** Uses `Groq` instances with fallback to `NVIDIA NIM`, `OpenRouter`, and `GLM` to aggressively bypass API rate limits during bulk generation.
- **Two-Pass "Humanization" Architecture:** Generates initial raw notes and follows up with an AI Humanizer pass (`Pass B`) to introduce natural imperfections, abbreviations, slang, and rhythmic variations to break traditional AI stylometric fingerprints.
- **Strict Validation & Deduplication:** Pipeline includes a 12-point validation check (US-English norms, banned AI vocab, name-gender consistencies) and an advanced 6-layer deduplication engine using Levenshtein distance matching.
- **Authentic Synthetic Formatting:** Prompts strictly enforce raw, choppy, single-line thoughts, mimicking genuine "note-to-self" mobile behaviors.
- **Pixel-Accurate Screenshot Renderer:** Employs Playwright to render simulated screenshots. Supports Apple Notes, Google Keep, Samsung Notes, and 14 custom MIUI Notes templates (complete with variable status bars, real-time-accurate clocks, generated notifications, battery metrics, etc.).

---

## 🛠 Tech Stack

- **Backend:** FastAPI, SQLite (for batching & deduplication logs), Playwright.
- **Frontend:** React + Vite + TypeScript interface with Server-Sent Events (SSE) tracking.
- **LLM Engine:** Groq, NVIDIA NIM, OpenRouter, GLM, and Google GenAI.

---

## 🚀 Setup on a New System

### Prerequisites

- **Python 3.11+** (required)
- **Node.js 18+** and **npm** (for frontend)
- **Git** (to clone the repo)

### 1. Clone the Repository

```bash
git clone https://github.com/kamlesh-IY9/notes_app.git
cd notes_app
```

### 2. Create Python Virtual Environment & Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Upgrade pip and install exact requirements
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

Playwright needs browser binaries for screenshot rendering:

```bash
playwright install chromium
```

### 4. Setup Environment Variables

The `.env` file is safely included in this private repository with all your API keys properly configured. 
If setting up from scratch without it, use the template:

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

**Required keys**: `GROQ_API_KEY`, `GEMINI_API_KEY`, `NIM_API_KEY`
**Optional keys**: `OPENROUTER_API_KEY`, `GLM_API_KEY` (pipeline gracefully falls back if absent or rate-limited)

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 🏃‍♂️ Running the Services

### 1. Start the Backend

```bash
# Ensure your virtual environment is active!
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

### 2. Start the Frontend

In a separate terminal tab:
```bash
cd frontend
npm run dev
```

### 3. Dashboard Access

Navigate to `http://localhost:5173` to configure batches and monitor live artifact generation!

---

## 🧪 Quick Smoke Test

For rapid pipeline validation without the frontend dashboard, a smoke-test script is provided:

```bash
source .venv/bin/activate
python -m backend.full_smoke
```

---

## 📂 Project Structure

```text
notes_app/
├── backend/               # FastAPI backend
│   ├── api/               # REST & SSE endpoints
│   ├── core/              # LLM clients, orchestrator, screenshot renderer
│   ├── config/            # Settings & configuration
│   ├── db/                # SQLite database layer
│   └── tests/             # Backend tests
├── frontend/              # React + Vite + TypeScript UI
│   └── src/               # Frontend source code
├── scripts/               # Utility scripts
├── sample/                # Sample data representations
├── output/                # Generated output (screenshots, text, sqlite logs)
├── .env                   # Live API keys (Private)
├── .env.example           # Template for environment variables
├── pyproject.toml         # Python project metadata & dependencies
├── requirements.txt       # Frozen pip dependencies for precise setups
├── the-humanizer.md       # Target humanization behavior constraints and guidelines
└── README.md              # Documentation
```

---

## 💡 Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| `ModuleNotFoundError` | Verify `.venv` is activated and `pip install -r requirements.txt` executed successfully. |
| Playwright browser missing | Run `playwright install chromium` |
| Rate limit errors | Pipeline auto-falls back to other LLM providers. Add additional API keys in `.env` if throttling persists. |
| Frontend won't start | Ensure you run `npm install` inside the `frontend/` directory first. |
