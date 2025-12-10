from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from pymongo import MongoClient

# Paths (server directory is the project root now)
ROOT_DIR = Path(__file__).resolve().parent
TOPICS_ROOT = ROOT_DIR / "topics"
ENV_FILE = ROOT_DIR / ".env"


def load_env(env_file: Path = ENV_FILE) -> None:
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_mongo_client() -> MongoClient:
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        load_env()
        mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is not set")
    return MongoClient(mongo_url)


def mongo_db(client: MongoClient):
    db_name = os.getenv("MONGO_DB")
    if db_name:
        return client[db_name]
    # If no DB provided in URI, fall back to a named DB
    return client["adhithev1"]


def list_slugs() -> List[str]:
    if not TOPICS_ROOT.exists():
        return []
    return [p.name for p in TOPICS_ROOT.iterdir() if p.is_dir()]


def upsert_slug(slug: str, client: MongoClient) -> None:
    tts_path = TOPICS_ROOT / slug / "tts_ready.txt"
    if not tts_path.exists():
        print(f"[skip] {slug}: missing tts_ready.txt")
        return
    data = json.loads(tts_path.read_text(encoding="utf-8"))
    db = mongo_db(client)
    coll = db["topics"]
    coll.update_one({"topic": slug}, {"$set": data}, upsert=True)
    print(f"[ok] upserted {slug}")


def main() -> None:
    load_env()
    slugs = list_slugs()
    if not slugs:
        print("No topics found under topics/")
        return
    with get_mongo_client() as client:
        for slug in slugs:
            upsert_slug(slug, client)


if __name__ == "__main__":
    main()

