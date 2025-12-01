from __future__ import annotations

import math
from typing import Literal

from prepare_tts import DEFAULT_DAY_COUNT, PrepareTtsResult, prepare_tts
from topic_utils import topic_file
from web_fetch import run_web_fetch
from web_search import run_web_search

DurationUnit = Literal["hours", "days"]
HOURS_PER_SYNTH_DAY = 3  # Rough heuristic to convert requested hours into content days.


def normalize_day_count(value: int | float, unit: DurationUnit = "days") -> int:
    if value <= 0:
        return DEFAULT_DAY_COUNT

    if unit == "hours":
        return max(1, int(math.ceil(value / HOURS_PER_SYNTH_DAY)))

    return max(1, int(math.ceil(value)))


def generate_learning_plan(
    topic: str, duration_value: int | float, duration_unit: DurationUnit = "days"
) -> PrepareTtsResult:
    """Run the full research → fetch → TTS pipeline for a topic."""
    day_count = normalize_day_count(duration_value, duration_unit)

    result_file = topic_file(topic, "result_url")
    summaries_file = topic_file(topic, "summaries")
    tts_file = topic_file(topic, "tts_ready")

    print(f"[Pipeline] Starting new plan for '{topic}' ({day_count} day(s)).")
    urls, _ = run_web_search(topic, result_file)
    if not urls:
        raise RuntimeError("Web search returned no URLs; aborting pipeline run.")

    run_web_fetch(result_file, summaries_file)
    return prepare_tts(topic, day_count, summaries_file, tts_file)

