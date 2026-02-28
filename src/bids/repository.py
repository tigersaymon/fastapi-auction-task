from src.bids.models import Bid
from src.core.interfaces import SQLAlchemyRepository


class BidRepository(SQLAlchemyRepository[Bid]):
    model = Bid
