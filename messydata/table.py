from copy import copy

import contextlib
import csv
import inspect
from abc import abstractmethod
from enum import Enum
from itertools import chain, groupby, islice

import six
import sqlite3
from uuid import uuid4
from warnings import warn
from weakref import WeakValueDictionary

from six import with_metaclass
# noinspection PyUnresolvedReferences
from six.moves import filter

from messydata.field import *
from messydata.field import Field, CalculatedField, ExpressionWrapper
from messydata.types_ import *
from messydata.util import *

__all__ = ("AggregationMethod", "JoinRelationship", "SortDirection", "Table")


def concat(*values):  # type: (Sequence[Primitive]) -> str
    """Concatenate a series of values into a comma-separated list"""
    unique_vals = sorted(set(str(v) for v in unwrap_to_list(values) if v))
    if unique_vals:
        return ", ".join(unique_vals)
    return ""


class AggregationMethod(Enum):
    Concat = "concat"
    First = "first"
    Last = "last"
    Max = "max"
    Min = "min"
    Sum = "sum"

    @property
    def fn(self):
        # type: (...) -> Callable[[Sequence[Primitive]], Primitive]
        """Method to apply the aggregation (e.g. sum)"""
        return {
            AggregationMethod.Concat: concat,
            AggregationMethod.First: lambda rows: next(iter(rows)),
            AggregationMethod.Last: lambda rows: list_wrapper(rows)[-1],
            AggregationMethod.Max: max,
            AggregationMethod.Min: min,
            AggregationMethod.Sum: sum
        }[self]

    @staticmethod
    def by_name(name):  # type: (str) -> "AggregationMethod"
        """Given a string, return a matching AggregationMethod if one exists"""
        if isinstance(name, AggregationMethod):
            return name
        try:
            return next(agg for agg in AggregationMethod if name == agg)
        except StopIteration:
            raise ValueError(
                "No aggregation method could be found matching the name {!r}"
                .format(name)
            )

    def __eq__(self, other):  # type: ("AggregationMethod") -> bool
        return str(self).lower()[:3] == str(other).lower()[:3]

    def __hash__(self):  # type: (...) -> int
        return id(self.value)

    def __str__(self):  # type: (...) -> str
        return self.value


class JoinRelationship(Enum):
    ManyToMany = "many-to-many"
    ManyToOne = "many-to-one"
    OneToMany = "one-to-many"
    OneToOne = "one-to-one"
    Unenforced = "unenforced"

    @staticmethod
    def by_name(relationship):
        if isinstance(relationship, JoinRelationship):
            return relationship
        try:
            return next(rel for rel in JoinRelationship if rel.value == relationship)
        except StopIteration:
            raise ValueError("There is no relationship type named {!r}.".format(relationship))

    def __eq__(self, other):
        if isinstance(other, JoinRelationship):
            return self.value == other.value
        raise NotImplementedError(
            "Could not compare {!r} to a JoinRelationship"
            .format(type(other))
        )

    def __repr__(self):
        return "JoinRelationship.{}".format(self.name)

    def __str__(self):
        return self.value


class SortDirection(Enum):
    Ascending = "asc"
    Descending = "desc"

    @staticmethod
    def by_name(direction):
        if isinstance(direction, SortDirection):
            return direction
        try:
            return next(d for d in SortDirection if d.value == direction)
        except StopIteration:
            raise ValueError("There is no sort direction named {!r}.".format(direction))

    def __eq__(self, other):  # type: (...) -> bool
        return str(self).lower()[:3] == str(other).lower()[:3]

    def __repr__(self):
        return "SortDirection.{}".format(self.name)

    def __str__(self):  # type: (...) -> str
        return self.value


def new_table_name(base_name):  # type: (str) -> str
    """Strip id from the name of a derived table, and add a new id"""
    def strip_id(name):
        last_pos = name.rfind("_id")
        if last_pos == -1:
            return name
        return name[:last_pos]

    uuid = str(uuid4()).replace("-", "")
    return "{}_id{}".format(strip_id(base_name), uuid)


