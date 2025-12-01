from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from openai import OpenAI

from .audio_generation import ElevenLabsSynthesizer

SYSTEM_PROMPT = """You are a helpful learning coach. Your job is to chat with users who want to master a topic.
Always gather:
1. The primary topic or skill they want to learn.
2. How many days OR hours they hope to spend.
3. Their current familiarity (beginner/intermediate/advanced).

Return JSON that includes:
- reply: conversational text (<= 80 words, no Markdown headings).
- topic: the topic string if known, else null.
- duration_value: number of days or hours if provided, else null.
- duration_unit: "days" or "hours" when duration_value is present.

Keep the tone warm and end with a clear next step or question."""

RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "LearningCoachResponse",
        "schema": {
            "type": "object",
            "properties": {
                "reply": {"type": "string"},
                "topic": {"type": ["string", "null"]},
                "duration_value": {"type": ["number", "null"]},
                "duration_unit": {"type": "string", "enum": ["hours", "days", ""]},
            },
            "required": ["reply"],
        },
    },
}


def _sanitize_history(history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    if not history:
        return cleaned

    for message in history[-10:]:
        role = message.get("role")
        content = (message.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})
    return cleaned


class ChatOrchestrator:
    """OpenAI-powered chatbot with optional ElevenLabs audio responses."""

    def __init__(
        self,
        synthesizer: Optional[ElevenLabsSynthesizer] = None,
        model: Optional[str] = None,
    ) -> None:
        self._client: Optional[OpenAI] = None
        try:
            self._client = OpenAI()
        except Exception as exc:  # noqa: BLE001
            print(f"OpenAI client unavailable; chatbot falling back to canned replies ({exc}).")

        self.model = model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.synthesizer = synthesizer or ElevenLabsSynthesizer()

    def respond(
        self,
        email: str,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        cleaned_history = _sanitize_history(history)
        user_message = message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        reply_payload = self._generate_reply(cleaned_history, user_message)
        audio_url = self.synthesizer.synthesize_chat_reply(
            identifier=str(uuid.uuid4()), text=reply_payload["reply"]
        )

        reply_payload["audio_url"] = audio_url
        reply_payload["email"] = email
        return reply_payload

    def _generate_reply(
        self, history: List[Dict[str, str]], message: str
    ) -> Dict[str, Any]:
        if not self._client:
            return {
                "reply": (
                    "Tell me which topic you want to learn and how many days or hours you have. "
                    "I'll outline a custom audio plan for you."
                ),
                "topic": None,
                "duration_value": None,
                "duration_unit": None,
            }

        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        conversation.extend(history)
        conversation.append({"role": "user", "content": message})

        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0.4,
            max_tokens=240,
            response_format=RESPONSE_SCHEMA,
            messages=conversation,
        )

        content = response.choices[0].message.content
        if not content:
            raise HTTPException(status_code=500, detail="Empty response from chatbot.")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Failed to parse chatbot reply: {exc}") from exc

        duration_unit = parsed.get("duration_unit") or None
        return {
            "reply": parsed.get("reply", "").strip(),
            "topic": parsed.get("topic"),
            "duration_value": parsed.get("duration_value"),
            "duration_unit": duration_unit,
        }

