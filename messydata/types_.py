from collections import OrderedDict

from decimal import Decimal

import datetime
from typing import (
    Any, Callable, Dict, Generator, Iterable, List, NamedTuple, Optional, Sequence,
    Tuple, TypeVar, Union, MutableMapping,
    Iterator
)

FieldName = str
TableName = str
Fields = TypeVar("Fields", bound=MutableMapping[FieldName, "Field"])
# class Fields(OrderedDict, MutableMapping[FieldName, "Field"]): pass
Primitive = Optional[Union[
    bool, datetime.date, datetime.datetime, datetime.timedelta, Decimal,
    float, int, str
]]
Row = Union[OrderedDict, Dict[Union[FieldName, Tuple[TableName, FieldName]], Primitive]]
Rows = Iterator[Row]
# Rows = Union[Generator[Row, None, None], Sequence[Row]]
Tbl = TypeVar("Tbl", bound="Table")