def row_wrapper(table):  # type: (Tbl) -> Callable[[...], Row]
    def wrapper(*args, **kwargs):  # type: (...) -> Row
        row = OrderedDict(zip(table.fields.keys(), args))
        row.update(kwargs)
        return row
    return wrapper


def row_wrapper_typed(table, ignore_errors=False):
    converters = {
        fld_name: fld.data_type.converter(ignore_errors)
        for fld_name, fld in table.fields.items()
    }

    def wrapper(*args, **kwargs):  # type: (...) -> Row
        row = OrderedDict(zip(table.fields.keys(), args))
        row.update(OrderedDict(((table.__name__, k), v) for k, v in kwargs.items()))
        return OrderedDict(
            (fld_name, converters[fld_name](row[fld_name]))
            for fld_name in table.fields.keys()
        )
    return wrapper


# tables = WeakValueDictionary()  # type: Dict[TableName, Tbl]


class Schema(type):
    """Metaclass for all tables"""

    def __new__(mcs, class_name, base_classes, attrs):
        # if class_name in tables:
        #     warn("Code attempted to redefine the class {!r}".format(class_name))
        #     return tables[class_name]

        cls = type.__new__(mcs, class_name, base_classes, attrs)  # type: Tbl
        # tables[class_name] = cls

        if attrs.get("_derived_table"):
            cls._derived_table = True
            cls.fields = attrs["fields"]
        else:
            cls._derived_table = False
            flds = inspect.getmembers(cls, lambda o: isinstance(o, Field))
            sorted_fields = sorted(flds, key=lambda f: f[1]._creation_order)
            cls.fields = OrderedDict()
            for fld_name, fld in sorted_fields:
                fld.name = fld_name
                fld.table_name = class_name
                cls.fields[(class_name, fld_name)] = fld

        cls.row_wrapper = staticmethod(row_wrapper(cls))
        cls.row_wrapper_typed = staticmethod(row_wrapper_typed(cls))

        return cls


