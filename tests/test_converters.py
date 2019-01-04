import pytest

from messydata.converters import *


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


def test_try_bool_invalid_input():
    with pytest.raises(TypeError) as e:
        try_bool(ignore_errors=False)("abc")
    assert "The value 'abc' could not be converted to a boolean." == str(e.value)

    assert try_bool(ignore_errors=True)("abc") is None


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


def test_try_currency_invalid_input():
    with pytest.raises(TypeError) as e:
        try_currency(ignore_errors=False)("abc")
    assert "The value 'abc' could not be converted to a Decimal." == str(e.value)

    assert try_currency(ignore_errors=True)("abc") is None


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


def test_try_date_invalid_input():
    with pytest.raises(TypeError) as e:
        try_date(ignore_errors=False)("abc")
    assert "The value 'abc' could not be converted to a date." == str(e.value)

    assert try_date(ignore_errors=True)("abc") is None


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


def test_try_datetime_invalid_input():
    with pytest.raises(TypeError) as e:
        try_datetime(ignore_errors=False)("abc")
    assert "The value 'abc' could not be converted to a datetime." == str(e.value)

    assert try_datetime(ignore_errors=True)("abc") is None


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


def test_try_float_invalid_input():
    with pytest.raises(TypeError) as e:
        try_float(ignore_errors=False)("abc")
    assert "The value 'abc' could not be converted to a float." == str(e.value)

    assert try_float(ignore_errors=True)("abc") is None


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


def test_try_int_invalid_input():
    with pytest.raises(TypeError) as e:
        try_int(ignore_errors=False)("abc")
    assert "The value 'abc' could not be converted to a int." == str(e.value)

    assert try_int(ignore_errors=True)("abc") is None


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


@pytest.mark.parametrize(
    "left, right, expected", [
        (1, 1, (1, 1)),
        (1.0, 1, (1, 1)),
        (1, 1.0, (1, 1)),
        (1.0, True, (1, 1)),
        (False, 1, (0, 1)),
        (True, 1.0, (1, 1)),
        (datetime.date(2010, 1, 1), datetime.datetime(2010, 1, 1),
         (datetime.datetime(2010, 1, 1), datetime.datetime(2010, 1, 1))),
        (Decimal(1.13), 1.13, (Decimal(1.13), Decimal(1.13))),
        ("2010-01-01", datetime.date(2010, 1, 1),
         (datetime.date(2010, 1, 1), datetime.date(2010, 1, 1)))
    ]
)
def test_upcast(left, right, expected):
    assert expected == upcast_values(left, right)
