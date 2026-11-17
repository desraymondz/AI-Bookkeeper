"""T-105, T-106. See planning/04-test-spec.md."""

from bookkeeper.db.models import UserRole
from bookkeeper.ledger.checks import known_supplier
from tests.unit.checks.builders import make_ctx, make_invoice, make_sender, make_supplier


async def test_t105_fuzzy_name_passes() -> None:
    result = await known_supplier.run(
        make_ctx(invoice=make_invoice(supplier_name="OCEAN FRESH PTE. LTD."))
    )
    assert result.passed


async def test_t106_other_name_fails_naming_both() -> None:
    result = await known_supplier.run(
        make_ctx(invoice=make_invoice(supplier_name="Dairy Best Pte Ltd"))
    )
    assert not result.passed
    assert "Dairy Best Pte Ltd" in result.detail
    assert "Ocean Fresh" in result.detail


async def test_inactive_supplier_fails() -> None:
    supplier = make_supplier(active=False)
    assert not (await known_supplier.run(make_ctx(supplier=supplier))).passed


async def test_sender_bound_to_other_supplier_fails() -> None:
    supplier = make_supplier()
    sender = make_sender(make_supplier(id=2))
    assert not (await known_supplier.run(make_ctx(supplier=supplier, sender=sender))).passed


async def test_boss_sender_fails() -> None:
    supplier = make_supplier()
    sender = make_sender(supplier, role=UserRole.BOSS)
    assert not (await known_supplier.run(make_ctx(supplier=supplier, sender=sender))).passed


async def test_unread_name_fails() -> None:
    assert not (await known_supplier.run(make_ctx(invoice=make_invoice(supplier_name=None)))).passed
