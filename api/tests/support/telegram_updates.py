"""Telegram update JSON builders. See planning/decisions.md#D-031."""

import itertools
import time
from typing import Any

_update_ids = itertools.count(1)
_message_ids = itertools.count(100)

PDF_MIME = "application/pdf"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _user(user_id: int, username: str | None) -> dict[str, Any]:
    user: dict[str, Any] = {"id": user_id, "is_bot": False, "first_name": username or "User"}
    if username:
        user["username"] = username
    return user


def _message(user_id: int, username: str | None, **content: Any) -> dict[str, Any]:
    return {
        "message_id": next(_message_ids),
        "date": int(time.time()),
        "chat": {"id": user_id, "type": "private", "first_name": username or "User"},
        "from": _user(user_id, username),
        **content,
    }


def _update(**body: Any) -> dict[str, Any]:
    return {"update_id": next(_update_ids), **body}


def text_message(user_id: int, text: str, username: str | None = "tester") -> dict[str, Any]:
    return _update(message=_message(user_id, username, text=text))


def start_command(user_id: int, token: str, username: str | None = "tester") -> dict[str, Any]:
    text = f"/start {token}"
    entities = [{"type": "bot_command", "offset": 0, "length": len("/start")}]
    return _update(message=_message(user_id, username, text=text, entities=entities))


def document_message(
    user_id: int,
    file_name: str,
    *,
    mime_type: str | None = None,
    file_id: str | None = None,
    file_size: int = 1024,
    caption: str | None = None,
    username: str | None = "tester",
) -> dict[str, Any]:
    if mime_type is None:
        mime_type = XLSX_MIME if file_name.lower().endswith(".xlsx") else PDF_MIME
    document = {
        "file_id": file_id or f"doc-{file_name}",
        "file_unique_id": f"uniq-{file_name}",
        "file_name": file_name,
        "mime_type": mime_type,
        "file_size": file_size,
    }
    content: dict[str, Any] = {"document": document}
    if caption is not None:
        content["caption"] = caption
    return _update(message=_message(user_id, username, **content))


def photo_message(
    user_id: int,
    *,
    file_id: str = "photo-1",
    caption: str | None = None,
    username: str | None = "tester",
) -> dict[str, Any]:
    sizes = [
        {"file_id": f"{file_id}-s", "file_unique_id": f"{file_id}-su", "width": 90, "height": 90},
        {"file_id": file_id, "file_unique_id": f"{file_id}-lu", "width": 1280, "height": 960},
    ]
    content: dict[str, Any] = {"photo": sizes}
    if caption is not None:
        content["caption"] = caption
    return _update(message=_message(user_id, username, **content))


def callback_query(
    user_id: int,
    data: str,
    *,
    message_id: int = 1,
    username: str | None = "tester",
) -> dict[str, Any]:
    message = _message(user_id, username, text="Prompt")
    message["message_id"] = message_id
    message["from"] = {"id": 1, "is_bot": True, "first_name": "Bot", "username": "cafe_books_bot"}
    return _update(
        callback_query={
            "id": f"cbq-{next(_update_ids)}",
            "from": _user(user_id, username),
            "chat_instance": "test-instance",
            "data": data,
            "message": message,
        }
    )
