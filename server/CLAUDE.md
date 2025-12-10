# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository is a **backend-only** automated research and content generation pipeline that transforms research topics into TTS-ready audio course material. It currently delivers script generation; the mobile frontend (Play Store release) is pending.

The pipeline has three main stages:

1. **Web Search** (`web_search.py`) - Multi-pass citation gathering using Anthropic API with subtopic prompts (fundamentals, case studies, ethics, tooling). Targets ≥35 unique sources with rate-limit resilience.
2. **Web Fetch** (`web_fetch.py`) - Downloads and extracts full text from cited URLs (HTML/PDF), generates summaries, estimates speaking time.
3. **TTS Preparation** (`prepare_tts.py`) - Uses OpenAI GPT-4o to generate conversational lecture scripts with quizzes. Doubles the requested day count (200% content multiplier) for progressive learning.

The main orchestrator is `run_pipeline.py`, which executes all stages sequentially and prints aggregated token usage (Anthropic + OpenAI).

## Environment Setup

**Python version:** 3.10+

**Required dependencies:** Install via `pip install -r requirements.txt` (not checked in)
- `anthropic` - Claude API client
- `openai` - OpenAI API client
- `requests` - HTTP fetching
- `beautifulsoup4` - HTML parsing

**API Keys:** Create a `.env` file in the repository root:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

The codebase includes a custom `.env` loader (`config.py:load_env()`) that reads key-value pairs without requiring the `python-dotenv` package. It strips quotes and only sets variables not already in the environment.

## Running the Pipeline

**Complete pipeline (interactive):**
```bash
python run_pipeline.py
```
Interactive prompts will ask for:
- Topic name (default: "Answer Engine Optimization")
- Number of learning days (default: 20)
- Hours of content per day (optional, leave blank to auto-balance)
- Episodes per day (default: 1)
- Generate audio assets? (Y/n, controlled by `AUDIO_ENABLED` setting)
- Target languages (comma-separated, includes English by default, max 2 total)

**Environment variable overrides:**
```bash
# Skip all prompts with environment variables
TOPIC="machine learning" DAYS=30 python run_pipeline.py

# Control audio generation and caching
AUDIO_ENABLED=false REUSE_CACHED=true python run_pipeline.py

# Multi-language support
LANGUAGES="english,spanish" python run_pipeline.py

# Testing mode (uses cached placeholders, no API calls)
MOCK_MODE=true python run_pipeline.py
```

**Individual stages:**
```bash
# Stage 1: Web search only (requires TOPIC env var or prompts)
python web_search.py

# Stage 2: Fetch and summarize (requires result_url.txt from stage 1)
python web_fetch.py

# Stage 3: Generate TTS episodes (requires summaries.txt from stage 2)
python prepare_tts.py
```

## Architecture

### Configuration System

All pipeline behavior is controlled by `config.py` with a centralized `Settings` dataclass:

- **Environment variable overrides:** Every setting can be overridden via `.env` or shell variables
- **Cached singleton:** `get_settings()` uses `@lru_cache` for consistent configuration across modules
- **Type safety:** Settings uses typed fields with helper functions (`_bool_env`, `_int_env`, `_float_env`)
- **Default fallbacks:** If environment variables are missing or malformed, defaults from the dataclass are used

**Available configuration variables:**
```python
TARGET_UNIQUE_URLS = 35          # Citation URL target (default: 35)
MAX_TOOL_USES = 75               # Max web_search tool calls per request
MAX_SEARCH_ATTEMPTS = 6          # Max search passes across subtopics
CLAUDE_COOLDOWN_SECONDS = 20     # Delay between Anthropic API calls
CONTENT_MULTIPLIER = 2.0         # Episode multiplier (2.0 = 200% content)
MOCK_MODE = false                # Testing mode (no API calls, uses caches)
AUDIO_ENABLED = true             # Generate audio assets
REUSE_CACHED = true              # Skip stages if cached files exist
MAX_LANGUAGES = 2                # Maximum target languages
```

### Data Flow