class Table(with_metaclass(Schema, object)):
    """Base class for all Tables"""
    fields = {}  # type: Dict[Tuple[TableName, FieldName], Field]

    def __new__(cls, *args, **kwargs):  # type: (...) -> Row
        return cls.row_wrapper_typed(*args, **kwargs)

    @classmethod
    def all(cls, **kwargs):  # type: (...) -> Rows
        return list(cls.display_rows(**kwargs))

    @classmethod
    def assign(
        cls,
        display_name,      # type: str
        expression,        # type: ExpressionWrapper
        description="",    # type: str
        data_type="infer"  # type: DataType
    ):                     # type: (...) -> Tbl
        """Add a calculated field to a table"""
        calc_fld = CalculatedField(
            display_name=display_name,
            expression=expression,
            description=description,
            data_type=data_type
        )

        flds = copy(cls.fields)
        flds[("Calculation", calc_fld.name)] = calc_fld

        def rows(**kwargs):  # type: (...) -> Rows
            for row in cls.rows(**kwargs):
                calculated_value = calc_fld(row)
                converted_value = calc_fld.data_type.converter(ignore_errors=True)(calculated_value)
                row[("Calculation", calc_fld.name)] = converted_value
                yield row

        return new_table(
            base_name=cls.__name__,
            fields=flds,
            rows_method=rows
        )

    @classmethod
    def describe(cls):  # type: () -> List[Dict[str, str]]
        return [
            OrderedDict([
                ("field", fld.display_name),
                ("data type", str(fld.data_type)),
                ("table", fld.table_name),
                ("description", fld.description)
            ])
            for _, fld in sorted(cls.fields.items())
        ]

    @classmethod
    def field_display_names(cls):
        return dedupe_field_names(cls.fields)

    @classmethod
    def display_rows(cls, **kwargs):
        display_names = cls.field_display_names()
        for row in cls.rows(**kwargs):
            yield OrderedDict(zip(display_names, row.values()))

    @classmethod
    def field_by_display_name(cls, display_name):  # type: (str) -> Field
        if display_name in calculated_fields:
            return calculated_fields[display_name]
        raise ValueError("There is no calculated field named {!r}.".format(display_name))

    # @classmethod
    # def field_by_display_name(cls, display_name):  # type: (str) -> Field
    #     matches = []
    #     if display_name in cls.fields:
    #         matches.append(cls.fields[display_name])
    #
    #     if display_name in calculated_fields:
    #         matches.append(calculated_fields[display_name])
    #
    #     if not matches:
    #         raise ValueError(
    #             "There is no field named {!r} on the current table and no calculated field "
    #             "by that name."
    #             .format(display_name)
    #         )
    #     elif len(matches) == 1:
    #         return matches[0]
    #     else:
    #         raise ValueError(
    #             "The name of the field is ambiguous, as it matches the name of "
    #             "a field on the table and a calculated field.  Please specify it using the "
    #             "syntax calculated_fields[field_name] if it is a calculated field, or using "
    #             "normal table field systanx, eg. Sales.id, if it is a table."
    #         )

    @classmethod
    def from_sqlite(cls, db_path, table_name):  # type: (str, str) -> Rows
        sql_fields = cls.sql_fields()
        field_list = ", ".join(sql_fields.keys())
        select_sql = "SELECT {flds} FROM {tbl}".format(
            flds=field_list,
            tbl=table_name
        )

        def rows(**kwargs):  # type: (...) -> Rows
            with contextlib.closing(sqlite3.connect(
                database=db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )) as con:
                cur = con.cursor()
                cur.execute(select_sql)
                for row in cur:
                    yield OrderedDict(zip(cls.fields.keys(), row))

        return new_table(
            base_name=cls.__name__,
            fields=cls.fields,
            rows_method=rows
        )

    @classmethod
    def head(cls, **kwargs):  # type: (...) -> Callable[[int], Rows]
        """Return the first n rows of a table"""
        return lambda n: list(islice(cls.rows(**kwargs), n))

    @classmethod
    def join(
        cls,
        right,                                    # type: Tbl
        left_on,                                  # type: Field
        right_on,                                 # type: Field
        how="inner",                              # type: str
        relationship=JoinRelationship.Unenforced  # type: JoinRelationship
    ):                                            # type: (...) -> Tbl
        """Create a table as a combination of two tables"""

        if how not in ("inner", "left", "outer", "right"):
            raise ValueError("{!r} is an invalid join type".format(how))

        relationship = JoinRelationship.by_name(relationship)

        # We perform a right join by simply replacing left and right and doing a
        # left-join.
        if how == "right":
            left, right = right, cls
            left_on, right_on = right_on, left_on
            how = "left"
        else:
            left = cls

        left_on, right_on = tuple_wrapper(left_on), tuple_wrapper(right_on)

        if len(left_on) != len(right_on):
            raise ValueError(
                "The left side of the join has {} fields to join on but the "
                "right side has {} fields.".format(len(left_on), len(right_on)
                ))

        def rows(**kwargs):  # type: (...) -> Rows
            lrows, rrows = left.rows(**kwargs), right.rows(**kwargs)
            if lrows or rrows:
                left_key = tuple(
                    (fld.table_name, fld.name)
                    for fld in left_on
                )  # type: Tuple[Primitive]
                right_key = tuple(
                    (fld.table_name, fld.name)
                    for fld in right_on
                )  # type: Tuple[Primitive]

                if relationship == JoinRelationship.OneToOne:
                    left_one_row_per_key = True
                    right_one_row_per_key = True
                elif relationship == JoinRelationship.OneToMany:
                    left_one_row_per_key = True
                    right_one_row_per_key = False
                elif relationship == JoinRelationship.ManyToOne:
                    left_one_row_per_key = False
                    right_one_row_per_key = True
                else:
                    left_one_row_per_key = False
                    right_one_row_per_key = False

                left_rows = group_rows_by_keys(
                    rows=lrows,
                    key=left_key,
                    fields=left.fields,
                    one_row_per_key=left_one_row_per_key
                )

                right_rows = group_rows_by_keys(
                    rows=rrows,
                    key=right_key,
                    fields=right.fields,
                    one_row_per_key=right_one_row_per_key
                )

                right_keys_used = set()  # used for outer join
                for left_key_val, row_grp in left_rows.items():
                    for left_row in row_grp:
                        if how in ("left", "outer"):
                            default_row = [create_dummy_row(right)]
                        else:
                            default_row = []
                        for right_row in right_rows.get(left_key_val, default_row):
                            combined_row = left_row
                            combined_row.update(right_row)
                            yield combined_row
                            if how == "outer":
                                right_keys_used.add(left_key_val)

                if how == "outer":
                    unused_right_keys = set(right_rows.keys()) - right_keys_used
                    for right_key_val in unused_right_keys:
                        for right_row in right_rows[right_key_val]:
                            default_row = create_dummy_row(left)
                            combined_row = default_row
                            combined_row.update(right_row)
                            yield combined_row

        fields = OrderedDict(
            ((fld.table_name, fld.name), fld)
            for fld in chain(left.fields.values(), right.fields.values())
        )

        return new_table(
            base_name=left.__name__,
            fields=fields,
            rows_method=rows
        )

    @classmethod
    def pivot(
        cls,
        group_by_fields,  # type: Sequence[Field]
        aggregations      # type: List[Tuple[Field, str]]
    ):                    # type: (...) -> Tbl
        """Group-by and aggregate a table"""

        agg_map = OrderedDict(
            ((fld.table_name, fld.name), AggregationMethod.by_name(agg_name).fn)
            for fld, agg_name in aggregations
        )
        aggregate_fields = [a[0] for a in aggregations]
        group_by_fields = list_wrapper(group_by_fields)
        grp_flds = [(fld.table_name, fld.name) for fld in group_by_fields]
        defaults = {
            (fld.table_name, fld.name): fld.data_type.default
            for fld in aggregate_fields
        }
        fields = OrderedDict([
            ((fld.table_name, fld.name), fld)
            for fld in chain(group_by_fields, aggregate_fields)
        ])  # type: Fields

        def rows(**kwargs):  # type: (...) -> Rows
            return (
                OrderedDict(chain(zip(grp_flds, list_wrapper(grp or [None])), (
                    (fld_name, agg(row[fld_name] or defaults[fld_name] for row in rows))
                    for fld_name, agg in agg_map.items()
                )))
                for grp, rows in groupby(
                    sorted(
                        cls.rows(**kwargs),
                        key=field_value_getter_or_default(
                            field_names=grp_flds,
                            fields=fields
                        )
                    ),
                    key=field_value_getter(field_names=grp_flds)
                )
            )

        return new_table(
            base_name=cls.__name__,
            fields=fields,
            rows_method=rows
        )

    @classmethod
    def from_csv(
        cls,
        file_path,            # type: str
        has_header=True,      # type: bool
        ignore_errors=False   # type: bool
    ):                        # type: (...) -> Table
        """Read a .csv and generate a series of rows to pass through the pipeline"""
        # We should convert values that are entered in from the outside world
        # after that we can assume the values match their specified data type.

        def rows(**kwargs):  # type: (...) -> Rows
            mapper = row_wrapper_typed(table=cls, ignore_errors=ignore_errors)
            with open(file_path, mode="r") as fh:
                reader = csv.reader(fh)
                if has_header:
                    next(reader)  # skip the header
                for row in reader:
                    yield mapper(*row)

        return new_table(
            base_name=cls.__name__,
            fields=cls.fields,
            rows_method=rows
        )

    @staticmethod
    @abstractmethod
    def rows(**kwargs):  # type: (...) -> Rows
        """Abstract method to be overridden by Table subclasses"""
        raise NotImplementedError(
            "Please specify a rows() @staticmethod for the Table."
            "\nFor example:"
            "\n\t@staticmethod"
            "\n\tdef rows(**kwargs):"
            "\n\t    return Sales.read_csv('sales.csv')"
        )

    @classmethod
    def select(cls, *columns):  # type: (Sequence[Union[str, Field]]) -> Tbl
        """Select a subset of columns from a Table"""

        cols = [
            cls.field_by_display_name(col)
            if isinstance(col, six.string_types) else col
            for col in columns
        ]

        def rows(**kwargs):  # type: (...) -> Rows
            fld_names = [(fld.table_name, fld.name) for fld in cols]
            for row in cls.rows(**kwargs):
                yield OrderedDict(
                    (fld_name, row[fld_name])
                    for fld_name in fld_names
                )

        fields = OrderedDict(((fld.table_name, fld.name), fld) for fld in cols)

        return new_table(
            base_name=cls.__name__,
            fields=fields,
            rows_method=rows
        )

    @classmethod
    def sort(cls, *order_by):  # type: (List[Tuple[Field, SortDirection]]) -> Tbl
        """Sort the table based on one or more fields"""

        def rows(**kwargs):  # type: (...) -> Rows
            sorted_rows = cls.rows(**kwargs)
            for fld, direction in reversed(list_wrapper(order_by)):
                direction = SortDirection.by_name(direction)
                if direction == SortDirection.Ascending:
                    reverse = False
                elif direction == SortDirection.Descending:
                    reverse = True
                else:
                    raise ValueError(
                        "Invalid sort direction: {}"
                            .format(direction)
                    )
                sorted_rows = sorted(
                    sorted_rows,
                    key=field_value_getter_or_default(
                        field_names=((fld.table_name, fld.name),),
                        fields=cls.fields
                    ),
                    reverse=reverse
                )
            return sorted_rows

        return new_table(
            base_name=cls.__name__,
            fields=cls.fields,
            rows_method=rows
        )

    @classmethod
    def sql_fields(cls):  # type: () -> Dict[FieldName, Field]
        return OrderedDict(zip((
            field.lower().replace(" ", "_")
            for field in dedupe_field_names(cls.fields)),
            cls.fields.values()
        ))

    @classmethod
    def to_sqlite(
        cls,
        db_path,     # type: str
        table_name,  # type: str
        mode="o",    # type: str
        **kwargs     # type: Dict[str, Any]
    ):               # type: (...) -> None
        """Write rows to a sqlite database

        :param db_path: file path to the sqlite database
        :param table_name: Name of the table in the sqlite database
        :param mode: available modes include 'a' = append, 'o' = overwrite
        :return: None
        """
        sql_flds = cls.sql_fields()
        field_list = ", ".join(
            "{} {}".format(fld_name, fld.data_type.sqlite_data_type)
            for fld_name, fld in sql_flds.items()
        )
        create_sql = "CREATE TABLE IF NOT EXISTS {} ({})".format(table_name, field_list)
        fld_list = ", ".join(sql_flds.keys())
        fld_value_dummies = ", ".join("?" for _ in sql_flds.keys())
        insert_sql = (
            "INSERT INTO {table_name}({field_names}) "
            "VALUES ({field_dummies})".format(
                table_name=table_name,
                field_names=fld_list,
                field_dummies=fld_value_dummies
            )
        )
        converters = {
            col: fld.data_type.sqlite_converter
            for col, fld in enumerate(sql_flds.values())
        }
        converted_rows = (
            [converters[col](cell) for col, cell in enumerate(row.values())]
            for row in cls.rows(**kwargs)
        )
        with contextlib.closing(sqlite3.connect(
            database=db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )) as con:
            with con:
                if mode == "o":
                    con.execute("DROP TABLE IF EXISTS {}".format(table_name))
                con.execute(create_sql)
                con.executemany(insert_sql, converted_rows)

    @classmethod
    def unique(cls):
        def rows(**kwargs):  # type: (Dict[str, Any]) -> Rows
            used_rows = set()
            for row in cls.rows(**kwargs):
                row_vals = tuple(row.values())
                if row_vals not in used_rows:
                    used_rows.add(row_vals)
                    yield row

        return new_table(
            base_name=cls.__name__,
            fields=cls.fields,
            rows_method=rows
        )

    @classmethod
    def where(cls, condition):  # type: (Callable[[Row], bool]) -> Tbl
        """Filter rows by a series of predicates"""

        def rows(**kwargs):  # type: (Dict[str, Any]) -> Rows
            return filter(condition, cls.rows(**kwargs))

        return new_table(
            base_name=cls.__name__,
            fields=cls.fields,
            rows_method=rows
        )

    @classmethod
    def to_csv(cls, file_path, **kwargs):  # type: (str, ...) -> str
        """Write results to a .csv file

        :param file_path: Include the file extension ('.csv') at the end of the path.
        :return: filepath of the csv output
        """
        with open(file_path, "w") as fh:
            writer = csv.DictWriter(
                fh, delimiter=",", quoting=csv.QUOTE_NONE, quotechar='',
                lineterminator='\n', fieldnames=cls.field_display_names()
            )
            writer.writeheader()
            writer.writerows(cls.display_rows(**kwargs))
        return file_path

    def __class_getitem__(cls, field_name):
        return cls.fields[(cls.__name__, field_name)]


