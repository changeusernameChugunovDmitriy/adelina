from fastapi_users import FastAPIUsers
from auth.auth import auth_backend
from fastapi_users.exceptions import UserAlreadyExists
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from auth.manager import UserManager
from auth.schemas import UserCreate, UserUpdate
from fastapi import FastAPI, Form, UploadFile, File, Path, APIRouter
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from auth.manager import get_user_manager

fastapi_users = FastAPIUsers(
    get_user_manager,
    [auth_backend],
)

router = APIRouter()
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

templates = Jinja2Templates(directory="templates")


router.mount("/static", StaticFiles(directory="static"), name="static")


@router.get("/register", response_class=HTMLResponse)
async def get_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register_page(
        request: Request,
        name: str = Form(...),
        number: int = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        password2: str = Form(...),
        user_manager: UserManager = Depends(get_user_manager)
):
    if password != password2 or len(password) < 8:
        error = 'Пароли не совпадают или длина пароля менее 8 символов.'
        return templates.TemplateResponse("register.html", {"request": request, "error": error})
    user_create = UserCreate(
        username=name,
        number=number,
        email=email,
        password=password,
    )
    try:
        new_user = await user_manager.create(user_create)
        return RedirectResponse(url='/login', status_code=303)
    except IntegrityError as e:
        if 'users_username_key' in str(e):
            error = 'Такое имя пользователя уже существует.'
        elif 'users_email_key' in str(e):
            error = 'Такой электронный адрес уже зарегистрирован.'
        else:
            error = 'Произошла ошибка при регистрации. Пожалуйста, попробуйте снова.'
        return templates.TemplateResponse("register.html", {"request": request, "error": error})
    except UserAlreadyExists:
        error = 'Пользователь с такой почтой уже существует.'
        return templates.TemplateResponse("register.html", {"request": request, "error": error})

@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})