1. **Topic normalization** (`topic_utils.py`):
   - Converts topic names to slugs (e.g., "Machine Learning" → "machine-learning")
   - Creates organized directory structure: `topics/<slug>/`
   - All intermediate files are topic-scoped (topics/ directory is gitignored)

2. **Stage outputs** (stored in `topics/<slug>/`):
   - `result_url.txt` - Line-separated citation URLs from web search
   - `summaries.txt` - Formatted entries with URL, word count, summary, and full article text
   - `tts_ready.txt` - JSON with structured episodes, scripts, quiz questions, and metadata

3. **Caching and reuse** (`run_pipeline.py`):
   - If `REUSE_CACHED=true` (default), existing outputs are reused without re-running stages
   - Stages report "Reusing cached..." when skipping API calls
   - Allows iterating on later stages without re-fetching earlier data
   - Override with `REUSE_CACHED=false` to force fresh runs

4. **Content multiplier logic** (`prepare_tts.py`):
   - Generates 2x the requested days as content episodes (CONTENT_MULTIPLIER = 2.0)
   - If user requests 20 days, generates 40 content episodes
   - Episodes are then suggested to be released over the original 20-day schedule
   - This provides extra buffer content and flexibility

### Web Search Multi-Pass Strategy

`web_search.py` uses an iterative approach to gather diverse citations:

1. **Subtopic passes:** Prompts Claude to search across different angles (fundamentals, case studies, applications, ethics, tooling, research papers)
2. **De-duplication:** Tracks unique URLs across all passes to avoid redundancy
3. **Rate limit handling:** If Anthropic API rate-limits, logs a warning and continues with next pass
4. **Citation extraction:** Recursively walks response payloads to extract all `citations[].url` fields
5. **Token tracking:** Reports input/output token usage per run

**Configuration:**
- `TARGET_UNIQUE_URLS = 35` - Stops when this many unique URLs are collected
- `MAX_TOOL_USES = 75` - Maximum web_search tool calls per request
- `MAX_SEARCH_ATTEMPTS = 6` - Number of subtopic passes

### Episode Generation Logic

The `prepare_tts.py` module transforms raw summaries into structured learning episodes:

1. **Content parsing:** Reads `summaries.txt` and extracts segments with word counts and estimated minutes (based on WORDS_PER_MINUTE = 160)
2. **Content filtering:** Skips entries with errors, insufficient content (<50 words), or banned phrases (ads, copyright notices)
3. **TTS cleaning:** Applies `clean_text_for_tts()` to remove LaTeX, Greek letters, mathematical symbols
4. **Episode grouping:** Distributes segments across episodes based on:
   - Per-episode target duration (computed from total content ÷ requested days × CONTENT_MULTIPLIER)
   - Episode bounds: 20-45 minutes (configurable)
   - Attempts to balance content across episodes
5. **Script generation:** For each episode:
   - Calls OpenAI API (GPT-4o) with structured prompt for conversational script
   - Expects JSON response with `title`, `script`, and `quiz` fields
   - Quiz has 3 multiple-choice questions per episode
   - Falls back to template-based script if JSON parsing fails
6. **Difficulty progression:** Assigns difficulty labels (Beginner → Advanced) based on episode position
7. **Token tracking:** Reports OpenAI token usage (prompt + completion + total)
8. **Output format:** JSON with episodes array, metadata (topic, days, total episodes, languages)

### Error Handling and Resilience

All modules use defensive error handling to ensure partial results even when failures occur:

- **Bare exception catches:** `except Exception` with `# noqa: BLE001` prevents pipeline crashes
- **Per-URL tolerance:** `web_fetch.py` continues if individual URLs fail (timeout, parsing errors, 404s)
- **Rate limit handling:** `web_search.py` logs rate-limit warnings and continues with next subtopic pass
- **API call cooldowns:** `CLAUDE_COOLDOWN_SECONDS = 20` delay between calls to avoid overwhelming APIs
- **Fallback scripts:** If OpenAI JSON parsing fails, `prepare_tts.py` generates template-based scripts
- **Encoding safety:** All file I/O explicitly uses UTF-8 encoding

