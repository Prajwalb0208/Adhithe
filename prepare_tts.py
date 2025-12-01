from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from openai import OpenAI

from config import get_settings
from topic_utils import topic_file

SETTINGS = get_settings()

DEFAULT_TOPIC = "Answer Engine Optimization"
DEFAULT_DAY_COUNT = 20
DEFAULT_SUMMARIES_FILE = Path(__file__).with_name("summaries.txt")
DEFAULT_TTS_FILE = Path(__file__).with_name("tts_ready.txt")

BANNED_PHRASES = {
    "advertisement",
    "copyright",
    "all rights reserved",
    "for premium support please call",
}

MIN_LINE_LENGTH = 3
WORDS_PER_MINUTE = 160
MAX_SNIPPET_CHARS = 600
EPISODE_TARGET_MINUTES = 30.0
EPISODE_MIN_MINUTES = 20.0
EPISODE_MAX_MINUTES = 45.0
QUIZ_LENGTH = 3
CONTENT_MULTIPLIER = SETTINGS.content_multiplier
CLAUDE_COOLDOWN_SECONDS = SETTINGS.claude_cooldown_seconds


@dataclass(frozen=True)
class PrepareTtsResult:
    topic: str
    requested_days: int
    content_days: int
    total_minutes: float
    episodes: List[Dict[str, object]]
    openai_usage: Dict[str, int]
    output_file: Path

    @property
    def episode_count(self) -> int:
        return len(self.episodes)


def log_tool_usage(tool_name: str, detail: str) -> None:
    print(f"[TOOL] {tool_name}: {detail}")


def parse_positive_int(value: str, default: int) -> int:
    digits = re.findall(r"\d+", value)
    if not digits:
        return default
    result = int("".join(digits))
    return result if result > 0 else default


def prompt_topic_and_days(
    default_topic: str = DEFAULT_TOPIC, default_days: int = DEFAULT_DAY_COUNT
) -> Tuple[str, int]:
    topic_input = input(f"Enter a topic for TTS preparation [{default_topic}]: ").strip()
    topic = topic_input or default_topic

    days_input = input(
        f"Enter number of course days [{default_days}]: "
    ).strip()
    day_count = parse_positive_int(days_input, default_days) if days_input else default_days

    return topic, day_count


def read_summaries(file_path: Path) -> List[str]:
    log_tool_usage("FileRead", f"Reading summaries from {file_path}")
    if not file_path.exists():
        raise FileNotFoundError(f"Summaries file not found: {file_path}")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    entries: List[str] = []
    buffer: List[str] = []

    for line in lines:
        if line.startswith("URL: ") and buffer:
            entries.append("\n".join(buffer).strip())
            buffer = [line]
        else:
            buffer.append(line)

    if buffer:
        entries.append("\n".join(buffer).strip())

    return [entry for entry in entries if entry]


def parse_entry(entry_text: str) -> Dict[str, Optional[str]]:
    data: Dict[str, Optional[str]] = {
        "url": None,
        "word_count": None,
        "estimated_hours": None,
        "summary": "",
        "content": "",
    }

    summary_lines: List[str] = []
    content_lines: List[str] = []
    mode: Optional[str] = None

    for line in entry_text.splitlines():
        if line.startswith("URL: "):
            data["url"] = line.partition("URL: ")[2].strip()
            continue
        if line.startswith("Word count: "):
            data["word_count"] = line.partition("Word count: ")[2].strip()
            continue
        if line.startswith("Estimated audio hours"):
            data["estimated_hours"] = line.partition(":")[2].strip()
            continue
        if line.strip() == "Summary:":
            mode = "summary"
            continue
        if line.strip() == "Full content:":
            mode = "content"
            continue

        if mode == "summary":
            summary_lines.append(line)
        elif mode == "content":
            content_lines.append(line)

    data["summary"] = "\n".join(summary_lines).strip()
    data["content"] = "\n".join(content_lines).strip()
    return data


