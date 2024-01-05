from datetime import datetime
from typing import AsyncGenerator
from urllib.request import Request

from fastapi import Depends, FastAPI
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from pydantic import BaseModel
from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP, ForeignKey, \
    BIGINT, LargeBinary, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker, Mapped, Session, relationship
from werkzeug.security import check_password_hash

from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
app = FastAPI()
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
Base: DeclarativeMeta = declarative_base()
# Your other setup code...

# Add the database session to the app's state during startup


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    number = Column(BIGINT, nullable=False, unique=True)
    username = Column(String, nullable=False, unique=True)
    registered_time = Column(TIMESTAMP, default=datetime.utcnow)
    hashed_password = Column(String(length=1024), nullable=False)  # Only one hashed_password field is needed
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)


engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def db_session_middleware(request: Request, call_next):
    async with async_session_maker() as session:
        request.state.db = session
        try:
            response = await call_next(request)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
    return response



async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
Base = declarative_base()

class ProductType(Base):
    __tablename__ = 'product_types'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    products = relationship('Product', back_populates='type')
class ProductVariety(Base):
    __tablename__ = 'product_varieties'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    products = relationship('Product', back_populates='variety')
class Product(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type_id = Column(Integer, ForeignKey('product_types.id'), nullable=False)
    variety_id = Column(Integer, ForeignKey('product_varieties.id'), nullable=False)
    manufacturer = Column(String, nullable=False)
    characteristics = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    availability = Column(Integer, nullable=False)
    photo = Column(String, default='/static/alabuga.jpg', nullable=True)

    type = relationship('ProductType', back_populates='products')
    variety = relationship('ProductVariety', back_populates='products')

class Notification(Base):
    __tablename__ = 'notification'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    status = Column(Boolean)

class NotificationRequest(BaseModel):
    product_id: int


