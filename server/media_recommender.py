from __future__ import annotations

import os
from typing import Dict, List, Sequence, Tuple

from openai import OpenAI

from config import get_settings

SETTINGS = get_settings()


def _render_source_hints(segments: Sequence[Dict[str, object]]) -> str:
    lines = []
    for idx, seg in enumerate(segments, start=1):
        url = seg.get("url") or f"Source {idx}"
        summary = seg.get("summary") or ""
        lines.append(f"[Source {idx}] {url}\nSummary: {summary[:240]}")
    return "\n\n".join(lines)


def _fallback_recs(topic: str) -> List[Dict[str, str]]:
    return [
        {
            "type": "video",
            "title": f"Deep dive on {topic}",
            "url": "https://www.youtube.com",
            "description": "Suggested video placeholder.",
        },
        {
            "type": "visual",
            "title": f"{topic} diagram",
            "url": "https://www.example.com/diagram.png",
            "description": "Suggested visual placeholder.",
        },
    ]


def generate_media_recommendations(
    topic: str,
    episode_number: int,
    duration_minutes: float,
    segments: Sequence[Dict[str, object]],
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """
    Use OpenAI to propose 2–3 videos and 1–2 visuals relevant to the episode.
    """
    if SETTINGS.mock_mode:
        return _fallback_recs(topic), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env or export it in the environment.")

    client = OpenAI()
    sources_hint = _render_source_hints(segments)
    prompt = "\n".join(
        [
            f"Topic: {topic}",
            f"Episode: {episode_number}, target duration ~{duration_minutes:.1f} minutes.",
            "Provide 2-3 high-quality video recommendations (YouTube/Vimeo) and 1-2 visual/diagram links.",
            "Respond as a JSON array of objects: {type: 'video'|'visual', title, url, description}.",
            "Prioritize authoritative, recent, and free-to-access content. Keep descriptions concise.",
            "",
            "## Sources/context",
            sources_hint or "(no sources provided)",
        ]
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=900,
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    usage_info = {
        "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
        "completion_tokens": getattr(response.usage, "completion_tokens", 0),
        "total_tokens": getattr(response.usage, "total_tokens", 0),
    }
    try:
        data = raw
        # Expecting a JSON array; handle if wrapped in object
        import json

        parsed = json.loads(data)
        if isinstance(parsed, dict) and "items" in parsed:
            parsed = parsed["items"]
        if isinstance(parsed, list):
            recs: List[Dict[str, str]] = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                t = item.get("type") or ""
                if t not in {"video", "visual"}:
                    continue
                recs.append(
                    {
                        "type": t,
                        "title": item.get("title") or "Untitled",
                        "url": item.get("url") or "",
                        "description": item.get("description") or "",
                    }
                )
            return recs, usage_info
    except Exception:
        pass

    return _fallback_recs(topic), usage_info

