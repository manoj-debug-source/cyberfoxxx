from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Literal


class UserCreate(BaseModel):
    username: str
    password: str
    role: Literal["admin", "officer"]
    email: EmailStr


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    email: str
    role: str