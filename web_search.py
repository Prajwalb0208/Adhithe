import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import anthropic
from config import get_settings
from topic_utils import topic_file, topic_slug

DEFAULT_TOPIC = "Answer Engine Optimization"
SETTINGS = get_settings()


def extract_citation_urls(payload: Any) -> List[str]:
    """Recursively collect citation URLs from an Anthropics response payload."""
    urls: List[str] = []

    if isinstance(payload, dict):
        citations = payload.get("citations")
        if isinstance(citations, list):
            for citation in citations:
                url = citation.get("url")
                if url:
                    urls.append(url)

        for value in payload.values():
            urls.extend(extract_citation_urls(value))

    elif isinstance(payload, list):
        for item in payload:
            urls.extend(extract_citation_urls(item))

    return urls


def save_urls(urls: List[str], file_path: Path) -> None:
    """Persist the collected URLs to disk (one per line)."""
    file_path.write_text("\n".join(urls), encoding="utf-8")


def _read_existing_urls(file_path: Path) -> List[str]:
    if not file_path.exists():
        return []
    return [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _mock_urls(topic: str, count: int) -> List[str]:
    slug = topic_slug(topic)
    return [f"https://example.com/{slug}/mock-source-{idx + 1}" for idx in range(count)]


def _subtopic_variations(topic: str) -> List[str]:
    base = topic.strip()
    return [
        base,
        f"{base} fundamentals overview",
        f"{base} case studies and real-world deployments",
        f"{base} advanced research breakthroughs",
        f"{base} ethics, governance, and future trends",
        f"{base} tooling, frameworks, and implementation guides",
    ]


def _build_search_prompt(topic: str, subtopic: str, existing_urls: List[str]) -> str:
    base = (
        f"Use the web_search tool to research the topic '{topic}' with a focus on '{subtopic}'. "
        "Provide a concise summary and include citations for every fact so I can extract the source URLs. "
        "Return as many distinct, high-quality citation links as possible (ideally 35 or more) and prioritize "
        "long-form resources such as papers, whitepapers, books, or in-depth blog series."
    )
    if existing_urls:
        base += (
            "\n\nAvoid repeating any sources from this list of already collected URLs:\n"
            + "\n".join(existing_urls)
        )
        base += "\nFocus on fresh angles, applications, or subtopics that haven't been covered yet."
    return base


def run_web_search(
    topic: str, result_file: Optional[Path] = None
) -> Tuple[List[str], Dict[str, int]]:
    settings = get_settings()

    collected: List[str] = []
    usage_totals = {"input_tokens": 0, "output_tokens": 0}
    output_file = result_file or topic_file(topic, "result_url")

    if settings.mock_mode:
        print("Mock mode enabled: skipping Anthropic web search calls.")
        existing = _read_existing_urls(output_file)
        collected = existing or _mock_urls(
            topic, min(settings.target_unique_urls, 10)
        )
        save_urls(collected, output_file)
        return collected, usage_totals

    if "ANTHROPIC_API_KEY" not in os.environ:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is missing. Add it to .env or export it in the environment."
        )

    client = anthropic.Anthropic()

    subtopics = _subtopic_variations(topic)
    for attempt in range(1, settings.max_search_attempts + 1):
        subtopic = subtopics[(attempt - 1) % len(subtopics)]
        prompt = _build_search_prompt(topic, subtopic, collected)
        print(
            f"Running web search attempt {attempt}/{settings.max_search_attempts} "
            f"focused on '{subtopic}'..."
        )

        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": settings.max_tool_uses,
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            }
                        ],
                    }
                ],
            )
        except anthropic.RateLimitError as exc:
            print(
                f"Warning: attempt {attempt} hit rate limit ({exc}); continuing with next attempt..."
            )
            continue
        except Exception as exc:  # noqa: BLE001
            print(
                f"Warning: attempt {attempt} failed with {exc}; continuing with next attempt..."
            )
            continue

        usage = getattr(response, "usage", None)
        if usage:
            usage_totals["input_tokens"] += getattr(usage, "input_tokens", 0)
            usage_totals["output_tokens"] += getattr(usage, "output_tokens", 0)

        response_dict = response.model_dump()
        new_urls = extract_citation_urls(response_dict)

        before_count = len(collected)
        for url in new_urls:
            if url not in collected:
                collected.append(url)

        print(
            f"Attempt {attempt}: gathered {len(new_urls)} URLs "
            f"({len(collected) - before_count} new; total {len(collected)})."
        )

        if len(collected) >= settings.target_unique_urls:
            break

    save_urls(collected, output_file)

    if len(collected) < settings.target_unique_urls:
        print(
            "Warning: "
            f"only {len(collected)} unique citation URL(s) were returned; "
            f"target is {settings.target_unique_urls}. Continuing with available sources."
        )

    return collected, usage_totals


def main() -> None:
    topic = os.getenv("TOPIC", DEFAULT_TOPIC)
    output_file = topic_file(topic, "result_url")
    urls, usage = run_web_search(topic, output_file)

    if urls:
        print(f"Saved {len(urls)} citation URL(s) to {output_file}")
    else:
        print("No citation URLs found; wrote an empty file.")

    if usage:
        print(
            "Anthropic token usage — "
            f"input: {usage['input_tokens']} | output: {usage['output_tokens']}"
        )


if __name__ == "__main__":
    main()