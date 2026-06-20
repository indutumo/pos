# app/services/customer_service.py

class CustomerService:
    def __init__(self, repository):
        self.repo = repository

    def get_total_count(self, search_query: str = "") -> int:
        """Returns the total number of customer records matching the search query."""
        return self.repo.get_total_count(search_query)

    def get_customers_paginated(self, search_query: str = "", limit: int = 30, offset: int = 0):
        """Returns a specific slice of customer records for pagination."""
        return self.repo.get_customers_paginated(search_query, limit, offset)

    def get_customers_list(self, search_query: str = ""):
        """Returns all customers (used for Excel/PDF exports)."""
        return self.repo.get_all(search_query)

    def create_customer(self, name: str, mobile_number: str, email: str):
        if not name:
            raise ValueError("Customer name is required.")
        return self.repo.create(name=name, mobile_number=mobile_number, email=email)

    def update_customer(self, customer_id: int, name: str, mobile_number: str, email: str):
        if not name:
            raise ValueError("Customer name is required.")
        return self.repo.update(customer_id, name=name, mobile_number=mobile_number, email=email)