"""Comex Stat MDIC integration helper for IBIAG.
The official API is public and exposes aggregated trade statistics.
"""
import os
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
    if search.strip(): params["search"]=search.strip()
    r=requests.get(f"{BASE_URL}/tables/ncm",params=params,headers=headers(),timeout=30)
    r.raise_for_status()
    return r.json()

def general(payload):
    r=requests.post(f"{BASE_URL}/general?language=pt",json=payload,headers=headers(),timeout=60)
    r.raise_for_status()
    return r.json()
