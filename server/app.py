from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv:
    load_dotenv()

from config import load_env
from services.audio_generation import ElevenLabsSynthesizer
from services.chatbot import ChatOrchestrator
from services.pipeline_runner import DurationUnit, generate_learning_plan
from services.redis_store import RedisUserStore, UserRecord
from topic_utils import TOPICS_ROOT, topic_slug

load_env()

app = FastAPI(title="Answer Engine Learning API", version="0.2.0")

raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
if raw_origins.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOPICS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/topics", StaticFiles(directory=TOPICS_ROOT), name="topics")

_user_store = RedisUserStore()
_synthesizer = ElevenLabsSynthesizer()
_chatbot = ChatOrchestrator(synthesizer=_synthesizer)


def get_user_store() -> RedisUserStore:
    return _user_store


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=4)
    confirm_password: str = Field(..., min_length=4)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)


class UserResponse(BaseModel):
    name: str
    email: EmailStr
    topics: List[Dict[str, Any]] = []


class PlanRequest(BaseModel):
    email: EmailStr
    topic: str = Field(..., min_length=3)
    duration_value: float = Field(..., gt=0)
    duration_unit: DurationUnit = "days"


class PlanResponse(BaseModel):
    topic: str
    slug: str
    requested_days: int
    content_days: int
    episode_count: int
    total_minutes: float
    episodes: List[Dict[str, Any]]
    audio_enabled: bool
    tts_file: Optional[str] = None
    course_url: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    email: EmailStr
    message: str
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    reply: str
    audio_url: Optional[str] = None
    topic: Optional[str] = None
    duration_value: Optional[float] = None
    duration_unit: Optional[str] = None


def _serialize_user(record: UserRecord) -> UserResponse:
    return UserResponse(
        name=record.name,
        email=record.email,
        topics=list(record.topics.values()),
    )


@app.post("/auth/signup", response_model=UserResponse)
def signup(payload: SignupRequest, user_store: RedisUserStore = Depends(get_user_store)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    record = user_store.create_user(payload.name, payload.email, payload.password)
    return _serialize_user(record)


@app.post("/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, user_store: RedisUserStore = Depends(get_user_store)):
    record = user_store.verify_credentials(payload.email, payload.password)
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return _serialize_user(record)


@app.get("/users/{email}/topics", response_model=List[Dict[str, Any]])
def list_topics(email: EmailStr, user_store: RedisUserStore = Depends(get_user_store)):
    return user_store.list_topics(email)


@app.post("/planning/episodes", response_model=PlanResponse)
async def create_plan(
    payload: PlanRequest, user_store: RedisUserStore = Depends(get_user_store)
):
    existing_user = user_store.get_user(payload.email)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

    def _run_pipeline() -> Dict[str, Any]:
        result = generate_learning_plan(
            payload.topic, payload.duration_value, payload.duration_unit
        )
        enriched = _synthesizer.attach_audio_to_episodes(
            payload.topic, [dict(ep) for ep in result.episodes]
        )
        try:
            relative_tts_path = result.output_file.relative_to(TOPICS_ROOT)
            course_url = f"/topics/{relative_tts_path.as_posix()}"
        except ValueError:
            course_url = f"/topics/{topic_slug(result.topic)}/tts_ready.txt"

        topic_payload = {
            "topic": result.topic,
            "slug": topic_slug(result.topic),
            "requested_days": result.requested_days,
            "content_days": result.content_days,
            "episode_count": result.episode_count,
            "total_minutes": result.total_minutes,
            "episodes": enriched,
            "audio_enabled": _synthesizer.enabled,
            "tts_file": str(result.output_file),
            "course_url": course_url,
        }
        stored = user_store.upsert_topic(payload.email, topic_payload)
        return stored

    stored_topic = await run_in_threadpool(_run_pipeline)
    return PlanResponse(**stored_topic)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    history = [msg.model_dump() for msg in payload.history or []]
    result = _chatbot.respond(payload.email, payload.message, history)
    return ChatResponse(
        reply=result["reply"],
        audio_url=result.get("audio_url"),
        topic=result.get("topic"),
        duration_value=result.get("duration_value"),
        duration_unit=result.get("duration_unit"),
    )

