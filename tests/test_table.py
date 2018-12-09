import os
import shutil
import tempfile
from collections import OrderedDict

from decimal import Decimal

import pytest

from messydata.table import concat, dedupe_field_names
from messydata.util import list_wrapper
from test.conftest import *


class MissingRows(Table):
    id = IntField("id")
    name = StringField("name")


def test_aggretation_method():
    assert AggregationMethod.Sum.fn == sum
    assert AggregationMethod.by_name("min").fn == min
    assert "min" == AggregationMethod.Min
    assert "max" == str(AggregationMethod.Max)


def test_all():
    expected = [
        OrderedDict([('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic')]),
        OrderedDict([('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith')]),
        OrderedDict([('id', 7), ('First Name', 'Sally'), ('Last Name', 'Jones')]),
        OrderedDict([('id', 8), ('First Name', 'Mr. X'), ('Last Name', None)])]

    actual = Customer.all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_all_returns_list_of_ordered_dicts():
    actual = Customer.assign(
        display_name="Full Name",
        expression=Customer.first_name + " " + Customer.last_name
    ).all()
    expected = [
        OrderedDict([
            ('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic'),
            ('Full Name', 'Mark Stefanovic')
        ]),
        OrderedDict([
            ('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith'),
            ('Full Name', 'Mike Smith')
        ]),
        OrderedDict([
            ('id', 7), ('First Name', 'Sally'), ('Last Name', 'Jones'),
            ('Full Name', 'Sally Jones')
        ]),
        OrderedDict([
            ('id', 8), ('First Name', 'Mr. X'), ('Last Name', None),
            ('Full Name', 'Mr. X ')]
        )]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_assign_multiple():
    tax_rate = 0.04

    actual = Customer.assign(
        display_name="Last Initial",
        expression=lambda row:
            row[("Customer", "last_name")][0] if row[("Customer", "last_name")] else "",
        data_type=DataType.String
    ).assign(
        display_name="Full Name",
        expression=Customer.first_name + " " + calculated_fields["Last Initial"]
    ).join(
        right=Sales,
        left_on=Customer.id,
        right_on=Sales.customer_id,
        how="inner"
    ).assign(
        display_name="Sales Tax",
        expression=Sales.amount * tax_rate
    ).select(
        calculated_fields["Full Name"],
        Sales.amount,
        calculated_fields["Sales Tax"]
    ).all()

    expected = [
        OrderedDict([
            ('Full Name', 'Mark S'), ('Amount', Decimal('100.00')), ('Sales Tax', Decimal('4.00'))
        ]),
        OrderedDict([
            ('Full Name', 'Mark S'), ('Amount', Decimal('300.00')), ('Sales Tax', Decimal('12.00'))
        ]),
        OrderedDict([
            ('Full Name', 'Mike S'), ('Amount', Decimal('300.00')), ('Sales Tax', Decimal('12.00'))
        ])
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_assign_multiplier():
    tax_rate = 0.04

    actual = Sales.assign(
        display_name="Sales Tax",
        expression=Sales.amount * tax_rate
    ).select(
        Sales.amount,
        calculated_fields["Sales Tax"]
    ).all()

    expected = [
        OrderedDict([('Amount', Decimal('100.00')), ('Sales Tax', Decimal('4.00'))]),
        OrderedDict([('Amount', Decimal('200.00')), ('Sales Tax', Decimal('8.00'))]),
        OrderedDict([('Amount', Decimal('300.00')), ('Sales Tax', Decimal('12.00'))]),
        OrderedDict([('Amount', Decimal('300.00')), ('Sales Tax', Decimal('12.00'))]),
        OrderedDict([('Amount', Decimal('300.00')), ('Sales Tax', Decimal('12.00'))])
    ]

    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_class_must_have_rows_method():
    with pytest.raises(NotImplementedError):
        MissingRows.rows()


def test_concat():
    assert "1, 2, 3" == concat(3, 2, 3, 1)
    assert "" == concat(None)
    assert "" == concat()
    assert "1" == concat(1)
    assert "1, 2, 3" == concat([1, 2, 3])


def test_concat_table():
    expected = [
        OrderedDict([('Item ID', None), ('Customer ID', '4')]),
        OrderedDict([('Item ID', 1), ('Customer ID', '4')]),
        OrderedDict([('Item ID', 2), ('Customer ID', '5, 6')])
    ]
    actual = Sales.pivot([Sales.item_id], [(Sales.customer_id, "concat")]).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_dedupe_field_names():
    expected = ["id", "First Name", "Last Name"]
    actual = dedupe_field_names(Customer.fields)
    assert expected == actual, str(actual)


def test_describe():
    expected = [
        OrderedDict([
            ('field', 'First Name'),
            ('data type', 'str'),
            ('table', 'Customer'),
            ('description', '')
        ]),
        OrderedDict([
            ('field', 'id'),
            ('data type', 'int'),
            ('table', 'Customer'),
            ('description', '')
        ]),
        OrderedDict([
            ('field', 'Last Name'),
            ('data type', 'str'),
            ('table', 'Customer'),
            ('description', '')
        ])
    ]
    actual = Customer.describe()
    assert expected == actual, str(actual)


def test_bomonth():
    expected = [
        OrderedDict([("ID", 1), ("BOMonth", datetime.date(2010, 1, 1))]),
        OrderedDict([("ID", 2), ("BOMonth", datetime.date(2010, 1, 1))]),
        OrderedDict([("ID", 3), ("BOMonth", datetime.date(2010, 1, 1))]),
        OrderedDict([("ID", 4), ("BOMonth", datetime.date(2010, 1, 1))]),
        OrderedDict([("ID", 4), ("BOMonth", datetime.date(2010, 1, 1))])
    ]
    actual = Sales.assign(
        "BOMonth", Sales.sales_date.bomonth(0)
    ).select(Sales.id, "BOMonth").all()
    assert expected == actual, str(actual)


def test_eomonth():
    expected = [
        OrderedDict([("ID", 1), ("EOMonth", datetime.date(2010, 1, 31))]),
        OrderedDict([("ID", 2), ("EOMonth", datetime.date(2010, 1, 31))]),
        OrderedDict([("ID", 3), ("EOMonth", datetime.date(2010, 1, 31))]),
        OrderedDict([("ID", 4), ("EOMonth", datetime.date(2010, 1, 31))]),
        OrderedDict([("ID", 4), ("EOMonth", datetime.date(2010, 1, 31))])
    ]
    actual = Sales.assign(
        "EOMonth", Sales.sales_date.eomonth(0)
    ).select(Sales.id, "EOMonth").all()
    assert expected == actual, str(actual)


def test_read_write_csv():
    folder = tempfile.mkdtemp()
    fp = os.path.join(folder, "tmp.csv")
    try:
        out_fp = Sales.to_csv(fp)
        assert out_fp == fp
        expected = [
            OrderedDict([
                ('ID', 1), ('Customer ID', 4), ('Item ID', 1),
                ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)),
                ('Amount', Decimal('100.00')),
                ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0))
            ]),
            OrderedDict([
                ('ID', 2), ('Customer ID', 5), ('Item ID', 2),
                ('Sales Date', datetime.datetime(2010, 1, 2, 0, 0)),
                ('Amount', Decimal('200.00')),
                ('Payment Due', datetime.datetime(2010, 1, 12, 0, 0))
            ]),
            OrderedDict([
                ('ID', 3), ('Customer ID', 4), ('Item ID', None),
                ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
                ('Amount', Decimal('300.00')),
                ('Payment Due', datetime.datetime(2010, 1, 13, 0, 0))
            ]),
            OrderedDict([
                ('ID', 4), ('Customer ID', 6), ('Item ID', 2),
                ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
                ('Amount', Decimal('300.00')), ('Payment Due', None)
            ]),
            OrderedDict([
                ('ID', 4), ('Customer ID', None), ('Item ID', 1),
                ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
                ('Amount', Decimal('300.00')), ('Payment Due', None)
            ])
        ]
        actual = Sales.from_csv(fp, has_header=True, ignore_errors=True).all()
        assert expected == actual, "\nACTUAL: {}".format(actual)
    finally:
        shutil.rmtree(folder)


