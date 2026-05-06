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
# python3 -m venv .venv
# source .venv/bin/activate        # Linux/macOS
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



Done. Here's the summary:

All 159 files re-translated — every word including names is now in Devanagari. Only pure phone numbers and email addresses stay as-is.

Your clean reusable script for the future: translate_to_hindi.py


# For P&R notes:
python3 translate_to_hindi.py \
  "output/your-job-folder/notes" \
  "output/your-hindi-output"

# For contact notes:
python3 translate_to_hindi.py \
  "output/your-contacts-folder/notes" \
  "output/your-hindi-contacts-output"
No API keys needed — uses Google Translate (free)
Converts everything to Devanagari including names
Re-renders .jpg screenshots with Devanagari font automatically
Works on any folder of .txt notes



so now we alrady dong the p and r and contat note catrgory right now we need to go for other categorys also sof or that will provid eall the clients feedbakc and rules and all okay and also all the samples okay and also follow the samel ike above rule for both languae just new categorye (What do you want to generate?) okay 

--


so i will give you example in enlish but we need to creat in hinid nd for indi okay so make usre tha talso okay. this is give you for example so you can know okay.

and what every i every geneart also hard core the ruels it has all has to be not any thing relate to beorer 2021 year okay aftter 2021 all data if anythig like that is included okay.

--

goldern sample - /home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/Event notes sample/Notes

check all okay txt and jpg okay.

--

1. General Rules for All Notes (Common)
Is it real?:
• It must be a real note written by you, not something made up by an AI or
copied from a generic source.
Is it recent?:
• It should be from the last 5 years (2021~now).
Is it from your assigned country?:
• The data must be generated in the country you are assigned to.
Is it the right file?:
• It must be a file. If you can't export it natively from your app, copying
the text into a file is perfectly fine!

.txt
.txt
Is it readable?:
• Make sure the text is clear, even if there are typos or grammar mistakes
(those are actually okay, as long as it's real!).
No spam!:
• Avoid simple product ads or junk mail content.

Anti-AI Evidence (Required)!:
• No Evidence = Rejection. You MUST submit a separate screenshot as proof
that the note is real and not AI-generated.
• Physical Notes: Submit a photo of the actual handwritten paper.
• Submit a screenshot from the app that clearly shows the
creation date and modification history.
Digital Notes:

Metadata check!:
• You must record the following info in the metadata sheet: age, gender,
country, occupation, primary, secondary, topics of interest, application
used, OS, device info, YYYY.MM.DD.
• Use these ranges: ["18-25","26-35","36-45","46-60", "60+",
"prefer_not_to_say"]
Age Scope:

• YYYY.MM.DD must be the

, not the submission date.

Date (Crucial): actual date the note was
originally written or modified
Evidence check!:
• Notes data must always be accompanied by a corresponding screenshot as
proof.
• Please note that verifying the date through TXT file properties is not
acceptable; the screenshot itself must clearly show the date the note was
written.
Geographic Data Restrictions!
• If the assigned language is , the data must not include any
information collected from the states of . Also,
participants must not reside in these states.


-- 

3. Is it for an Event?
What is the plan?:
• There must be a title or a clear description (e.g., "Dinner with Mom" or
"Project Sync").
When is it?:
• A date is required. (Times are even better!)
Where is it?:
• A location must be shown (e.g., "Starbucks" or "Room 3B").
• Routine appointments or globally unique
locations (e.g., "Eiffel Tower") are acceptable.


--

client feedack batch - 1

EVENT - 138 of 200 accepted (69%)
Notes

1. Strange template-style writing. People usually don't write Anchorage Alaska or San Francisco, California. They just write SF or Alaska or just saying home, bar is more natural.
2. Not native writing - 4959 living alone or 4966 make mozarella (grammatically very incorrect and  not native at all) Or "practice for  spanish  language" or "Drive for LA " is definitely not native.
3. Template written texts. All the text look the same. Title>full time/date, in.. (place, City+State)
4. Texas, Illinois, or Washington is not allowed
5. Wrong data. 
Example: tatum is puting googly eyes on everything in her fridge on dec 14 at 8pm at her place in Santa Fe. , 
"Sandra is  a making deep dish pizzas at my appartment on saterday, aug 14 at 6pm in Kimberly's home  so dont be late." It says "my appartment" but then  "Kimberly's home"


- Not a native structure


---
client feedback batch - 2

Notes - Event
174 accepted
- Not Natural
- Texas,illinoi,Washington
- Not specific location



--

client feedbakc batch - 3
EVENT_Notes
92 accepted
- too short
- tiltle is not good enough

No titile

__



----

and now im givieng you the other category is 

To pic of intreset TOI file snotes i will same provide all like i provide you in event right okay.

/home/kamleshpatil/Desktop/Notes - PR and ontata/notes_app/TOI notes sample/Notes-20260506T175626Z-3-001/Notes

golden sample above path -

--

 1. General Rules for All Notes (Common)
Is it real?:
• It must be a real note written by you, not something made up by an AI or
copied from a generic source.
Is it recent?:
• It should be from the last 5 years (2021~now).
Is it from your assigned country?:
• The data must be generated in the country you are assigned to.
Is it the right file?:
• It must be a file. If you can't export it natively from your app, copying
the text into a file is perfectly fine!

.txt
.txt
Is it readable?:
• Make sure the text is clear, even if there are typos or grammar mistakes
(those are actually okay, as long as it's real!).
No spam!:
• Avoid simple product ads or junk mail content.

Anti-AI Evidence (Required)!:
• No Evidence = Rejection. You MUST submit a separate screenshot as proof
that the note is real and not AI-generated.
• Physical Notes: Submit a photo of the actual handwritten paper.
• Submit a screenshot from the app that clearly shows the
creation date and modification history.
Digital Notes:

Metadata check!:
• You must record the following info in the metadata sheet: age, gender,
country, occupation, primary, secondary, topics of interest, application
used, OS, device info, YYYY.MM.DD.
• Use these ranges: ["18-25","26-35","36-45","46-60", "60+",
"prefer_not_to_say"]
Age Scope:

• YYYY.MM.DD must be the

, not the submission date.

Date (Crucial): actual date the note was
originally written or modified
Evidence check!:
• Notes data must always be accompanied by a corresponding screenshot as
proof.
• Please note that verifying the date through TXT file properties is not
acceptable; the screenshot itself must clearly show the date the note was
written.
Geographic Data Restrictions!
• If the assigned language is , the data must not include any
information collected from the states of . Also,
participants must not reside in these states.


--

5. Is it about a Topic of Interest?
Is it a deep capture?
• Avoid very simple notes like "Buy milk" or "Go to gym."
• We prefer notes that

(e.g., lecture notes, technical meeting minutes, expert
instructions). (FAIL if only simple personal thoughts/diaries/reviews).
Prefer Recorded Info: capture information delivered
by others

No Recipes/Tips:
• Recipes are NOT considered deep interest. (FAIL)
• (e.g., natural disaster safety tips, survival tips) are NOT
considered deep interest. (FAIL)
General Tips

Focus on the music/movie/TV show

itself (composition, technical analysis).
Focus on the work? (Music/Movie/TV)

NO Gossip/Athletes:
• Do not include content about individual actors, artists, celebrity gossip, or
. Focus only on the work, production, or technical

aspects of the sport itself.
individual athletes/players

Quantity Limit:
• You can submit a maximum of 2~3 data assets for a single detailed
'interest/topic' per contributor to ensure diversity.
Health & Fitness Warning!:
• While workout plans or food logs are okay, NEVER submit medical
consultations, insurance info, or sensitive disease records!

Realistic "Deep Interest" Examples (Recorded Info)
[!IMPORTANT] These examples are for reference only. Do NOT copy or
recreate these exact topics!
※ WARNING: Submissions that copy or closely mimic these examples will be
strictly REJECTED due to lack of originality and failure to follow guidelines.

1. Sports
• Detailed instructions or session notes dictated by a professional coach.
• Note: NO athlete gossip or personal player stats.

2. Movies/TV-Shows
• Detailed notes summarizing a professional screenwriting workshop or a
director's talk.
• Note: Avoid personal fan theories; prioritize info recorded from expert/formal
sources.

3. Music
• Technical session notes from a sound engineering masterclass or a professional
mixing workshop.

4. Food
• Technical brewing parameters or fermentation steps provided by a master baker
or brewmaster.
• Note: NO Recipes.

5. Arts & Crafts (Hobbies)
• Notes from a workshop on advanced art conservation or specialized pottery
techniques.

6. Automotive
• Professional maintenance specifications or technical service instructions from a
car manufacturer manual.

7. Technology
• Study notes summarizing a textbook chapter on how specific AI "Attention"
architectures work.

8. Travel & Vacation
• Transit tickets are for the category. Use this for expert-level logistics
notes (e.g., high-altitude trekking requirements).
Note: Event

9. Weather
• Expert summary of meteorological patterns (e.g., El Niño) or atmospheric
physics.
• Note: NO Safety Tips or other Tips.

10. Health & Fitness (NON-MEDICAL ONLY!)
• Professional instructions or coaching plans from a certified fitness trainer (e.g.,
biomechanics breakdown).

11. Finance & Stocks
• Detailed notes summarizing a market analysis report or expert investment talk.

12. Government & Politics
• Expert summary or lecture notes on a new local zoning law or legislative draft.

13. School & College Life
• Notes capturing a professor's analysis or a formal lecture on graduate ROI math.

14. Gaming
• Recorded strategy instructions or level navigation splits dictated by a
professional speedrunner.

15. Outdoor Adventure

• Expert-led training notes on survival techniques or high-altitude navigation
logistics.

16. Academic & Professional
• Detailed notes from a Ph.D. seminar or a professional engineering symposium.

17. Traditions & Celebrations
• Study notes on the historical symbolism and ritual steps of a regional festival.

18. Work Life
• Technical workshop minutes or formal corporate training notes on workflow
optimization.


.....

---

client feedback batch 1 - 

TOPICS OF INTEREST
Notes - 0 of 150 accepted
1. Notes Topics of Interest are just text taken from articles.
AI detector shows 80%. It is not something we are looking for.
We need personal notes, written by user. 


--

client feedback batch 2 -  TOI Notes - 270 accepted
- Many were out of category. - Boarding process for example is not Travel.
- No about traveling.
- Automative category is about cars only


-- client feedback batch 3 - TOPICS OF INTEREST_Notes - All rejected
- not natural
- the content does not match real information




Information that does not reflect the real world.
