from pydantic import BaseModel


class AddressCreate(BaseModel):
    label: str | None = None
    line1: str
    line2: str | None = None
    city: str
    state: str
    pincode: str
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    is_default: bool | None = None


class AddressOut(BaseModel):
    address_id: int
    user_id: int
    label: str | None
    line1: str
    line2: str | None
    city: str
    state: str
    pincode: str
    is_default: bool

    model_config = {"from_attributes": True}
