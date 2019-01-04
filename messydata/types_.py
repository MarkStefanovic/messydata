from collections import OrderedDict

from decimal import Decimal

import datetime
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

FieldName = str
TableName = str
# Fields = TypeVar("Fields", bound=MutableMapping[FieldName, "Field"])
# Primitive = TypeVar(
#     "Primitive",
#     bound=Union[
#         bool,
#         datetime.date,
#         datetime.datetime,
#         datetime.timedelta,
#         Decimal,
#         float,
#         int,
#         str,
#     ]
# )
Primitive = Union[
    bool,
    datetime.date,
    datetime.datetime,
    datetime.timedelta,
    Decimal,
    float,
    int,
    str,
    None
]
Row = TypeVar("Row", bound=Dict[Union[FieldName, Tuple[TableName, FieldName]], Primitive])
Rows = Iterator[Row]
Tbl = TypeVar("Tbl", bound="Table")
