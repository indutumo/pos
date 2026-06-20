from app.models.schema import StockTake, Product

class StockTakeRepository:
    def __init__(self, db_session):
        self.db_session = db_session

    def _apply_filters(self, query, search_query):
        """Helper to apply search logic to a base query."""
        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            return query.join(Product).filter(Product.name.ilike(term))
        return query

    def get_total_count(self, search_query: str = "") -> int:
        """Counts records for pagination based on filter."""
        query = self.db_session.query(StockTake)
        query = self._apply_filters(query, search_query)
        return query.count()

    def get_paginated(self, search_query: str = "", limit: int = 30, offset: int = 0):
        """Fetches a specific page of records."""
        query = self.db_session.query(StockTake)
        query = self._apply_filters(query, search_query)
        return query.order_by(StockTake.stocktake_date.desc())\
                    .limit(limit)\
                    .offset(offset)\
                    .all()

    def get_all(self, search_query: str = ""):
        """Fetches all records (used for export)."""
        query = self.db_session.query(StockTake)
        query = self._apply_filters(query, search_query)
        return query.order_by(StockTake.stocktake_date.desc()).all()

    def get_active_products(self):
        """Fetches products for the dropdown selection."""
        return self.db_session.query(Product).order_by(Product.name).all()

    def add(self, model_instance):
        """Adds a new record to the session."""
        self.db_session.add(model_instance)

    def commit(self):
        """Persists all pending changes to the database."""
        self.db_session.commit()