from app.repositories.user_repo import UserRepository
from app.core.security import verify_pin
from app.models.schema import UserStatus

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate(self, username: str, pin: str):
        user = self.user_repo.get_user_by_username(username)
        if not user:
            return False, "User not found"
        
        if user.status != UserStatus.ACTIVE:
            return False, "User account is inactive"
            
        if not verify_pin(pin, user.pin_hash):
            return False, "Invalid PIN"
            
        return True, user
