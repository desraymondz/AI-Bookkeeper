"""See planning/01-prd.md#f-003-chart-of-accounts."""

from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bookkeeper.db.models import Account, AccountType


@dataclass(frozen=True, slots=True)
class DefaultAccount:
    code: str
    name: str
    type: AccountType
    subtype: str


DEFAULT_CHART: tuple[DefaultAccount, ...] = (
    DefaultAccount("1000", "Cash", AccountType.ASSET, "cash"),
    DefaultAccount("1010", "Bank", AccountType.ASSET, "cash"),
    DefaultAccount("1200", "Input GST", AccountType.ASSET, "current_asset"),
    DefaultAccount("1500", "Equipment", AccountType.ASSET, "fixed_asset"),
    DefaultAccount("1510", "Accumulated Depreciation", AccountType.CONTRA_ASSET, "fixed_asset"),
    DefaultAccount("2000", "Accounts Payable", AccountType.LIABILITY, "current_liability"),
    DefaultAccount("2100", "Output GST", AccountType.LIABILITY, "current_liability"),
    DefaultAccount("3000", "Owner's Capital", AccountType.EQUITY, "capital"),
    DefaultAccount("3100", "Retained Earnings", AccountType.EQUITY, "retained_earnings"),
    DefaultAccount("4000", "Sales", AccountType.REVENUE, "operating_revenue"),
    DefaultAccount("5000", "COGS Seafood", AccountType.EXPENSE, "cogs"),
    DefaultAccount("5010", "COGS Dairy", AccountType.EXPENSE, "cogs"),
    DefaultAccount("5100", "Packaging", AccountType.EXPENSE, "cogs"),
    DefaultAccount("6000", "Rent", AccountType.EXPENSE, "operating_expense"),
    DefaultAccount("6010", "Utilities", AccountType.EXPENSE, "operating_expense"),
    DefaultAccount("6020", "Wages", AccountType.EXPENSE, "operating_expense"),
    DefaultAccount("6030", "Bank Charges", AccountType.EXPENSE, "operating_expense"),
    DefaultAccount("6200", "Depreciation Expense", AccountType.EXPENSE, "operating_expense"),
)


async def seed_default_chart(session: AsyncSession) -> int:
    stmt = (
        insert(Account)
        .values(
            [
                {"code": a.code, "name": a.name, "type": a.type, "subtype": a.subtype}
                for a in DEFAULT_CHART
            ]
        )
        .on_conflict_do_nothing(index_elements=[Account.code])
        .returning(Account.id)
    )
    result = await session.execute(stmt)
    return len(result.all())
