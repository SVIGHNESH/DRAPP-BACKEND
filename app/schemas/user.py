from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str


class FamilyMemberCreate(BaseModel):
    name: str
    age: int | None = None
    relation: str | None = None
    medical_notes: str | None = None


class FamilyMemberUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    relation: str | None = None
    medical_notes: str | None = None


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class FamilyMemberOut(BaseModel):
    member_id: int
    user_id: int
    name: str
    age: int | None
    relation: str | None
    medical_notes: str | None

    model_config = {"from_attributes": True}
