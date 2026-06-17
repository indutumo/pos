# app/repositories/product_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.schema import Product

class ProductRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, product_id: int) -> Product:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_barcode(self, barcode: str) -> Product:
        return self.db.query(Product).filter(Product.barcode == barcode.strip()).first()

    def get_all(self):
        return self.db.query(Product).order_by(Product.name).all()

    def search(self, search_query: str):
        if not search_query.strip():
            return self.get_all()
        
        token = f"%{search_query.strip()}%"
        return self.db.query(Product).filter(
            or_(
                Product.name.ilike(token),
                Product.barcode.ilike(token)
            )
        ).order_by(Product.name).all()

    def add(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        return product

    def commit(self):
        self.db.commit()