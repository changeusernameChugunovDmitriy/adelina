from datetime import datetime

from sqlalchemy import MetaData, Table, Column, Integer, String, TIMESTAMP, \
    ForeignKey, JSON, Boolean, BIGINT, LargeBinary, ForeignKeyConstraint

metadata = MetaData()

# Модифицируем таблицу "users"
user = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, nullable=False, unique=True),
    Column("number", BIGINT, nullable=True),
    Column("username", String, nullable=False, unique=True),
    Column("hashed_password", String, nullable=False),
    Column("registered_time", TIMESTAMP, default=datetime.utcnow),
    Column("is_active", Boolean, default=True, nullable=False),
    Column("is_superuser", Boolean, default=False, nullable=False),
    Column("is_verified", Boolean, default=False, nullable=False),
)

basket_table = Table(
    "basket",
    metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("product.id"), primary_key=True),
    Column("basket_int", Integer, nullable=False),
)

order = Table(
    "order",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("product.id"), primary_key=True),
    Column("status", String, nullable=False),
    Column("order_int", Integer, nullable=False)
)


# ... (другие поля пользователя)

# Модифицируем таблицу "product"
products_table = Table(
    "product",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column('type_id', Integer, ForeignKey('product_types.id'), nullable=False),
    Column('variety_id', Integer, ForeignKey('product_varieties.id'), nullable=False),
    Column("manufacturer", String, nullable=False),
    Column("characteristics", String, nullable=False),
    Column("price", Integer, nullable=False),
    Column("availability", Integer, nullable=False),
    Column("photo", String, default='/static/alabuga.jpg', nullable=True),
)
product_types = Table(
    "product_types",
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False, unique=True)

)

product_varieties = Table(
    "product_varieties",
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False, unique=True)

)


notification = Table(
    "notification",
    metadata,
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("product_id", Integer, ForeignKey("product.id"), nullable=False),
    Column('status', Boolean)
)