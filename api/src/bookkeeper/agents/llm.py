"""See planning/decisions.md#D-016 and planning/03-tech-stack.md section 3.2 (google-genai row)."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class LLMPart:
    text: str | None = None
    data: bytes | None = None
    mime: str | None = None

    @classmethod
    def from_text(cls, text: str) -> LLMPart:
        return cls(text=text)

    @classmethod
    def from_bytes(cls, data: bytes, mime: str) -> LLMPart:
        return cls(data=data, mime=mime)


@dataclass(frozen=True, slots=True)
class LLMResult:
    parsed: BaseModel | None = None
    text: str | None = None
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    async def generate(
        self,
        *,
        task: str,
        system: str,
        parts: Sequence[LLMPart],
        schema: type[BaseModel] | None,
    ) -> LLMResult: ...
