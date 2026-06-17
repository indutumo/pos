# app/services/stocktake_service.py
from app.models.schema import StockTake, Product, User
from app.repositories.stocktake_repo import StockTakeRepository

class StockTakeService:
    def __init__(self, stocktake_repo: StockTakeRepository):
        self.stocktake_repo = stocktake_repo

    def _verify_clearance(self, current_user: User):
        ALLOWED_ROLES = ["ADMIN", "MANAGE_STOCK"]
        if not current_user or current_user.role.role_name not in ALLOWED_ROLES:
            raise PermissionError("Access Denied: This operational window requires Management or Admin security clearance.")

    def get_stocktakes_list(self, current_user: User, search_query: str = None):
        self._verify_clearance(current_user)
        return self.stocktake_repo.get_all(search_query)

    def get_available_products(self, current_user: User):
        self._verify_clearance(current_user)
        return self.stocktake_repo.get_active_products()

    def execute_stocktake(self, current_user: User, product_id: int, actual_quantity: int) -> StockTake:
        self._verify_clearance(current_user)
        
        if actual_quantity < 0:
            raise ValueError("Validation Error: Physical unit balance count cannot fall below zero.")

        session = self.stocktake_repo.db_session
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Data Missing: Selected target product reference profile could not be verified.")

        system_quantity = product.quantity
        discrepancy_difference = actual_quantity - system_quantity

        new_audit_record = StockTake(
            product_id=product.id,
            quantity=system_quantity,
            actual_quantity=actual_quantity,
            difference=discrepancy_difference,
            user_id=current_user.id
        )

        # =================================================================
        # FIXED: Explicitly flag product instance state change for persistence
        # =================================================================
        product.quantity = actual_quantity
        session.add(product)  
        
        self.stocktake_repo.add(new_audit_record)
        self.stocktake_repo.commit()  # Commits both product mutation and stocktake logging safely
        return new_audit_record