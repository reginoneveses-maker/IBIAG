"""External discovery is opt-in; client JSON cannot grant spend permission."""
import os
from fastapi import HTTPException


def paid_discovery_enabled():
    return os.environ.get("ALLOW_PAID_DISCOVERY", "false").strip().lower() == "true"


def require_paid_discovery():
    if not paid_discovery_enabled():
        raise HTTPException(403, "Pesquisas externas estão pausadas. O CRM continua disponível.")
