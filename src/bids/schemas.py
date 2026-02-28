from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class BidCreateSchema(BaseModel):
    bidder: Annotated[str, Field(min_length=1, max_length=255, examples=["John"])]
    amount: Annotated[Decimal, Field(gt=0, examples=[105.00])]


class BidResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_id: int
    bidder: str
    amount: Decimal
    created_at: datetime
