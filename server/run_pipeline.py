import os
from typing import List

from config import get_settings
from prepare_tts import DEFAULT_DAY_COUNT, prepare_tts
from topic_utils import topic_file
from web_fetch import run_web_fetch
from web_search import DEFAULT_TOPIC, run_web_search


def parse_positive_int(value: str, default: int) -> int:
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return default
    parsed = int(digits)
    return parsed if parsed > 0 else default


def prompt_plan(default_topic: str, default_days: int) -> tuple[str, int]:
    noninteractive = os.getenv("NONINTERACTIVE", "").strip().lower() in {"1", "true", "yes"}
    if noninteractive:
        topic = os.getenv("TOPIC", default_topic)
        days_env = os.getenv("DAYS")
        day_count = parse_positive_int(days_env, default_days) if days_env else default_days
        return topic, day_count

    topic_input = input(f"Enter a topic to research [{default_topic}]: ").strip()
    topic = topic_input or default_topic

    days_input = input(
        f"Enter number of learning days [{default_days}]: "
    ).strip()
    day_count = parse_positive_int(days_input, default_days) if days_input else default_days

    return topic, day_count


def load_urls(file_path) -> List[str]:
    if not file_path.exists():
        return []
    return [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def prompt_yes_no(message: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"{message} {hint}: ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def main() -> None:
    settings = get_settings()
    noninteractive = os.getenv("NONINTERACTIVE", "").strip().lower() in {"1", "true", "yes"}
    print("=== Research & Fetch Pipeline ===")
    if settings.mock_mode:
        print("MOCK_MODE is enabled; skipping live API calls and using cached placeholders.")
    topic, day_count = prompt_plan(DEFAULT_TOPIC, DEFAULT_DAY_COUNT)
    result_file = topic_file(topic, "result_url")
    summaries_file = topic_file(topic, "summaries")
    tts_file = topic_file(topic, "tts_ready")

    # Early reuse / existence checks
    if not noninteractive and tts_file.exists():
        if prompt_yes_no(f"Found existing TTS for '{topic}'. Reuse and skip regeneration?", True):
            print(f"Reusing {tts_file}; no new web search/fetch/TTS run.")
            return

    urls: List[str] = []
    used_cached_urls = False
    if not noninteractive and result_file.exists():
        if prompt_yes_no(f"Found cached URLs for '{topic}'. Reuse and skip web search?", True):
            urls = load_urls(result_file)
            used_cached_urls = True

    print(f"Running web search for topic: {topic}")

    anthropic_usage = {"input_tokens": 0, "output_tokens": 0}
    openai_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if not used_cached_urls:
        try:
            urls, anthropic_usage = run_web_search(topic, result_file)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to collect citation URLs: {exc}")
            return

    if not urls:
        print("No URLs were returned; stopping before fetch.")
        return

    print(f"Saved {len(urls)} URL(s) to {result_file}")
    print("Starting web fetch and summarization pipeline...")

    used_cached_summaries = False
    if not noninteractive and summaries_file.exists():
        if prompt_yes_no(f"Found cached summaries for '{topic}'. Reuse and skip web fetch?", True):
            used_cached_summaries = True
            # We don't recompute hours from cached summaries; leave as 0 placeholder.
            count = len(urls)
            hours = 0.0
            print(f"Reusing {summaries_file}")

    if not used_cached_summaries:
        try:
            count, hours, _ = run_web_fetch(result_file, summaries_file)
        except Exception as exc:  # noqa: BLE001
            print(f"Web fetch failed: {exc}")
            return

    print(f"Saved {count} summaries to {summaries_file} "
          f"(estimated {hours:.2f} hours).")

    try:
        tts_count, openai_usage = prepare_tts(topic, day_count, summaries_file, tts_file)
    except Exception as exc:  # noqa: BLE001
        print(f"TTS preparation failed: {exc}")
        return

    if tts_count:
        print(f"TTS-ready content ({tts_count} entries) stored at {tts_file}")
    else:
        print("No TTS entries were generated.")

    print(
        "Usage summary:\n"
        f"  Anthropic tokens — input: {anthropic_usage['input_tokens']} | "
        f"output: {anthropic_usage['output_tokens']}\n"
        f"  OpenAI tokens — prompt: {openai_usage['prompt_tokens']} | "
        f"completion: {openai_usage['completion_tokens']} | "
        f"total: {openai_usage['total_tokens']}"
    )


if __name__ == "__main__":
    main()

