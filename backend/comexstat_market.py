"""Normalization helpers for Comex Stat market aggregates."""
def _first_value(row, keys):
    lowered = {str(k).lower().replace("_", ""): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key.lower().replace("_", ""))
        if value not in (None, ""):
            return value
    return None

def flatten_rows(value):
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                if any(k in item for k in ("country", "coPais", "co_pais", "noPais", "no_pais", "countryCode")):
                    out.append(item)
                else:
                    out.extend(flatten_rows(item))
        return out
    if isinstance(value, dict):
        for key in ("list", "data", "items", "results", "result", "content", "rows"):
            if key in value:
                rows = flatten_rows(value[key])
                if rows:
                    return rows
    return []

def normalize_markets(data):
    normalized = []
    for row in flatten_rows(data):
        country = _first_value(row, ["country", "noPais", "countryName", "pais", "coPais"])
        kg = _first_value(row, ["metricKG", "kg", "kgLiquido", "kg_liquido", "netWeight", "quantity"])
        fob = _first_value(row, ["metricFOB", "fob", "vlFob", "vl_fob", "valueFOB", "value"])
        try:
            kg = float(kg or 0)
        except (TypeError, ValueError):
            kg = 0.0
        try:
            fob = float(fob or 0)
        except (TypeError, ValueError):
            fob = 0.0
        if country is not None:
            normalized.append({"country": str(country), "volume_kg": kg, "fob_usd": fob})
    total_kg = sum(x["volume_kg"] for x in normalized)
    total_fob = sum(x["fob_usd"] for x in normalized)
    for x in normalized:
        x["share_pct"] = round(x["fob_usd"] * 100 / total_fob, 2) if total_fob else 0
        x["avg_usd_kg"] = round(x["fob_usd"] / x["volume_kg"], 4) if x["volume_kg"] else 0
    normalized.sort(key=lambda x: x["fob_usd"], reverse=True)
    return {"rows": normalized, "totals": {"volume_kg": total_kg, "fob_usd": total_fob}}
