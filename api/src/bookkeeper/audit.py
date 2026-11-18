"""Audit log writes. See planning/01-prd.md#global-rules (G-7)."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import AuditActor, AuditLog


def record(
    session: AsyncSession,
    actor: AuditActor,
    action: str,
    ref_type: str,
    ref_id: int | str,
    detail: dict[str, Any] | None = None,
    *,
    model: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            ref_type=ref_type,
            ref_id=str(ref_id),
            model=model,
            detail_json=detail or {},
        )
    )
