import pytest

from messydata.operators import *


def test_operator_eq():
    assert Operator.Add == Operator.Add
    assert Operator.Subtract != Operator.Add


@pytest.mark.parametrize(
    "left, right, expected", [
        ("Test", "This", "TestThis"),
        (1, 2, 3),
        (None, 2, 2),
        (None, "abc", "abc"),
        (Decimal(1.13).quantize(Decimal(".01")), Decimal(2.4).quantize(Decimal(".01")), Decimal(3.53).quantize(Decimal(".01"))),
        (Decimal(1.13).quantize(Decimal(".01")), None, Decimal(1.13).quantize(Decimal(".01"))),
        (datetime.date(2010, 1, 1), 1, datetime.date(2010, 1, 2)),
        (datetime.datetime(2010, 1, 1), 1, datetime.datetime(2010, 1, 2)),
        (datetime.datetime(2010, 1, 1), 1.4, datetime.datetime(2010, 1, 2, 9, 36)),
        (datetime.date(2010, 1, 1), datetime.timedelta(days=3), datetime.date(2010, 1, 4)),
        (datetime.datetime(2010, 1, 1), datetime.timedelta(days=3), datetime.datetime(2010, 1, 4)),
    ]
)
def test_safe_add(left, right, expected):
    actual = add_fields(left, right)
    assert expected == actual


@pytest.mark.parametrize(
    "left, right, error_msg", [
        ("Test", datetime.date(2010, 1, 1), "Cannot add 'Test' to a date"),
        (datetime.date(1900, 1, 1), datetime.date(2010, 1, 1),
         "Cannot add datetime.date(2010, 1, 1) to a date"),
    ]
)
def test_safe_add_invalid_inputs(left, right, error_msg):
    with pytest.raises(ValueError) as excinfo:
        add_fields(left, right)
    assert error_msg in str(excinfo.value), (
        "\nExpected error message: {}\nActual error message: {}"
        .format(error_msg, str(excinfo.value))
    )


@pytest.mark.parametrize(
    "left, right, expected", [
        (1, 2, 0.5),
        (None, 2, 0),
        (Decimal(2).quantize(Decimal(".01")), Decimal(4.0).quantize(Decimal(".01")),
         Decimal(0.5).quantize(Decimal(".01"))),
        (Decimal(2).quantize(Decimal(".01")), None, Decimal(0)),
    ]
)
def test_safe_divide(left, right, expected):
    actual = divide_fields(left, right)
    assert expected == actual


@pytest.mark.parametrize(
    "left, right, error_msg", [
        ("Test", datetime.date(2010, 1, 1),
         "Cannot divide 'Test' from datetime.date(2010, 1, 1)"),
        (datetime.date(1900, 1, 1), datetime.date(2010, 1, 1),
         "Cannot divide datetime.date(1900, 1, 1) from datetime.date(2010, 1, 1)"),
    ]
)
def test_safe_divide_invalid_inputs(left, right, error_msg):
    with pytest.raises(ValueError) as excinfo:
        divide_fields(left, right)
    assert error_msg in str(excinfo.value), (
        "\nExpected error message: {}\nActual error message: {}"
        .format(error_msg, str(excinfo.value))
    )


@pytest.mark.parametrize(
    "left, right, expected", [
        (1, 2, 2),
        (None, 2, 0),
        (Decimal(1.13).quantize(Decimal(".01")), Decimal(2.4).quantize(Decimal(".01")),
         Decimal("2.71")),
        (Decimal(1.13).quantize(Decimal(".01")), None, Decimal(0)),
        (Decimal(1.13).quantize(Decimal(".01")), 0, Decimal(0)),
        (Decimal(100).quantize(Decimal(".01")), 0.04, Decimal(4))
    ]
)
def test_safe_multiply(left, right, expected):
    actual = multiply_fields(left, right)
    if isinstance(actual, Decimal):
        actual = actual.quantize(Decimal(".01"))
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (1, -1),
        (None, None),
        (-1, 1),
        (Decimal(2), Decimal(-2))
    ]
)
def test_safe_negate(val, expected):
    actual = negate_field(val)
    assert expected == actual


@pytest.mark.parametrize(
    "left, right, expected", [
        (1, 2, -1),
        (None, 2, -2),
        (Decimal(1.13).quantize(Decimal(".01")), Decimal(2.4).quantize(Decimal(".01")),
         Decimal(-1.27).quantize(Decimal(".01"))),
        (Decimal(1.13).quantize(Decimal(".01")), None, Decimal(1.13).quantize(Decimal(".01"))),
        (datetime.date(2010, 1, 1), 1, datetime.date(2009, 12, 31)),
        (datetime.datetime(2010, 1, 1), 1, datetime.datetime(2009, 12, 31)),
        (datetime.datetime(2010, 1, 1), 1.4, datetime.datetime(2009, 12, 30, 14, 24)),
        (datetime.date(2010, 1, 1), datetime.timedelta(days=3), datetime.date(2009, 12, 29)),
        (datetime.datetime(2010, 1, 1), datetime.timedelta(days=3), datetime.datetime(2009, 12, 29)),
    ]
)
def test_safe_subtract(left, right, expected):
    actual = subtract_fields(left, right)
    assert expected == actual


@pytest.mark.parametrize(
    "val, expected", [
        (None, False),
        (1, True),
        (2.13, True),
        ("abc", False),
        (0, True),
        (0.0, True),
        (datetime.date.min, False)
    ]
)
def test_is_numeric(val, expected):
    assert is_numeric(val) is expected
