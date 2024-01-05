from fastapi import APIRouter, Depends
from fastapi_users import FastAPIUsers
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.requests import Request

from auth.auth import auth_backend
from auth.database import User
from auth.manager import get_user_manager

fastapi_users = FastAPIUsers(
    get_user_manager,
    [auth_backend],
)
router = APIRouter()
templates = Jinja2Templates(directory="templates")
router.mount("/static", StaticFiles(directory="static"), name="static")

@router.get("/profile", response_class=HTMLResponse)
async def get_profile_page(request: Request, user: User = Depends(fastapi_users.current_user(active=True))):
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": user}
    )

@router.get("/logout", response_class=RedirectResponse)
async def logout(request: Request):
    response = RedirectResponse(url="/login")
    response.delete_cookie("bonds")
    return response

