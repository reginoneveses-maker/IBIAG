import os, re, requests
from typing import List, Dict
from urllib.parse import urlparse

FIRECRAWL_URL = os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1").rstrip("/")
FIRECRAWL_KEY = os.environ.get("FIRECRAWL_API_KEY", "").strip()

def _headers():
    return {"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"}

def _extract_domain(url: str) -> str:
    try:
        return urlparse(url or "").netloc.lower().removeprefix("www.")
    except Exception:
        return ""

def _search(query: str, limit: int = 8) -> List[Dict]:
    if not FIRECRAWL_KEY:
        raise RuntimeError("FIRECRAWL_API_KEY não configurada")
    r = requests.post(f"{FIRECRAWL_URL}/search", headers=_headers(), json={"query": query, "limit": max(1, min(limit, 20))}, timeout=45)
    r.raise_for_status()
    payload = r.json()
    return payload.get("data", {}).get("web", []) or payload.get("web", []) or []

def _text(item: Dict) -> str:
    return " ".join(str(item.get(k, "") or "") for k in ("title", "description", "snippet", "markdown"))

def _score(text: str) -> int:
    t = (text or "").lower()
    score = 20
    for word, points in [("import",20),("importer",20),("buyer",18),("purchasing",15),("procurement",15),("ingredient",12),("distributor",10),("manufacturer",10),("juice",8),("powder",8),("organic",5)]:
        if word in t: score += points
    return min(score, 100)

def _emails(text: str) -> List[str]:
    return sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")))

def _phones(text: str) -> List[str]:
    values = re.findall(r"(?:\+|00)?[0-9][0-9 .()/-]{7,}[0-9]", text or "")
    return sorted(set(v.strip() for v in values if len(re.sub(r"\D", "", v)) >= 8))

def _linkedin(results: List[Dict]) -> str:
    return next((x.get("url", "") for x in results if "linkedin.com" in (x.get("url", "") or "").lower()), "")

def discover_buyers(product: str, country: str, limit: int = 8) -> List[Dict]:
    results = _search(f'"{product}" importer buyer distributor ingredient "{country}"', limit)
    buyers, seen = [], set()
    for item in results:
        url, domain = item.get("url", ""), _extract_domain(item.get("url", ""))
        title, desc = item.get("title", "") or "", item.get("description", "") or ""
        key = domain or title.lower()
        if not key or key in seen: continue
        seen.add(key)
        buyers.append({"company": re.sub(r"\s*[|–—-]\s*.*$", "", title).strip() or domain.split(".")[0].title(), "website": url, "domain": domain, "country": country, "product_interest": product, "source_url": url, "source_title": title, "source_description": desc, "priority_score": _score(_text(item)), "source": "firecrawl_web"})
    return sorted(buyers, key=lambda x: x["priority_score"], reverse=True)

def discover_decision_maker(company: str, country: str, product: str) -> Dict:
    queries = [f'"{company}" procurement purchasing buyer ingredients {product} {country}', f'"{company}" "purchasing manager" OR "procurement manager" {country}', f'"{company}" site:linkedin.com/in procurement purchasing buyer {country}']
    results = []
    for query in queries: results.extend(_search(query, 5))
    combined = " ".join(_text(x) for x in results)
    emails, phones = _emails(combined), _phones(combined)
    best = results[0] if results else {}
    linkedin = _linkedin(results)
    name, title = "", ""
    patterns = [r"([A-Z][A-Za-zÀ-ÿ.'-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'-]+){1,3})\s*[,-]\s*((?:Global |Senior |Head of |Director of |Chief )?(?:Procurement|Purchasing|Sourcing|Buying)[A-Za-z &/-]*)", r"((?:Procurement|Purchasing|Sourcing|Buying)[A-Za-z &/-]*)\s*[,:-]\s*([A-Z][A-Za-zÀ-ÿ.'-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'-]+){1,3})"]
    for pattern in patterns:
        m = re.search(pattern, combined, flags=re.I)
        if m:
            a,b=m.group(1).strip(),m.group(2).strip()
            if any(w in a.lower() for w in ("procurement","purchasing","sourcing","buying")): title,name=a,b
            else: name,title=a,b
            break
    return {"decision_maker":name,"decision_maker_title":title,"decision_maker_email":emails[0] if emails else "","decision_maker_phone":phones[0] if phones else "","linkedin":linkedin,"source_url":best.get("url",""),"source":"firecrawl_web","evidence_urls":list(dict.fromkeys(x.get("url","") for x in results if x.get("url")))[:10],"contact_candidates":{"emails":emails[:10],"phones":phones[:10]},"validation_status":"needs_validation" if (name or emails or phones or linkedin) else "not_found"}
