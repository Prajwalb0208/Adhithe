from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

try:
    from elevenlabs.client import ElevenLabs
except ImportError:  # pragma: no cover - optional dependency
    ElevenLabs = None  # type: ignore[assignment]

from topic_utils import TOPICS_ROOT, ensure_topic_dir

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsSynthesizer:
    """Thin wrapper around the ElevenLabs SDK with graceful fallbacks."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
        self.model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID)
        self.output_format = output_format or os.getenv(
            "ELEVENLABS_OUTPUT_FORMAT", DEFAULT_OUTPUT_FORMAT
        )
        self._client: Optional[ElevenLabs] = None
        self.enabled = bool(self.api_key and ElevenLabs is not None)

        if self.enabled:
            self._client = ElevenLabs(api_key=self.api_key)
        else:
            print(
                "ElevenLabs audio synthesis is disabled; set ELEVENLABS_API_KEY to enable audio output."
            )

    def synthesize_script_for_episode(
        self, topic: str, episode_number: int, script: str
    ) -> Optional[str]:
        if not script.strip():
            return None

        episode_dir = ensure_topic_dir(topic) / "audio"
        episode_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"episode-{episode_number:02d}.mp3"
        output_path = episode_dir / file_name
        return self._synthesize(script, output_path)

    def synthesize_chat_reply(self, identifier: str, text: str) -> Optional[str]:
        if not text.strip():
            return None

        chat_dir = TOPICS_ROOT / "chat_responses"
        chat_dir.mkdir(parents=True, exist_ok=True)
        output_path = chat_dir / f"{identifier}.mp3"
        return self._synthesize(text, output_path)

    def attach_audio_to_episodes(
        self, topic: str, episodes: List[dict]
    ) -> List[dict]:
        """Mutate and return the provided episode payloads with audio file references."""
        for episode in episodes:
            script = str(episode.get("script") or "").strip()
            number = int(episode.get("episode_number") or 0)
            if not script or number <= 0:
                episode["audio_file"] = None
                continue

            episode["audio_file"] = self.synthesize_script_for_episode(
                topic, number, script
            )
        return episodes

    def _synthesize(self, text: str, output_path: Path) -> Optional[str]:
        if not self.enabled or not self._client:
            return None

        try:
            audio_stream = self._client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id,
                output_format=self.output_format,
            )
            self._write_audio_file(audio_stream, output_path)
            relative = output_path.relative_to(TOPICS_ROOT)
            return f"/topics/{relative.as_posix()}"
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to synthesize audio via ElevenLabs: {exc}")
            return None

    @staticmethod
    def _write_audio_file(audio_stream: object, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as audio_file:
            if isinstance(audio_stream, (bytes, bytearray)):
                audio_file.write(audio_stream)
                return

            if isinstance(audio_stream, Iterable):
                for chunk in audio_stream:
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    audio_file.write(chunk)
                return

            raise TypeError(
                "Unexpected ElevenLabs audio payload type "
                f"{type(audio_stream)}; expected bytes or iterable."
            )

