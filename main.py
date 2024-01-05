from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from app.reg_log.main import router as reg_log
from app.profile_logout.main import router as profile_logout
from app.product_crud.main import router as product_crud
from app.basket.main import router as basket
from app.checkout.main import router as checkout
from app.notification.main import router as notification


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(reg_log, prefix="", tags=["reg_log"])
app.include_router(profile_logout, prefix="", tags=["profile_logout"])
app.include_router(product_crud, prefix="", tags=["product_crud"])
app.include_router(basket, prefix="", tags=["basket"])
app.include_router(checkout, prefix="", tags=["checkout"])
app.include_router(notification, prefix="", tags=["notification"])
