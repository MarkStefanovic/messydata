from calendar import monthrange
import six
from dateutil.parser import parse

from messydata.types_ import *

__all__ = (
    "bomonth", "eomonth", "is_iterable", "list_wrapper", "tuple_wrapper",
    "unwrap_to_list"
)

T = TypeVar("T")


def is_iterable(value):  # type: (...) -> bool
    """Is the value iterable?

    :param value: One or more values to check if they are iterable
    :return: True if the value is iterable (and not a string), False otherwise
    """
    if isinstance(value, six.string_types):
        return False
    elif isinstance(value, Iterable):
        return True
    else:
        return False


def list_wrapper(value):  # type: (T) -> List[T]
    """Wrap an item in a list if it isn't a list already"""
    if not value:
        return []
    elif is_iterable(value):
        return [val for val in value]
    else:
        return [value]


def tuple_wrapper(value):
    return tuple(list_wrapper(value))


def unwrap_to_list(*values):  # type: (Union[T, Sequence[T]]) -> List[T]
    def flatten(items):
        for item in items:
            if is_iterable(item):
                for itm in flatten(item):
                    yield itm
            else:
                yield item

    return list(flatten(values))


def end_of_current_month(
    dtime  # type: datetime.date
):         # type: (...) -> Optional[datetime.date]
    last_day_of_month = monthrange(dtime.year, dtime.month)[1]
    eom = datetime.date(dtime.year, dtime.month, last_day_of_month)
    return eom


def first_day_of_next_month(dtime):   # type: (datetime.date) -> Optional[datetime.date]
    eom = end_of_current_month(dtime)
    next_day = datetime.timedelta(days=1)
    return eom + next_day


def end_of_next_month(dtime):   # type: (datetime.date) -> Optional[datetime.date]
    dtime = first_day_of_next_month(dtime)
    eom = end_of_current_month(dtime)
    return eom


def end_of_prior_month(dtime):   # type: (datetime.date) -> Optional[datetime.date]
    if dtime is None:
        return
    days_in_month = dtime.day
    offset = datetime.timedelta(days=-days_in_month)
    eom = dtime + offset
    return eom


def eomonth(
    start_date,      # type: Union[datetime.date, datetime.datetime],
    months_offset=0  # type: int
):                   # type: (...) -> Optional[datetime.date]
    """Get the end of the month x months before or after.

    The functionality is modeled after the Excel function of
    the same name.
    """
    if not start_date:
        return None
    elif isinstance(start_date, datetime.datetime):
        dt = start_date.date()
    elif isinstance(start_date, datetime.date):
        dt = start_date
    elif isinstance(start_date, six.string_types):
        dt = parse(start_date).date()
    else:
        raise ValueError("The value {!r} cannot be interpreted as a date.".format(start_date))

    if months_offset == 0:
        eom = end_of_current_month(dt)
    elif months_offset > 0:
        eom = None
        for i in range(0, months_offset, 1):
            eom = end_of_next_month(dt)
            dt = eom
    else:
        eom = None
        for i in range(0, months_offset, -1):
            eom = end_of_prior_month(dt)
            dt = eom
    return eom


def bomonth(
    dt,              # type: Union[datetime.date, datetime.datetime]
    months_offset=0  # type: int
):                   # type: (...) -> Optional[Union[datetime.date, datetime.datetime]]
    if dt is None:
        return
    eom = eomonth(dt, months_offset - 1)
    add_day = datetime.timedelta(days=1)
    bom = eom + add_day
    return bom
