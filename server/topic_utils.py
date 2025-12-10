import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOPICS_ROOT = BASE_DIR / "topics"


def topic_slug(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug or "topic"


def ensure_topic_dir(topic: str) -> Path:
    slug = topic_slug(topic)
    topic_dir = TOPICS_ROOT / slug
    topic_dir.mkdir(parents=True, exist_ok=True)
    return topic_dir


def topic_file(topic: str, prefix: str, suffix: str = ".txt") -> Path:
    topic_dir = ensure_topic_dir(topic)
    filename = f"{prefix}{suffix}"
    return topic_dir / filename

