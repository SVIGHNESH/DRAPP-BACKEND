from decimal import Decimal
from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str
    description: str | None = None
    base_price: Decimal
    active: bool = True


class ServiceOut(BaseModel):
    service_id: int
    name: str
    description: str | None
    base_price: Decimal
    active: bool

    model_config = {"from_attributes": True}
