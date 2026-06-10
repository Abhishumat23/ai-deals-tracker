# AI Deals & Pricing Intelligence Tracker

A local-first tool that monitors AI pricing pages (OpenAI, Anthropic, Gemini, Perplexity, Cursor) and sends Telegram alerts when anything changes.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+ · FastAPI · APScheduler |
| Scraping | Playwright · BeautifulSoup4 |
| Database | SQLite (local file) |
| Notifications | Telegram Bot |
| Frontend | Next.js 14 · TailwindCSS |

---

## Project Structure

```
ai-deals-tracker/
├── backend/
│   ├── app.py          ← FastAPI app + routes + lifespan
│   ├── database.py     ← SQLite setup, session helpers
│   ├── models.py       ← SQLAlchemy ORM (Snapshot, Change)
│   ├── scheduler.py    ← APScheduler, runs every 60 min
│   ├── detector.py     ← Change detection + diff logic
│   ├── notifier.py     ← Telegram alerts
│   ├── utils.py        ← Hashing, normalization, diff
│   ├── scrapers/
│   │   ├── openai_scraper.py
│   │   ├── claude_scraper.py
│   │   ├── gemini_scraper.py
│   │   ├── perplexity_scraper.py
│   │   └── cursor_scraper.py
│   ├── data/           ← deals.db lives here (auto-created)
│   └── requirements.txt
├── frontend/
│   ├── pages/index.js  ← Dashboard
│   ├── components/     ← ToolCard, ChangeItem, StatusBar
│   └── package.json
├── .env.example
└── README.md
```

---

## Setup (One-time)

### 1. Clone / download and enter the project

```bash
cd ai-deals-tracker
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# Install Python deps
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Environment variables

```bash
# From the project root:
cp .env.example .env
```

Edit `.env` and fill in:

```env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SCRAPE_INTERVAL_MINUTES=60
```

---

## Telegram Bot Setup

1. Open Telegram → search **@BotFather**
2. Send `/newbot` → follow the prompts → copy the **token**
3. Search **@userinfobot** in Telegram → start it → copy your **chat id**
4. Paste both into your `.env` file
5. The app sends a startup ping when it launches — if you see it, Telegram is configured!

---

## Running the App

You need **two terminal windows**.

### Terminal 1 — Backend

```bash
cd backend
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Then open: **http://localhost:3000**

---

## Usage

| Action | How |
|---|---|
| View dashboard | http://localhost:3000 |
| Trigger immediate check | Click **↻ run check now** in the dashboard, or `POST http://localhost:8000/run-check` |
| View raw API | http://localhost:8000/tools, /changes, /latest |
| View API docs | http://localhost:8000/docs |

---

## API Endpoints

```
GET  /health       — backend heartbeat
GET  /tools        — latest snapshot per tool
GET  /changes      — all detected changes (newest first)
GET  /latest       — last 5 changes
POST /run-check    — trigger immediate scrape
```

---

## How It Works

1. **Scheduler** fires every N minutes (default 60)
2. Each **scraper** opens the pricing page headlessly via Playwright
3. HTML is parsed by **BeautifulSoup**, noise stripped, text normalized
4. A **SHA-256 hash** of the normalized text is compared to the previous snapshot
5. If hashes differ → a **Change** record is written to SQLite
6. A **Telegram alert** is sent with a diff summary
7. The **dashboard** polls `/tools` and `/changes` every 60 seconds

---

## Adding a New Tool

1. Create `backend/scrapers/mytool_scraper.py` (copy an existing scraper as template)
2. Set `TOOL_NAME` and `URL`
3. Add to `backend/scrapers/__init__.py`:
   ```python
   from scrapers.mytool_scraper import scrape as scrape_mytool, TOOL_NAME as MYTOOL_NAME
   ALL_SCRAPERS.append((MYTOOL_NAME, scrape_mytool))
   ```
4. Restart the backend — done.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `playwright install` fails | Run `playwright install-deps chromium` first |
| Backend won't start | Check `source venv/bin/activate` is active |
| No Telegram messages | Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` |
| Dashboard shows "backend offline" | Backend isn't running on port 8000 |
| Scraper returns None | Site may be blocking headless browsers; check backend logs |

---

## Future Extensions (not implemented)

- `notifier.py` is designed to easily add Discord / Email / Slack
- OpenAI API key is ready to plug in for AI-powered change summaries
- Database schema supports historical graphs per tool
- Add `multi_user` column to Snapshot when multi-user support is needed
