from __future__ import division

from enum import Enum
from operator import and_, eq, ge, gt, le, lt, ne, or_

import six

from messydata.converters import upcast
from messydata.types_ import *


def is_numeric(val):
    if isinstance(val, (float, int, Decimal)):
        return True
    return False


class Operator(Enum):
    Add = " + "
    And = " and "
    Divide = " / "
    Equals = " == "
    GreaterThan = " > "
    GreaterThanOrEquals = " >= "
    LessThan = " < "
    LessThanOrEquals = " <= "
    Multiply = " * "
    Negate = " -"  # unary operator
    NotEquals = " != "
    Or = " or "
    Subtract = " - "

    @property
    def comparison_operators(self):
        return {
            Operator.Add: False,
            Operator.And: False,
            Operator.Divide: False,
            Operator.Equals: True,
            Operator.GreaterThan: True,
            Operator.GreaterThanOrEquals: True,
            Operator.LessThan: True,
            Operator.LessThanOrEquals: True,
            Operator.Multiply: False,
            Operator.Negate: False,
            Operator.NotEquals: True,
            Operator.Or: False,
            Operator.Subtract: False
        }[self]

    @property
    def type(self):
        return {
            Operator.Add: "binary",
            Operator.And: "binary",
            Operator.Divide: "binary",
            Operator.Equals: "binary",
            Operator.GreaterThan: "binary",
            Operator.GreaterThanOrEquals: "binary",
            Operator.LessThan: "binary",
            Operator.LessThanOrEquals: "binary",
            Operator.Multiply: "binary",
            Operator.Negate: "unary",
            Operator.NotEquals: "binary",
            Operator.Or: "binary",
            Operator.Subtract: "binary"
        }[self]

    @property
    def fn(self):
        return {
            Operator.Add: add_fields,
            Operator.And: and_,
            Operator.Divide: divide_fields,
            Operator.Equals: fields_are_equal,
            Operator.GreaterThan: field_greater_than,
            Operator.GreaterThanOrEquals: field_greater_than_or_equals,
            Operator.LessThan: field_less_than,
            Operator.LessThanOrEquals: field_less_than_or_equals,
            Operator.Multiply: multiply_fields,
            Operator.Negate: negate_field,
            Operator.NotEquals: fields_are_not_equal,
            Operator.Or: or_,
            Operator.Subtract: subtract_fields
        }[self]

    @property
    def is_binary(self):
        return self.type == "binary"

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return id(self.value)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Operator.{}".format(self.name)

    def __str__(self):
        return self.value


def add_fields(left, right):  # type: (Primitive, Primitive) -> Primitive
    if left and right:
        if isinstance(left, (datetime.date, datetime.datetime)):
            if isinstance(right, (float, int)):
                return left + datetime.timedelta(days=right)
            elif isinstance(right, datetime.timedelta):
                return left + right
            else:
                raise ValueError("Cannot add {!r} to a date".format(right))
        elif isinstance(right, (datetime.date, datetime.datetime)):
            if isinstance(left, (float, int)):
                return right + datetime.timedelta(days=left)
            elif isinstance(left, datetime.timedelta):
                return right + left
            else:
                raise ValueError("Cannot add {!r} to a date".format(left))
        elif isinstance(left, six.string_types):
            return left + str(right)
            # return left + " " + str(right)
        elif isinstance(right, six.string_types):
            return str(left) + right
            # return str(left) + " " + right
        elif isinstance(left, (float, int, Decimal)):
            return left + type(left)(right)
        elif isinstance(right, (float, int, Decimal)):
            return type(right)(left) + right
        else:
            raise ValueError("Cannot add {!r} to {!r}".format(left, right))
    elif left:
        return left
    else:
        return right


def divide_fields(left, right):  # type: (Primitive, Primitive) -> Primitive
    if left and right:
        if is_numeric(left) and is_numeric(right):
            return left/type(left)(right)
        raise ValueError("Cannot divide {!r} from {!r}".format(left, right))
    elif left:
        if is_numeric(left):
            return type(left)(0)
        raise ValueError("{!r} is not a valid value for division".format(left))
    else:
        if is_numeric(right):
            return type(right)(0)
        raise ValueError("{!r} is not a valid value for division".format(right))


