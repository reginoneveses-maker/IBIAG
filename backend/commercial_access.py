"""Explicit commercial profile. Does not confer administrator, backup or finance powers."""
from fastapi import HTTPException
PROFILE = "commercial-operator-v1"
def commercial_access(user):
    return user.get("role") == "admin" or (user.get("role") == "user" and user.get("commercial_profile") == PROFILE)
def require_commercial(user):
    if not commercial_access(user):
        raise HTTPException(403, "Perfil comercial autorizado obrigatório.")
    return user
