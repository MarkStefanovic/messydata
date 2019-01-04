=========
messydata
=========

messydata is a package that allows you to manipulate ordinary
Python data structures as if they were tables in a database in a
structured, fluent manner.  It is similar to Pandas except that the
performance is likely to be terrible for large datasets.

The project has been tested with Python 2.7 and 3.7.


Examples
=============

.. code-block:: python

    class Sales(Table):
        id = IntField("ID")
        customer_id = IntField("Customer ID")
        item_id = IntField("Item ID")
        sales_date = DateField("Sales Date")
        amount = CurrencyField("Amount")
        payment_due = DateField("Payment Due")

        @staticmethod
        def rows(**kwargs):
            return [
                Sales(1, 4, 1, datetime.datetime(2010, 1, 1), 100,
                      datetime.date(2010, 1, 11)),
                Sales(2, 5, 2, datetime.datetime(2010, 1, 2), 200,
                      datetime.date(2010, 1, 12)),
                Sales(3, 4, None, datetime.datetime(2010, 1, 3), 300,
                      datetime.date(2010, 1, 13)),
                Sales(4, 6, 2, datetime.datetime(2010, 1, 3), 300, None),
                Sales(4, None, 1, datetime.datetime(2010, 1, 3), 300, None)
            ]


    class Customer(Table):
        id = IntField("id")
        first_name = StringField("First Name")
        last_name = StringField("Last Name")

        @staticmethod
        def rows(**kwargs):
            rows = [
                [4, "Mark", "Stefanovic"],
                [6, "Mike", "Smith"],
                [7, "Sally", "Jones"],
                [8, "Mr. X", None],
            ]

            if "id" in kwargs:
                yield next(Customer(*row) for row in rows if row[0] == kwargs["id"])
            else:
                for row in rows:
                    yield Customer(*row)


    class Inventory(Table):
        id = IntField("id")
        name = StringField("Item Name")
        cost = CurrencyField("Cost")

        @staticmethod
        def rows(**kwargs):
            return (
                Inventory(id=1, name="Cup", cost=4.72),
                Inventory(id=2, name="Shovel", cost=12.92),
                Inventory(id=3, name=u"Cupcake", cost=0.99)
            )

    tax_rate = 0.1
    actual = Sales.join(
        right =Customer,
        how="left",
        left_on=Sales.customer_id,
        right_on=Customer.id
    ).join(
        right=Inventory,
        how="left",
        left_on=Sales.item_id,
        right_on=Inventory.id
    ).where(
        Sales.amount >= 100
    ).assign(
        "Total Sale",
        Sales.amount * (1 + tax_rate)
    )all()
