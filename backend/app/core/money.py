"""Money handling utilities.

All monetary values are stored and moved as integer *minor units* (cents, pence,
paise, yen) to eliminate floating-point rounding errors. Decimal is used for any
arithmetic that crosses the major/minor boundary (e.g. FX conversion).
"""

from decimal import ROUND_HALF_EVEN, Decimal

# Number of decimal places in the minor unit for each currency.
CURRENCY_DECIMALS: dict[str, int] = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "INR": 2,
    "JPY": 0,
}


class UnsupportedCurrencyError(ValueError):
    pass


def _decimals(currency: str) -> int:
    try:
        return CURRENCY_DECIMALS[currency]
    except KeyError as exc:
        raise UnsupportedCurrencyError(currency) from exc


def to_minor(amount: Decimal, currency: str) -> int:
    scale = Decimal(10) ** _decimals(currency)
    return int((amount * scale).to_integral_value(rounding=ROUND_HALF_EVEN))


def to_major(minor: int, currency: str) -> Decimal:
    decimals = _decimals(currency)
    scale = Decimal(10) ** decimals
    quantum = Decimal(1).scaleb(-decimals)
    return (Decimal(minor) / scale).quantize(quantum)


def convert_minor(amount_minor: int, from_currency: str, to_currency: str, rate: Decimal) -> int:
    """Convert an amount in minor units from one currency to another.

    `rate` is the price of 1 unit of `from_currency` expressed in `to_currency`.
    """
    major = to_major(amount_minor, from_currency) * rate
    return to_minor(major, to_currency)
