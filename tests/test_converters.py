import pytest

from messydata.converters import *


@pytest.mark.parametrize(
    "left, right, expected", [
        (1, 1, (1, 1)),
        (1.0, 1, (1, 1)),
        (False, 1, (False, 1)),
        (datetime.date(2010, 1, 1), datetime.datetime(2010, 1, 1),
         (datetime.datetime(2010, 1, 1), datetime.datetime(2010, 1, 1))),
        (Decimal(1.13), 1.13, (Decimal(1.13), Decimal(1.13))),
        ("2010-01-01", datetime.date(2010, 1, 1),
         (datetime.date(2010, 1, 1), datetime.date(2010, 1, 1)))
    ]
)
def test_upcast(left, right, expected):
    assert expected == upcast(left, right)


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.date(2010, 1, 1), None),
        (datetime.datetime(2010, 1, 1), None),
        ("abc", None),
        ("2010-01-01", None),
        (True, True),
        (False, False),
        (1, True),
        (0, False)
    ]
)
def test_try_bool(val, expected):
    actual = try_bool(ignore_errors=True)(val)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.date(2010, 1, 1), None),
        (datetime.datetime(2010, 1, 1), None),
        ("abc", None),
        ("2010-01-01", None),
        (True, None),
        (False, None),
        (1.2, Decimal(1.2).quantize(Decimal(".01"))),
        (1, Decimal(1).quantize(Decimal(".01")))
    ]
)
def test_try_currency(val, expected):
    actual = try_currency(ignore_errors=True)(val)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.date(2010, 1, 1), datetime.date(2010, 1, 1)),
        (datetime.datetime(2010, 1, 1), datetime.date(2010, 1, 1)),
        ("abc", None),
        ("2010-01-01", datetime.date(2010, 1, 1)),
        (1, None)
    ]
)
def test_try_date(val, expected):
    actual = try_date(ignore_errors=True)(val)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.datetime(2010, 1, 1), datetime.datetime(2010, 1, 1)),
        (datetime.date(2010, 1, 1), datetime.datetime(2010, 1, 1)),
        ("abc", None),
        ("2010-01-01", datetime.datetime(2010, 1, 1))
    ]
)
def test_try_datetime(val, expected):
    actual = try_datetime(ignore_errors=True)(val)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.date(2010, 1, 1), None),
        (datetime.datetime(2010, 1, 1), None),
        ("abc", None),
        ("2010-01-01", None),
        (1.13, 1.13),
        (1, 1),
        ("1.13", 1.13)
    ]
)
def test_try_float(val, expected):
    actual = try_float(ignore_errors=True)(val)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.date(2010, 1, 1), None),
        (datetime.datetime(2010, 1, 1), None),
        ("abc", None),
        ("2010-01-01", None),
        (1.13, 1),
        (1, 1),
        ("1.13", 1)
    ]
)
def test_try_int(val, expected):
    actual = try_int(ignore_errors=True)(val)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, None),
        (datetime.date(2010, 1, 1), "2010-01-01"),
        (datetime.datetime(2010, 1, 1), "2010-01-01 00:00:00"),
        ("abc", "abc"),
        ("2010-01-01", "2010-01-01"),
        (1.13, "1.13"),
        (1, "1"),
        ("1.13", "1.13")
    ]
)
def test_try_str(val, expected):
    actual = try_str(ignore_errors=True)(val)
    assert expected == actual
