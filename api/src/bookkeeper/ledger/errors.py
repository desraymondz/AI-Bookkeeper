"""See planning/01-prd.md#global-rules (G-1, G-2, G-3)."""

from decimal import Decimal


class LedgerError(Exception):
    pass


class InvalidEntryError(LedgerError):
    pass


class TooFewLinesError(InvalidEntryError):
    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(f"An entry needs at least 2 lines; got {count}.")


class InvalidAmountError(InvalidEntryError):
    def __init__(self, reason: str, *, line_no: int | None = None) -> None:
        self.reason = reason
        self.line_no = line_no
        prefix = f"Line {line_no}: " if line_no is not None else ""
        super().__init__(f"{prefix}{reason}")


class UnbalancedEntryError(InvalidEntryError):
    def __init__(self, debits: Decimal, credits: Decimal) -> None:
        self.debits = debits
        self.credits = credits
        self.difference = abs(debits - credits)
        super().__init__(
            f"Entry is unbalanced: debits {debits} and credits {credits} "
            f"differ by {self.difference}."
        )


class ImmutableEntryError(LedgerError):
    pass


class EntryNotFoundError(LedgerError):
    def __init__(self, entry_id: int) -> None:
        self.entry_id = entry_id
        super().__init__(f"Journal entry {entry_id} does not exist.")


class EntryStateError(LedgerError):
    pass


class AlreadyReversedError(EntryStateError):
    def __init__(self, entry_id: int, reversal_id: int) -> None:
        self.entry_id = entry_id
        self.reversal_id = reversal_id
        super().__init__(f"Journal entry {entry_id} is already reversed by entry {reversal_id}.")
