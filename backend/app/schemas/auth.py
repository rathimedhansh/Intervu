from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# bcrypt silently ignores bytes past 72; capping here means what the user
# typed is what actually gets checked, never a truncated prefix of it.
_MAX_PASSWORD_LENGTH = 72


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=_MAX_PASSWORD_LENGTH)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=_MAX_PASSWORD_LENGTH)


# Never includes password_hash — this is the only user shape sent to the
# frontend.
class UserRead(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