def clean_text_for_tts(text: str) -> str:
    """Remove LaTeX, mathematical symbols, and problematic characters for TTS."""
    # Remove LaTeX expressions like {\displaystyle ...}, {\\mathcal{A}}, etc.
    text = re.sub(r'\{\\?[a-z]+style[^}]*\}', '', text, flags=re.I)
    text = re.sub(r'\{\\?[a-z]+\{[^}]*\}\}', '', text, flags=re.I)
    text = re.sub(r'\{[^}]{0,3}\}', '', text)  # Remove short brace content

    # Remove standalone mathematical symbols and Greek letters
    text = re.sub(r'[α-ωΑ-Ω]', '', text)  # Greek letters
    text = re.sub(r'[∈∑∏∫∂∆∇≤≥≠≈∞⊂⊃∪∩∧∨¬∀∃]', '', text)  # Math symbols
    text = re.sub(r'[×÷±≡⊕⊗→]', '', text)  # Operators

    # Remove citation markers like [ 1 ], [ 71 ], etc.
    text = re.sub(r'\[\s*\d+\s*\]', '', text)

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def clean_lines(text: str) -> List[str]:
    # First apply TTS-specific cleaning
    text = clean_text_for_tts(text)

    cleaned: List[str] = []
    seen = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lowered = line.lower()
        if any(phrase in lowered for phrase in BANNED_PHRASES):
            continue

        if len(line) <= MIN_LINE_LENGTH and not line.endswith("."):
            continue

        if re.fullmatch(r"[A-Z]{2,}", line):
            continue

        if line in seen:
            continue

        seen.add(line)
        cleaned.append(line)

    return cleaned


def condense_text(text: str, limit: int = MAX_SNIPPET_CHARS) -> str:
    cleaned = " ".join(clean_lines(text))
    return cleaned[:limit].strip()


def parse_word_count(value: Optional[str]) -> int:
    if not value:
        return 0
    digits = re.findall(r"\d+", value.replace(",", ""))
    if not digits:
        return 0
    return int("".join(digits))


def estimate_minutes(word_count: int) -> float:
    if word_count <= 0:
        return 0.0
    return word_count / WORDS_PER_MINUTE


def collect_segments(entries: Sequence[str]) -> Tuple[List[Dict[str, object]], float]:
    segments: List[Dict[str, object]] = []
    total_minutes = 0.0

    for idx, entry_text in enumerate(entries, start=1):
        # Skip error entries
        if "Error:" in entry_text and entry_text.count("\n") < 3:
            continue

        parsed = parse_entry(entry_text)
        summary = condense_text(parsed.get("summary") or "")
        if not summary:
            summary = condense_text(parsed.get("content") or "")

        # Clean the content for TTS
        content = clean_text_for_tts(parsed.get("content") or "")

        # Skip entries with no meaningful content
        if not content or len(content.split()) < 50:
            continue

        word_count = parse_word_count(parsed.get("word_count"))
        if word_count == 0:
            word_count = len(content.split())

        minutes = estimate_minutes(word_count)
        total_minutes += minutes

        segments.append(
            {
                "source_index": idx,
                "url": parsed.get("url") or f"Source {idx}",
                "word_count": word_count,
                "minutes": minutes,
                "summary": summary,
                "content": content,
            }
        )

    return segments, total_minutes


def compute_episode_targets(
    total_minutes: float, day_count: int
) -> Tuple[float, float]:
    if total_minutes <= 0:
        return EPISODE_TARGET_MINUTES, EPISODE_MAX_MINUTES

    if day_count > 0:
        target = total_minutes / day_count
    else:
        target = EPISODE_TARGET_MINUTES

    target = max(EPISODE_MIN_MINUTES, min(EPISODE_MAX_MINUTES, target))
    max_cap = max(target * 1.4, target + 10.0)
    max_cap = min(max_cap, EPISODE_MAX_MINUTES)
    return target, max_cap


def group_segments_into_episodes(
    segments: Sequence[Dict[str, object]],
    total_minutes: float,
    day_count: int,
) -> List[Tuple[List[Dict[str, object]], float]]:
    target_minutes, max_minutes = compute_episode_targets(total_minutes, day_count)
    episodes: List[Tuple[List[Dict[str, object]], float]] = []
    current: List[Dict[str, object]] = []
    current_minutes = 0.0

    for segment in segments:
        minutes = float(segment.get("minutes") or 0.0)
        if minutes == 0.0:
            continue

        if current and current_minutes + minutes > max_minutes:
            episodes.append((current, current_minutes))
            current = []
            current_minutes = 0.0

        current.append(segment)
        current_minutes += minutes

        if current_minutes >= target_minutes and len(current) >= 1:
            episodes.append((current, current_minutes))
            current = []
            current_minutes = 0.0

    if current:
        episodes.append((current, current_minutes))

    return episodes


def render_sources_for_prompt(segments: Sequence[Dict[str, object]]) -> str:
    lines: List[str] = []
    for idx, segment in enumerate(segments, start=1):
        summary = segment.get("summary") or ""
        url = segment.get("url") or f"Source {idx}"
        lines.append(
            f"[Source {idx}] URL: {url}\n"
            f"Key insights: {summary if summary else 'Content available in full text.'}"
        )
    return "\n\n".join(lines)


