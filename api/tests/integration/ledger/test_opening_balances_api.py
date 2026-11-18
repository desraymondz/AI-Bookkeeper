from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, EntryKind, EntryStatus, JournalEntry, JournalLine
from bookkeeper.ledger.coa import seed_default_chart

pytestmark = pytest.mark.integration


async def _ids(session: AsyncSession) -> dict[str, int]:
    await seed_default_chart(session)
    await session.commit()
    rows = await session.execute(select(Account.name, Account.id))
    return {name: acc_id for name, acc_id in rows.all()}


async def _entries(session: AsyncSession) -> list[JournalEntry]:
    rows = await session.scalars(
        select(JournalEntry)
        .order_by(JournalEntry.entry_no)
        .execution_options(populate_existing=True)
    )
    return list(rows.all())


def _body(acc: dict[str, int], capital: str, as_at: str = "2026-08-31") -> dict[str, object]:
    return {
        "as_at": as_at,
        "lines": [
            {"account_id": acc["Cash"], "debit": "1000.00"},
            {"account_id": acc["Bank"], "debit": "5000.00"},
            {"account_id": acc["Owner's Capital"], "credit": capital},
            {"account_id": acc["Sales"], "debit": "0", "credit": "0"},
        ],
    }


async def test_t047_unbalanced_opening_rejected(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    acc = await _ids(db_session)

    res = await client.put("/api/opening-balances", json=_body(acc, "5500.00"))

    assert res.status_code == 422
    count = await db_session.scalar(select(func.count()).select_from(JournalEntry))
    assert count == 0


async def test_t048_balanced_opening_posts_one_entry(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    acc = await _ids(db_session)

    res = await client.put("/api/opening-balances", json=_body(acc, "6000.00"))

    assert res.status_code == 200
    assert res.json()["entry_no"] == "JE-00001"
    entries = await _entries(db_session)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.kind is EntryKind.OPENING
    assert entry.status is EntryStatus.POSTED
    assert entry.date.isoformat() == "2026-08-31"
    lines = (
        await db_session.scalars(select(JournalLine).where(JournalLine.entry_id == entry.id))
    ).all()
    assert len(lines) == 3
    assert sum((ln.debit for ln in lines), Decimal(0)) == Decimal("6000.00")

    state = (await client.get("/api/opening-balances")).json()
    assert state["entry_no"] == "JE-00001"
    assert state["as_at"] == "2026-08-31"
    assert len(state["lines"]) == 3


async def test_resave_reverses_previous_and_links(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    acc = await _ids(db_session)
    await client.put("/api/opening-balances", json=_body(acc, "6000.00"))
    body = _body(acc, "7000.00")
    body["lines"][1]["debit"] = "6000.00"  # type: ignore[index]

    res = await client.put("/api/opening-balances", json=body)

    assert res.status_code == 200
    assert res.json() == {
        "entry_no": "JE-00003",
        "as_at": "2026-08-31",
        "reversed_entry_no": "JE-00001",
        "reversal_entry_no": "JE-00002",
    }
    first, reversal, second = await _entries(db_session)
    assert reversal.kind is EntryKind.REVERSAL
    assert reversal.reverses_id == first.id
    assert second.kind is EntryKind.OPENING
    assert second.reverses_id == first.id
    state = (await client.get("/api/opening-balances")).json()
    assert state["entry_no"] == "JE-00003"


async def test_unknown_account_rejected(client: httpx.AsyncClient) -> None:
    res = await client.put(
        "/api/opening-balances",
        json={
            "as_at": "2026-08-31",
            "lines": [
                {"account_id": 9999, "debit": "10.00"},
                {"account_id": 9998, "credit": "10.00"},
            ],
        },
    )
    assert res.status_code == 422


async def test_empty_state(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/opening-balances")
    assert res.json() == {"entry_no": None, "as_at": None, "lines": []}
