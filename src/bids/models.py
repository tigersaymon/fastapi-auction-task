from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    from src.lots.models import Lot


class Bid(Base):
    bidder: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # RELATIONS
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("lots.id", ondelete="CASCADE"),
        index=True,
    )
    lot: Mapped["Lot"] = relationship(back_populates="bids")
