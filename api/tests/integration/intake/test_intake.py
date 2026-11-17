"""T-090 to T-096, T-245."""

import datetime as dt
import hashlib
import io
import time
from pathlib import Path

import httpx
import pillow_heif
import pytest
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper import invoice_pipeline
from bookkeeper.db.models import Document, Supplier
from bookkeeper.telegram.handlers import supplier_docs
from bookkeeper.templates import render
from tests.integration.telegram.conftest import SUPPLIER_ID, post_update
from tests.support import telegram_updates as tu
from tests.support.fakes import RecordingBot

MB = 1024 * 1024
PDF = b"%PDF-1.4\n" + b"x" * 200


def _image(fmt: str) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (32, 24), "white").save(out, format=fmt)
    return out.getvalue()


def _heic() -> bytes:
    pillow_heif.register_heif_opener()
    return _image("HEIF")


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []

    async def fake_start(document_id: int) -> None:
        calls.append(document_id)

    monkeypatch.setattr(invoice_pipeline, "start", fake_start)
    return calls


@pytest.fixture(autouse=True)
def storage_root(tg_app: FastAPI, tmp_path: Path) -> Path:
    root = tmp_path / "storage"
    tg_app.state.settings = tg_app.state.settings.model_copy(update={"storage_dir": root})
    return root


def _stored_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


async def _send(
    client: httpx.AsyncClient,
    app: FastAPI,
    bot: RecordingBot,
    name: str,
    data: bytes,
    *,
    size: int | None = None,
    mime: str | None = None,
    file_id: str | None = None,
) -> None:
    fid = file_id or f"f-{name}"
    bot.files[fid] = data
    update = tu.document_message(
        SUPPLIER_ID,
        name,
        file_id=fid,
        mime_type=mime,
        file_size=len(data) if size is None else size,
    )
    await post_update(client, app, update)


async def _docs(session: AsyncSession) -> list[Document]:
    return list((await session.scalars(select(Document).order_by(Document.id))).all())


async def test_t090_pdf_jpg_png_heic_accepted(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
) -> None:
    files = {
        "a.pdf": PDF,
        "b.jpg": _image("JPEG"),
        "c.png": _image("PNG"),
        "d.heic": _heic(),
    }
    for name, data in files.items():
        await _send(client, tg_app, bot, name, data)
    docs = await _docs(db_session)
    assert [d.mime for d in docs] == [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/heic",
    ]
    assert all((storage_root / d.path).is_file() for d in docs)
    heic = docs[3]
    assert heic.preview_path is not None
    with Image.open(storage_root / heic.preview_path) as preview:
        assert preview.format == "JPEG"
    assert started == [d.id for d in docs]


async def test_t090_photo_message_is_accepted(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
) -> None:
    bot.files["photo-1"] = _image("JPEG")
    await post_update(client, tg_app, tu.photo_message(SUPPLIER_ID))
    docs = await _docs(db_session)
    assert [d.mime for d in docs] == ["image/jpeg"]
    assert started == [docs[0].id]


@pytest.mark.parametrize(
    ("name", "mime", "data"),
    [
        (
            "invoice.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK\x03\x04docx",
        ),
        ("files.zip", "application/zip", b"PK\x03\x04zip"),
    ],
)
async def test_t091_other_types_rejected(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
    name: str,
    mime: str,
    data: bytes,
) -> None:
    await _send(client, tg_app, bot, name, data, mime=mime)
    assert bot.sent_texts == [render("document_wrong_type")]
    assert await _docs(db_session) == []
    assert started == []
    assert _stored_files(storage_root) == []


async def test_t092_21mb_pdf_rejected(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
) -> None:
    await _send(client, tg_app, bot, "big.pdf", PDF + b"0" * (21 * MB))
    assert bot.sent_texts == [render("document_too_big")]
    assert await _docs(db_session) == []
    assert started == []
    assert _stored_files(storage_root) == []


async def test_t093_executable_named_pdf_rejected(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
) -> None:
    await _send(
        client, tg_app, bot, "invoice.pdf", b"MZ\x90\x00" + b"\x00" * 100, mime="application/pdf"
    )
    assert bot.sent_texts == [render("document_wrong_type")]
    assert await _docs(db_session) == []
    assert started == []
    assert _stored_files(storage_root) == []


async def test_t094_stored_by_date_and_supplier(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    when = dt.datetime(2026, 11, 18, 9, 30, tzinfo=dt.UTC)
    monkeypatch.setattr(supplier_docs, "now", lambda: when)
    await _send(client, tg_app, bot, "inv.pdf", PDF)
    (doc,) = await _docs(db_session)
    digest = hashlib.sha256(PDF).hexdigest()
    assert doc.path == f"invoices/2026/11/ocean-fresh/{digest}.pdf"
    assert (storage_root / doc.path).read_bytes() == PDF
    assert doc.sha256 == digest
    assert doc.mime == "application/pdf"
    assert doc.size == len(PDF)
    assert doc.sender_user_id is not None
    assert doc.received_at == when


async def test_t095_ack_is_prompt_template(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    started: list[int],
) -> None:
    begun = time.monotonic()
    await _send(client, tg_app, bot, "inv.pdf", PDF)
    assert time.monotonic() - begun < 10
    assert bot.sent_texts == ["Got it, thanks."]
    assert bot.calls_for("send_message")[0].chat_id == SUPPLIER_ID


async def test_t096_identical_file_is_not_stored_twice(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
) -> None:
    await _send(client, tg_app, bot, "inv.pdf", PDF)
    await _send(client, tg_app, bot, "copy.pdf", PDF, file_id="other-file-id")
    docs = await _docs(db_session)
    assert len(docs) == 1
    assert len(_stored_files(storage_root)) == 1
    assert started == [docs[0].id, docs[0].id]
    assert await db_session.scalar(select(func.count()).select_from(Document)) == 1


async def test_t245_25mb_pdf_gets_size_reply(
    client: httpx.AsyncClient,
    tg_app: FastAPI,
    bot: RecordingBot,
    people: dict[str, Supplier | None],
    db_session: AsyncSession,
    started: list[int],
    storage_root: Path,
) -> None:
    await _send(client, tg_app, bot, "huge.pdf", PDF, size=25 * MB)
    assert bot.sent_texts == [render("document_too_big")]
    assert "20 MB" in bot.sent_texts[0]
    assert bot.calls_for("get_file") == []
    assert await _docs(db_session) == []
    assert started == []
    assert _stored_files(storage_root) == []
