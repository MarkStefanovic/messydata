from enum import Enum
from weakref import WeakValueDictionary

import six

from messydata.converters import *
from messydata.operators import Operator
from messydata.types_ import *
from messydata.util import unwrap_to_list, eomonth, bomonth

__all__ = (
    "calculated_fields", "CurrencyField", "DateField", "FloatField",
    "IntField", "StringField", "DataType", "Expression"
)


class DataType(Enum):
    Boolean = "bool"
    Currency = "currency"
    Date = "date"
    DateTime = "datetime"
    Float = "float"
    Int = "int"
    String = "str"

    @staticmethod
    def by_name(name):  # type: (str) -> "DataType"
        """Given a string, return a matching DataType if one exists"""
        if isinstance(name, DataType):
            return name
        try:
            return next(dt for dt in DataType if name == name)
        except StopIteration:
            raise ValueError(
                "No data type could be found matching the name {!r}"
                .format(name)
            )

    @property
    def converter(self):  # type: () -> Callable[[bool], Callable[[str], Any]]
        return {
            DataType.Boolean: try_bool,
            DataType.Currency: try_currency,
            DataType.Date: try_date,
            DataType.DateTime: try_datetime,
            DataType.Float: try_float,
            DataType.Int: try_int,
            DataType.String: try_str
        }[self]

    @property
    def default(self):  # type: () -> Primitive
        return {
            DataType.Boolean: False,
            DataType.Currency: Decimal(0),
            DataType.Date: datetime.date.min,
            DataType.DateTime: datetime.datetime.min,
            DataType.Float: 0.0,
            DataType.Int: 0,
            DataType.String: ""
        }[self]

    @property
    def is_numeric(self):  # type: () -> bool
        return {
            DataType.Boolean: False,
            DataType.Currency: True,
            DataType.Date: False,
            DataType.DateTime: False,
            DataType.Float: True,
            DataType.Int: True,
            DataType.String: False
        }[self]

    @property
    def sqlite_converter(self):  # type: () -> Callable[[Primitive], Primitive]
        noop = lambda v: v
        return {
            DataType.Boolean: lambda v: 1 if v else 0,
            DataType.Currency: lambda v: float(v),
            DataType.Date: noop,
            DataType.DateTime: noop,
            DataType.Float: noop,
            DataType.Int: lambda v: int(v) if v else None,
            DataType.String: noop
        }[self]

    @property
    def sqlite_data_type(self):  # type: () -> str
        return {
            DataType.Boolean: "INTEGER",
            DataType.Currency: "NUMERIC",
            DataType.Date: "DATE",
            DataType.DateTime: "TIMESTAMP",
            DataType.Float: "REAL",
            DataType.Int: "INTEGER",
            DataType.String: "TEXT"
        }[self]

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return id(self.value)

    def __repr__(self):
        return "DataType.{}".format(self.name)

    def __str__(self):
        return self.value


class Expression(object):
    __slots__ = ("operator", "operand1", "operand2", "_fields")

    def __init__(
        self,
        operator,      # type: Operator
        operand1,      # type: Union[Field, ExpressionWrapper]
        operand2=None  # type: Optional[Union[Field, ExpressionWrapper]]
    ):
        self.operator = operator
        self.operand1 = operand1
        self.operand2 = operand2

        self._fields = None

    def __call__(self, row):  # type: (Row) -> Primitive
        """Unwrap an expression to a single Primitive value"""

        left, right = self.operand1, self.operand2

        if isinstance(self.operand1, Expression):
            left = self.operand1(row)

        if isinstance(self.operand2, Expression):
            right = self.operand2(row)

        if self.operator.type == "binary":
            return self.operator.fn(
                unwrap_field_value(row, left),
                unwrap_field_value(row, right)
            )
        elif self.operator.type == "unary":
            return self.operator.fn(unwrap_field_value(row, left))
        else:
            raise ValueError("Unrecognized operator {!r}".format(self.operator))

    @property
    def fields(self):  # type: (...) -> List[Field]
        """Return a unique, sorted list of the fields involved in the expression"""
        if self._fields is None:
            flds = []

            if isinstance(self.operand1, Expression):
                flds.append(self.operand1.fields)
            elif isinstance(self.operand1, Field):
                flds.append(self.operand1)

            if isinstance(self.operand2, Expression):
                flds.append(self.operand2.fields)
            elif isinstance(self.operand2, Field):
                flds.append(self.operand2)

            self._fields = sorted(set(unwrap_to_list(flds)))

        return self._fields

    def __repr__(self):
        return "Expression(operator={!r}, operand1={!r}, operand2={!r})".format(
            self.operator, self.operand1, self.operand2
        )

    def __str__(self):
        if self.operator.is_binary:
            return "{}{}{}".format(self.operand1, self.operator, self.operand2)
        else:
            return "{}{}".format(self.operator, self.operand1)


