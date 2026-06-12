from datetime import datetime
from pydantic import BaseModel, EmailStr


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


class FamilyMemberOut(BaseModel):
    member_id: int
    user_id: int
    name: str
    age: int | None
    relation: str | None
    medical_notes: str | None

    model_config = {"from_attributes": True}
