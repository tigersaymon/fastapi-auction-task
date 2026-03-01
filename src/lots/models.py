from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.bids.models import Bid


class LotStatus(StrEnum):
    RUNNING = "running"
    ENDED = "ended"


class Lot(Base):
    # to avoid race condition
    version: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {"version_id_col": version}  # noqa

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1024))
    start_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, name="lot_status"),
        default=LotStatus.RUNNING,
    )

    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # RELATIONS
    bids: Mapped[list["Bid"]] = relationship(
        back_populates="lot",
        order_by="Bid.created_at.desc()",
    )

    @property
    def is_expired(self) -> bool:
        return datetime.now(tz=UTC) >= self.end_time