def test_inner_join_unenforced():
    # Customer id 5 on the sales table is an orphaned key and should
    # not be included.
    expected = [
        OrderedDict([
            ('ID', 1), ('Customer ID', 4), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)),
            ('Amount', Decimal('100.00')),
            ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0)),
            ('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 3), ('Customer ID', 4), ('Item ID', None),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
            ('Amount', Decimal('300.00')),
            ('Payment Due', datetime.datetime(2010, 1, 13, 0, 0)), ('id', 4),
            ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 4), ('Customer ID', 6), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
            ('Amount', Decimal('300.00')), ('Payment Due', None), ('id', 6),
            ('First Name', 'Mike'), ('Last Name', 'Smith')
        ])
    ]

    actual = Sales.join(
        right=Customer,
        how="inner",
        left_on=Sales.customer_id,
        right_on=Customer.id
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_inner_join_enforced_one_to_one():
    # Customer id 4 has 2 rows on the Sales table.  Only the first should be included.
    expected = [
        OrderedDict([
            ('ID', 1), ('Customer ID', 4), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)),
            ('Amount', Decimal('100.00')),
            ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0)),
            ('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 4), ('Customer ID', 6), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
            ('Amount', Decimal('300.00')), ('Payment Due', None),
            ('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith')
        ])
    ]

    actual = Sales.join(
        right=Customer,
        how="inner",
        left_on=Sales.customer_id,
        right_on=Customer.id,
        relationship=JoinRelationship.OneToOne
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_outer_join():
    actual = Sales.join(
        right=Customer,
        how="outer",
        left_on=Sales.customer_id,
        right_on=Customer.id
    ).all()
    # All sales ids (1, 2, 3, 4) and all customer ids (4, 6, 7, 8) should
    # be included in the output.  Customer id 0 has no matches on the sales
    # table, so the sales data from that row should be default values.
    expected = [
        OrderedDict([
            ('ID', 4), ('Customer ID', None), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None), ('id', None), ('First Name', None), ('Last Name', None)
        ]),
        OrderedDict([
            ('ID', 1), ('Customer ID', 4), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)), ('Amount', Decimal('100.00')),
            ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0)), ('id', 4),
            ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 3), ('Customer ID', 4), ('Item ID', None),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', datetime.datetime(2010, 1, 13, 0, 0)), ('id', 4),
            ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 2), ('Customer ID', 5), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 2, 0, 0)), ('Amount', Decimal('200.00')),
            ('Payment Due', datetime.datetime(2010, 1, 12, 0, 0)), ('id', None),
            ('First Name', None), ('Last Name', None)
        ]),
        OrderedDict([
            ('ID', 4), ('Customer ID', 6), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None), ('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith')
        ]),
        OrderedDict([
            ('ID', None), ('Customer ID', None), ('Item ID', None), ('Sales Date', None),
            ('Amount', None), ('Payment Due', None), ('id', 7), ('First Name', 'Sally'),
            ('Last Name', 'Jones')
        ]),
        OrderedDict([
            ('ID', None), ('Customer ID', None), ('Item ID', None), ('Sales Date', None),
            ('Amount', None), ('Payment Due', None), ('id', 8), ('First Name', 'Mr. X'),
            ('Last Name', None)
        ])
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_left_join():
    actual = Sales.join(
        right=Customer,
        how="left",
        left_on=Sales.customer_id,
        right_on=Customer.id
    ).all()
    # All 5 sales rows should be included.
    expected = [
        OrderedDict([
            ('ID', 4), ('Customer ID', None), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None), ('id', None), ('First Name', None), ('Last Name', None)
        ]),
        OrderedDict([
            ('ID', 1), ('Customer ID', 4), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)), ('Amount', Decimal('100.00')),
            ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0)), ('id', 4),
            ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 3), ('Customer ID', 4), ('Item ID', None),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', datetime.datetime(2010, 1, 13, 0, 0)), ('id', 4),
            ('First Name', 'Mark'), ('Last Name', 'Stefanovic')
        ]),
        OrderedDict([
            ('ID', 2), ('Customer ID', 5), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 2, 0, 0)), ('Amount', Decimal('200.00')),
            ('Payment Due', datetime.datetime(2010, 1, 12, 0, 0)), ('id', None),
            ('First Name', None), ('Last Name', None)
        ]),
        OrderedDict([
            ('ID', 4), ('Customer ID', 6), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None), ('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith')
        ])
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_right_join():
    actual = Sales.join(
        right=Customer,
        how="right",
        left_on=Sales.customer_id,
        right_on=Customer.id
    ).all()
    # There are 2 Sales rows for customer id 4, so both were included.
    # All customer id"s (4, 6, 7, 8) should be included in the output, including
    # the ones with no matches on the Sales table (7, 8).
    expected = [
        OrderedDict([
            ('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic'), ('ID', 1),
            ('Customer ID', 4), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)), ('Amount', Decimal('100.00')),
            ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0))
        ]),
        OrderedDict([
            ('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic'), ('ID', 3),
            ('Customer ID', 4), ('Item ID', None),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', datetime.datetime(2010, 1, 13, 0, 0))
        ]),
        OrderedDict([
            ('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith'), ('ID', 4),
            ('Customer ID', 6), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None)
        ]),
        OrderedDict([
            ('id', 7), ('First Name', 'Sally'), ('Last Name', 'Jones'), ('ID', None),
            ('Customer ID', None), ('Item ID', None), ('Sales Date', None), ('Amount', None),
            ('Payment Due', None)
        ]),
        OrderedDict([
            ('id', 8), ('First Name', 'Mr. X'), ('Last Name', None), ('ID', None),
            ('Customer ID', None), ('Item ID', None), ('Sales Date', None), ('Amount', None),
            ('Payment Due', None)
        ])
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_three_way_join():
    expected = [
        OrderedDict([
            ('ID', 4), ('Customer ID', None), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None), ('id', None), ('First Name', None), ('Last Name', None),
            ('Inventory: id', 1), ('Item Name', 'Cup'), ('Cost', Decimal('4.72'))
        ]),
        OrderedDict([
            ('ID', 1), ('Customer ID', 4), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 1, 0, 0)), ('Amount', Decimal('100.00')),
            ('Payment Due', datetime.datetime(2010, 1, 11, 0, 0)), ('id', 4),
            ('First Name', 'Mark'), ('Last Name', 'Stefanovic'), ('Inventory: id', 1),
            ('Item Name', 'Cup'), ('Cost', Decimal('4.72'))
        ]),
        OrderedDict([
            ('ID', 2), ('Customer ID', 5), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 2, 0, 0)), ('Amount', Decimal('200.00')),
            ('Payment Due', datetime.datetime(2010, 1, 12, 0, 0)), ('id', None),
            ('First Name', None), ('Last Name', None), ('Inventory: id', 2),
            ('Item Name', 'Shovel'), ('Cost', Decimal('12.92'))
        ]),
        OrderedDict([
            ('ID', 4), ('Customer ID', 6), ('Item ID', 2),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)), ('Amount', Decimal('300.00')),
            ('Payment Due', None), ('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith'),
            ('Inventory: id', 2), ('Item Name', 'Shovel'), ('Cost', Decimal('12.92'))
        ])
    ]
    actual = Sales.join(
        right =Customer,
        how="left",
        left_on=Sales.customer_id,
        right_on=Customer.id
    ).join(
        right=Inventory,
        how="inner",
        left_on=Sales.item_id,
        right_on=Inventory.id
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_pivot():
    actual = Sales.join(
        right=Customer,
        left_on=Sales.customer_id,
        right_on=Customer.id,
        how="left"
    ).pivot(
        [Sales.customer_id],
        [(Sales.amount, "sum")]
    ).all()
    expected = [
        OrderedDict([('Customer ID', None), ('Amount', Decimal('300.00'))]),
        OrderedDict([('Customer ID', 4), ('Amount', Decimal('400.00'))]),
        OrderedDict([('Customer ID', 5), ('Amount', Decimal('200.00'))]),
        OrderedDict([('Customer ID', 6), ('Amount', Decimal('300.00'))])
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_join_then_pivot():
    actual = Sales.join(
        right=Customer,
        left_on=Sales.customer_id,
        right_on=Customer.id,
        how="left"
    ).pivot(
        [Customer.first_name, Customer.last_name],
        [(Sales.amount, "sum")]
    ).sort(
        (Customer.first_name, "desc")
    ).select(
        Customer.first_name, Customer.last_name, Sales.amount  # rearrange column order
    ).all()
    expected = [
        OrderedDict([('First Name', 'Mike'), ('Last Name', 'Smith'), ('Amount', Decimal('300.00'))]),
        OrderedDict([('First Name', 'Mark'), ('Last Name', 'Stefanovic'), ('Amount', Decimal('400.00'))]),
        OrderedDict([('First Name', None), ('Last Name', None), ('Amount', Decimal('500.00'))])
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_rows_args():
    expected = [OrderedDict([('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic')])]
    actual = Customer.all(id=4)
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_sort_rows():
    expected = [
        (3, Decimal('300.00')),
        (4, Decimal('300.00')),
        (4, Decimal('300.00')),
        (2, Decimal('200.00')),
        (1, Decimal('100.00'))
    ]
    actual = [
        (sales["ID"], sales["Amount"])
        for sales in Sales.sort((Sales.amount, SortDirection.Descending)).all()
    ]
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_unique():
    expected = [
        OrderedDict([('Customer ID', 4)]),
        OrderedDict([('Customer ID', 5)]),
        OrderedDict([('Customer ID', 6)]),
        OrderedDict([('Customer ID', None)])
    ]
    actual = Sales.select(Sales.customer_id).unique().all()
    assert expected == actual, str(actual)


def test_where_equals():
    expected = [
        OrderedDict([
            ('ID', 3), ('Customer ID', 4), ('Item ID', None),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
            ('Amount', Decimal('300.00')),
            ('Payment Due', datetime.datetime(2010, 1, 13, 0, 0))
        ])
    ]
    actual = Sales.where(Sales.id == 3).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_where_str_starts_or_ends_with():
    expected = [OrderedDict([('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic')])]
    actual = Customer.where(
        Customer.first_name.startswith("Ma") &
        Customer.last_name.endswith("vic")
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_where_is_null():
    expected = [
        OrderedDict([
            ('ID', 4), ('Customer ID', None), ('Item ID', 1),
            ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0)),
            ('Amount', Decimal('300.00')), ('Payment Due', None)
        ])
    ]
    actual = Sales.where(
        Sales.customer_id.is_null()
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)