## Model Selection

- **Web Search (Stage 1):** Claude Sonnet 4.5 (`model="claude-sonnet-4-5"`) via Anthropic API
  - Used for multi-pass citation extraction with web_search tool
  - Subtopic prompts guide search across fundamentals, case studies, ethics, tooling, research
- **Episode Script Generation (Stage 3):** GPT-4o (`model="gpt-4o"`) via OpenAI API
  - Structured JSON output with episode title, conversational script, and quiz questions
  - Optimized for long-form educational content generation

## Content Quality Improvements

The pipeline includes robust text cleaning for TTS (text-to-speech) compatibility:

**In `web_fetch.py`:**
- Removes navigation elements (nav, header, footer, aside, forms)
- Filters marketing content (newsletters, ads, social share buttons)
- Removes LaTeX/MathML mathematical expressions
- Cleans up citation markers and special symbols

**In `prepare_tts.py`:**
- Applies additional TTS-specific cleaning to all content
- Removes Greek letters and mathematical symbols (∈, ∑, ∏, π, etc.)
- Strips LaTeX display style expressions like `{\displaystyle ...}`
- Filters out entries with errors or insufficient content (<50 words)
- Skips duplicate or banned phrases (ads, copyright notices)

Both modules use a shared `clean_text_for_tts()` function that removes:
- LaTeX expressions and mathematical notation
- Greek alphabet characters (α-ω, Α-Ω)
- Mathematical operators (×, ÷, ±, →, etc.)
- Citation brackets like [1], [71]

## Repository Structure

```
.
├── config.py              # Centralized Settings dataclass and .env loader
├── topic_utils.py         # Topic slug generation and directory management
├── web_search.py          # Stage 1: Multi-pass citation gathering (Anthropic)
├── web_fetch.py           # Stage 2: URL fetching, text extraction, summarization
├── prepare_tts.py         # Stage 3: Episode script generation (OpenAI)
├── run_pipeline.py        # Main orchestrator with interactive prompts
├── .env                   # API keys (gitignored)
├── .gitignore             # Excludes topics/, .env, .claude/, __pycache__/
└── topics/                # Output directory (gitignored)
    └── <topic-slug>/
        ├── result_url.txt    # Stage 1 output: citation URLs
        ├── summaries.txt     # Stage 2 output: summaries + full text
        └── tts_ready.txt     # Stage 3 output: JSON with episodes
```

## Development Patterns

**Adding new configuration variables:**
1. Add field to `Settings` dataclass in `config.py` with default value
2. Add extraction logic in `get_settings()` using `_int_env()`, `_bool_env()`, or `_float_env()`
3. Document the variable in this file's Configuration System section

**Modifying pipeline stages:**
- Each stage (`web_search.py`, `web_fetch.py`, `prepare_tts.py`) can be run independently
- Stages read from/write to topic-scoped files via `topic_utils.topic_file()`
- Use `get_settings()` to access configuration instead of hardcoding constants
- Add token usage tracking for new API calls (follow existing patterns)

**Testing without API calls:**
- Set `MOCK_MODE=true` to skip live API calls and use cached placeholders
- Set `REUSE_CACHED=true` (default) to skip stages with existing outputs

## Contribution Guidelines

When submitting changes, highlight:
1. **Which stage(s) you touched:** Search, fetch, or TTS preparation
2. **Impact on token usage/costs:** New API calls increase expenses
3. **Required environment changes:** New API keys, dependencies, or configuration variables

**Code style:**
- Stick to ASCII in code (Unicode in output files is fine)
- Each script prints detailed logs including tool usage for traceability
- Preserve per-topic isolation (all outputs go to `topics/<slug>/`)
- Maintain UTF-8 encoding for all file operations

## Backend API Server (Mobile & Web Ready)

The `server/` directory contains a **production-ready FastAPI backend** that serves content to both mobile and web applications through a unified API.

