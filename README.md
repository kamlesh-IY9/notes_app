# 🤖 AI Phone Notes Generator Pipeline

A robust, end-to-end pipeline designed to generate high-quality, AI-detection-resistant training datasets consisting of phone notes. The application automatically generates authentic, fragmented, human-like text and renders pixel-perfect screenshots mirroring native device note apps.## 🎯 Target Categories

The generator now supports four primary note categories, each with strict validation rules:

- 🧑‍🤝‍🧑 **People & Relationships (P&R) Notes:** Informal thoughts, venting, updates, reminders, or relationship observations about friends, partners, family members, and colleagues.
- 📇 **Contact Notes:** Name-drops, situational context, professional contacts, saved business details, or brief interactions with service workers and acquaintances.
- 📅 **Event Notes:** Structured plans including titles, dates, times, and specific locations (e.g., "Dinner with Mom at Starbucks", "Project Sync in Room 3B").
- 🧠 **Topic of Interest (TOI) Notes:** Deep informational captures such as lecture notes, technical meeting minutes, or expert instructions (e.g., sound engineering parameters, meteorological patterns, market analysis).

---

## 🇮🇳 Hindi Localization & Translation

The pipeline now includes a robust Hindi (hi-IN) translation and re-rendering engine:

- **Full Devanagari Support:** Translates all text, including names, while preserving technical entities like emails and phone numbers.
- **Automatic Screenshot Re-rendering:** The `translate_to_hindi.py` script automatically updates generated `.jpg` screenshots with Devanagari text using compatible fonts.
- **Batch Translation:** Supports translating entire output folders from English to Hindi in one pass.

### Usage:
```bash
python3 translate_to_hindi.py "output/input_folder/notes" "output/hindi_output_folder"
```

---

## ✨ Advanced Features

- **Event & TOI Generators:** Specialized logic for generating high-fidelity event scheduling and deep-interest notes.
- **Regional Personalization:** Support for India-specific names, personas, and topics via YAML configurations in `backend/config/`.
- **Deduplication & Humanization:** Enhanced multi-pass architecture to ensure notes feel like real, handwritten or mobile-typed entries.

---

## 🛠 Tech Stack

- **Backend:** FastAPI, SQLite, Playwright.
- **Frontend:** React + Vite + TypeScript.
- **LLM Engine:** Groq (primary), Gemini, NVIDIA NIM, OpenRouter, GLM.
- **Translation:** Integrated Google Translate API (Free) for localization.

---

## 🚀 Setup & Usage

1. **Setup Environment:** Ensure `.env` contains necessary API keys.
2. **Backend:** `uvicorn backend.main:app --reload --port 8000`
3. **Frontend:** `cd frontend && npm run dev`
4. **Localization:** Use `translate_to_hindi.py` for Devanagari support.

---

## 📂 Project Structure (Updated)

```text
notes_app/
├── backend/               # FastAPI backend
│   ├── api/               # REST & SSE endpoints
│   ├── core/              # Generators (P&R, Contact, Event, TOI), Translator
│   ├── config/            # Regional YAML configs (India/Global)
│   └── db/                # Migration & database logic
├── frontend/              # React UI
├── output/                # Organized artifacts (Notes, Screenshots, Batches)
├── translate_to_hindi.py  # Devanagari translation & re-rendering utility
├── organize_notes.py      # Output organization script
├── requirements.txt       # Updated dependencies
└── README.md              # Documentation
```
. - Boarding process for example is not Travel.
- No about traveling.
- Automative category is about cars only


-- client feedback batch 3 - TOPICS OF INTEREST_Notes - All rejected
- not natural
- the content does not match real information




Information that does not reflect the real world.
