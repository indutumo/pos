# app/services/sales_service.py
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

from app.models.schema import Sale, BillReceipt, User, ReceiptStatus, Shift, ShiftStatus, PaymentMethod # Added missing models
from app.repositories.sales_repo import SalesRepository

class SalesService:
    def __init__(self, sales_repo: SalesRepository):
        self.sales_repo = sales_repo

    def get_receipts_ledger(self, search_query: str = None):
        return self.sales_repo.get_all_receipts(search_query)

    def get_receipt_details(self, receipt_id: int):
        return self.sales_repo.get_receipt_by_id(receipt_id)

    def get_flat_sales_history(self, search_query: str = None):
        return self.sales_repo.get_all_sales_standalone(search_query)

    def checkout_cart(self, current_user: User, customer_id: int, cart_items: list, paid_amount: float) -> BillReceipt:
        # ... (keep your existing checkout_cart logic here) ...
        if not cart_items:
            raise ValueError("Validation Error: Cannot finalize empty transactional cart logs.")

        total_accumulation = Decimal('0.00')
        sales_instances = []

        for item in cart_items:
            qty = int(item['qty'])
            u_price = Decimal(str(item['unit_price']))
            subtotal = qty * u_price
            total_accumulation += subtotal

            sale_row = Sale(
                product_id=item['product_id'],
                quantity=qty,
                price=u_price,
                user_id=current_user.id
            )
            sales_instances.append(sale_row)

        p_amount = Decimal(str(paid_amount))
        status_enum = ReceiptStatus.COMPLETED if p_amount >= total_accumulation else ReceiptStatus.PENDING

        new_receipt = BillReceipt(
            receipt_number=self.sales_repo.generate_unique_receipt_number(),
            total=total_accumulation,
            paid_amount=p_amount,
            user_id=current_user.id,
            customer_id=customer_id if customer_id != 0 else None,
            status=status_enum
        )

        return self.sales_repo.create_receipt_with_sales(new_receipt, sales_instances)

    def process_shift_aggregation(self, db_session, user_id, payments_staged):
        """
        Finds or creates an OPEN shift for the user for the current calendar date 
        and updates aggregate metrics safely with Decimal precision.
        """
        now = datetime.utcnow()
        today_date = now.date()

        # Lookup an existing OPEN shift for this user matching today's date
        current_shift = db_session.query(Shift).filter(
            Shift.user_id == user_id,
            Shift.status == ShiftStatus.OPEN,
            func.date(Shift.shift_date) == today_date
        ).first()

        # Fallback: If no open shift exists for today, initialize a new daily session record
        if not current_shift:
            current_shift = Shift(
                user_id=user_id,
                shift_date=now,
                total_sales=Decimal("0.00"),
                cash=Decimal("0.00"),
                mobile_payment=Decimal("0.00"),
                bank=Decimal("0.00"),
                status=ShiftStatus.OPEN
            )
            db_session.add(current_shift)
            db_session.flush()  # Extract primary keys without committing main transaction block

        # Aggregate the incoming payment slices into the daily ledger buckets
        for p_slice in payments_staged:
            amount = Decimal(str(p_slice['amount']))
            method = p_slice['method']

            current_shift.total_sales += amount

            if method == PaymentMethod.CASH:
                current_shift.cash += amount
            elif method == PaymentMethod.MOBILE_MONEY:
                current_shift.mobile_payment += amount
            elif method == PaymentMethod.BANK:
                current_shift.bank += amount

        # Save updates to persistence layers
        db_session.commit()
        return current_shift