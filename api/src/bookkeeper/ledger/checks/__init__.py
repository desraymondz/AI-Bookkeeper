"""See planning/01-prd.md#f-013-deterministic-checks."""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import CheckResult as CheckRow
from bookkeeper.ledger.checks import arithmetic, balanced, duplicate, gst, known_supplier
from bookkeeper.ledger.checks.base import CheckContext, CheckResult

CheckFn = Callable[[CheckContext], Awaitable[CheckResult]]

CHECKS: list[CheckFn] = [
    known_supplier.run,
    arithmetic.run,
    gst.run,
    balanced.run,
    duplicate.run,
]


async def run_checks(ctx: CheckContext) -> list[CheckResult]:
    return [await check(ctx) for check in CHECKS]


async def store_results(
    session: AsyncSession, entry_id: int, results: list[CheckResult]
) -> list[CheckRow]:
    rows = [
        CheckRow(entry_id=entry_id, check_code=r.code, passed=r.passed, detail=r.detail)
        for r in results
    ]
    session.add_all(rows)
    await session.flush()
    return rows


__all__ = ["CHECKS", "CheckContext", "CheckResult", "run_checks", "store_results"]
