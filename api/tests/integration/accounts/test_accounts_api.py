import datetime as dt
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import (
    Account,
    AccountType,
    EntrySource,
    EntryStatus,
    JournalEntry,
    JournalLine,
)
from bookkeeper.ledger.coa import DEFAULT_CHART, seed_default_chart

pytestmark = pytest.mark.integration

T038_ACCOUNTS = {
    "Cash": AccountType.ASSET,
    "Bank": AccountType.ASSET,
    "Accounts Payable": AccountType.LIABILITY,
    "Input GST": AccountType.ASSET,
    "Output GST": AccountType.LIABILITY,
    "Owner's Capital": AccountType.EQUITY,
    "Retained Earnings": AccountType.EQUITY,
    "Sales": AccountType.REVENUE,
    "COGS Seafood": AccountType.EXPENSE,
    "COGS Dairy": AccountType.EXPENSE,
    "Packaging": AccountType.EXPENSE,
    "Depreciation Expense": AccountType.EXPENSE,
    "Accumulated Depreciation": AccountType.CONTRA_ASSET,
    "Equipment": AccountType.ASSET,
}


async def _accounts(session: AsyncSession) -> dict[str, Account]:
    rows = (await session.scalars(select(Account).execution_options(populate_existing=True))).all()
    return {a.name: a for a in rows}


async def _post_to(session: AsyncSession, account_id: int, other_id: int) -> None:
    entry = JournalEntry(
        entry_no=1,
        date=dt.date(2026, 11, 10),
        description="Ocean Fresh INV-1043",
        source=EntrySource.AUTO,
        status=EntryStatus.POSTED,
        posted_at=dt.datetime(2026, 11, 10, 2, 0, tzinfo=dt.UTC),
    )
    session.add(entry)
    await session.flush()
    session.add_all(
        [
            JournalLine(
                entry_id=entry.id,
                line_no=1,
                account_id=account_id,
                debit=Decimal("400.00"),
                credit=Decimal("0"),
            ),
            JournalLine(
                entry_id=entry.id,
                line_no=2,
                account_id=other_id,
                debit=Decimal("0"),
                credit=Decimal("400.00"),
            ),
        ]
    )
    await session.commit()


async def test_t038_fresh_install_seeds_default_chart(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await client.put("/api/settings", json={"name": "Kopi Corner"})

    accounts = await _accounts(db_session)
    for name, kind in T038_ACCOUNTS.items():
        assert name in accounts, name
        assert accounts[name].code
        assert accounts[name].type is kind


async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    assert await seed_default_chart(db_session) == len(DEFAULT_CHART)
    assert await seed_default_chart(db_session) == 0
    assert len(await _accounts(db_session)) == len(DEFAULT_CHART)


async def test_list_flags_postings(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    await seed_default_chart(db_session)
    accounts = await _accounts(db_session)
    await _post_to(db_session, accounts["COGS Seafood"].id, accounts["Accounts Payable"].id)

    res = await client.get("/api/accounts")

    assert res.status_code == 200
    by_name = {a["name"]: a for a in res.json()}
    assert by_name["COGS Seafood"]["has_postings"] is True
    assert by_name["COGS Dairy"]["has_postings"] is False
    assert by_name["Accumulated Depreciation"]["type"] == "contra_asset"


async def test_add_account(client: httpx.AsyncClient) -> None:
    res = await client.post(
        "/api/accounts", json={"code": "6100", "name": "Ice", "type": "expense"}
    )

    assert res.status_code == 201
    body = res.json()
    assert body["code"] == "6100"
    assert body["active"] is True
    assert body["has_postings"] is False


async def test_add_duplicate_code_refused(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seed_default_chart(db_session)

    res = await client.post(
        "/api/accounts", json={"code": "1000", "name": "Petty", "type": "asset"}
    )

    assert res.status_code == 409
    assert res.json()["detail"][0]["loc"] == ["body", "code"]
    assert len(await _accounts(db_session)) == len(DEFAULT_CHART)


async def test_add_invalid_type_rejected(client: httpx.AsyncClient) -> None:
    res = await client.post("/api/accounts", json={"code": "7000", "name": "X", "type": "magic"})
    assert res.status_code == 422


async def test_rename_and_deactivate_unused(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seed_default_chart(db_session)
    dairy = (await _accounts(db_session))["COGS Dairy"]

    res = await client.patch(
        f"/api/accounts/{dairy.id}", json={"name": "COGS Milk", "active": False}
    )

    assert res.status_code == 200
    assert res.json()["name"] == "COGS Milk"
    assert res.json()["active"] is False


async def test_change_type_allowed_without_postings(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seed_default_chart(db_session)
    pack = (await _accounts(db_session))["Packaging"]

    res = await client.patch(f"/api/accounts/{pack.id}", json={"type": "asset"})

    assert res.status_code == 200
    assert res.json()["type"] == "asset"


async def test_delete_unused_account(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    created = (
        await client.post("/api/accounts", json={"code": "6100", "name": "Ice", "type": "expense"})
    ).json()

    res = await client.delete(f"/api/accounts/{created['id']}")

    assert res.status_code == 204
    assert "Ice" not in await _accounts(db_session)


async def test_unknown_account_404(client: httpx.AsyncClient) -> None:
    assert (await client.patch("/api/accounts/999999", json={"name": "X"})).status_code == 404
    assert (await client.delete("/api/accounts/999999")).status_code == 404


async def test_t043_account_with_postings_cannot_be_deleted_or_retyped(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await seed_default_chart(db_session)
    accounts = await _accounts(db_session)
    seafood = accounts["COGS Seafood"]
    await _post_to(db_session, seafood.id, accounts["Accounts Payable"].id)
    before = (seafood.code, seafood.name, seafood.type, seafood.active)

    deleted = await client.delete(f"/api/accounts/{seafood.id}")
    retyped = await client.patch(f"/api/accounts/{seafood.id}", json={"type": "asset"})
    deactivated = await client.patch(f"/api/accounts/{seafood.id}", json={"active": False})

    assert deleted.status_code == 409
    assert retyped.status_code == 409
    assert retyped.json()["detail"][0]["loc"] == ["body", "type"]
    assert deactivated.status_code == 409
    after = (await _accounts(db_session))["COGS Seafood"]
    assert (after.code, after.name, after.type, after.active) == before
