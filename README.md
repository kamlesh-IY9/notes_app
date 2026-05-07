<div align="center">
  <h1>🤖 AI Phone Notes Generator Pipeline</h1>
  <p>A robust, end-to-end pipeline designed to generate high-quality, AI-detection-resistant training datasets consisting of synthetic phone notes. The application automatically generates authentic, fragmented, human-like text and renders pixel-perfect screenshots mirroring native device note apps.</p>
</div>

---

## 🌟 Key Features

### 🌍 Global Localization (English, Hindi, Arabic)
The pipeline is fully equipped for multi-regional synthetic dataset generation:
- **US / English:** Western personas, realistic US cities/carriers, standard numerals.
- **India / Hindi:** Full Devanagari support, localized Indian personas, regional app icons (Truecaller, Paytm), and seamless translation matrices.
- **Gulf & MENA / Arabic:** Proper Right-to-Left (RTL) screenshot rendering, localized Arabic fonts (Noto Sans/Naskh), 50/50 mix of Arabic-Indic/Western numerals, and hyper-local personas across Morocco, Egypt, Levant, and the Gulf.

### 🎨 Hyper-Realistic Visual Engine
- **143+ Device Themes:** Generates completely unrepeated visual aesthetics using solid colors, rich neons, exotic gradients, and 25+ textural patterns (honeycomb, circuit board, aurora, linen).
- **Region-Aware Status Bars:** Dynamically picks region-appropriate app icons (e.g., heavy WhatsApp/Telegram usage for Arabic; Truecaller/PhonePe for Hindi; Snapchat/Discord for English).
- **Authentic Device Dimensions:** Screenshots are rendered randomly across real-world screen dimensions corresponding to the simulated app:
  - iPhone 14/15 Pro (Apple Notes)
  - Galaxy S23 (Samsung Notes)
  - Pixel 7 (Google Keep)
  - Randomised Xiaomi/Redmi devices (MIUI Notes)

### 🧠 Intelligent Orchestration & Generation
- **LLM Fallback Chain:** Implements a highly resilient `auto` fallback chain utilizing lightning-fast providers (Cerebras, Groq, Together.ai) backed up by heavy models (Gemini 2.0 Flash, NIM, OpenRouter) to easily handle rate limits during massive 1,000+ note batches.
- **Smart Persona Engine:** Selects specific occupations, ethnicities, quirks, and relationship networks to inject deep human authenticity into every note.

---

## 🎯 Target Categories

The generator currently targets four primary note categories:

1. 🧑‍🤝‍🧑 **People & Relationships (P&R):** Informal thoughts, venting, updates, reminders, or relationship observations about friends, partners, family members, and colleagues.
2. 📇 **Contact Notes:** Name-drops, situational context, professional contacts, saved business details, or brief interactions with service workers and acquaintances.
3. 📅 **Event Notes:** Structured plans including titles, dates, times, and specific locations (e.g., "Dinner with Mom at Starbucks", "Project Sync in Room 3B").
4. 🧠 **Topic of Interest (TOI):** Deep informational captures such as lecture notes, technical meeting minutes, or expert instructions.

---

## ⚖️ Strict Data Guidelines (Client Driven)

To ensure datasets pass rigorous QA, the pipeline and generated content heavily adhere to the following strict rules:
* **Natural Content:** Text must perfectly mimic human fragmentation, typos, and shorthand. Overly formal or AI-sounding prose is immediately rejected.
* **Factual Consistency:** Information in TOI notes must reflect the real world exactly (e.g., real parameters, actual historical data). Hallucinations are strictly forbidden.
* **Category Enforcement:** 
  - "Travel" cannot just be boarding processes; it must encompass actual travel concepts.
  - "Automotive" is strictly about cars/vehicles.

---

## 🛠 Tech Stack

- **Backend:** FastAPI, Python, SQLite, Playwright (for headless DOM rendering)
- **Frontend:** React + Vite + TypeScript
- **LLM Engine:** Cerebras (primary), Groq, Gemini, NVIDIA NIM, OpenRouter, Together.ai, GLM
- **Translators:** Integrated Google Translate / Deep-Translator API

---

## 🚀 Setup & Usage

1. **Environment Setup:** Ensure `.env` is populated with the required API keys (Cerebras, Groq, Gemini, etc.).
2. **Launch Backend:** 
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
3. **Launch Frontend:** 
   ```bash
   cd frontend && npm run dev
   ```
4. **Localization Utilities:** Use `translate_to_hindi.py` for post-process batch Devanagari translation if needed.

---

## 📂 Project Structure

```text
notes_app/
├── backend/               # FastAPI backend
│   ├── api/               # REST & SSE endpoints
│   ├── core/              # Generators (P&R, Contact, Event, TOI), Translation, Rendering
│   ├── config/            # Regional YAML configs (Arabic, India, Global)
│   └── templates/         # HTML/CSS templates for iOS, Samsung, Keep, and MIUI
├── frontend/              # React UI (Theme & Locale selectors)
├── output/                # Artifacts (Notes text, JPG Screenshots, SQLite DB)
├── requirements.txt       # Python dependencies
└── README.md              # Documentation
```
