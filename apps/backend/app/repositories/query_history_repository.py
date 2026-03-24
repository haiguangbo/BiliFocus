from app.models.query_history import QueryHistory
from sqlalchemy.orm import Session


class QueryHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_entry(
        self,
        *,
        query: str,
        filter_text: str | None,
        source: str,
        result_count: int,
        executed_at: str,
    ) -> QueryHistory:
        entry = QueryHistory(
            query=query,
            filter_text=filter_text,
            source=source,
            result_count=result_count,
            executed_at=executed_at,
        )
        self.db.add(entry)
        return entry
