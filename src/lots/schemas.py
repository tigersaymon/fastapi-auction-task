from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.bids.schemas import BidResponseSchema
from src.lots.models import LotStatus


class LotCreateSchema(BaseModel):
    title: Annotated[
        str, Field(min_length=1, max_length=255, examples=["Vintage Watch"])
    ]
    description: Annotated[str, Field(default="", max_length=1024)]
    start_price: Annotated[Decimal, Field(gt=0, examples=[100.00])]
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime) -> datetime:
        if v <= datetime.now(tz=UTC):
            raise ValueError("End time need to be in the future")
        return v


class LotResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    start_price: Decimal
    current_price: Decimal
    status: LotStatus
    end_time: datetime
    created_at: datetime
    bids: list[BidResponseSchema] = []


class PaginationParamsSchema(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponseSchema[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool
