"""Comex Stat MDIC integration helper for IBIAG.
The official API is public and exposes aggregated trade statistics.
"""
import os
import time
import requests

BASE_URL = os.environ.get("COMEXSTAT_API_URL", "https://api-comexstat.mdic.gov.br").rstrip("/")

def headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "IBIAG/1.0",
        "Origin": "https://comexstat.mdic.gov.br",
        "Referer": "https://comexstat.mdic.gov.br/",
    }

def ncm_search(search="", page=1, per_page=50):
    params={"language":"pt","perPage":min(max(per_page,1),100),"page":max(page,1)}
    if search.strip():
        params["search"]=search.strip()
    r=requests.get(f"{BASE_URL}/tables/ncm",params=params,headers=headers(),timeout=30)
    r.raise_for_status()
    return r.json()

def general(payload):
    """Query Comex Stat with bounded retry/backoff for transient throttling."""
    last_response = None
    for attempt in range(3):
        r = requests.post(
            f"{BASE_URL}/general?language=pt",
            json=payload,
            headers=headers(),
            timeout=60,
        )
        last_response = r
        if r.status_code != 429:
            r.raise_for_status()
            return r.json()
        if attempt < 2:
            retry_after = r.headers.get("Retry-After", "").strip()
            try:
                delay = min(max(float(retry_after), 1.0), 8.0) if retry_after else (2 ** attempt)
            except ValueError:
                delay = 2 ** attempt
            time.sleep(delay)
    last_response.raise_for_status()
    return last_response.json()
