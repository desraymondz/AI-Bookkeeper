"""Handler registry. See planning/build-plan.md (P2-T01)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bookkeeper.telegram.router import Handler

HANDLERS: list[Handler] = []
