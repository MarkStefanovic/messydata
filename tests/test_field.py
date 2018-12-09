from messydata.field import Field, CalculatedField
from messydata.operators import *

from tests.conftest import *


def test_add_expression():
    expected = Expression(
        operator=Operator.Add,
        operand1=StringField("First Name"),
        operand2=StringField("Last Name")
    )
    actual = Customer.first_name + Customer.last_name
    assert str(expected) == str(actual), "\nACTUAL: {}".format(actual)


def test_calculated_field_add():
    expected = Field(
        display_name='FullName', data_type=DataType.String,
        description='Full name of the customer'
    )
    actual = CalculatedField(
        display_name="FullName",
        expression=Customer.first_name + Customer.last_name,
        description="Full name of the customer"
    )
    assert str(expected) == str(actual), "\nACTUAL: {}".format(actual)


def test_calculated_field_multiply():
    expected = Field(
        display_name="Total Sale", data_type=DataType.Currency,
        description="Sales + tax"
    )
    actual = CalculatedField(
        display_name="Total Sale",
        expression=Sales.amount * 1.04,
        description="Sales + tax"
    )
    assert str(expected) == str(actual), "\nACTUAL: {}".format(actual)


def test_calculated_field_lookup():
    calc = CalculatedField(display_name="Full Name",
                           expression=Customer.first_name + Customer.last_name)
    assert calc == calculated_fields["Full Name"]


def test_data_type_converter():
    assert Decimal(0.04).quantize(Decimal(".01")) == DataType.Currency.converter()(0.04)


def test_datetime_on_or_after():
    expected = [
        OrderedDict([('ID', 3), ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0))]),
        OrderedDict([('ID', 4), ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0))]),
        OrderedDict([('ID', 4), ('Sales Date', datetime.datetime(2010, 1, 3, 0, 0))])
    ]
    actual = Sales.where(
        Sales.sales_date >= datetime.datetime(2010, 1, 3)
    ).select(
        Sales.id,
        Sales.sales_date
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)


def test_field_eq():
    fld1 = Field(display_name="1", data_type=DataType.String)
    fld2 = Field(display_name="1", data_type=DataType.String)
    assert fld1 == fld2

    assert Customer.first_name == Customer.first_name
    assert Sales.id != Customer.id


def test_field_repr():
    fld = Field(
        display_name="ID",
        data_type=DataType.Int,
        description="Test ID field"
    )
    expected = (
        "Field(display_name='ID', data_type=DataType.Int, description='Test ID field')"
    )
    actual = repr(fld)
    assert expected == actual


def test_map():
    expected = [
        OrderedDict([("First Name", "Mark"), ("New Name", "Steve")]),
        OrderedDict([("First Name", "Mike"), ("New Name", None)]),
        OrderedDict([("First Name", "Sally"), ("New Name", "Jane")]),
        OrderedDict([("First Name", "Mr. X"), ("New Name", None)])
    ]
    actual = Customer.assign(
        "New Name",
        Customer.first_name.map({
            "Mark": "Steve",
            "Sally": "Jane"
        })
    ).select(
        Customer.first_name,
        "New Name"
    ).all()
    assert expected == actual


def test_multiply_expression():
    expected = Expression(
        operator=Operator.Multiply,
        operand1=Sales.amount,
        operand2=0.04
    )
    actual = Sales.amount * 0.04
    assert str(expected) == str(actual), "\nACTUAL: {}".format(actual)


def test_replace():
    expected = [
        OrderedDict([('id', 4), ('First Name', 'Mark'), ('Last Name', 'Stefanovic'), ('Better Name', 'Zark')]),
        OrderedDict([('id', 6), ('First Name', 'Mike'), ('Last Name', 'Smith'), ('Better Name', 'Zike')]),
        OrderedDict([('id', 7), ('First Name', 'Sally'), ('Last Name', 'Jones'), ('Better Name', 'Sally')]),
        OrderedDict([('id', 8), ('First Name', 'Mr. X'), ('Last Name', None), ('Better Name', 'Zr. X')])
    ]
    actual = Customer.assign(
        "Better Name",
        Customer.first_name.replace("M", "Z")
    ).all()
    assert expected == actual, "\nACTUAL: {}".format(actual)

    expected = "Customer.last_name.replace(fragment='S', replacement='Z')"
    actual = Customer.last_name.replace("S", "Z")
    assert expected == actual.description, actual.description


