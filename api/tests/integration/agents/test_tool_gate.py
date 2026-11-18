"""T-077."""

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.agents.tool_gate import ToolCall, run_tool_call
from bookkeeper.db.models import AuditLog
from bookkeeper.telegram.router import Role, Sender


async def test_t077_supplier_tool_calls_are_refused_and_audited(db_session: AsyncSession) -> None:
    ran: list[str] = []

    def tool(name: str) -> Any:
        async def _run(**_: Any) -> str:
            ran.append(name)
            return "data"

        return _run

    tools = {n: tool(n) for n in ("trial_balance", "profit_and_loss", "send_message")}
    supplier = Sender(Role.SUPPLIER, 2002, supplier_id=1)

    outcomes = [
        await run_tool_call(db_session, supplier, ToolCall(name, {}), tools) for name in tools
    ]

    assert [o.ran for o in outcomes] == [False, False, False]
    assert ran == []
    logged = (
        await db_session.scalars(select(AuditLog).where(AuditLog.action == "tool_refused"))
    ).all()
    assert [row.detail_json["tool"] for row in logged] == list(tools)
    assert {row.ref_id for row in logged} == {"2002"}


@pytest.mark.parametrize("role", [Role.SUPPLIER, Role.STRANGER])
async def test_unlisted_tool_is_refused_for_every_role(
    db_session: AsyncSession, role: Role
) -> None:
    outcome = await run_tool_call(db_session, Sender(role, 5), ToolCall("anything", {}), {})
    assert outcome.ran is False


async def test_boss_runs_registered_tool(db_session: AsyncSession) -> None:
    async def tool(**kwargs: Any) -> Any:
        return kwargs

    outcome = await run_tool_call(
        db_session, Sender(Role.BOSS, 1), ToolCall("t", {"a": 1}), {"t": tool}
    )
    assert (outcome.ran, outcome.value) == (True, {"a": 1})
