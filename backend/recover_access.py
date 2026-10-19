"""Host-operator recovery. No public endpoint, email service or startup side effects."""
import argparse
import asyncio
from datetime import datetime, timezone
import getpass
import os
import re
import sys
import uuid
import warnings

import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from password_inputs import password_bytes


class RecoveryRefused(Exception):
    """Intentionally carries no account, credential or database details."""


def validate_request(account_id, expected_role, reason, case_id):
    if (not isinstance(account_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", account_id)
            or expected_role not in {"admin", "user"}
            or reason not in {"lost-password", "admin-emergency"}
            or (reason == "admin-emergency" and expected_role != "admin")
            or not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", case_id)):
        raise RecoveryRefused() from None


async def recovery_target(db, account_id, expected_role, reason, case_id):
    validate_request(account_id, expected_role, reason, case_id)
    projection = {key: 1 for key in ("id", "email", "role", "active", "password_hash", "session_version", "access_recovery_audit")}
    records = await db.users.find({"id": account_id}, projection).limit(2).to_list(2)
    if len(records) != 1:
        raise RecoveryRefused()
    record = records[0]
    email = record.get("email")
    if (record.get("role", "user") != expected_role or record.get("active", True) is not True
            or not isinstance(email, str) or not email or email != email.strip().lower()
            or not isinstance(record.get("password_hash"), str)
            or type(record.get("session_version", 0)) is not int or record.get("session_version", 0) < 0
            or not isinstance(record.get("access_recovery_audit", []), list)
            or len(record.get("access_recovery_audit", [])) >= 100):
        raise RecoveryRefused()
    if await db.users.count_documents({"email": email}, limit=2) != 1:
        raise RecoveryRefused()
    return record


async def recover(db, record, new_password, expected_role, reason, case_id):
    validate_request(record.get("id"), expected_role, reason, case_id)
    try:
        raw = password_bytes(new_password, minimum=8)
        if bcrypt.checkpw(raw, record["password_hash"].encode()):
            raise RecoveryRefused()
        encoded = bcrypt.hashpw(raw, bcrypt.gensalt()).decode()
    except (TypeError, ValueError, KeyError, UnicodeError):
        raise RecoveryRefused() from None
    # Compare credential, generation, identity and access state read before the
    # operator prompt. Rotation, suspension or identity changes win over stale input.
    query = {"_id": record["_id"], "id": record["id"], "email": record["email"],
             "password_hash": record["password_hash"]}
    for field in ("session_version", "active", "role", "access_recovery_audit"):
        query[field] = record[field] if field in record else {"$exists": False}
    if record.get("role", "user") != expected_role or record.get("active", True) is not True:
        raise RecoveryRefused()
    now = datetime.now(timezone.utc).isoformat()
    event = {"id": uuid.uuid4().hex, "at": now, "actor": "host-operator",
             "reason": reason, "case_id": case_id}
    result = await db.users.update_one(query, {
        "$set": {"password_hash": encoded, "password_changed_at": now},
        "$inc": {"session_version": 1}, "$push": {"access_recovery_audit": event}})
    if not result.modified_count:
        raise RecoveryRefused()


async def execute(args):
    validate_request(args.account_id, args.expected_role, args.reason, args.case_id)
    if args.apply and not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr)):
        raise RecoveryRefused()
    # Use only the target's existing server environment; never import server or
    # load arbitrary .env files, run startup, provision services or print a URI.
    uri, name = os.environ.get("MONGO_URL"), os.environ.get("DB_NAME")
    if not uri or not name:
        raise RecoveryRefused()
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, socketTimeoutMS=10000, w="majority", journal=True)
    try:
        record = await recovery_target(client[name], args.account_id, args.expected_role, args.reason, args.case_id)
        if not args.apply:
            print("Verificação concluída; nenhuma alteração aplicada.")
            return
        confirmation = input("Após verificar a identidade por canal confiável, digite RECUPERAR seguido do ID informado: ")
        if confirmation != "RECUPERAR " + args.account_id:
            raise RecoveryRefused()
        with warnings.catch_warnings():
            # A broken terminal must abort before getpass falls back to echoed input.
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Nova senha (oculta): ")
            repeated = getpass.getpass("Repita a nova senha (oculta): ")
        if password != repeated:
            raise RecoveryRefused()
        await recover(client[name], record, password, args.expected_role, args.reason, args.case_id)
        print("Recuperação aplicada; sessões anteriores revogadas. Exija novo login.")
    finally:
        client.close()


class RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Parâmetros inválidos. Use --help; não informe credenciais como argumentos.\n")


def main(argv=None):
    parser = RedactedArgumentParser(description="Recuperação por operador do servidor; somente verificação por padrão.")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--expected-role", required=True, choices=("admin", "user"))
    parser.add_argument("--reason", required=True, choices=("lost-password", "admin-emergency"))
    parser.add_argument("--case-id", required=True, help="Referência não confidencial da verificação de identidade")
    parser.add_argument("--apply", action="store_true", help="Exige terminal interativo e confirmação do alvo")
    args = parser.parse_args(argv)
    try:
        asyncio.run(execute(args))
        return 0
    except (Exception, KeyboardInterrupt):
        # Do not report whether an interrupted/failed write committed. Verify
        # state through a fresh login before retrying a network-uncertain outcome.
        print("Operação não confirmada. Verifique o acesso antes de repetir; detalhes não são exibidos.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
