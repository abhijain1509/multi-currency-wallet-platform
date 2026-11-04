from decimal import Decimal

from app.core.money import convert_minor, to_major, to_minor


def test_to_minor_usd():
    assert to_minor(Decimal("10.00"), "USD") == 1000
    assert to_minor(Decimal("10.005"), "USD") == 1000  # banker's rounding


def test_to_minor_jpy_zero_decimals():
    assert to_minor(Decimal("1500"), "JPY") == 1500


def test_to_major_roundtrip():
    assert to_major(1234, "USD") == Decimal("12.34")
    assert to_major(1500, "JPY") == Decimal("1500")


def test_convert_minor_usd_to_eur():
    # 10.00 USD at 0.5 -> 5.00 EUR
    assert convert_minor(1000, "USD", "EUR", Decimal("0.5")) == 500


def test_convert_minor_usd_to_jpy():
    # 10.00 USD at 100 -> 1000 JPY (0 decimals)
    assert convert_minor(1000, "USD", "JPY", Decimal("100")) == 1000
