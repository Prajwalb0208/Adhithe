## Answer Engine Audio Backend

Pipeline scripts that transform web research into long-form, citation-aware lesson scripts that can be turned into audio. This repo currently delivers **backend-only** automation; the mobile frontend (Play Store release) is still pending.

---

### Features

- **Iterative web research (Anthropic)**
  - Multi-pass prompts across subtopics (fundamentals, case studies, ethics, tooling, etc.).
  - De-duplicates citations to reach ≥35 unique sources whenever possible.
  - Resilient to rate limits; warns and continues with the next pass.
  - Logs Anthropic token usage per run.

- **Full-text retrieval + summarization**
  - Downloads each cited URL (HTML/PDF) with `requests + BeautifulSoup`.
  - Strips boilerplate, estimates speaking time, and stores summaries and raw text in `topics/<slug>/summaries.txt`.

- **LLM-authored TTS scripts (OpenAI)**
  - Doubles requested day count (200%) to create progressive, human-sounding lectures with quizzes.
  - Cleans mathematical notation/LaTeX artifacts for better speech synthesis.
  - Outputs structured JSON (`topics/<slug>/tts_ready.txt`) ready for downstream TTS engines.
  - Tracks OpenAI token consumption.

- **Topic-scoped artifacts**
  - Every run writes to `topics/<slug>/result_url.txt`, `summaries.txt`, and `tts_ready.txt`.
  - CLI prints aggregated stats: URL counts, estimated hours, and token usage.

---

### Quick Start

1. **Install deps**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment**
   ```
   ANTHROPIC_API_KEY=...
   OPENAI_API_KEY=...
   ```
   Optional: `TOPIC`, `DAYS` to skip prompts in individual scripts.

3. **Run the pipeline**
   ```bash
   python run_pipeline.py
   ```
   - Prompts for topic + learning days.
   - Runs search → fetch → TTS.
   - Outputs live logs and final token usage summary.

4. **Inspect outputs**
   ```
   topics/<topic-slug>/
     result_url.txt     # unique citations
     summaries.txt      # summaries + raw full text
     tts_ready.txt      # JSON episodes with scripts, quizzes, sources
   ```

---

### File Guide

| File | Purpose |
| --- | --- |
| `run_pipeline.py` | CLI orchestrator; prints token usage (Anthropic + OpenAI). |
| `web_search.py` | Multi-pass citation gathering with subtopic prompts and rate-limit resilience. |
| `web_fetch.py` | Fetches each URL, extracts text, estimates hours, writes summaries. |
| `prepare_tts.py` | Builds conversational episodes, doubles day count, emits JSON. |
| `topic_utils.py` | Slug/dir helpers to isolate artifacts per topic. |

---

### Roadmap / TODO (Pre Play-Store)

- **Frontend (mobile)** – UI, playback, progress tracking, offline support, billing.
- **API services** – Auth, topic queues, job orchestration, surfacing JSON/audio to apps.
- **Persistent storage** – DB for users/topics/quizzes; object storage for audio assets.
- **TTS integration** – Hook these scripts into a production-grade speech provider and CDN.
- **Scheduling & workers** – Background jobs for refresh, retries, notifications.
- **Observability & billing** – Cost dashboards, alerts, usage throttles.
- **Compliance** – Privacy policy, ToS, telemetry controls required for Play Store.

Until those pieces land, treat this repo as a content factory for internal use/testing. The final product experience (app UI, user management, delivery) still needs to be built.

---

### Contribution Notes

- Stick to ASCII in code; rely on existing lint setup.
- Each script prints detailed logs (including tool usage) so you can trace pipeline steps.
- Feel free to extend file formats (e.g., add markdown exports) as long as per-topic isolation is preserved.

PRs should highlight:
1. Which stage(s) you touched (search, fetch, TTS).
2. Any impact on token usage/costs.
3. Required environment changes.

Happy building!