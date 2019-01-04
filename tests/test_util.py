import datetime
import pytest

from messydata.util import is_iterable, list_wrapper, unwrap_to_list, eomonth, bomonth


@pytest.fixture
def dummy_date():
    return datetime.datetime(year=2010, month=7, day=3, hour=4, minute=32, second=11, microsecond=3)


@pytest.mark.parametrize(
    "value, expected", [
        ("Test", False),
        (range(10), True),
        ([1, 2, 3, 4, 5], True),
        ([], True),
        (None, False),
        (1, False),
        ({1, 2, 3}, True)
    ]
)
def test_is_iterable(value, expected):
    actual = is_iterable(value)
    assert expected == actual


@pytest.mark.parametrize(
    "value, expected", [
        ("Test", ["Test"]),
        (range(10), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        ([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]),
        ([], []),
        (None, []),
        (1, [1])
    ]
)
def test_list_wrapper(value, expected):
    actual = list_wrapper(value)
    assert expected == actual


def test_unwrap_to_list():
    assert [1, 2, 3] == unwrap_to_list(1, 2, 3)
    assert [1, 2, 3] == unwrap_to_list([1, 2, 3])
    assert [1, 2, 3, 4, 3] == unwrap_to_list([1, [2, 3, 4], 3])
    assert [1, 2, 3, 4, 5, 4, 3] == unwrap_to_list([1, [2, [3, 4, 5], 4], 3])
    assert [] == unwrap_to_list()
    assert [None] == unwrap_to_list(None)


def test_eomonth(dummy_date):
    assert eomonth(dummy_date, 0) == datetime.date(2010, 7, 31)
    assert eomonth(dummy_date, -1) == datetime.date(2010, 6, 30)
    assert eomonth(dummy_date, -2) == datetime.date(2010, 5, 31)
    assert eomonth(dummy_date, 1) == datetime.date(2010, 8, 31)
    assert eomonth(dummy_date, 2) == datetime.date(2010, 9, 30)
    assert eomonth(None, 1) is None
    assert eomonth(datetime.date(2010, 1, 15), 1) == datetime.date(2010, 2, 28)
    assert eomonth("2010-1-15 02:25:51.771550", 1) == datetime.date(2010, 2, 28)
    with pytest.raises(ValueError) as e:
        eomonth(4, 3)
    assert "The value 4 cannot be interpreted as a date." == str(e.value)


def test_bomonth(dummy_date):
    assert bomonth(dummy_date, 0) == datetime.date(2010, 7, 1)
    assert bomonth(dummy_date, -1) == datetime.date(2010, 6, 1)
    assert bomonth(dummy_date, -2) == datetime.date(2010, 5, 1)
    assert bomonth(dummy_date, 1) == datetime.date(2010, 8, 1)
    assert bomonth(dummy_date, 2) == datetime.date(2010, 9, 1)
    assert bomonth(None, 1) is None
