"""Create the first owner on an empty local installation; never reset a user."""
import getpass
import os
import sys
import uuid
from datetime import datetime, timezone

import bcrypt
from email_validator import validate_email, EmailNotValidError
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from password_inputs import password_bytes


def create_owner(db, email, password):
    email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
    encoded = password_bytes(password, minimum=12)
    if db.users.find_one({}, {"_id": 1}):
        return False
    # Fixed primary key also prevents duplicate owners if two first starts race.
    record = {
        "_id": "local-bootstrap-owner", "id": str(uuid.uuid4()),
        "email": email, "name": "Administrador IBIAG", "role": "admin",
        "active": True, "session_version": 0,
        "password_hash": bcrypt.hashpw(encoded, bcrypt.gensalt()).decode(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        db.users.insert_one(record)
    except DuplicateKeyError:
        return False
    return True


def main():
    if os.environ.get("IBIAG_LOCAL_ONLY") != "1" or os.environ.get("DB_NAME") != "ibiag_local":
        raise ValueError("Este assistente atende somente a instalacao local.")
    with MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=15000) as client:
        db = client["ibiag_local"]
        if db.users.find_one({}, {"_id": 1}):
            print("Conta local existente preservada.")
            return
        print("Primeiro acesso: crie sua conta. A senha nao aparece ao digitar.")
        email = input("Seu e-mail: ")
        password = getpass.getpass("Crie uma senha (12 a 72 bytes): ")
        if password != getpass.getpass("Repita a senha: "):
            raise ValueError("As senhas nao coincidem.")
        created = create_owner(db, email, password)
        print("Conta local criada." if created else "Conta existente preservada.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, EmailNotValidError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception:
        # No Mongo URL, credentials, password or traceback in operator output.
        print("Nao foi possivel preparar a conta local. Nenhum reset foi feito.", file=sys.stderr)
        sys.exit(1)
