"""Offline CRM interchange. No database, filesystem writes, credentials or network."""
FORMAT = "ibiag-crm-transfer-v1"

def build_crm_transfer(leads):
    if not isinstance(leads, list) or len(leads) > 1000:
        raise ValueError("Use uma lista com até 1.000 empresas por prévia.")
    def text(row, key, limit):
        value = row.get(key, "")
        if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
            raise ValueError("Campo de texto inválido.")
        return value.strip()
    companies, ids = [], set()
    for row in leads:
        if not isinstance(row, dict):
            raise ValueError("Empresa inválida.")
        ident, name = text(row, "id", 180), text(row, "company", 180)
        if not ident or not name or ident in ids:
            raise ValueError("Identificador ou empresa ausente/duplicado.")
        ids.add(ident)
        companies.append({
            "sourceId": ident, "name": name, "country": text(row, "country", 180),
            "website": text(row, "website", 1000), "industry": text(row, "industry", 180),
            "contact": {"name": text(row, "contact_name", 180), "email": text(row, "email", 320),
                        "phone": text(row, "phone", 80)}
        })
    # Deliberately omit owner IDs, notes, passwords, quote values and inferred decision makers.
    return {"format": FORMAT, "source": "IBIAG", "companies": companies}
