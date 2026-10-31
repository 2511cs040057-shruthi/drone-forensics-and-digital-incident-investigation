from getpass import getpass

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .models.user import User
from .services.database import SessionLocal, initialize_database


def main() -> None:
    initialize_database()
    username = input("New investigator username: ").strip()
    if not username or len(username) > 80:
        raise SystemExit("Username must be between 1 and 80 characters.")

    password = getpass("New password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    if password != confirmation:
        raise SystemExit("Passwords did not match.")

    with SessionLocal() as database:
        if database.scalar(select(User).where(User.username == username)):
            raise SystemExit("That username already exists.")
        database.add(User(username=username, password_hash=generate_password_hash(password)))
        database.commit()
    print(f"Investigator account '{username}' created.")


if __name__ == "__main__":
    main()