### Backend Stack

- **FastAPI** - Async Python web framework with auto-generated OpenAPI docs
- **PostgreSQL** - Relational database for users, topics, episodes (with async SQLAlchemy)
- **Redis** - Caching layer for episodes, translations, media
- **Celery** - Background task queue for translations and pipeline execution
- **WebSocket** - Real-time updates for pipeline progress and notifications
- **JWT** - Token-based authentication
- **OpenAI Integration** - GPT-4o for translations and DALL-E 3 for image generation
- **Judge0 API** - Code sandbox execution (8+ languages)

### Platform Support

**Mobile Apps:**
- ✅ React Native (iOS & Android)
- ✅ Native iOS (Swift)
- ✅ Native Android (Kotlin)
- ✅ Flutter
- ✅ Full REST API, JWT auth, offline export, WebSocket

**Web Apps:**
- ✅ React, Vue, Angular, Svelte
- ✅ Vanilla JavaScript
- ✅ Same REST API + WebSocket, static file serving, admin dashboard

### Running the Backend

**Quick start with Docker:**
```bash
cd server
cp .env.example .env
# Edit .env with API keys
./scripts/docker_start.sh
```

**Manual setup:**
```bash
cd server
./scripts/start.sh  # Linux/Mac
# OR
scripts\start.bat   # Windows
```

Access:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Flower (Celery): http://localhost:5555

### API Endpoints (Mobile & Web)

**Core APIs:**
- **Episodes**: `GET /api/v1/episodes?topic=<slug>` - Load from `topics/<slug>/tts_ready.txt`
- **Translations**: `GET /api/v1/episodes/{id}/translations?lang=<language>` - OpenAI translation
- **Media**: `GET /api/v1/episodes/{id}/media?generate_missing=true` - Generate images with DALL-E
- **Sandbox**: `POST /api/v1/sandbox/run` - Execute code via Judge0
- **Audio**: `GET/POST /api/v1/episodes/{id}/audio` - Audio asset management
- **Topics**: `GET /api/v1/topics/{slug}/status` - Pipeline status and metadata

**Mobile & Web APIs:**
- **Export**: `GET /api/v1/export/episodes/export?topic=<slug>&format=json|txt|markdown` - Download for offline
- **Search**: `GET /api/v1/search/episodes?q=query` - Full-text search
- **Batch**: `POST /api/v1/batch/pipeline/batch` - Bulk operations
- **Admin**: `GET /api/v1/admin/stats/overview` - System statistics
- **WebSocket**: `ws://.../ws/progress/{topic}` - Real-time updates

See `server/API_GUIDE.md` and `server/DEVELOPER_GUIDE.md` for complete documentation with code examples.

### Architecture

- **Episode Loader**: Reads from `topics/<slug>/tts_ready.txt` (generated by pipeline)
- **Redis Caching**: 1hr for episodes, 24hr for translations
- **Celery Tasks**: Background translations, pipeline execution
- **Database**: Optional persistent storage (topics load from files by default)

### Development Workflow

1. **Generate content**: Run `python run_pipeline.py` (creates `topics/<slug>/tts_ready.txt`)
2. **Start backend**: Backend automatically reads from topics directory
3. **Test API**: Use interactive docs at `/docs` or send requests
4. **Add languages**: Request translation via API, cached for future requests

## Roadmap

**Backend (Completed ✅):**
- ✅ API services - Auth, episodes, translations, media, sandbox endpoints
- ✅ Persistent storage - PostgreSQL database for users/topics/episodes
- ✅ Scheduling & workers - Celery background jobs for translations
- ✅ Caching - Redis caching layer

**Pre Play Store release (Pending):**
- Frontend (mobile) - UI, playback, progress tracking, offline support, billing
- TTS integration - Production-grade speech provider and CDN
- Observability & billing - Cost dashboards, alerts, usage throttles
- Compliance - Privacy policy, ToS, telemetry controls

The backend is **production-ready** and serves content from the pipeline. Mobile app development can proceed using the REST API.
