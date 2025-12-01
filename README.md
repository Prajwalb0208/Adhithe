## Answer Engine Audio Backend

This project turns any topic into an audio-first micro‑course. It scrapes and summarizes cited material, asks GPT‑4o to craft quiz-ready lecture scripts, optionally voices them with ElevenLabs, and exposes everything through a Redis-backed FastAPI service plus a React chatbot that gathers requirements via text or speech.

---

## Features

- **Research stage (Anthropic)**
  - Multi-pass web search with per-subtopic prompts.
  - Enforces ≥35 unique citations when possible and logs token usage.
  - Resilient to rate limits and gracefully continues.

- **Fetch & summarize stage**
  - Downloads each URL, strips boilerplate, estimates reading/audio time, and saves summaries + full text under `topics/<slug>/summaries.txt`.

- **Script & quiz generation (OpenAI)**
  - Groups sources into day-by-day “episodes,” doubles requested duration to build a progressive curriculum, and emits JSON stored in `topics/<slug>/tts_ready.txt`.
  - Each episode carries a conversational script, a quiz, and the cited sources.

- **Audio synthesis (ElevenLabs, optional)**
  - Generates MP3 narration per episode and for chatbot replies when an ElevenLabs key is present.

- **Persistent state (Redis)**
  - Users are saved as `user:<email>` keys containing their profile and all generated topics/episodes (no password hashing per product requirements).

- **FastAPI service**
  - Auth, planning, and chatbot endpoints plus static hosting of generated JSON/audio.

- **React front-end**
  - Signup/login form, planner that re-runs the full pipeline, a “Course” section that always links to the latest plan, and a chatbot that can capture requirements via text or microphone before triggering course generation.

---

## How It Works

1. **Chatbot collects intent** – OpenAI produces both the friendly response and structured metadata (`topic`, `duration_value`, `duration_unit`). ElevenLabs optionally reads the response aloud.
2. **Course generation pipeline** – When the user clicks “Course” (or uses the planner form), the backend runs:
   - `web_search.py` → multi-pass Anthropic search to get citations.
   - `web_fetch.py` → requests/BeautifulSoup extraction + summarization.
   - `prepare_tts.py` → GPT‑4o scripting, quiz creation, and JSON export.
   - `services/audio_generation.py` → ElevenLabs MP3s (if enabled).
3. **Redis sync** – The resulting payload (episodes, durations, `course_url`, audio paths) is saved to Redis, making it instantly available to the UI via `/users/{email}/topics`.
4. **Static hosting** – `server/app.py` mounts `topics/` so the frontend can stream JSON and audio via normal HTTP URLs.

---

## Getting Started

1. **Clone & install Python dependencies**
   ```bash
   git clone <repo>
   cd <repo>
   python -m venv .venv && .\.venv\Scripts\activate  # or your preferred shell
   pip install -r requirements.txt
   ```

2. **Create your environment file**
   - Copy `env.template` to `.env` at the repo root.
   - Fill in the placeholders (API keys, Redis URL, etc.).  
     | Variable | Description |
     | --- | --- |
     | `ANTHROPIC_API_KEY` | Needed for citation gathering. |
     | `OPENAI_API_KEY` | Required for script + quiz generation and chatbot replies. |
     | `ELEVENLABS_API_KEY` *(optional)* | Enables audio narration (episodes + chat). |
     | `REDIS_URL` | Connection string for topic/user storage. |
     | `ALLOWED_ORIGINS` | Comma-separated frontend origins allowed by CORS. |
     | plus tuning knobs `TARGET_UNIQUE_URLS`, `MAX_TOOL_USES`, `MAX_SEARCH_ATTEMPTS`, `MOCK_MODE`. |

3. **Start the FastAPI server**
   ```bash
   uvicorn server.app:app --reload
   ```
   - API lives at `http://localhost:8000`.
   - Generated files are served from `http://localhost:8000/topics/<slug>/...`.

4. **Start the React app**
   ```bash
   cd webapp
   npm install
   npm run dev
   ```
   - The UI expects `VITE_API_BASE_URL` (defaults to `http://localhost:8000`) for API calls.

5. **(Optional) Run the CLI pipeline manually**
   ```bash
   python run_pipeline.py
   ```
   This prompts for a topic + day count and writes artifacts under `topics/<slug>/`.

---

## API & UI Highlights

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/signup` | Create a user (plaintext password per requirements). |
| `POST` | `/auth/login` | Authenticate and return the stored topics array. |
| `GET` | `/users/{email}/topics` | List every generated course stored in Redis. |
| `POST` | `/planning/episodes` | Runs search → fetch → script → audio, saves the payload, and returns the `course_url`. |
| `POST` | `/chat` | Conversational coach that responds with text/audio + structured hints (topic/duration). |

The React dashboard:
- Shows a **Course** card with the latest plan (title, total time, first episodes, audio players, and a button linking directly to the JSON).
- Provides a planner form for manual runs.
- Hosts the chatbot with both text input and a mic button next to the field, plus a one-click **Course** button to trigger the pipeline directly from the conversation.

---

## Future Plans

- Add password hashing + OAuth providers.
- Queue/batch pipeline runs with progress notifications.
- Downloadable lesson bundles (PDF + MP3 zip).
- Replace Redis with a persistent DB (Postgres) and add per-episode analytics.
- Mobile clients and push notifications for daily lessons.

---

## Contributing

Pull requests are welcome! Please:
1. Keep changes scoped (search, fetch, TTS, API, or UI).
2. Explain any token/cost impacts or new environment variables.
3. Include screenshots or sample payloads when touching the UI or API.

Lint (frontend + backend) before opening a PR, and avoid committing real API keys—use the `.env` file locally and keep only sanitized templates (`env.template`) in git.

