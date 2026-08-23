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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# Always the same shape/message regardless of whether the email is
# registered — never lets a caller probe which emails have accounts.
# reset_link is only ever populated in dev mode (see
# Settings.password_reset_dev_mode); in production it's always None and the
# link only ever reaches the user via a real, separately-configured mailer.
class ForgotPasswordResponse(BaseModel):
    detail: str = "If that email is registered, a password reset link has been generated."
    reset_link: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=_MAX_PASSWORD_LENGTH)
