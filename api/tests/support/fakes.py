"""See planning/decisions.md#D-031."""

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import BaseModel

from bookkeeper.agents.llm import LLMPart, LLMResult


@dataclass(frozen=True, slots=True)
class LLMCall:
    task: str
    system: str
    parts: tuple[LLMPart, ...]
    schema: type[BaseModel] | None


class FakeLLMClient:
    """Implements bookkeeper.agents.llm.LLMClient with canned results per task."""

    def __init__(self) -> None:
        self.calls: list[LLMCall] = []
        self._queued: dict[str, deque[LLMResult]] = defaultdict(deque)
        self._defaults: dict[str, LLMResult] = {}

    def queue(self, task: str, *results: LLMResult) -> None:
        self._queued[task].extend(results)

    def set_default(self, task: str, result: LLMResult) -> None:
        self._defaults[task] = result

    def calls_for(self, task: str) -> list[LLMCall]:
        return [call for call in self.calls if call.task == task]

    async def generate(
        self,
        *,
        task: str,
        system: str,
        parts: Sequence[LLMPart],
        schema: type[BaseModel] | None,
    ) -> LLMResult:
        self.calls.append(LLMCall(task, system, tuple(parts), schema))
        if self._queued[task]:
            return self._queued[task].popleft()
        if task in self._defaults:
            return self._defaults[task]
        raise AssertionError(f"FakeLLMClient has no canned result for task {task!r}")


@dataclass(frozen=True, slots=True)
class FakeMessage:
    message_id: int
    chat_id: int


@dataclass(slots=True)
class FakeFile:
    file_id: str
    file_path: str
    content: bytes = b""

    async def download_as_bytearray(self) -> bytearray:
        return bytearray(self.content)


@dataclass(frozen=True, slots=True)
class BotCall:
    method: str
    chat_id: int | None = None
    text: str | None = None
    reply_markup: Any = None
    message_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class RecordingBot:
    """Mimics the python-telegram-bot Bot methods the app uses."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.calls: list[BotCall] = []
        self.files: dict[str, bytes] = dict(files or {})
        self._next_id = 1000

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def calls_for(self, method: str) -> list[BotCall]:
        return [call for call in self.calls if call.method == method]

    @property
    def sent_texts(self) -> list[str]:
        return [c.text for c in self.calls if c.method == "send_message" and c.text is not None]

    async def send_message(
        self, chat_id: int, text: str, reply_markup: Any = None, **kwargs: Any
    ) -> FakeMessage:
        self.calls.append(BotCall("send_message", chat_id, text, reply_markup, extra=kwargs))
        return FakeMessage(self._new_id(), chat_id)

    async def send_document(
        self, chat_id: int, document: Any, caption: str | None = None, **kwargs: Any
    ) -> FakeMessage:
        reply_markup = kwargs.pop("reply_markup", None)
        extra = {"document": document, **kwargs}
        self.calls.append(BotCall("send_document", chat_id, caption, reply_markup, extra=extra))
        return FakeMessage(self._new_id(), chat_id)

    async def send_photo(
        self, chat_id: int, photo: Any, caption: str | None = None, **kwargs: Any
    ) -> FakeMessage:
        reply_markup = kwargs.pop("reply_markup", None)
        extra = {"photo": photo, **kwargs}
        self.calls.append(BotCall("send_photo", chat_id, caption, reply_markup, extra=extra))
        return FakeMessage(self._new_id(), chat_id)

    async def edit_message_text(
        self,
        text: str,
        chat_id: int | None = None,
        message_id: int | None = None,
        reply_markup: Any = None,
        **kwargs: Any,
    ) -> FakeMessage:
        self.calls.append(
            BotCall("edit_message_text", chat_id, text, reply_markup, message_id, kwargs)
        )
        return FakeMessage(message_id or self._new_id(), chat_id or 0)

    async def edit_message_reply_markup(
        self,
        chat_id: int | None = None,
        message_id: int | None = None,
        reply_markup: Any = None,
        **kwargs: Any,
    ) -> FakeMessage:
        self.calls.append(
            BotCall("edit_message_reply_markup", chat_id, None, reply_markup, message_id, kwargs)
        )
        return FakeMessage(message_id or self._new_id(), chat_id or 0)

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None, **kwargs: Any
    ) -> bool:
        self.calls.append(
            BotCall("answer_callback_query", text=text, extra={"id": callback_query_id, **kwargs})
        )
        return True

    async def get_file(self, file_id: str, **kwargs: Any) -> FakeFile:
        self.calls.append(BotCall("get_file", extra={"file_id": file_id, **kwargs}))
        return FakeFile(file_id, f"files/{file_id}", self.files.get(file_id, b""))


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def bot() -> RecordingBot:
    return RecordingBot()
