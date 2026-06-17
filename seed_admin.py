import sys
import bcrypt
from sqlalchemy.orm import Session

# Adjust these imports according to your exact directory structure
from app.core.database import SessionLocal  # This should return your sessionmaker() instance
from app.models.schema import User, UserRole, RoleStatus, UserStatus


def generate_secure_pin(pin: str) -> str:
    """Hashes a text PIN safely using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pin.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')


def seed_database():
    # Establish a fresh database session
    db: Session = SessionLocal()
    
    try:
        print("[*] Starting database seeding process...")

        # 1. Seed System Roles
        target_roles = ["ADMIN", "MANAGE_STOCK", "CASHIER"]
        cached_roles = {}

        for role_name in target_roles:
            # Query to check if the role exists
            existing_role = db.query(UserRole).filter(UserRole.role_name == role_name).first()
            
            if not existing_role:
                new_role = UserRole(
                    role_name=role_name, 
                    status=RoleStatus.ACTIVE
                )
                db.add(new_role)
                db.flush()  # Flushes changes to database to populate new_role.id
                cached_roles[role_name] = new_role
                print(f"[+] Successfully seeded role: {role_name}")
            else:
                cached_roles[role_name] = existing_role
                print(f"[-] Role '{role_name}' already exists. Skipping creation.")

        # 2. Seed Default Admin User
        admin_username = "admin"
        default_pin = "1234"  # Secure default value; change on first environment configuration

        # Query to check if the admin username is taken
        existing_admin = db.query(User).filter(User.username == admin_username).first()

        if not existing_admin:
            print("[*] Generating secure pin hash for Admin...")
            hashed_pin = generate_secure_pin(default_pin)

            new_admin = User(
                name="System Administrator",
                username=admin_username,
                pin_hash=hashed_pin,
                role_id=cached_roles["ADMIN"].id,
                status=UserStatus.ACTIVE
            )
            db.add(new_admin)
            print(f"[+] Successfully seeded administrative user.")
            print(f"    -> Username: {admin_username}")
            print(f"    -> Default PIN: {default_pin}")
        else:
            print(f"[-] User '{admin_username}' already exists. Skipping creation.")

        # Commit transaction safely if everything passed without issues
        db.commit()
        print("[*] Seeding operational execution complete.")

    except Exception as e:
        db.rollback()
        print(f"[!] Critical error occurred during seeding transaction: {e}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()