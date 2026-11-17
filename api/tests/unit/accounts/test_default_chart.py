from bookkeeper.db.models import AccountType
from bookkeeper.ledger.coa import DEFAULT_CHART


def test_codes_and_names_unique() -> None:
    assert len({a.code for a in DEFAULT_CHART}) == len(DEFAULT_CHART)
    assert len({a.name for a in DEFAULT_CHART}) == len(DEFAULT_CHART)


def test_accumulated_depreciation_is_contra_asset() -> None:
    by_name = {a.name: a for a in DEFAULT_CHART}
    assert by_name["Accumulated Depreciation"].type is AccountType.CONTRA_ASSET
