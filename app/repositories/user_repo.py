# app/repositories/user_repo.py
from sqlalchemy.orm import Session, joinedload
from app.models.schema import User, UserRole

class UserRepository:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_user_by_username(self, username: str) -> User:
        return self.db.query(User).options(joinedload(User.role)).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> User:
        return self.db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()

    def get_all_users(self):
        return self.db.query(User).options(joinedload(User.role)).order_by(User.id).all()

    def get_all_roles(self):
        return self.db.query(UserRole).order_by(UserRole.role_name).all()

    def add_user(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        return user

    def commit(self):
        self.db.commit()