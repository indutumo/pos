# app/repositories/stocktake_repo.py
from app.models.schema import StockTake, Product

class StockTakeRepository:
    def __init__(self, db_session):
        self.db_session = db_session

    def get_all(self, search_query: str = None):
        """Fetches audit sessions joined with product records to allow dynamic name filtering."""
        query = self.db_session.query(StockTake)
        
        if search_query and search_query.strip():
            wildcard_query = f"%{search_query.strip()}%"
            # Perform explicit relation join mapping to search across foreign tables safely
            query = query.join(Product).filter(Product.name.ilike(wildcard_query))
            
        return query.order_by(StockTake.stocktake_date.desc()).all()

    def get_active_products(self):
        return self.db_session.query(Product).filter(Product.status == "ACTIVE").order_by(Product.name.asc()).all()

    def add(self, stocktake: StockTake) -> StockTake:
        self.db_session.add(stocktake)
        return stocktake

    def commit(self):
        self.db_session.commit()