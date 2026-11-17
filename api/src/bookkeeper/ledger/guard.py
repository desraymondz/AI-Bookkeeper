"""See planning/01-prd.md#global-rules (G-2) and planning/decisions.md#D-018."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import ORMExecuteState, Session, UOWTransaction

from bookkeeper.db.models import EntryStatus, JournalEntry, JournalLine
from bookkeeper.ledger.errors import ImmutableEntryError

_AUTHORIZED = "bookkeeper.ledger.posting"


@contextmanager
def authorize_posting(session: Session, entry: JournalEntry) -> Iterator[None]:
    allowed: set[int] = session.info.setdefault(_AUTHORIZED, set())
    allowed.add(id(entry))
    try:
        yield
    finally:
        allowed.discard(id(entry))


def _persisted_status(entry: JournalEntry) -> EntryStatus | None:
    state = inspect(entry)
    if state.transient or state.pending:
        return None
    history = state.attrs.status.history
    if history.deleted:
        old = history.deleted[0]
    elif history.unchanged:
        old = history.unchanged[0]
    else:
        old = entry.status
    return EntryStatus(old) if old is not None else None


def _label(entry: JournalEntry) -> str:
    return f"JE-{entry.entry_no:05d}" if entry.entry_no is not None else f"entry {entry.id}"


def _entry_is_posted(session: Session, entry_id: int | None) -> bool:
    if entry_id is None:
        return False
    entry = session.get(JournalEntry, entry_id)
    return entry is not None and _persisted_status(entry) == EntryStatus.POSTED


def _check_entry(session: Session, entry: JournalEntry, *, deleting: bool) -> None:
    was_posted = _persisted_status(entry) == EntryStatus.POSTED
    if was_posted and (deleting or session.is_modified(entry)):
        raise ImmutableEntryError(f"{_label(entry)} is posted and cannot be changed or deleted.")
    persisted = not (inspect(entry).transient or inspect(entry).pending)
    becomes_posted = persisted and entry.status == EntryStatus.POSTED and not was_posted
    if becomes_posted and id(entry) not in session.info.get(_AUTHORIZED, set()):
        raise ImmutableEntryError("Entries are posted only through bookkeeper.ledger.post.")


def _check_line(session: Session, line: JournalLine) -> None:
    entry_ids = {line.entry_id}
    state = inspect(line)
    if state.persistent or state.deleted:
        entry_ids.update(state.attrs.entry_id.history.deleted)
    for entry_id in entry_ids:
        if _entry_is_posted(session, entry_id):
            raise ImmutableEntryError(
                f"Lines of posted entry {entry_id} cannot be added, changed or deleted."
            )


def _before_flush(session: Session, flush_context: UOWTransaction, instances: Any) -> None:
    for obj in list(session.deleted):
        if isinstance(obj, JournalEntry):
            _check_entry(session, obj, deleting=True)
        elif isinstance(obj, JournalLine):
            _check_line(session, obj)
    for obj in list(session.dirty) + list(session.new):
        if isinstance(obj, JournalEntry):
            _check_entry(session, obj, deleting=False)
        elif isinstance(obj, JournalLine) and obj not in session.new and session.is_modified(obj):
            _check_line(session, obj)


def _do_orm_execute(state: ORMExecuteState) -> None:
    if not (state.is_update or state.is_delete):
        return
    mapper = state.bind_mapper
    if mapper is not None and mapper.class_ in (JournalEntry, JournalLine):
        raise ImmutableEntryError(
            "Bulk UPDATE or DELETE on journal tables is refused; use bookkeeper.ledger.post."
        )


def install() -> None:
    if not event.contains(Session, "before_flush", _before_flush):
        event.listen(Session, "before_flush", _before_flush)
    if not event.contains(Session, "do_orm_execute", _do_orm_execute):
        event.listen(Session, "do_orm_execute", _do_orm_execute)
