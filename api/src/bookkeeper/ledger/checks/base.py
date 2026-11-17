"""Stand-in for P2-T05 base. See planning/build-plan.md#p2-t06-checks-f-0136-to-f-01310."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import BusinessSettings, Document, Supplier, User


@dataclass(frozen=True, slots=True)
class CheckResult:
    code: str
    passed: bool
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class CheckContext:
    session: AsyncSession
    settings: BusinessSettings
    supplier: Supplier
    sender_user: User | None
    invoice: Any
    document: Document
    proposed_entry: Any


Check = Callable[[CheckContext], Awaitable[CheckResult]]
