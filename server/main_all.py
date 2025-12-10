import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import ConfigurationError

# Ensure we can import pipeline pieces
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import get_settings  # noqa: E402
import run_pipeline  # noqa: E402
from web_search import DEFAULT_TOPIC  # noqa: E402
from topic_utils import topic_slug  # noqa: E402


settings = get_settings()


SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR  # treat server/ as project root
TOPICS_ROOT = ROOT_DIR / "topics"          # pipeline writes here (now inside server/)
SERVER_TOPICS = TOPICS_ROOT                # mirror is same path now
SERVER_TOPICS.mkdir(parents=True, exist_ok=True)


def get_mongo_client() -> MongoClient:
    mongo_url = os.getenv("MONGO_URL", settings.mongo_url)
    return MongoClient(mongo_url)


def mongo_db(client: MongoClient):
    db_name = os.getenv("MONGO_DB")
    fallback_name = os.getenv("MONGO_DB_FALLBACK", "adhithev1")
    if db_name:
        return client[db_name]
    try:
        # If URI has default DB, use it; else fallback to adhithev1
        return client.get_default_database() or client[fallback_name]
    except ConfigurationError:
        return client[fallback_name]


def mirror_to_server_topics(slug: str) -> Path:
    """
    Mirror the topic folder into server/topics for visibility.
    Returns the path of the tts_ready file inside server/topics.
    """
    src_dir = TOPICS_ROOT / slug
    dst_dir = SERVER_TOPICS / slug
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in ("result_url.txt", "summaries.txt", "tts_ready.txt"):
        src_file = src_dir / name
        dst_file = dst_dir / name
        if src_file.exists():
            dst_file.write_text(src_file.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            dst_file.touch()
    return dst_dir / "tts_ready.txt"


def upsert_topic_to_mongo(slug: str, tts_path: Path, client: MongoClient) -> None:
    if not tts_path.exists():
        raise FileNotFoundError(f"Missing tts_ready file at {tts_path}")
    data = json.loads(tts_path.read_text(encoding="utf-8"))
    db = mongo_db(client)
    coll = db["topics"]
    coll.update_one({"topic": slug}, {"$set": data}, upsert=True)


def load_topic_from_mongo(slug: str, client: MongoClient) -> Optional[Dict[str, Any]]:
    db = mongo_db(client)
    coll = db["topics"]
    return coll.find_one({"topic": slug}, {"_id": 0})


def list_topics_from_mongo(client: MongoClient) -> List[str]:
    db = mongo_db(client)
    coll = db["topics"]
    return [doc.get("topic") for doc in coll.find({}, {"_id": 0, "topic": 1})]


def prompt_topic_and_days() -> tuple[str, int]:
    topic_env = os.getenv("PIPELINE_TOPIC")
    days_env = os.getenv("PIPELINE_DAYS")
    if topic_env:
        topic = topic_env.strip()
    else:
        topic = input(f"Enter a topic to research [{DEFAULT_TOPIC}]: ").strip() or DEFAULT_TOPIC

    if days_env:
        days = int(days_env)
    else:
        days_raw = input("Enter number of learning days [1]: ").strip()
        days = int(days_raw) if days_raw.isdigit() and int(days_raw) > 0 else 1

    return topic, days


def run_pipeline_once(slug: str, days: int) -> None:
    # Make pipeline non-interactive: use provided slug/days without re-prompting
    os.environ["NONINTERACTIVE"] = "true"
    if slug:
        os.environ["TOPIC"] = slug
    if days:
        os.environ["DAYS"] = str(days)
    run_pipeline.main()


# Build FastAPI
app = FastAPI(title="Adhithe Pipeline + API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/topics")
def list_topics():
    with get_mongo_client() as client:
        return {"topics": list_topics_from_mongo(client)}


@app.get("/topics/{slug}")
def get_topic(slug: str):
    with get_mongo_client() as client:
        doc = load_topic_from_mongo(slug, client)
        if not doc:
            raise HTTPException(status_code=404, detail="Topic not found in Mongo")
        return doc


@app.post("/topics/{slug}/sync")
def sync_topic(slug: str, days: int = 1):
    # Run pipeline and push into Mongo
    run_pipeline_once(slug, days)
    tts_path = mirror_to_server_topics(slug)
    with get_mongo_client() as client:
        upsert_topic_to_mongo(slug, tts_path, client)
    return {"detail": f"Synced topic '{slug}'", "topic": slug}


def start():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


if __name__ == "__main__":
    # Prompt user (or use env) for topic and days each run
    chosen_topic, chosen_days = prompt_topic_and_days()
    slug = topic_slug(chosen_topic)
    run_pipeline_once(slug, chosen_days)
    tts_path = mirror_to_server_topics(slug)
    with get_mongo_client() as client:
        upsert_topic_to_mongo(slug, tts_path, client)
    start()