def field_value_getter(
    field_names  # type: Tuple[[TableName, FieldName]]
):               # type: (...) -> Callable[[Row], Tuple[Any]]
    field_names = list_wrapper(field_names)

    def get(row):
        fn = lambda fld_name: row[fld_name]
        return tuple(map(fn, field_names))

    return get


def field_value_getter_or_default(
    field_names,  # type: Tuple[[TableName, FieldName]]
    fields        # type: Dict[Tuple[TableName, FieldName], Field]
):                # type: (...) -> Callable[[Row], Tuple[Any]]

    field_names = list_wrapper(field_names)

    def get_or_default(row):
        fn = lambda fld_name: row[fld_name] or fields[fld_name].data_type.default
        return tuple(map(fn, field_names))

    return get_or_default


def group_rows_by_keys(
    rows,            # type: Rows
    key,             # type: Tuple[Primitive]
    fields,          # type: Dict[Tuple[TableName, FieldName], Field]
    one_row_per_key  # type: bool
):                   # type: (...) -> Dict[Tuple[Primitive], Rows]
    if one_row_per_key:
        rows_fn = lambda r: [list(r)[0]]
    else:
        rows_fn = lambda r: list(r)
    return OrderedDict(
        (fk, rows_fn(r))
        for fk, r in groupby(
            sorted(
                rows,
                key=field_value_getter_or_default(
                    field_names=key,
                    fields=fields
                )
            ),
            key=field_value_getter(key)
        )
    )


