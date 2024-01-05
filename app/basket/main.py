import asyncio
from sqlalchemy import select, update, delete, insert
from starlette.staticfiles import StaticFiles

from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.templating import Jinja2Templates
from auth.database import Product, ProductType, ProductVariety, Notification, NotificationRequest
from fastapi import FastAPI, Form, UploadFile, File, Path, APIRouter
from fastapi import Depends, HTTPException, status
from fastapi_users import FastAPIUsers
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from auth.auth import auth_backend
from auth.database import User
from auth.manager import get_user_manager

from models.models import user, basket_table, products_table, product_types, order, notification

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

router = APIRouter()


async def get_db():
    async with async_session_maker() as session:
        asyncio.create_task(asyncio.sleep(0))
        yield session



fastapi_users = FastAPIUsers(
    get_user_manager,
    [auth_backend],
)

templates = Jinja2Templates(directory="templates")

router.mount("/static", StaticFiles(directory="static"), name="static")

@router.post("/add_to_basket/{user_id}/{product_id}")
async def add_to_basket_endpoint(user_id: int, product_id: int, db: AsyncSession = Depends(get_db)):
    try:
        user = await db.execute(select(User).filter(User.id == user_id))
        product = await db.execute(select(Product).filter(Product.id == product_id))

        user = user.scalar()
        product = product.scalar()

        if user is None or product is None:
            raise HTTPException(status_code=404, detail="Пользователь или товар не найден")

        if product.availability <= 0:
            raise HTTPException(status_code=400, detail="Товара нет в наличии")

        stmt = (
            update(basket_table)
            .values(basket_int=basket_table.c.basket_int + 1)
            .where(basket_table.c.user_id == user_id)
            .where(basket_table.c.product_id == product_id)
            .returning(*basket_table.columns)
        )

        result = await db.execute(stmt)

        if result.rowcount == 0:
            await db.execute(basket_table.insert().values(user_id=user_id, product_id=product_id, basket_int=1))

        product.availability -= 1

        await db.commit()

        return {"message": "Product added to basket successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/basket/{user_id}", response_class=HTMLResponse)
async def view_basket_endpoint(request: Request, user_id: int = Path(...), db: AsyncSession = Depends(get_db),
                               user: User = Depends(fastapi_users.current_user(active=True))):
    try:
        stmt = (
            select(basket_table, products_table, product_types.c.name.label('type_name'))
            .join(products_table, basket_table.c.product_id == products_table.c.id)
            .join(product_types, products_table.c.type_id == product_types.c.id)
            .where(basket_table.c.user_id == user_id)
        )

        result = await db.execute(stmt)
        basket_items = result.fetchall()
        total_price = 0
        basket_total_price = 0

        basket_items_data = []

        for basket_item in basket_items:
            total_price += basket_item.price

            product_total_price = basket_item.price * basket_item.basket_int
            basket_total_price += product_total_price

            basket_item_data = {
                "name": basket_item.name,
                "type_name": basket_item.type_name,
                "basket_int": basket_item.basket_int,
                "price": basket_item.price,
                "product_total_price": product_total_price,
                "photo": basket_item.photo
            }

            basket_items_data.append(basket_item_data)

        return templates.TemplateResponse("basket.html",
                                          {"request": request, "user": user, "basket_items": basket_items_data,
                                           "total_price": total_price, "basket_total_price": basket_total_price})
    except Exception as e:
        print(f"Error: {e}")