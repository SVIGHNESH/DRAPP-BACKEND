from datetime import datetime
from pydantic import BaseModel, model_validator


class BookingCreate(BaseModel):
    service_id: int
    member_id: int | None = None
    slot_start: datetime
    slot_end: datetime
    address_id: int | None = None
    custom_address: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_address(self):
        has_saved = self.address_id is not None
        has_custom = self.custom_address is not None and self.custom_address.strip() != ""
        if has_saved == has_custom:
            raise ValueError("Provide exactly one of address_id or custom_address")
        return self


class BookingNoteCreate(BaseModel):
    message: str


class AssignedNurseIn(BaseModel):
    nurse_name: str
    nurse_contact: str | None = None


class BookingStatusUpdate(BaseModel):
    status: str


class AssignedNurseOut(BaseModel):
    assignment_id: int
    nurse_name: str
    nurse_contact: str | None
    assigned_at: datetime

    model_config = {"from_attributes": True}


class BookingNoteOut(BaseModel):
    note_id: int
    author: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingOut(BaseModel):
    booking_id: int
    user_id: int
    member_id: int | None
    service_id: int
    address_id: int | None
    custom_address: str | None
    slot_start: datetime
    slot_end: datetime
    status: str
    created_at: datetime
    notes: list[BookingNoteOut] = []
    assigned_nurse: AssignedNurseOut | None = None

    model_config = {"from_attributes": True}
