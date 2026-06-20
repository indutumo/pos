from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.schema import Product


class ProductRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, product_id: int) -> Product:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_barcode(self, barcode: str) -> Product:
        return self.db.query(Product).filter(
            Product.barcode == barcode.strip()
        ).first()

    def get_all(self):
        return self.db.query(Product).order_by(Product.name).all()

    def search(self, search_query: str):
        if not search_query.strip():
            return self.get_all()

        token = f"%{search_query.strip()}%"

        return (
            self.db.query(Product)
            .filter(
                or_(
                    Product.name.ilike(token),
                    Product.barcode.ilike(token)
                )
            )
            .order_by(Product.name)
            .all()
        )

    # ==========================
    # PAGINATION METHODS
    # ==========================

    def get_all_paginated(self, limit: int, offset: int):
        return (
            self.db.query(Product)
            .order_by(Product.name)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def search_paginated(
        self,
        search_query: str,
        limit: int,
        offset: int
    ):
        token = f"%{search_query.strip()}%"

        return (
            self.db.query(Product)
            .filter(
                or_(
                    Product.name.ilike(token),
                    Product.barcode.ilike(token)
                )
            )
            .order_by(Product.name)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_all(self):
        return self.db.query(Product).count()

    def count_search(self, search_query: str):
        token = f"%{search_query.strip()}%"

        return (
            self.db.query(Product)
            .filter(
                or_(
                    Product.name.ilike(token),
                    Product.barcode.ilike(token)
                )
            )
            .count()
        )

    def add(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        return product

    def commit(self):
        self.db.commit()