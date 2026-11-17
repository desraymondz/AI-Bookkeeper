"""See planning/01-prd.md (F-008.3) and planning/decisions.md#D-019."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import AuditActor, AuditLog
from bookkeeper.telegram.router import Role, Sender

REFUSED_ROLES = frozenset({Role.SUPPLIER, Role.STRANGER})

ToolFn = Callable[..., Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    args: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolOutcome:
    ran: bool
    value: Any = None


async def run_tool_call(
    session: AsyncSession, sender: Sender, call: ToolCall, tools: Mapping[str, ToolFn]
) -> ToolOutcome:
    handler = tools.get(call.name)
    if sender.role in REFUSED_ROLES or handler is None:
        session.add(
            AuditLog(
                actor=AuditActor.AGENT,
                action="tool_refused",
                ref_type="telegram_user",
                ref_id=str(sender.telegram_user_id),
                detail_json={"tool": call.name, "role": sender.role.value},
            )
        )
        await session.flush()
        return ToolOutcome(ran=False)
    return ToolOutcome(ran=True, value=await handler(**call.args))
