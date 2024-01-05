import asyncio
from sqlalchemy import select, update, delete, insert
from starlette.staticfiles import StaticFiles

from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.templating import Jinja2Templates
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


@router.post("/checkout/{user_id}", response_class=HTMLResponse)
async def checkout(
    request: Request,
    user_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(fastapi_users.current_user(active=True)),
):
    try:
        stmt = (
            select(basket_table, products_table, product_types.c.name.label('type_name'))
            .join(products_table, basket_table.c.product_id == products_table.c.id)
            .join(product_types, products_table.c.type_id == product_types.c.id)
            .where(basket_table.c.user_id == user_id)
        )
        result = await db.execute(stmt)
        basket_items = result.fetchall()

        order_status_in_progress = "В сборке"
        order_status_in_transit = "В пути"
        order_items = []

        async with db.begin_nested():
            for basket_item in basket_items:
                order_id = await db.execute(
                    order.insert().values(
                        user_id=user_id,
                        product_id=basket_item.product_id,
                        status=order_status_in_progress,
                        order_int=basket_item.basket_int
                    )
                )
                order_id = order_id.scalar()

                order_items.append({
                    "product_name": basket_item.name,
                    "type_name": basket_item.type_name,
                    "quantity": basket_item.basket_int,
                })

            await db.execute(
                basket_table.delete()
                .where(basket_table.c.user_id == user_id)
                .where(basket_table.c.product_id.in_([item.product_id for item in basket_items]))
            )


            await db.commit()
        return templates.TemplateResponse("very.html", {"request": request, "user": user, "order_items": order_items,
                                                        "message": "Order placed successfully"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/checkout/{user_id}", response_class=HTMLResponse)
async def show_order_items(
        request: Request,
        user_id: int = Path(...),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(fastapi_users.current_user(active=True))
):
    try:
        stmt = (
            select(order, products_table, product_types.c.name.label('type_name'))
            .join(products_table, order.c.product_id == products_table.c.id)
            .join(product_types, products_table.c.type_id == product_types.c.id)
            .where(order.c.user_id == user_id)
        )
        result = await db.execute(stmt)
        order_items = result.fetchall()

        print("Order Items:", order_items)

        orders_info = {}
        for order_item in order_items:
            order_item_info = {
                "id": order_item.id,
                "product_name": order_item.name,
                "type_name": order_item.type_name,
                "quantity": order_item.order_int,
                "status": order_item.status,
                "photo": order_item.photo,
                "price": order_item.price,
                "order_int": order_item.order_int,
                "manufacturer": order_item.manufacturer,
                "availability": order_item.availability,
            }

            if order_item.id not in orders_info:
                orders_info[order_item.id] = {
                    "items": []
                }

            orders_info[order_item.id]["items"].append(order_item_info)
        print('orders_info', orders_info)
        return templates.TemplateResponse("checkout.html",
                                          {"request": request, "user": user, "order_items": orders_info,
                                           "message": "Order items retrieved successfully"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
