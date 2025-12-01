## Backend Inventory – Current State vs. Planned Services

### 1. `web_search.py`
- **Purpose**: Multi-pass Anthropic search with subtopic prompts, de-duplication, and token accounting.
- **Inputs**: Topic string, optional result file path.
- **Outputs**: `result_url.txt` (per topic) + usage metrics.
- **Gaps / Next Service**:
  - Wrap into a `search-service` (FastAPI endpoint + worker task) so the mobile app or scheduler can trigger searches without invoking CLI scripts.
  - Add mock provider (reads cached URLs) to avoid API usage during development or when quotas run out.

### 2. `web_fetch.py`
- **Purpose**: Fetch each URL, extract readable text, estimate audio hours, and log tooling.
- **Outputs**: `summaries.txt` per topic.
- **Gaps / Next Service**:
  - Promote to a `fetch-service` worker that can run inside the job queue (Redis/RQ).
  - Introduce hashing/caching layer (Redis/Upstash) so the same URL isn’t refetched.
  - Add structured output (JSON blobs) for easier storage in Postgres/Supabase.

### 3. `prepare_tts.py`
- **Purpose**: Build episodic scripts, clean text, double duration, emit JSON episodes, track OpenAI tokens.
- **Outputs**: `tts_ready.txt` (JSON) per topic.
- **Gaps / Next Service**:
  - Split into `episode-service` (context-aware script generation) and `tts-service` (actual audio rendering, currently mocked).
  - Accept a user-context payload (pace, preferences, progress) rather than just a topic.
  - Provide offline/mock mode so we can run without hitting OpenAI.

### 4. `run_pipeline.py`
- **Purpose**: CLI orchestrator tying search → fetch → TTS together and printing usage.
- **Gaps / Next Service**:
  - Replace with a scheduler/worker system (APScheduler + Redis queue). Each stage should become an independent task to support retries and per-user schedules.
  - Expose orchestration via REST endpoints so the mobile app/backend can request new courses or refreshes.

### 5. Supporting Files
- `topic_utils.py`: Handles per-topic slug folders; will evolve into asset manifest helper.
- `README.md`: Documents pipeline and roadmap; will need updates as services/API surface grow.

---

### Service Boundary Proposal
| Service | Backed By | Responsibility |
| --- | --- | --- |
| Search Service | FastAPI endpoint + worker | Calls Anthropic (or mock) to gather citations, stores results in Postgres/Redis. |
| Fetch Service | Worker + cache | Downloads URLs, extracts text, stores normalized JSON + metadata. |
| Episode Service | FastAPI + worker | Generates scripts using user context (mock or real LLM). |
| TTS Service | Worker + storage | Converts scripts to audio (mock now), uploads to Supabase Storage/S3. |
| Scheduler | APScheduler + Redis queue | Triggers daily lessons per user, chains services in order. |
| API Gateway | FastAPI | Exposes auth, topic catalog, episodes, playback, chat stubs. |

This inventory will guide Phase 1 tasks: creating shared configs, enabling mock mode, and preparing each script to be wrapped into the upcoming services.






