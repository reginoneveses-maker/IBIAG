"""Persistent, bounded multi-market discovery. Regions follow the UN M49 snapshot."""
import asyncio
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime, timezone

MARKETS = json.loads(Path(__file__).with_name("search_markets.json").read_text())
REGIONS = {"europe": {"name": "Europa", "countries": [x for x in MARKETS if x["region_en"] == "Europe"]},
           "asia": {"name": "Ásia", "countries": [x for x in MARKETS if x["region_en"] == "Asia"]}}
SLOTS = asyncio.Semaphore(3)


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value or "")).casefold() if not unicodedata.combining(c)).strip()


def resolve_markets(country="", countries=None, region=""):
    region_key = {"europa": "europe", "europe": "europe", "asia": "asia"}.get(normalize(region or country))
    if region:
        if not region_key:
            raise ValueError("Região não reconhecida. Escolha Europa ou Ásia.")
        return REGIONS[region_key]["countries"]
    if region_key and not countries:
        return REGIONS[region_key]["countries"]
    values = list(countries or []) + re.split(r"[,;\n]+", country or "")
    lookup = {normalize(alias): item for item in MARKETS for alias in (item["code"], item["name"], item["name_en"])}
    selected, seen = [], set()
    for value in values:
        if not str(value).strip():
            continue
        item = lookup.get(normalize(value))
        if not item:
            raise ValueError("País não reconhecido: " + str(value)[:80] + ". Use o nome do país ou código ISO (ex.: DE, ES, PT).")
        if item["code"] not in seen:
            seen.add(item["code"])
            selected.append(item)
    if not selected:
        raise ValueError("Informe ao menos um país ou escolha uma região.")
    if len(selected) > 60:
        raise ValueError("Selecione até 60 países por pesquisa.")
    return selected


def now():
    return datetime.now(timezone.utc).isoformat()


async def run_discovery_job(db, job, discover):
    results, completed, failures = {}, 0, 0
    lock = asyncio.Lock()
    await db.buyer_search_jobs.update_one({"id": job["id"]}, {"$set": {"status": "running", "updated_at": now()}})

    async def search(market):
        nonlocal completed, failures
        async with SLOTS:
            current = await db.buyer_search_jobs.find_one({"id": job["id"]}, {"cancel_requested": 1})
            if not current or current.get("cancel_requested"):
                return
            await db.buyer_search_jobs.update_one({"id": job["id"]}, {"$set": {f"progress.{market['code']}.status": "running"}})
            error, rows = "", []
            try:
                raw = await asyncio.to_thread(discover, job["product"], market["name_en"], job["limit"])
                seen = set()
                for row in raw[:job["limit"]]:
                    key = (normalize(row.get("company")), str(row.get("website") or row.get("source_url") or "").rstrip("/"))
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({**row, "country": market["name"], "country_code": market["code"], "search_country": market["name"], "product_interest": job["product"]})
            except RuntimeError as exc:
                error = str(exc)
            except Exception:
                error = "Não foi possível pesquisar este país agora."
            async with lock:
                completed += 1
                failures += bool(error)
                results[market["code"]] = rows
                ordered = [row for target in job["targets"] for row in results.get(target["code"], [])]
                await db.buyer_search_jobs.update_one({"id": job["id"]}, {"$set": {
                    "results": ordered, "completed": completed, "failures": failures, "updated_at": now(),
                    f"progress.{market['code']}": {"country": market["name"], "status": "failed" if error else "complete", "count": len(rows), "error": error}}})
    try:
        await asyncio.gather(*(search(market) for market in job["targets"]))
        current = await db.buyer_search_jobs.find_one({"id": job["id"]}, {"cancel_requested": 1})
        status = "cancelled" if current and current.get("cancel_requested") else "failed" if failures == len(job["targets"]) else "partial" if failures else "complete"
        await db.buyer_search_jobs.update_one({"id": job["id"]}, {"$set": {"status": status, "updated_at": now()}})
    except asyncio.CancelledError:
        await db.buyer_search_jobs.update_one({"id": job["id"]}, {"$set": {"status": "interrupted", "updated_at": now()}})
        raise