def equals(
    left,      # type: Primitive
    right,     # type: Primitive
    or_equals  # type: bool
):             # type: (...) -> bool
    left, right = upcast(left, right)
    if or_equals:
        op = eq
    else:
        op = ne
    if left and right:
        return op(left, right)
    elif left:
        return False
    elif right:
        return False
    else:
        return True


def field_greater_than(left, right):  # type: (Primitive, Primitive) -> bool
    left, right = upcast(left, right)
    return greater_than(left, right, or_equals=False)


def field_greater_than_or_equals(left, right):  # type: (Primitive, Primitive) -> bool
    left, right = upcast(left, right)
    return greater_than(left, right, or_equals=True)


def field_less_than(left, right):  # type: (Primitive, Primitive) -> bool
    left, right = upcast(left, right)
    return less_than(left, right, or_equals=False)


def field_less_than_or_equals(left, right):  # type: (Primitive, Primitive) -> bool
    left, right = upcast(left, right)
    return less_than(left, right, or_equals=True)


def fields_are_equal(left, right):  # type: (Primitive, Primitive) -> bool
    left, right = upcast(left, right)
    return equals(left, right, or_equals=True)


def fields_are_not_equal(left, right):  # type: (Primitive, Primitive) -> bool
    left, right = upcast(left, right)
    return equals(left, right, or_equals=True)


def greater_than(
    left,      # type: Primitive
    right,     # type: Primitive
    or_equals  # type: bool
):             # type: (...) -> bool
    left, right = upcast(left, right)
    if or_equals:
        op = ge
    else:
        op = gt
    if left and right:
        return op(left, right)
    elif left:
        return False
    elif right:
        return False
    else:
        return True


def less_than(
    left,      # type: Primitive
    right,     # type: Primitive
    or_equals  # type: bool
):             # type: (...) -> bool
    left, right = upcast(left, right)
    if or_equals:
        op = le
    else:
        op = lt
    if left and right:
        return op(left, right)
    elif left:
        return False
    elif right:
        return False
    else:
        return True


def multiply_fields(left, right):  # type: (Primitive, Primitive) -> Primitive
    if left:
        if is_numeric(left):
            if isinstance(left, int):
                left = float(left)
        else:
            raise ValueError("Cannot multiply {!r} by {!r}".format(left, right))

    if right:
        if is_numeric(right):
            if isinstance(right, int):
                right = float(right)
        else:
            raise ValueError("Cannot multiply {!r} by {!r}".format(left, right))

    if left and right:
        return left * type(left)(right)
    return 0


def negate_field(val):  # type: (Primitive) -> Primitive
    if is_numeric(val) or val is None:
        if val:
            return val * type(val)(-1)
        return val
    else:
        raise ValueError("{!r} is not a valid value for negation".format(val))


def subtract_fields(left, right):  # type: (Primitive, Primitive) -> Primitive
    if left and right:
        if isinstance(left, (datetime.date, datetime.datetime)):
            if isinstance(right, (float, int)):
                return left - datetime.timedelta(days=right)
            elif isinstance(right, datetime.timedelta):
                return left - right
            else:
                raise ValueError("Cannot subtract {!r} from a date".format(right))
        elif isinstance(right, (datetime.date, datetime.datetime)):
            if isinstance(left, (float, int)):
                return right - datetime.timedelta(days=left)
            elif isinstance(left, datetime.timedelta):
                return right - left
            else:
                raise ValueError("Cannot subtract {!r} from a date".format(left))
        elif isinstance(left, (float, int, Decimal)):
            return left - type(left)(right)
        elif isinstance(right, (float, int, Decimal)):
            return type(right)(left) - right
        else:  # strings
            raise ValueError("Cannot subtract {!r} from {!r}".format(left, right))
    elif left:
            return left
    else:
        if isinstance(right, (bool, Decimal, float, int)):
            return -right
        else:
            raise ValueError("Cannot subtract the value {!r}".format(right))
