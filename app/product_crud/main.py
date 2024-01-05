import asyncio
import os
from typing import Optional

from sqlalchemy import select, update, delete, insert
from starlette.staticfiles import StaticFiles

from config import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from sqlalchemy.orm import Session, DeclarativeMeta, declarative_base, sessionmaker, selectinload, joinedload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlette.templating import Jinja2Templates
from werkzeug.utils import secure_filename

from auth.database import Product, ProductType, ProductVariety, Notification, NotificationRequest
from fastapi import FastAPI, Form, UploadFile, File, Path, APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
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



@router.get("/add_product", response_class=HTMLResponse)
async def get_add_product_page(
        request: Request,
        user: User = Depends(fastapi_users.current_user(active=True)),
        db: AsyncSession = Depends(get_db),
):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Нет прав")
    product_types = await db.execute(select(ProductType))
    product_varieties = await db.execute(select(ProductVariety))
    product_types = product_types.scalars().all()
    product_varieties = product_varieties.scalars().all()

    return templates.TemplateResponse(
        "add_product.html",
        {"request": request, "user": user, "product_types": product_types, "product_varieties": product_varieties},
    )


async def save_photo(file_content, filename):
    save_path = os.path.join("static", secure_filename(filename))

    with open(save_path, "wb") as f:
        await asyncio.to_thread(f.write, file_content)


@router.post("/add_product")
async def add_product_page(
        request: Request,
        name: str = Form(...),
        type_id: int = Form(...),
        variety_id: int = Form(...),
        manufacturer: str = Form(...),
        characteristics: str = Form(...),
        price: int = Form(...),
        availability: int = Form(...),
        photo: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(fastapi_users.current_user(active=True)),
):

    if not photo.content_type.startswith("image"):
        return templates.TemplateResponse("add_product.html", {"request": request, "error": "Only images are allowed"})

    photo_content = await photo.read()

    await save_photo(photo_content, photo.filename)
    new_product = Product(
        name=name,
        type_id=type_id,
        variety_id=variety_id,
        manufacturer=manufacturer,
        characteristics=characteristics,
        price=price,
        availability=availability,
        photo=secure_filename(photo.filename)
    )

    try:
        db.add(new_product)
        await db.commit()
        return RedirectResponse(url='/index', status_code=303)
    except IntegrityError as e:
        return templates.TemplateResponse("add_product.html", {"request": request, "error": str(e)})
    except Exception as e:
        return templates.TemplateResponse("add_product.html", {"request": request, "error": str(e)})


@router.get("/index", response_class=HTMLResponse)
async def get_index_page(request: Request, db: AsyncSession = Depends(get_db),
                         user: User = Depends(fastapi_users.current_user(active=True)),
                         query: Optional[str] = None):
    try:
        if query:
            search_query = f"%{query}%"
            search_results = await db.execute(
                select(Product)
                .filter(Product.name.ilike(search_query))
                .options(selectinload(Product.type), selectinload(Product.variety))
            )
            posts = search_results.scalars().all()
        else:
            query_all = select(Product).options(selectinload(Product.type), selectinload(Product.variety))
            posts = await db.execute(query_all)
            posts = posts.scalars().all()

        return templates.TemplateResponse("index.html", {"request": request, "posts": posts, "user": user, "query": query})
    except Exception as e:
        print(f"Error: {e}")


@router.get("/product_info/{product_id}", response_class=HTMLResponse)
async def get_product_info(request: Request, product_id: int = Path(...), db: AsyncSession = Depends(get_db),
                           user: User = Depends(fastapi_users.current_user(active=True))):
    try:
        product = await db.execute(
            select(Product).options(selectinload(Product.type), selectinload(Product.variety)).filter(
                Product.id == product_id))
        product = product.scalar()

        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        return templates.TemplateResponse("product_info.html", {"request": request, "user": user, "product": product})
    except Exception as e:
        print(f"Error: {e}")


async def delete_product_info(product_id: int = Path(...), db: AsyncSession = Depends(get_db),
                              user: User = Depends(fastapi_users.current_user(active=True))):
    try:
        async with db.begin():
            if not user.is_superuser:
                raise HTTPException(status_code=403, detail="Нет прав")
            product = await db.execute(select(Product).filter(Product.id == product_id))
            product = product.scalar()

            if product is None:
                raise HTTPException(status_code=404, detail="Product not found")

            await db.delete(product)

            await db.execute(basket_table.delete().where(basket_table.c.product_id == product_id))

            await db.execute(order.delete().where(order.c.product_id == product_id))

            await db.execute(notification.delete().where(notification.c.product_id == product_id))

        return {"message": "Product deleted successfully"}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


router.add_api_route(
    path="/delete_product/{product_id}",
    methods=["DELETE"],
    endpoint=delete_product_info,
)


@router.get("/edit_product/{product_id}", response_class=HTMLResponse)
async def get_edit_product_page(
        request: Request,
        product_id: int = Path(...),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(fastapi_users.current_user(active=True))
):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Нет прав")
    product = await db.execute(
        select(Product).options(selectinload(Product.type), selectinload(Product.variety)).filter(
            Product.id == product_id))
    product = product.scalar()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_types = await db.execute(select(ProductType))
    product_varieties = await db.execute(select(ProductVariety))
    product_types = product_types.scalars().all()
    product_varieties = product_varieties.scalars().all()

    return templates.TemplateResponse(
        "edit_product.html",
        {"request": request, "user": user, "product": product, "product_types": product_types,
         "product_varieties": product_varieties},
    )


@router.post("/edit_product/{product_id}")
async def edit_product_page(
        request: Request,
        product_id: int = Path(...),
        name: str = Form(...),
        type_id: int = Form(...),
        variety_id: int = Form(...),
        manufacturer: str = Form(...),
        characteristics: str = Form(...),
        price: int = Form(...),
        availability: int = Form(...),
        photo: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
):
    existing_product = await db.execute(select(Product).filter(Product.id == product_id))
    existing_product = existing_product.scalar()

    if existing_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    existing_product.name = name
    existing_product.type_id = type_id
    existing_product.variety_id = variety_id
    existing_product.manufacturer = manufacturer
    existing_product.characteristics = characteristics
    existing_product.price = price
    existing_product.availability = availability

    if photo.content_type.startswith("image"):
        photo_content = await photo.read()
        await save_photo(photo_content, photo.filename)
        existing_product.photo = secure_filename(photo.filename)

    await db.commit()

    return RedirectResponse(url=f'/product_info/{product_id}', status_code=303)