def call_claude_episode_script(
    topic: str,
    episode_number: int,
    difficulty: str,
    total_days: int,
    duration_minutes: float,
    segments: Sequence[Dict[str, object]],
) -> Tuple[Dict[str, object], Dict[str, int]]:
    if SETTINGS.mock_mode:
        meta = build_fallback_meta(
            topic, episode_number, difficulty, total_days, segments
        )
        usage_info = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        return meta, usage_info

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add it to .env or export it in the environment."
        )

    client = OpenAI()
    log_tool_usage("OpenAI", f"Generating script for episode {episode_number}")

    target_words = max(int(duration_minutes * WORDS_PER_MINUTE), 400)
    sources_text = render_sources_for_prompt(segments)
    quiz_instructions = (
        f"Provide exactly {QUIZ_LENGTH} reflective quiz questions at the end."
    )

    prompt = "\n".join(
        [
            (
                f"You are crafting Episode {episode_number} of a {max(total_days, 1)}-day "
                f"audio-first course on '{topic}'. This session should feel {difficulty} "
                "and introduce slightly more challenge than prior days."
            ),
            "Write in a warm, conversational, single-speaker tone at normal human speaking speed "
            "(~160 wpm). Sound like a friendly lecturer talking directly to the listener.",
            f"Target length: about {duration_minutes:.1f} minutes (~{target_words} words).",
            "Structure:",
            "1. A compelling title.",
            "2. A narration script that weaves the provided sources into progressively deeper insights.",
            "3. Show how today's content builds on previous episodes and sets up the next.",
            "4. Close with a quick recap and transition to the quiz.",
            "5. Ask exactly the requested number of reflective quiz questions; you pose the questions, "
            "the listener self-reflects (no multi-speaker dialogue).",
            "Reference sources inline as [Source n] using the numbers provided.",
            quiz_instructions,
            "Stay one-sided but personable: ask rhetorical questions, answer them yourself, "
            "and include verbal cues like 'let's pause' or 'notice how'.",
            "",
            "## SOURCES",
            sources_text,
            "",
            "## OUTPUT FORMAT",
            '{'
            '"title": "...",'
            '"script": "Long-form narration text...",'
            '"quiz": ["Question 1", "Question 2", "Question 3"]'
            '}',
            "Return JSON only.",
        ]
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    raw_text = response.choices[0].message.content.strip()

    usage_info = {
        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
        "total_tokens": getattr(response.usage, "total_tokens", 0),
    }

    try:
        return json.loads(raw_text), usage_info
    except json.JSONDecodeError:
        return (
            build_fallback_meta(
                topic, episode_number, difficulty, total_days, segments, raw_text
            ),
            usage_info,
        )


def build_fallback_meta(
    topic: str,
    episode_number: int,
    difficulty: str,
    total_days: int,
    segments: Sequence[Dict[str, object]],
    raw_text: Optional[str] = None,
) -> Dict[str, object]:
    summary_text = " ".join(
        str(segment.get("summary") or "") for segment in segments
    ).strip()
    script_body = raw_text or summary_text or "Content unavailable."
    script = (
        f"Hey there, welcome to Day {episode_number} of our {topic} journey "
        f"(out of {max(total_days, 1)} days). This lesson feels {difficulty} and "
        f"builds on everything we've covered so far. {script_body}"
    )

    quiz_items: List[str] = []
    for idx, segment in enumerate(segments, start=1):
        url = segment.get("url") or f"Source {idx}"
        quiz_items.append(f"What was the key takeaway from {url}?")
        if len(quiz_items) >= QUIZ_LENGTH:
            break

    while len(quiz_items) < QUIZ_LENGTH:
        quiz_items.append(f"Summarize one insight from Episode {episode_number}.")

    return {
        "title": f"{topic} Episode {episode_number}",
        "script": script,
        "quiz": quiz_items,
    }


def build_episode_payload(
    topic: str,
    episode_number: int,
    requested_days: int,
    total_days: int,
    duration_minutes: float,
    difficulty: str,
    meta: Dict[str, object],
    segments: Sequence[Dict[str, object]],
    content_multiplier: float,
) -> Dict[str, object]:
    sources_payload: List[Dict[str, object]] = []
    for idx, segment in enumerate(segments, start=1):
        sources_payload.append(
            {
                "label": f"Source {idx}",
                "url": segment.get("url"),
                "word_count": int(segment.get("word_count") or 0),
                "estimated_minutes": round(float(segment.get("minutes") or 0.0), 2),
                "content": segment.get("content") or "(No article text extracted.)",
            }
        )

    suggested_day = max(
        1,
        min(
            requested_days,
            int(math.ceil(episode_number / max(content_multiplier, 1e-9))),
        ),
    )

    return {
        "episode_number": episode_number,
        "day_label": (
            f"Content Day {episode_number} of {max(total_days, 1)} "
            f"(suggested release day {suggested_day} of {max(requested_days, 1)})"
        ),
        "difficulty": difficulty,
        "title": meta.get("title", f"{topic} Episode {episode_number}"),
        "duration_minutes": round(duration_minutes, 2),
        "script": meta.get("script", "").strip(),
        "quiz": meta.get("quiz") or [],
        "sources": sources_payload,
    }


def difficulty_label(episode_number: int, total_episodes: int) -> str:
    """Generate a difficulty label based on episode progression."""
    progress = episode_number / max(total_episodes, 1)
    if progress <= 0.33:
        return "introductory"
    elif progress <= 0.66:
        return "intermediate"
    else:
        return "advanced"


def save_tts(
    topic: str,
    requested_days: int,
    total_days: int,
    total_minutes: float,
    episodes: List[Dict[str, object]],
    file_path: Path,
) -> None:
    log_tool_usage("FileWrite", f"Writing TTS-ready JSON to {file_path}")
    payload = {
        "topic": topic,
        "requested_day_count": requested_days,
        "content_day_count": total_days,
        "content_multiplier": CONTENT_MULTIPLIER,
        "episode_count": len(episodes),
        "total_estimated_minutes": round(total_minutes, 2),
        "episodes": episodes,
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_tts(
    topic: str,
    day_count: int,
    summaries_file: Optional[Path] = None,
    tts_file: Optional[Path] = None,
) -> int:
    source_file = summaries_file or topic_file(topic, "summaries")
    output_file = tts_file or topic_file(topic, "tts_ready")
    requested_days = day_count if day_count > 0 else DEFAULT_DAY_COUNT
    content_days = max(1, int(math.ceil(requested_days * CONTENT_MULTIPLIER)))

    raw_entries = read_summaries(source_file)
    if not raw_entries:
        print(f"No entries found in {source_file}.")
        return 0

    segments, total_minutes = collect_segments(raw_entries)
    episodes = group_segments_into_episodes(segments, total_minutes, content_days)

    if not episodes:
        print("No valid segments available to build episodes.")
        return 0

    episode_payloads: List[Dict[str, object]] = []
    total_schedule_minutes = 0.0
    openai_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for idx, (episode_segments, duration) in enumerate(episodes, start=1):
        total_schedule_minutes += duration
        difficulty = difficulty_label(idx, content_days)
        try:
            meta, usage = call_claude_episode_script(
                topic, idx, difficulty, content_days, duration, episode_segments
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Episode {idx} script generation failed: {exc}")
            meta = build_fallback_meta(
                topic, idx, difficulty, content_days, episode_segments
            )
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        payload = build_episode_payload(
            topic,
            idx,
            requested_days,
            content_days,
            duration,
            difficulty,
            meta,
            episode_segments,
            CONTENT_MULTIPLIER,
        )
        episode_payloads.append(payload)
        if not SETTINGS.mock_mode:
            time.sleep(CLAUDE_COOLDOWN_SECONDS)

        openai_usage["prompt_tokens"] += usage["prompt_tokens"]
        openai_usage["completion_tokens"] += usage["completion_tokens"]
        openai_usage["total_tokens"] += usage["total_tokens"]

    save_tts(
        topic,
        requested_days,
        content_days,
        total_schedule_minutes,
        episode_payloads,
        output_file,
    )
    return PrepareTtsResult(
        topic=topic,
        requested_days=requested_days,
        content_days=content_days,
        total_minutes=total_schedule_minutes,
        episodes=episode_payloads,
        openai_usage=openai_usage,
        output_file=output_file,
    )


if __name__ == "__main__":
    topic_env = os.getenv("TOPIC")
    days_env = os.getenv("DAYS")

    if topic_env and days_env:
        topic = topic_env
        day_count = parse_positive_int(days_env, DEFAULT_DAY_COUNT)
        print(
            f"Using topic '{topic}' and {day_count} day(s) from environment variables."
        )
    else:
        topic, day_count = prompt_topic_and_days()

    summaries_path = topic_file(topic, "summaries")
    tts_path = topic_file(topic, "tts_ready")

    result = prepare_tts(topic, day_count, summaries_path, tts_path)
    if result.episode_count:
        print(f"Prepared {result.episode_count} TTS-ready episode(s) at {tts_path}")
    print(
        "OpenAI token usage — "
        f"prompt: {result.openai_usage['prompt_tokens']} | "
        f"completion: {result.openai_usage['completion_tokens']} "
        f"| total: {result.openai_usage['total_tokens']}"
    )
