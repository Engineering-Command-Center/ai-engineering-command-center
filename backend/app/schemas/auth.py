from pydantic import BaseModel


class UserInfo(BaseModel):
    email: str
    name: str
    picture: str | None = None


class TokenData(BaseModel):
    sub: str      # email
    name: str
    picture: str | None = None
