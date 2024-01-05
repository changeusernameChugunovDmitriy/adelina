import uuid
from typing import Optional

from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    id: int
    email: str
    username: str
    number: Optional[int]
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    class Config:
        orm_mode = True

class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None
    number: Optional[int] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None



class UserCreate(schemas.BaseUserCreate):
    username: str
    number: Optional[int]
    email: str
    password: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False

