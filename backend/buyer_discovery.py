import os, re, requests
from typing import List, Dict
from urllib.parse import urlparse

FIRECRAWL_URL = os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v2").rstrip("/")
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
    try:
        r = requests.post(f"{FIRECRAWL_URL}/search", headers=_headers(), json={"query": query, "limit": max(1, min(limit, 20))}, timeout=45)
        r.raise_for_status()
    except requests.RequestException:
        raise RuntimeError("O serviço de pesquisa não respondeu. Confira a configuração e o saldo do serviço.") from None
    payload = r.json()
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise RuntimeError("O serviço de pesquisa não retornou uma resposta válida.")
    data = payload.get("data")
    results = data if isinstance(data, list) else (data.get("web", []) if isinstance(data, dict) else payload.get("web", []))
    if not isinstance(results, list):
        raise RuntimeError("Formato de resultados de pesquisa não reconhecido.")
    return [item for item in results if isinstance(item, dict) and item.get("url")]

def _text(item: Dict) -> str:
    return " ".join(str(item.get(k, "") or "") for k in ("title", "description", "snippet", "markdown"))

def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

def _product_terms(product: str) -> List[str]:
    stop = {"powder", "juice", "concentrate", "extract", "organic", "natural", "frozen", "pulp", "puree"}
    return [x for x in _normalize(product).split() if len(x) >= 3 and x not in stop]

def _is_product_relevant(item: Dict, product: str) -> bool:
    text = _normalize(_text(item))
    phrase = _normalize(product)
    terms = _product_terms(product)
    if phrase and phrase in text:
        return True
    # Require the distinctive product identity (e.g. "acerola"), not merely
    # generic form words such as powder/juice/extract.
    return bool(terms) and all(term in text for term in terms)

def _score(text: str, product: str = "") -> int:
    t = (text or "").lower()
    score = 20
    if product and _normalize(product) in _normalize(text):
        score += 30
    for word, points in [("import",20),("importer",20),("buyer",18),("purchasing",15),("procurement",15),("ingredient",12),("distributor",10),("manufacturer",10),("juice",8),("powder",8),("organic",5)]:
        if word in t: score += points
    return min(score, 100)

def _emails(text: str) -> List[str]:
    return sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")))

def _phones(text: str) -> List[str]:
    values = re.findall(r"(?:\+|00)?[0-9][0-9 .()/-]{7,}[0-9]", text or "")
    return sorted(set(v.strip() for v in values if len(re.sub(r"\D", "", v)) >= 8))

def _linkedin(results: List[Dict]) -> str:
    return next((x.get("url", "") for x in results if _extract_domain(x.get("url", "")) in {"linkedin.com", "br.linkedin.com"}), "")

def discover_buyers(product: str, country: str, limit: int = 8) -> List[Dict]:
    results = _search(f'"{product}" importer buyer distributor ingredient "{country}"', limit)
    buyers, seen = [], set()
    for item in results:
        url, domain = item.get("url", ""), _extract_domain(item.get("url", ""))
        title, desc = item.get("title", "") or "", item.get("description", "") or ""
        key = domain or title.lower()
        if not key or key in seen or not _is_product_relevant(item, product): continue
        seen.add(key)
        buyers.append({"company": re.sub(r"\s*[|–—-]\s*.*$", "", title).strip() or domain.split(".")[0].title(), "website": url, "domain": domain, "country": country, "product_interest": product, "source_url": url, "source_title": title, "source_description": desc, "priority_score": _score(_text(item), product), "source": "firecrawl_web"})
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
