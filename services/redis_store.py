from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import redis

from topic_utils import topic_slug

DEFAULT_REDIS_URL = os.getenv("DEFAULT_REDIS_URL", "redis://localhost:6379/0")


@dataclass
class UserRecord:
    name: str
    email: str
    password: str
    topics: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class RedisUserStore:
    """Minimal user/topic persistence backed by Redis JSON blobs."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL") or DEFAULT_REDIS_URL
        self.client = redis.Redis.from_url(self.redis_url, decode_responses=True)

    @staticmethod
    def _key(email: str) -> str:
        return f"user:{email.strip().lower()}"

    def create_user(self, name: str, email: str, password: str) -> UserRecord:
        key = self._key(email)
        if self.client.exists(key):
            raise ValueError("Account already exists for this email address.")

        record = UserRecord(name=name.strip(), email=email.strip().lower(), password=password)
        self._write_record(record)
        return record

    def get_user(self, email: str) -> Optional[UserRecord]:
        raw = self.client.get(self._key(email))
        if not raw:
            return None

        data = json.loads(raw)
        return UserRecord(
            name=data.get("name", ""),
            email=data.get("email", email.strip().lower()),
            password=data.get("password", ""),
            topics=data.get("topics", {}) or {},
        )

    def verify_credentials(self, email: str, password: str) -> Optional[UserRecord]:
        record = self.get_user(email)
        if not record or record.password != password:
            return None
        return record

    def upsert_topic(self, email: str, topic_payload: Dict[str, Any]) -> Dict[str, Any]:
        record = self.get_user(email)
        if not record:
            raise ValueError("User not found; please sign up first.")

        slug = topic_payload.get("slug") or topic_slug(topic_payload.get("topic", "topic"))
        record.topics[slug] = {**topic_payload, "slug": slug}
        self._write_record(record)
        return record.topics[slug]

    def list_topics(self, email: str) -> List[Dict[str, Any]]:
        record = self.get_user(email)
        if not record:
            return []
        return list(record.topics.values())

    def _write_record(self, record: UserRecord) -> None:
        payload = {
            "name": record.name,
            "email": record.email,
            "password": record.password,
            "topics": record.topics,
        }
        self.client.set(self._key(record.email), json.dumps(payload, ensure_ascii=False))

