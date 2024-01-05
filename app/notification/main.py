import asyncio
from sqlalchemy import select, update, delete, insert
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from starlette.templating import Jinja2Templates
from fastapi import FastAPI, Form, UploadFile, File, Path, APIRouter
from fastapi import Depends, HTTPException, status
from fastapi_users import FastAPIUsers
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from auth.auth import auth_backend
from auth.database import User, Product, NotificationRequest, Notification
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


@router.post("/change_status/{order_id}/{new_status}", response_class=HTMLResponse)
async def change_status(
    request: Request,
    order_id: int = Path(...),
    new_status: str = Path(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(fastapi_users.current_user(active=True)),
):
    try:
        if not user.is_superuser:
            raise HTTPException(status_code=403, detail="Нет прав")

        await db.execute(
            order.update()
            .values(status=new_status)
            .where(order.c.id == order_id)
        )

        await db.commit()

        return RedirectResponse(url=f"/checkout/{user.id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")



from fastapi import Query

@router.get("/search", response_class=HTMLResponse)
async def search_products(request: Request, db: AsyncSession = Depends(get_db),
                          user: User = Depends(fastapi_users.current_user(active=True)),
                          query: str = Query(..., min_length=1)):
    try:
        search_query = f"%{query}%"
        search_results = await db.execute(
            select(Product)
            .filter(Product.name.ilike(search_query))
            .options(selectinload(Product.type), selectinload(Product.variety))
        )
        products = search_results.scalars().all()

        return templates.TemplateResponse("index.html", {"request": request, "posts": products, "user": user})
    except Exception as e:
        print(f"Error: {e}")

@router.post("/notify", response_model=dict)
async def notify_user(request: NotificationRequest, db: AsyncSession = Depends(get_db),
                      user: User = Depends(fastapi_users.current_user(active=True))):
    try:
        await db.execute(notification.insert().values(user_id=user.id, product_id=request.product_id, status=False))
        await db.commit()

        return {"message": "Уведомление успешно создано"}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/notification/{user_id}", response_model=dict)
async def check_notifications(request: Request,user_id: int = Path(..., title="User ID"), db: AsyncSession = Depends(get_db),  user: User = Depends(fastapi_users.current_user(active=True))):
    try:
        user_notifications = await db.execute(
            select(Notification.product_id, Product.name, Product.availability)
            .join(Product, Product.id == Notification.product_id)
            .filter(Notification.user_id == user_id, Notification.status == False)
        )
        user_notifications = [(product_id, product_name, availability) for product_id, product_name, availability in user_notifications]

        available_products = [product_name for product_id, product_name, availability in user_notifications if availability > 0]


        return templates.TemplateResponse("notification.html", {"request":request, "available_products":available_products,  "user": user})
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")