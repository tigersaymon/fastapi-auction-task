from typing import Annotated

from fastapi import APIRouter, Query, status

from src.bids.schemas import BidCreateSchema, BidResponseSchema
from src.core.dependencies import AuctionServiceDep
from src.lots.schemas import LotCreateSchema, LotResponseSchema, PaginatedResponseSchema

router = APIRouter(prefix="/lots", tags=["lots"])


@router.post(
    "",
    response_model=LotResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new auction lot",
)
async def create_lot(
    data: LotCreateSchema,
    service: AuctionServiceDep,
) -> LotResponseSchema:
    lot = await service.create_lot(data)
    return LotResponseSchema.model_validate(lot)


@router.get(
    "",
    response_model=PaginatedResponseSchema[LotResponseSchema],
    summary="List active (running) lots with pagination",
)
async def list_active_lots(
    service: AuctionServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponseSchema[LotResponseSchema]:
    lots, total = await service.get_active_lots(offset=offset, limit=limit)
    return PaginatedResponseSchema(
        items=[LotResponseSchema.model_validate(lot) for lot in lots],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{lot_id}",
    response_model=LotResponseSchema,
    summary="Get a specific lot by ID",
)
async def get_lot(
    lot_id: int,
    service: AuctionServiceDep,
) -> LotResponseSchema:
    lot = await service.get_lot(lot_id)
    return LotResponseSchema.model_validate(lot)


@router.post(
    "/{lot_id}/bids",
    response_model=BidResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Place a bid on a lot",
)
async def place_bid(
    lot_id: int,
    data: BidCreateSchema,
    service: AuctionServiceDep,
) -> BidResponseSchema:
    bid = await service.place_bid(lot_id, data)
    return BidResponseSchema.model_validate(bid)
