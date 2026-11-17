"""Stand-in for P2-T05 package. See planning/build-plan.md#p2-t06-checks-f-0136-to-f-01310."""

from bookkeeper.ledger.checks.base import Check, CheckContext, CheckResult

CHECKS: list[Check] = []

__all__ = ["CHECKS", "Check", "CheckContext", "CheckResult"]
