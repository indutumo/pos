# app/services/product_service.py
from decimal import Decimal
from app.repositories.product_repo import ProductRepository
from app.models.schema import Product, User, ProductStatus

class ProductService:
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo

    def _verify_mutation_clearance(self, current_user: User):
        """Enforces a strict role gate allowing mutations only for Admin and Store Manager roles."""
        ALLOWED_MUTATION_ROLES = ["ADMIN", "STORE_MANAGER", "MANAGE_STOCK"]
        if not current_user or current_user.role.role_name not in ALLOWED_MUTATION_ROLES:
            raise PermissionError("Access Denied: This operation requires Administrator or Store Manager privileges.")

    def get_products_list(self, search_query: str = None):
        """Universally open query accessible to all authenticated system users."""
        if search_query and search_query.strip():
            return self.product_repo.search(search_query)
        return self.product_repo.get_all()

    def create_product(self, current_user: User, name: str, barcode: str, 
                       buying_price: float, selling_price: float, 
                       quantity: int = 0, description: str = None) -> Product:
        self._verify_mutation_clearance(current_user)  # Updated clearance check

        if not name.strip() or not barcode.strip():
            raise ValueError("Validation Error: Product Name and Barcode are required fields.")
        
        try:
            b_price = Decimal(str(buying_price))
            s_price = Decimal(str(selling_price))
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Validation Error: Invalid price or quantity configuration values.")

        if b_price < 0 or s_price < 0 or qty < 0:
            raise ValueError("Validation Error: Prices and quantities cannot be negative numbers.")

        if s_price < b_price:
            raise ValueError("Business Rule Violation: Selling price cannot be lower than buying price.")

        if self.product_repo.get_by_barcode(barcode.strip()):
            raise ValueError(f"Constraint Violation: Barcode identifier '{barcode}' is already assigned.")

        new_product = Product(
            name=name.strip(),
            barcode=barcode.strip(),
            buying_price=b_price,
            selling_price=s_price,
            quantity=qty,
            description=description.strip() if description else None,
            status=ProductStatus.ACTIVE
        )
        return self.product_repo.add(new_product)

    def update_product(self, current_user: User, product_id: int, name: str, barcode: str, 
                       buying_price: float, selling_price: float, 
                       quantity: int, description: str, status_value: str) -> Product:
        self._verify_mutation_clearance(current_user)  # Updated clearance check

        target_product = self.product_repo.get_by_id(product_id)
        if not target_product:
            raise ValueError("Data Missing: Selected product reference could not be found.")

        if not name.strip() or not barcode.strip():
            raise ValueError("Validation Error: Product Name and Barcode cannot be empty.")

        try:
            b_price = Decimal(str(buying_price))
            s_price = Decimal(str(selling_price))
            qty = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("Validation Error: Input format parsing error on numerical metrics.")

        if b_price < 0 or s_price < 0 or qty < 0:
            raise ValueError("Validation Error: Financial values and stock balances cannot be negative.")

        if s_price < b_price:
            raise ValueError("Business Rule Violation: Selling price cannot drop below standard cost margins.")

        existing = self.product_repo.get_by_barcode(barcode.strip())
        if existing and existing.id != product_id:
            raise ValueError(f"Constraint Violation: Barcode identifier '{barcode}' is claimed by another entry.")

        target_product.name = name.strip()
        target_product.barcode = barcode.strip()
        target_product.buying_price = b_price
        target_product.selling_price = s_price
        target_product.quantity = qty
        target_product.description = description.strip() if description else None
        
        from app.models.schema import ProductStatus
        target_product.status = ProductStatus(status_value)

        self.product_repo.commit()
        return target_product