import sys
import bcrypt
from sqlalchemy.orm import Session

# Adjust these imports according to your directory structure
from app.core.database import SessionLocal, engine  # Ensure engine is imported
from app.models.schema import Base, User, UserRole, RoleStatus, UserStatus, Organization

def generate_secure_pin(pin: str) -> str:
    """Hashes a text PIN safely using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pin.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def seed_database():
    # 1. Create all database tables first
    print("[*] Ensuring database schema exists...")
    Base.metadata.create_all(bind=engine)
    
    # Establish a fresh database session
    db: Session = SessionLocal()
    
    try:
        print("[*] Starting database seeding process...")

        # 2. Seed System Roles
        target_roles = ["ADMIN", "MANAGE_STOCK", "CASHIER"]
        cached_roles = {}

        for role_name in target_roles:
            existing_role = db.query(UserRole).filter(UserRole.role_name == role_name).first()
            
            if not existing_role:
                new_role = UserRole(
                    role_name=role_name, 
                    status=RoleStatus.ACTIVE
                )
                db.add(new_role)
                db.flush()  # Flushes to DB to populate ID
                cached_roles[role_name] = new_role
                print(f"[+] Successfully seeded role: {role_name}")
            else:
                cached_roles[role_name] = existing_role
                print(f"[-] Role '{role_name}' already exists. Skipping.")

        # 3. Seed Default Organization Profile
        # This prevents the 'NoneType' error in print_thermal_receipt
        existing_org = db.query(Organization).first()
        if not existing_org:
            new_org = Organization(
                name="Zola POS Terminal",
                address="Nairobi, Kenya",
                phone="+254 700 000 000",
                kra_pin="P000000000X"
            )
            db.add(new_org)
            print("[+] Successfully seeded default organization profile.")
        else:
            print("[-] Organization profile already exists. Skipping.")

        # 4. Seed Default Admin User
        admin_username = "admin"
        default_pin = "1234" 

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
        else:
            print(f"[-] User '{admin_username}' already exists. Skipping.")

        # Commit all transactions
        db.commit()
        print("[*] Seeding operational execution complete.")

    except Exception as e:
        db.rollback()
        print(f"[!] Critical error occurred during seeding transaction: {e}", file=sys.stderr)
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()