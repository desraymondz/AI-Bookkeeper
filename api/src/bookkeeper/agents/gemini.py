"""See planning/decisions.md#D-016, planning/03-tech-stack.md section 3.2 and PRD G-7."""

import io
import time
from collections.abc import Sequence
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bookkeeper.agents.llm import LLMPart, LLMResult
from bookkeeper.config import Settings
from bookkeeper.db.models import AuditActor, AuditLog

INLINE_MAX_BYTES = 15 * 1024 * 1024

TASKS = (
    "extract",
    "extract_escalate",
    "revise",
    "excel_map",
    "assistant",
    "sales",
    "router",
    "reply",
)


class UnknownTaskError(ValueError):
    pass


class ModelNotConfiguredError(RuntimeError):
    pass


def model_for_task(settings: Settings, task: str) -> str:
    if task not in TASKS:
        raise UnknownTaskError(f"No model setting for LLM task {task!r}")
    model: str = getattr(settings, f"gemini_model_{task}")
    if not model:
        raise ModelNotConfiguredError(f"GEMINI_MODEL_{task.upper()} is not set")
    return model


class GeminiClient:
    def __init__(
        self,
        settings: Settings,
        *,
        audit_sessionmaker: async_sessionmaker[AsyncSession] | None = None,
        client: Any | None = None,
        inline_max_bytes: int = INLINE_MAX_BYTES,
    ) -> None:
        self._settings = settings
        self._audit = audit_sessionmaker
        self._inline_max = inline_max_bytes
        self._client = client or genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=settings.llm_timeout_seconds * 1000),
        )

    async def generate(
        self,
        *,
        task: str,
        system: str,
        parts: Sequence[LLMPart],
        schema: type[BaseModel] | None,
    ) -> LLMResult:
        model = model_for_task(self._settings, task)
        started = time.monotonic()
        try:
            contents: list[Any] = [await self._to_part(part) for part in parts]
            config = types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json" if schema else None,
                response_schema=schema,
                temperature=0,
            )
            response = await self._client.aio.models.generate_content(
                model=model, contents=contents, config=config
            )
            usage = _usage(response)
            text = response.text
            parsed = schema.model_validate_json(text) if schema and text else None
        except Exception as exc:
            await self._record(task, model, started, ok=False, error=type(exc).__name__)
            raise
        await self._record(task, model, started, ok=True, usage=usage)
        return LLMResult(parsed=parsed, text=text, model=model, usage=usage)

    async def _to_part(self, part: LLMPart) -> types.Part:
        if part.text is not None:
            return types.Part.from_text(text=part.text)
        if part.data is None or part.mime is None:
            raise ValueError("LLMPart needs text, or data and mime")
        if len(part.data) <= self._inline_max:
            return types.Part.from_bytes(data=part.data, mime_type=part.mime)
        uploaded = await self._client.aio.files.upload(
            file=io.BytesIO(part.data), config=types.UploadFileConfig(mime_type=part.mime)
        )
        return types.Part.from_uri(file_uri=str(uploaded.uri), mime_type=part.mime)

    async def _record(
        self,
        task: str,
        model: str,
        started: float,
        *,
        ok: bool,
        usage: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        if self._audit is None:
            return
        detail: dict[str, Any] = {
            "task": task,
            "ok": ok,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "usage": usage or {},
        }
        if error:
            detail["error"] = error
        async with self._audit() as session, session.begin():
            session.add(
                AuditLog(actor=AuditActor.AGENT, action="llm.call", model=model, detail_json=detail)
            )


def _usage(response: Any) -> dict[str, Any]:
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return {}
    return {
        "prompt_tokens": meta.prompt_token_count,
        "output_tokens": meta.candidates_token_count,
        "total_tokens": meta.total_token_count,
    }
