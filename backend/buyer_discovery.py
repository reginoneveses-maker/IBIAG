import os, re, requests
from typing import List, Dict

FIRECRAWL_URL = os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1").rstrip("/")
FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY", "").strip()

def _headers():
    return {"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"}

def _extract_domain(url: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else ""

def _search(query: str, limit: int = 8) -> List[Dict]:
    if not FIRECRAWL_KEY:
        raise RuntimeError("FIRECRAWL_API_KEY não configurada")
    r = requests.post(
        f"{FIRECRAWL_URL}/search",
        headers=_headers(),
        json={"query": query, "limit": limit},
        timeout=45,
    )
    r.raise_for_status()
    payload = r.json()
    return payload.get("data", {}).get("web", []) or payload.get("web", []) or []

def _score(text: str) -> int:
    t = (text or "").lower()
    score = 20
    for word, points in [
        ("import", 20), ("importer", 20), ("buyer", 18), ("purchasing", 15),
        ("procurement", 15), ("ingredient", 12), ("distributor", 10),
        ("manufacturer", 10), ("juice", 8), ("powder", 8), ("organic", 5),
    ]:
        if word in t:
            score += points
    return min(score, 100)

def discover_buyers(product: str, country: str, limit: int = 8) -> List[Dict]:
    query = f'"{product}" importer buyer distributor ingredient "{country}"'
    results = _search(query, limit)
    buyers = []
    seen = set()
    for item in results:
        url = item.get("url", "")
        domain = _extract_domain(url)
        title = item.get("title", "") or ""
        desc = item.get("description", "") or ""
        key = domain.lower() or title.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        buyers.append({
            "company": re.sub(r"\s*[|–—-]\s*.*$", "", title).strip() or domain.split(".")[0].title(),
            "website": url,
            "domain": domain,
            "country": country,
            "product_interest": product,
            "source_url": url,
            "source_title": title,
            "source_description": desc,
            "priority_score": _score(title + " " + desc),
            "source": "firecrawl_web",
        })
    return sorted(buyers, key=lambda x: x["priority_score"], reverse=True)

def discover_decision_maker(company: str, country: str, product: str) -> Dict:
    query = f'"{company}" procurement purchasing buyer ingredients {product} {country}'
    results = _search(query, 5)
    best = results[0] if results else {}
    return {
        "decision_maker": "",
        "decision_maker_title": "",
        "decision_maker_email": "",
        "decision_maker_phone": "",
        "linkedin": next((x.get("url","") for x in results if "linkedin.com" in x.get("url","")), ""),
        "source_url": best.get("url",""),
        "source": "firecrawl_web",
    }
