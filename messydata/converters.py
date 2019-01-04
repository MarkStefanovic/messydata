import decimal
import six

from dateutil.parser import parse

from messydata.types_ import *
from messydata.util import list_wrapper


def try_bool(
    ignore_errors=False
):  # type: (bool) -> Callable[[Primitive], Optional[bool]]
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
            raise TypeError(
                "The value {!r} could not be converted to a boolean.".format(val)
            )

    return wrapper


def try_currency(
    ignore_errors=False
):  # type: (bool) -> Callable[[Primitive], Optional[Decimal]]
    def wrapper(val):  # type: (Primitive) -> Optional[Decimal]
        if val is None:
            return None
        elif isinstance(val, Decimal):
            try:
                return val.quantize(Decimal(".01"))
            except decimal.InvalidOperation:  # Decimal("-sNaN")
                return None
        elif isinstance(val, bool):
            return None
        try:
            return Decimal(val).quantize(Decimal(".01"))
        except:
            if ignore_errors:
                return None
            raise TypeError(
                "The value {!r} could not be converted to a Decimal.".format(val)
            )

    return wrapper


def try_date(
    ignore_errors=False
):  # type: (bool) -> Callable[[Primitive], Optional[datetime.date]]
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
            raise TypeError(
                "The value {!r} could not be converted to a date.".format(val)
            )

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
            raise TypeError(
                "The value {!r} could not be converted to a datetime.".format(val)
            )

    return wrapper


def try_float(
    ignore_errors=False
):  # type: (bool) -> Callable[[Primitive], Optional[float]]
    def wrapper(val):  # type: (Primitive) -> Optional[float]
        if val is None:
            return None
        try:
            return float(val)
        except:
            if ignore_errors:
                return None
            raise TypeError(
                "The value {!r} could not be converted to a float.".format(val)
            )

    return wrapper


def try_int(
    ignore_errors=False
):  # type: (bool) -> Callable[[Primitive], Optional[int]]
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
                raise TypeError(
                    "The value {!r} could not be converted to a int.".format(val)
                )

    return wrapper


def try_str(
    ignore_errors=False
):  # type: (bool) -> Callable[[Primitive], Optional[str]]
    def wrapper(val):  # type: (Primitive) -> Optional[str]
        if val is None:
            return None
        try:
            return str(val)
        except UnicodeEncodeError:
            return None

    return wrapper


def upcast_values(left, right):
    # type: (Primitive, Primitive) -> Tuple[Primitive, Primitive]
    """Coalesce the types of two values so that they can be compared"""
    casts = {
        bool: try_bool(ignore_errors=False),
        datetime.date: try_date(ignore_errors=False),
        datetime.datetime: try_datetime(ignore_errors=False),
        float: try_float(ignore_errors=False),
        int: try_int(ignore_errors=False),
        Decimal: try_currency(ignore_errors=False),
        str: try_str(ignore_errors=False),
    }
    upcast_type = coalesce_pair(left=left, right=right)
    if not isinstance(left, upcast_type):
        left = casts[upcast_type](left)
    if not isinstance(right, upcast_type):
        right = casts[upcast_type](right)
    return left, right


def valid_upcasts(v):  # type: (Primitive) -> List[type]
    if isinstance(v, six.string_types):
        return [str, bool, datetime.date, datetime.datetime, float, Decimal]
    return {
        bool: [bool, int, str],
        datetime.date: [datetime.date, datetime.datetime, str],
        datetime.datetime: [datetime.datetime, datetime.date, str],
        float: [float, Decimal, int, str],
        int: [int, Decimal, float, bool],
        Decimal: [Decimal, float, int]
    }[type(v)]


def coalesce_pair(left, right):  # type: (Primitive, Primitive) -> type
    left_upcasts = valid_upcasts(left)
    return next(
        rtype for rtype in valid_upcasts(right)
        if rtype in left_upcasts
    )


def coalesce_types(types):
    types = list_wrapper(types)
    if len(set(types)) == 1:
        return types[0]
    elif len(types) == 2:
        return coalesce_pair(types[0], types[1])
    else:
        unique_types = list(set(types))
        prior_type = unique_types[0]
        current_type = None
        for t in unique_types[1:]:
            current_type = coalesce_pair(left=prior_type, right=t)
            prior_type = current_type
        return current_type
