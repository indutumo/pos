# app/repositories/customer_repo.py
from app.models.schema import Customer

class CustomerRepository:
    def __init__(self, db_session):
        self.db_session = db_session

    def get_all(self):
        return self.db_session.query(Customer).order_by(Customer.name.asc()).all()

    def get_by_id(self, customer_id: int):
        return self.db_session.query(Customer).filter(Customer.id == customer_id).first()

    # =================================================================
    # FIXED: Replaced .like() with .ilike() for case-insensitive search
    # =================================================================
    def search(self, query: str):
        wildcard_query = f"%{query}%"
        return self.db_session.query(Customer).filter(
            (Customer.name.ilike(wildcard_query)) | 
            (Customer.mobile_number.ilike(wildcard_query))
        ).order_by(Customer.name.asc()).all()

    def add(self, customer: Customer) -> Customer:
        self.db_session.add(customer)
        self.db_session.commit()
        return customer

    def commit(self):
        self.db_session.commit()