class ExpressionWrapper(object):
    def __add__(self, other):
        return Expression(Operator.Add, self, other)

    def __and__(self, other):
        return Expression(Operator.And, self, other)

    def __ge__(self, other):
        return Expression(Operator.GreaterThanOrEquals, self, other)

    def __gt__(self, other):
        return Expression(Operator.GreaterThan, self, other)

    def __eq__(self, other):
        return Expression(Operator.Equals, self, other)

    def __hash__(self):
        return id(repr(self))

    def __radd__(self, other):
        return Expression(Operator.Add, other, self)

    def __truediv__(self, other):
        return Expression(Operator.Divide, self, other)

    def __rtruediv__(self, other):
        return Expression(Operator.Divide, other, self)

    def __mul__(self, other):
        return Expression(Operator.Multiply, self, other)

    def __or__(self, other):
        return Expression(Operator.Or, self, other)

    def __rmul__(self, other):
        return Expression(Operator.Multiply, other, self)

    def __le__(self, other):
        return Expression(Operator.LessThan, other, self)

    def __lt__(self, other):
        return Expression(Operator.LessThanOrEquals, self, other)

    def __ne__(self, other):
        return Expression(Operator.NotEquals, self, other)

    def __neg__(self):
        return Expression(Operator.Negate, self)


class Field(ExpressionWrapper):
    __slots__ = (
        "data_type", "description", "display_name", "table_name", "name",
        "_creation_order"
    )

    counter = 0

    def __init__(
        self,
        display_name,   # type: FieldName
        data_type,      # type: Union[str, DataType]
        description=""  # type: str
    ):
        """descriptor containing metadata for a field"""

        self.display_name = display_name
        self.data_type = DataType.by_name(data_type)
        self.description = description or ""

        self.name = None
        self.table_name = None

        # Python 2.7 doesn't maintain the order class attributes were added
        # (see PEP520), so we have to do a hack around it to mimic the behavior using
        # a counter.
        self._creation_order = Field.counter
        Field.counter += 1

        super(Field, self).__init__()

    @property
    def full_name(self):  # type: (...) -> str
        return "{}.{}".format(self.table_name, self.name)

    def map(
        self,
        values,       # type: Dict[Primitive, Primitive]
        default=None  # type: Primitive
    ):                # type: (...) -> DeferredRowValue
        def mapper(row):  # type: (Row) -> Primitive
            val = row[(self.table_name, self.name)]
            return values.get(val, default)

        return DeferredRowValue(
            expression=mapper,
            data_type=self.data_type,
            description="{}.map(values={})".format(self.full_name, values)
        )

    def is_null(self, or_blank=False):  # type: (bool) -> DeferredRowValue
        def expression(row):  # type: (Row) -> bool
            val = row[(self.table_name, self.name)]
            if or_blank:
                return val is None or val == ""
            return val is None

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.Boolean,
            description="{}.is_null(or_blank={})".format(self.name, or_blank)
        )

    def __repr__(self):  # type: () -> str
        return (
            "{cls}(display_name={display_name!r}, data_type={data_type!r}, "
            "description={description!r})"
        ).format(
            cls=self.__class__.__name__,
            display_name=self.display_name,
            data_type=self.data_type,
            description=self.description,
            dataframe=self.table_name
        )

    def __str__(self):  # type: () -> str
        return "[{}]".format(self.display_name)


class DeferredRowValue(ExpressionWrapper):
    """
    The main difference between a DeferredRowValue and a CalculatedField is that
    a DeferredRowValue is not named, and is not persisted.
    """
    __slots__ = ("expression", "data_type", "description")

    def __init__(
        self,
        expression,     # type: Expression
        data_type,      # type: DataType
        description=""  # type: str
    ):
        super(DeferredRowValue, self).__init__()

        self.expression = expression
        self.data_type = data_type
        self.description = description

    def __call__(self, row):  # type: (Row) -> Primitive
        return self.expression(row)

    def __repr__(self):
        return (
            "DeferredRowValue(row_fn=lambda row:..., description={!r})"
            .format(self.description)
        )

    def __str__(self):
        return str(self.expression)


calculated_fields = WeakValueDictionary()  # type: Dict[FieldName, "CalculatedField"]


class CalculatedField(Field):
    """Reusable row expression"""
    def __init__(
        self,
        display_name,      # type: FieldName
        expression,        # type: ExpressionWrapper
        description="",    # type: str
        data_type="infer"  # type: DataType
    ):
        if isinstance(expression, Expression):
            if data_type == "infer":
                if len(set(fld.data_type for fld in expression.fields)) == 1:
                    data_type = expression.fields[0].data_type
                elif all(fld.data_type.is_numeric for fld in expression.fields):
                    data_type = DataType.Float
                else:
                    data_type = DataType.String
        elif isinstance(expression, DeferredRowValue):
            if data_type == "infer":
                data_type = expression.data_type
            expression = expression.expression
        else:
            if data_type == "infer":
                raise ValueError("The data_type of a lambda cannot be inferred.  Please specify.")

        self._expression = expression

        super(CalculatedField, self).__init__(
            display_name=display_name,
            data_type=data_type,
            description=description
        )

        self.name = display_name.replace(" ", "_").lower()
        self.table_name = "Calculation"

        calculated_fields[display_name] = self

    def __call__(self, row):  # type: (Row) -> Primitive
        return self._expression(row)

    def __eq__(self, other):  # type: (Field) -> bool
        if isinstance(other, (CalculatedField, Field)):
            return repr(self) == repr(other)
        raise ValueError("Cannot compare {!r} to a CalculatedField".format(other))

    def __hash__(self):  # type: (...) -> int
        return id(repr(self))