def new_table(
    base_name,   # type: TableName
    fields,      # type: Dict[[TableName, FieldName], Field]
    rows_method  # type: Callable[[...], Rows]
):               # type: (...) -> Tbl
    """Create a new Table subclass from a bag of fields"""
    new_tbl = type(
        new_table_name(base_name),
        (Table,),
        {"fields": fields, "_derived_table": True}
    )
    new_tbl.rows = staticmethod(rows_method)
    return new_tbl


def dedupe_field_names(
    fields  # type: Dict[Tuple[TableName, FieldName], Field]
):          # type: (...) -> List[str]
    """Create alternate display names for duplicate column names in a join"""

    deduped_fields = []
    for fld in fields.values():
        if fld.display_name in deduped_fields:
            final_name = "{}: {}".format(fld.table_name, fld.display_name)
            warn(
                "WARNING: the field {!r} is present in both tables.  The field "
                "on the {} table has been renamed to {!r} on the output."
                .format(fld.display_name, fld.table_name, final_name)
            )
        else:
            final_name = fld.display_name
        deduped_fields.append(final_name)
    return deduped_fields


def create_dummy_row(table):  # type: (Tbl) -> Row
    """Wrap a row of data for the table inside a namedtuple"""
    return OrderedDict((fld, None) for fld in table.fields.keys())
