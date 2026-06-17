# app/services/user_service.py
import re
from app.repositories.user_repo import UserRepository
from app.models.schema import User, UserStatus
from app.core.security import hash_pin

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def _verify_admin_clearance(self, current_user: User):
        if not current_user or current_user.role.role_name != "ADMIN":
            raise PermissionError("Security Violation: This action requires Administrator clearance.")

    def get_users_list(self, current_user: User):
        self._verify_admin_clearance(current_user)
        return self.user_repo.get_all_users()

    def get_roles_list(self, current_user: User):
        self._verify_admin_clearance(current_user)
        return self.user_repo.get_all_roles()

    def create_new_user(self, current_user: User, name: str, username: str, pin: str, 
                        role_id: int, mobile_number: str = None, email: str = None) -> User:
        self._verify_admin_clearance(current_user)

        if not name.strip() or not username.strip() or not pin.strip() or not role_id:
            raise ValueError("Validation Failure: Name, Username, Secure PIN, and Role fields are mandatory.")
        
        if len(pin) < 4:
            raise ValueError("Validation Failure: Secure access PIN must be at least 4 digits.")

        normalized_email = email.strip() if email and email.strip() else None
        if normalized_email and not re.match(r"[^@]+@[^@]+\.[^@]+", normalized_email):
            raise ValueError("Validation Failure: Invalid format configuration provided for Email Address.")

        normalized_username = username.strip().lower()
        if self.user_repo.get_user_by_username(normalized_username):
            raise ValueError(f"Constraint Violation: Username '{username}' is already allocated.")

        new_user = User(
            name=name.strip(),
            username=normalized_username,
            mobile_number=mobile_number.strip() if mobile_number else None,
            email=normalized_email,
            pin_hash=hash_pin(pin.strip()),
            role_id=role_id,
            status=UserStatus.ACTIVE
        )
        return self.user_repo.add_user(new_user)

    def update_user_details(self, current_user: User, target_user_id: int, name: str, username: str, 
                            role_id: int, mobile_number: str = None, email: str = None, pin: str = None) -> User:
        self._verify_admin_clearance(current_user)

        if not name.strip() or not username.strip() or not role_id:
            raise ValueError("Validation Failure: Name, Username, and Role fields are mandatory.")

        target_user = self.user_repo.get_user_by_id(target_user_id)
        if not target_user:
            raise ValueError("Data Missing: Selected user context cannot be tracked.")

        normalized_email = email.strip() if email and email.strip() else None
        if normalized_email and not re.match(r"[^@]+@[^@]+\.[^@]+", normalized_email):
            raise ValueError("Validation Failure: Invalid format configuration provided for Email Address.")

        # Ensure the updated username isn't already taken by another account
        normalized_username = username.strip().lower()
        existing_user = self.user_repo.get_user_by_username(normalized_username)
        if existing_user and existing_user.id != target_user_id:
            raise ValueError(f"Constraint Violation: Username '{username}' is already claimed by another operator.")

        # Apply structural changes
        target_user.name = name.strip()
        target_user.username = normalized_username
        target_user.role_id = role_id
        target_user.mobile_number = mobile_number.strip() if mobile_number else None
        target_user.email = normalized_email

        # Update PIN security string only if a new value is specified
        if pin and pin.strip():
            if len(pin.strip()) < 4:
                raise ValueError("Validation Failure: New secure access PIN must be at least 4 digits.")
            target_user.pin_hash = hash_pin(pin.strip())

        self.user_repo.commit()
        return target_user

    def toggle_user_status(self, current_user: User, target_user_id: int) -> User:
        self._verify_admin_clearance(current_user)

        if current_user.id == target_user_id:
            raise ValueError("Operation Blocked: You cannot self-deactivate your active administration session.")

        target_user = self.user_repo.get_user_by_id(target_user_id)
        if not target_user:
            raise ValueError("Data Missing: Selected user reference target could not be found.")

        target_user.status = UserStatus.INACTIVE if target_user.status == UserStatus.ACTIVE else UserStatus.ACTIVE
        self.user_repo.commit()
        return target_user