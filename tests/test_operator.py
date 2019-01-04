import pytest

from messydata.operators import *
from hypothesis import given, reproduce_failure, example, assume
from hypothesis import strategies as st

from tests.conftest import any_primitive, primitive_st, Sales, example_sales_rows


@pytest.mark.parametrize(
    "left, right, or_equals, expected", [
        (True, True, True, True),
        (True, False, True, False),
        (1.0, 1, True, True),
        (1.0, -1, True, False),
        (1.0, -1, False, True)
    ]
)
def test_equals(left, right, or_equals, expected):
    actual = equals(left=left, right=right, or_equals=or_equals)
    assert expected == actual


@given(
    data=st.data(),
    primitive_st=primitive_st,
)
def test_equals_for_same_type_always_returns_bool(data, primitive_st):
    left = data.draw(primitive_st)
    right = data.draw(primitive_st)
    assert isinstance(equals(left=left, right=right, or_equals=False), bool)


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
        (1, 1.0, 0),
        (1, 1, 0)
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


@given(any_primitive)
def test_is_numeric_always_returns_bool(v):
    assert isinstance(is_numeric(v), bool)


def test_operator_repr():
    assert "Operator.Add" == repr(Operator.Add)


@given(rows=example_sales_rows)
def test_field_greater_than(rows):
    assume(len(rows) > 0)
    actual = Sales.from_iterable(rows).where(Sales.amount > 100).all()
    assert all(r["Amount"] > Decimal(100) for r in actual)


@given(rows=example_sales_rows)
def test_field_greater_than_or_equal_to(rows):
    assume(len(rows) > 0)
    actual = Sales.from_iterable(rows).where(Sales.amount >= 100).all()
    assert all(r["Amount"] >= Decimal(100) for r in actual)


@given(rows=example_sales_rows)
def test_field_less_than(rows):
    assume(len(rows) > 0)
    actual = Sales.from_iterable(rows).where(Sales.amount < 100).all()
    assert all(r["Amount"] < 100 for r in actual), str(actual)


@given(rows=example_sales_rows)
def test_field_less_than_or_equals(rows):
    assume(len(rows) > 0)
    actual = Sales.from_iterable(rows).where(Sales.amount <= 100).all()
    assert all(r["Amount"] <= 100 for r in actual), str(actual)


def test_fields_are_not_equal():
    actual = Sales.from_iterable([
        Sales(
            id=1,
            customer_id=1,
            item_id=1,
            sales_date=datetime.date(2018, 11, 1),
            amount=100,
            payment_due=datetime.date(2018, 11, 1)
        ),
        Sales(
            id=2,
            customer_id=1,
            item_id=1,
            sales_date=datetime.date(2018, 12, 1),
            amount=200,
            payment_due=datetime.date(2018, 12, 1)
        ),
        Sales(
            id=2,
            customer_id=1,
            item_id=1,
            sales_date=datetime.date(2018, 12, 1),
            amount=100,
            payment_due=datetime.date(2018, 12, 1)
        )
    ]).where(Sales.amount != 100).all()
    expected = [
        OrderedDict([
            ('ID', 2), ('Customer ID', 1), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2018, 12, 1, 0, 0)),
            ('Amount', Decimal('200.00')),
            ('Payment Due', datetime.datetime(2018, 12, 1, 0, 0))
        ])
    ]
    assert expected == actual, str(actual)


def test_multiply_fields_non_numeric_inputs():
    with pytest.raises(ValueError) as e:
        multiply_fields("abc", 123)
    assert "Cannot multiply 'abc' by 123" in str(e.value)

    with pytest.raises(ValueError) as e:
        multiply_fields(123, "abc")
    assert "Cannot multiply 123.0 by 'abc'" in str(e.value)


def test_negate_field_invalid_input():
    with pytest.raises(ValueError) as e:
        negate_field("abc")
    assert "'abc' is not a valid value for negation" in str(e.value)


def test_subtract_fields_invalid_input():
    with pytest.raises(ValueError) as e:
        subtract_fields(datetime.date(2010, 12, 31), "abc")
    assert "Cannot subtract 'abc' from a date" in str(e.value)

    with pytest.raises(ValueError) as e:
        subtract_fields("abc", 1)
    assert "Cannot subtract 'abc' from 1" in str(e.value)

