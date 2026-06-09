from pydantic import BaseModel


class UserInfo(BaseModel):
    email: str
    name: str
    picture: str | None = None
    is_admin: bool = False


class TokenData(BaseModel):
    sub: str      # email
    name: str
    picture: str | None = None
    is_admin: bool = False


class AdminLoginRequest(BaseModel):
    email: str
    password: str
