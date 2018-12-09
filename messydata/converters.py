from dateutil.parser import parse

from messydata.types_ import *


def try_bool(ignore_errors=False):  # type: (bool) -> Callable[[Primitive], Optional[bool]]
    def wrapper(val):  # type: (Primitive) -> Optional[bool]
        if val is None:
            return None
        elif isinstance(val, bool):
            return val
        elif isinstance(val, (float, int)) and val in (0, 1):
            return bool(val)
        else:
            if ignore_errors:
                return None
            raise TypeError("The value {!r} could not be converted to a boolean".format(val))
    return wrapper


def try_currency(ignore_errors=False):  # type: (bool) -> Callable[[Primitive], Optional[Decimal]]
    def wrapper(val):  # type: (Primitive) -> Optional[Decimal]
        if val is None:
            return None
        elif isinstance(val, Decimal):
            return val.quantize(Decimal(".01"))
        elif isinstance(val, bool):
            return None
        try:
            return Decimal(val).quantize(Decimal(".01"))
        except:
            if ignore_errors:
                return None
            raise TypeError("The value {!r} could not be converted to a Decimal".format(val))
    return wrapper


def try_date(ignore_errors=False):  # type: (bool) -> Callable[[Primitive], Optional[datetime.date]]
    def wrapper(val):  # type: (Primitive) -> Optional[datetime.date]
        if not val:
            return None
        elif isinstance(val, datetime.datetime):
            return val.date()
        elif isinstance(val, datetime.date):
            return val
        elif isinstance(val, (float, int, Decimal)):
            return None
        try:
            return parse(str(val)).date()
        except:
            if ignore_errors:
                return None
            raise TypeError("The value {!r} could not be converted to a datetime.date".format(val))
    return wrapper


def try_datetime(ignore_errors=False):
    # type: (bool) -> Callable[[Primitive], Optional[datetime.date]]
    def wrapper(val):  # type: (Primitive) -> Optional[datetime.date]
        if not val:
            return None
        elif isinstance(val, datetime.datetime):
            return val
        elif isinstance(val, datetime.date):
            return datetime.datetime.combine(val, datetime.datetime.min.time())
        try:
            return parse(str(val))
        except:
            if ignore_errors:
                return None
            raise TypeError("The value {!r} could not be converted to a datetime.datetime".format(val))
    return wrapper


def try_float(ignore_errors=False):  # type: (bool) -> Callable[[Primitive], Optional[float]]
    def wrapper(val):  # type: (Primitive) -> Optional[float]
        if val is None:
            return None
        try:
            return float(val)
        except:
            if ignore_errors:
                return None
            raise TypeError("The value {!r} could not be converted to a float".format(val))
    return wrapper


def try_int(ignore_errors=False):  # type: (bool) -> Callable[[Primitive], Optional[int]]
    def wrapper(val):  # type: (Primitive) -> Optional[int]
        if val is None:
            return None
        try:
            return int(val)
        except:
            try:
                return int(float(val))
            except:
                if ignore_errors:
                    return None
                raise TypeError("The value {!r} could not be converted to a int".format(val))
    return wrapper


def try_str(ignore_errors=False):  # type: (bool) -> Callable[[Primitive], Optional[str]]
    def wrapper(val):  # type: (Primitive) -> Optional[str]
        if val is None:
            return None
        return str(val)
    return wrapper


def upcast(left, right):  # type: (Primitive, Primitive) -> Tuple[Primitive, Primitive]
    """Coalesce the types of two values so that they can be compared"""
    valid_upcasts = {
        bool: [bool, int, str, Decimal, float],
        datetime.date: [datetime.date, datetime.datetime, str],
        datetime.datetime: [datetime.datetime, datetime.date, str],
        float: [float, Decimal, int, str, bool],
        int: [int, Decimal, float, bool],
        Decimal: [Decimal, float, int, bool],
        str: [str, bool, datetime.date, datetime.datetime, float, Decimal]
    }

    casts = {
        bool: try_bool(ignore_errors=False),
        datetime.date: try_date(ignore_errors=False),
        datetime.datetime: try_datetime(ignore_errors=False),
        float: try_float(ignore_errors=False),
        int: try_int(ignore_errors=False),
        Decimal: try_currency(ignore_errors=False),
        str: try_str(ignore_errors=False)
    }

    left_upcasts = valid_upcasts[type(left)]
    upcast_type = next(
        rtype for rtype in valid_upcasts[type(right)]
        if rtype in left_upcasts
    )

    if not isinstance(left, upcast_type):
        left = casts[upcast_type](left)
    if not isinstance(right, upcast_type):
        right = casts[upcast_type](right)
    return left, right
