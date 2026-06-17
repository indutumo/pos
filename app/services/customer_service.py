# app/services/customer_service.py
from app.models.schema import Customer
from app.repositories.customer_repo import CustomerRepository

class CustomerService:
    def __init__(self, customer_repo: CustomerRepository):
        self.customer_repo = customer_repo

    def get_customers_list(self, search_query: str = None):
        if search_query and search_query.strip():
            return self.customer_repo.search(search_query.strip())
        return self.customer_repo.get_all()

    def create_customer(self, name: str, mobile_number: str, email: str) -> Customer:
        if not name.strip():
            raise ValueError("Validation Error: Customer profile Name is a required field.")
        
        new_customer = Customer(
            name=name.strip(),
            mobile_number=mobile_number.strip() if mobile_number else None,
            email=email.strip() if email else None
        )
        return self.customer_repo.add(new_customer)

    def update_customer(self, customer_id: int, name: str, mobile_number: str, email: str) -> Customer:
        target_customer = self.customer_repo.get_by_id(customer_id)
        if not target_customer:
            raise ValueError("Data Missing: Selected customer profile could not be found.")

        if not name.strip():
            raise ValueError("Validation Error: Customer profile Name cannot be left empty.")

        target_customer.name = name.strip()
        target_customer.mobile_number = mobile_number.strip() if mobile_number else None
        target_customer.email = email.strip() if email else None
        
        self.customer_repo.commit()
        return target_customer