class CurrencyField(Field):
    def __init__(
        self,
        display_name,   # type: str
        description=""  # type: str
    ):
        super(CurrencyField, self).__init__(
            display_name=display_name,
            data_type=DataType.Currency,
            description=description
        )


class DateField(Field):
    def __init__(
        self,
        display_name,    # type: str
        description="",  # type: str
        and_time=True    # type: bool
    ):
        if and_time:
            super(DateField, self).__init__(
                display_name=display_name,
                data_type=DataType.DateTime,
                description=description
            )
        else:
            super(DateField, self).__init__(
                display_name=display_name,
                data_type=DataType.Date,
                description=description
            )

    def bomonth(self, months=0):  # type: (int) -> DeferredRowValue
        def expression(row):  # type: (Row) -> Union[datetime.date, datetime.datetime]
            val = row[(self.table_name, self.name)]
            if val:
                return bomonth(val, months)

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.Date,
            description="{}.eomonth(months={})".format(self.full_name, months)
        )

    def eomonth(self, months=0):  # type: (int) -> DeferredRowValue
        def expression(row):  # type: (Row) -> Union[datetime.date, datetime.datetime]
            val = row[(self.table_name, self.name)]
            if val:
                return eomonth(val, months)

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.Date,
            description="{}.eomonth(months={})".format(self.full_name, months)
        )


class FloatField(Field):
    def __init__(self, display_name, description=""):
        super(FloatField, self).__init__(
            display_name=display_name,
            data_type=DataType.Float,
            description=description
        )


class IntField(Field):
    def __init__(self, display_name, description=""):
        super(IntField, self).__init__(
            display_name=display_name,
            data_type=DataType.Int,
            description=description
        )


class StringField(Field):
    def __init__(
        self,
        display_name,         # type: str
        description=""        # type: str
    ):
        super(StringField, self).__init__(
            display_name=display_name,
            data_type=DataType.String,
            description=description
        )

    def contains(
        self,
        fragment,          # type: str
        ignore_case=False  # type: bool
    ):                     # type: (...) -> DeferredRowValue
        fragment = str(fragment or "")

        def expression(row):  # type: (Row) -> bool
            val = row[(self.table_name, self.name)] or ""
            if val:
                if ignore_case:
                    return fragment.lower() in str(val).lower()
                return fragment in str(val)
            return False

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.Boolean,
            description=(
                "{}.contains(fragment={!r}, ignore_case={})"
                .format(self.full_name, fragment, ignore_case)
            )
        )

    def endswith(
        self,
        suffix,            # type: str
        ignore_case=False  # type: bool
    ):                     # type: (...) -> DeferredRowValue

        def expression(row):  # type: (Row) -> bool
            val = row[(self.table_name, self.name)] or ""
            if ignore_case:
                return val.lower().endswith(suffix)
            return val.endswith(suffix)

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.String,
            description=(
                "{}.endswith(suffix={!r}, ignore_case={})"
                .format(self.full_name, suffix, ignore_case)
            )
        )

    def matches_regex(self, regex):  # type: (str) -> DeferredRowValue
        pass

    def replace(
        self,
        fragment,      # type: str
        replacement    # type: str
    ):                 # type: (...) -> DeferredRowValue

        def expression(row):  # type: (Row) -> Primitive
            val = row[(self.table_name, self.name)] or ""
            return str(val).replace(fragment, replacement)

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.String,
            description=(
                "{}.replace(fragment={!r}, replacement={!r})"
                .format(self.full_name, fragment, replacement)
            )
        )

    def startswith(
        self,
        prefix,             # type: str
        ignore_case=False   # type: bool
    ):                      # type: (...) -> DeferredRowValue

        def expression(row):  # type: (Row) -> bool
            val = row[(self.table_name, self.name)] or ""
            if ignore_case:
                return val.lower().startswith(prefix)
            return val.startswith(prefix)

        return DeferredRowValue(
            expression=expression,
            data_type=DataType.String,
            description=(
                "{}.startswith(prefix={!r}, ignore_case={})"
                .format(self.full_name, prefix, ignore_case)
            )
        )


def unwrap_field_value(row, field):  # type: (Row, ExpressionWrapper) -> Optional[Primitive]
    """Get value corresponding to field out of a row"""
    if field is None:
        return
    elif isinstance(field, (bool, datetime.date, datetime.datetime, float, Decimal, float, int, str)):
        return field
    elif isinstance(field, Field):
        return row[(field.table_name, field.name)]
    elif isinstance(field, DeferredRowValue):
        return field.expression(row)
    else:
        raise ValueError("Unrecognized expression value: {}".format(field))
