from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base
from sqlalchemy.types import TypeDecorator

class RoleStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ProductStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ReceiptStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentMethod(enum.Enum):
    CASH = "CASH"
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK = "BANK"

class ShiftStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class UserRole(Base):
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)
    status = Column(Enum(RoleStatus), default=RoleStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    mobile_number = Column(String(20))
    email = Column(String(100))
    username = Column(String(50), unique=True, nullable=False)
    pin_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey('user_roles.id'), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role = relationship("UserRole", back_populates="users")
    sales = relationship("Sale", back_populates="user")
    receipts = relationship("BillReceipt", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    shifts = relationship("Shift", back_populates="user")
    stocktakes = relationship("StockTake", back_populates="user")

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(String(255))
    barcode = Column(String(50), unique=True, nullable=False, index=True)
    buying_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, default=0)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE) # Ensure ProductStatus is imported/defined
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales = relationship("Sale", back_populates="product")
    stocktakes = relationship("StockTake", back_populates="product")

class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    mobile_number = Column(String(20))
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    receipts = relationship("BillReceipt", back_populates="customer")

class Sale(Base):
    __tablename__ = 'sales'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    # =================================================================
    # ADDED: Linked individual transaction items directly to a master receipt
    # =================================================================
    receipt_id = Column(Integer, ForeignKey('bill_receipts.id'), nullable=True) 
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sale_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="sales")
    user = relationship("User", back_populates="sales")
    # Bidirectional back-reference linking to parent invoice sheet container
    receipt = relationship("BillReceipt", back_populates="sales")
    

# ====================================================================
# NEW: Automatic translation layer to handle database enum values safely
# ====================================================================
class PostgresSafeReceiptStatus(TypeDecorator):
    """Ensures enum attributes match lowercase PostgreSQL constraints seamlessly."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # If passed as a Python Enum object, extract its string value
        if isinstance(value, enum.Enum):
            return value.value.lower()
        # If passed as a raw string (e.g., "COMPLETED"), force it to lowercase
        return str(value).lower()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Convert back to a clean Python Enum object when reading records out of the DB
        for status_enum in ReceiptStatus:
            if status_enum.value == str(value).lower():
                return status_enum
        return value


class BillReceipt(Base):
    __tablename__ = 'bill_receipts'

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    total = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), default=0)
    receipt_date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    status = Column(PostgresSafeReceiptStatus, default=ReceiptStatus.PENDING, nullable=False)

    user = relationship("User", back_populates="receipts")
    customer = relationship("Customer", back_populates="receipts")
    payments = relationship("Payment", back_populates="receipt")
    # =================================================================
    # ADDED: Relationship mapping out all child line item instances 
    # =================================================================
    sales = relationship("Sale", back_populates="receipt", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey('bill_receipts.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(10, 2), nullable=False)
    change_amount = Column(Numeric(10, 2), default=0)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)

    receipt = relationship("BillReceipt", back_populates="payments")
    user = relationship("User", back_populates="payments")

class StockTake(Base):
    __tablename__ = 'stocktakes'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)  # System quantity at time of check
    actual_quantity = Column(Integer, nullable=False) # Physical count
    difference = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    stocktake_date = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="stocktakes")
    user = relationship("User", back_populates="stocktakes")

class Shift(Base):
    __tablename__ = 'shifts'

    id = Column(Integer, primary_key=True, index=True)
    shift_date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    total_sales = Column(Numeric(10, 2), default=0)
    cash = Column(Numeric(10, 2), default=0)
    mobile_payment = Column(Numeric(10, 2), default=0)
    bank = Column(Numeric(10, 2), default=0)
    actual_sales = Column(Numeric(10, 2), nullable=True) # Entered on close
    difference = Column(Numeric(10, 2), nullable=True)
    status = Column(Enum(ShiftStatus), default=ShiftStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="shifts")