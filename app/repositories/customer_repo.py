from sqlalchemy import or_

class CustomerRepository:
    def __init__(self, db_session):
        self.db = db_session

    def _build_search_query(self, base_query, search_term: str):
        """Helper method to apply search filters consistently."""
        from app.models.schema import Customer  # Updated import path
        
        if search_term and search_term.strip():
            term = f"%{search_term.strip()}%"
            return base_query.filter(
                or_(
                    Customer.name.ilike(term),
                    Customer.mobile_number.ilike(term),
                    Customer.email.ilike(term)
                )
            )
        return base_query

    def get_total_count(self, search_query: str = "") -> int:
        from app.models.schema import Customer  # Updated import path
        query = self.db.query(Customer)
        query = self._build_search_query(query, search_query)
        return query.count()

    def get_customers_paginated(self, search_query: str = "", limit: int = 30, offset: int = 0):
        from app.models.schema import Customer  # Updated import path
        query = self.db.query(Customer)
        query = self._build_search_query(query, search_query)
        
        # Order by newest first, then apply pagination limits
        return query.order_by(Customer.created_at.desc())\
                    .limit(limit)\
                    .offset(offset)\
                    .all()

    def get_all(self, search_query: str = ""):
        from app.models.schema import Customer  # Updated import path
        query = self.db.query(Customer)
        query = self._build_search_query(query, search_query)
        return query.order_by(Customer.created_at.desc()).all()

    def get_by_id(self, customer_id: int):
        from app.models.schema import Customer  # Updated import path
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def create(self, name: str, mobile_number: str, email: str):
        from app.models.schema import Customer  # Updated import path
        new_customer = Customer(name=name, mobile_number=mobile_number, email=email)
        self.db.add(new_customer)
        self.db.commit()
        self.db.refresh(new_customer)
        return new_customer

    def update(self, customer_id: int, name: str, mobile_number: str, email: str):
        customer = self.get_by_id(customer_id)
        if customer:
            customer.name = name
            customer.mobile_number = mobile_number
            customer.email = email
            self.db.commit()
            self.db.refresh(customer)
        return customer