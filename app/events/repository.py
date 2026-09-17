from sqlalchemy.orm import Session
from app.events.models import StockEvent

class StockEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, stock_event: StockEvent) -> StockEvent:
        self._session.add(stock_event)
        return stock_event