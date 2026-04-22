# 🐍 Loki — Time-Aware AI Assistant

> *"I am Loki. God of time, mischief, and your personal AI."*

Loki is an AI assistant that actually perceives time. Unlike traditional chatbots that are stateless and only respond when called, Loki tracks time between conversations and proactively reaches out to you — without you asking again.

---

## ⚡ What Makes Loki Different

Most AI assistants are reactive. You talk, they respond. They have zero concept of time passing between sessions.

Loki solves this with a simple but powerful insight:

> LLMs can't generate responses on their own — they only fire when called. So instead of fighting that limitation, Loki works with it. It schedules delayed LLM calls and pushes responses to the frontend via polling.

### Core Features

- 🕐 **Time Awareness** — Reads message timestamps to calculate real elapsed time between conversations
- 🧠 **Context-Sensitive** — Adjusts tone based on how long you've been away (seconds, minutes, hours, days)
- ⚡ **Natural Language Reminders** — Detects reminder intent using an LLM, no rigid commands or regex needed
- 🔔 **Proactive Messaging** — Sends reminders to you after a set time, completely unprompted
- 📡 **Real-time Polling** — Frontend polls for new Loki messages every 5 seconds

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-CORS |
| AI Engine | Groq API (LLaMA 3.3 70B) |
| Database | Supabase (PostgreSQL) |
| Scheduler | APScheduler |
| Frontend | Vanilla JS, PWA |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Groq API key (free at console.groq.com)
- Supabase project (free at supabase.com)

### Installation

```bash
git clone https://github.com/CouchCarrot/loki.git
cd loki
python -m venv venv
venv\Scripts\activate
pip install flask flask-cors supabase groq apscheduler python-dotenv
```

### Environment Setup

Create a `.env` file in the root directory:

GROQ_API_KEY=your_groq_key_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

### Supabase Table Setup

Create a table called `conversations` with these columns:

| Column | Type | Default |
|---|---|---|
| id | int8 | auto increment |
| user_id | text | null |
| message | text | null |
| role | text | null |
| timestamp | timestamptz | now() |

Make sure RLS is disabled for development.

### Run

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

---

## 💡 How Proactive Reminders Work
User: "remind me in 10 minutes"
↓
LLM extracts intent → { is_reminder: true, delay_seconds: 600, about: "..." }
↓
APScheduler schedules a job 10 minutes from now
↓
After 10 minutes → Groq API is called automatically
↓
Loki's response is saved to Supabase
↓
Frontend polling picks it up → Message appears in chat

No WebSockets. No push notification services. Just clean delayed responses.

---

## 🗺️ Roadmap

- [ ] PWA push notifications
- [ ] Multi-user authentication
- [ ] Recurring reminders ("every Monday")
- [ ] Mobile app (React Native)
- [ ] Deploy to Render + Vercel

---

## 👤 Author

**Aakarsh Handa (CouchCarrot)**
- Portfolio: [aakarshdevs.netlify.app](https://aakarshdevs.netlify.app)
- GitHub: [@CouchCarrot](https://github.com/CouchCarrot)

---

