# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains an automated research and content generation pipeline that transforms a research topic into TTS-ready audio course material. The pipeline has three main stages:

1. **Web Search** (`web_search.py`) - Uses Anthropic's web search API to find and collect citation URLs
2. **Web Fetch** (`web_fetch.py`) - Fetches web pages, extracts article text, and generates summaries
3. **TTS Preparation** (`prepare_tts.py`) - Calls OpenAI's GPT-4o to generate structured episode scripts with quizzes

The main orchestrator is `run_pipeline.py`, which executes all three stages sequentially.

## Environment Setup

This project requires Python 3.10+ and uses both Anthropic API (for web search) and OpenAI API (for episode script generation). Create a `.env` file with:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

The codebase includes a custom `.env` loader that reads key-value pairs without requiring the `python-dotenv` package.

## Running the Pipeline

**Complete pipeline (interactive):**
```bash
python run_pipeline.py
```
You'll be prompted for:
- Topic name (default: "Answer Engine Optimization")
- Number of learning days (default: 20)

**Individual stages:**
```bash
# Stage 1: Web search only
python web_search.py

# Stage 2: Fetch and summarize (requires result_url.txt)
python web_fetch.py

# Stage 3: Generate TTS episodes (requires summaries.txt)
python prepare_tts.py
```

**Environment variable override:**
```bash
TOPIC="machine learning" DAYS=30 python run_pipeline.py
```

## Architecture

### Data Flow

1. **Topic normalization** (`topic_utils.py`):
   - Converts topic names to slugs (e.g., "Machine Learning" → "machine-learning")
   - Creates organized directory structure: `topics/<slug>/`
   - All intermediate files are topic-scoped

2. **Stage outputs** (stored in `topics/<slug>/`):
   - `result_url.txt` - Line-separated URLs from web search
   - `summaries.txt` - Formatted entries with URL, word count, summary, and full content
   - `tts_ready.txt` - JSON with structured episodes, scripts, and quiz questions

3. **Content multiplier logic** (`prepare_tts.py`):
   - Generates 2x the requested days as content episodes (CONTENT_MULTIPLIER = 2.0)
   - If user requests 20 days, generates 40 content episodes
   - Episodes are then suggested to be released over the original 20-day schedule
   - This provides extra buffer content and flexibility

### Key Parameters

**Web Search** (`web_search.py`):
- `TARGET_UNIQUE_URLS = 20` - Target number of citation URLs to collect
- `MAX_TOOL_USES = 25` - Maximum web_search tool invocations per request

**Web Fetch** (`web_fetch.py`):
- `MAX_SENTENCES_PER_SUMMARY = 6` - Summary length (uses word frequency scoring)
- `WORDS_PER_MINUTE = 160` - Used to estimate audio duration
- Warns if total estimated hours < 20

**TTS Preparation** (`prepare_tts.py`):
- `CONTENT_MULTIPLIER = 2.0` - Generates 2x requested days as episodes
- `EPISODE_TARGET_MINUTES = 30.0` - Target episode length
- `EPISODE_MIN_MINUTES = 20.0` / `EPISODE_MAX_MINUTES = 45.0` - Episode bounds
- `QUIZ_LENGTH = 3` - Number of quiz questions per episode
- `CLAUDE_COOLDOWN_SECONDS = 20` - Delay between API calls to avoid rate limits

### Episode Generation Logic

The `prepare_tts.py` module groups content segments into episodes:

1. Parses summaries file into segments with word counts and estimated minutes
2. Computes per-episode target duration based on total content and requested days
3. Groups segments into episodes, respecting min/max bounds
4. For each episode:
   - Calls OpenAI API (GPT-4o) with structured prompt for script generation
   - Expects JSON response with `title`, `script`, and `quiz` fields
   - Falls back to template-based script if JSON parsing fails
5. Assigns difficulty labels based on progression through content
6. Outputs final JSON with all episodes and metadata

### Error Handling

All modules use bare `except Exception` with `# noqa: BLE001` to catch and report errors without crashing the pipeline. This allows partial results even if individual URLs fail or API calls timeout.

## Dependencies

Core packages used (no requirements.txt present):
- `anthropic` - Claude API client for web search
- `openai` - OpenAI API client for episode script generation
- `requests` - HTTP fetching
- `beautifulsoup4` - HTML parsing
- Standard library: `pathlib`, `re`, `json`, `typing`

## Model Selection

- **Web Search**: Uses Claude Sonnet 4.5 (`model="claude-sonnet-4-5"`) via Anthropic API for citation extraction
- **Episode Script Generation**: Uses GPT-4o (`model="gpt-4o"`) via OpenAI API for structured episode scripts with JSON output

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

## Notes

- No git repository initialized (per /init detection)
- All file I/O uses UTF-8 encoding explicitly
- Topic directories are created on-demand via `ensure_topic_dir()`
- The pipeline is designed to be run multiple times for different topics without conflicts
- All improvements to content extraction and cleaning apply automatically on every run
