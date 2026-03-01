class DomainError(Exception):
    def __init__(self, detail: str, code: str) -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


class LotNotFoundError(DomainError):
    def __init__(self, lot_id: int) -> None:
        super().__init__(
            detail=f"Lot {lot_id} not found",
            code="LOT_NOT_FOUND",
        )


class LotEndedError(DomainError):
    def __init__(self, lot_id: int) -> None:
        super().__init__(
            detail=f"Lot {lot_id} has already ended",
            code="LOT_ENDED",
        )


class BidTooLowError(DomainError):
    def __init__(self, lot_id: int, current_price: float, bid_amount: float) -> None:
        super().__init__(
            detail=(
                f"Bid {bid_amount} must be higher than current price {current_price} "
                f"for lot {lot_id}"
            ),
            code="BID_TOO_LOW",
        )


class ConcurrentUpdateError(DomainError):
    def __init__(self, lot_id: int) -> None:
        super().__init__(
            detail=f"Lot {lot_id} was modified concurrently, please retry",
            code="CONCURRENT_UPDATE",
        )
