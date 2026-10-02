"""Shared document areas and sections, including legacy category names."""
import re
import unicodedata

AREAS = ("Financeiro & Fiscal", "Produtos", "Fornecedores", "Clientes & Comercial",
         "Societário", "Qualidade & Compliance", "Exportação & Logística")
SECTIONS = {
    "pop": ("Qualidade & Compliance", "Procedimentos"),
    "pop_signed": ("Qualidade & Compliance", "Procedimentos assinados"),
    "marketing": ("Clientes & Comercial", "Marketing"),
    "ibiag_organic": ("Qualidade & Compliance", "Certificação orgânica IBIAG"),
}
LEGACY = {"general": "Clientes & Comercial", "finance": "Financeiro & Fiscal",
          "fiscal": "Financeiro & Fiscal", "products": "Produtos", "suppliers": "Fornecedores",
          "commercial": "Clientes & Comercial", "societario": "Societário",
          "quality": "Qualidade & Compliance", "logistics": "Exportação & Logística"}

def folded(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text or "")
                   if not unicodedata.combining(c)).casefold()

def normalize_document(record):
    result = dict(record)
    category = result.get("category") or "general"
    section = result.get("section") or ""
    if category in SECTIONS:
        section = section or category
        category = SECTIONS[category][0]
    category = LEGACY.get(category, category)
    name = folded(" ".join([result.get("title", ""), result.get("file_name", "")]))
    # Classification identifies a document type. It does not approve its contents,
    # signatures, current version, validity or scope of certification.
    if not section:
        if category == "Qualidade & Compliance" and re.search(r"\bpop(?:[-_\s]|\b)", name):
            section = "pop"
        elif category in ("Clientes & Comercial", "Fornecedores") and re.search(
                r"portfolio|portfol[ií]o|presenta|apresenta|instituc|catalog|flyer|folder|cartaz|fair.tags", name):
            section = "marketing"
    result.update(category=category, section=section)
    return result

def matches_document(record, category=None, section=None):
    normalized = normalize_document(record)
    if record.get("deleted_at"):
        return False
    if category in SECTIONS:
        section = category
        category = None
    elif category:
        category = LEGACY.get(category, category)
    return (not category or normalized["category"] == category) and (
        not section or normalized["section"] == section)

def validate_classification(category, section):
    normalized = normalize_document({"category": category, "section": section})
    if normalized["category"] not in AREAS:
        raise ValueError("Área documental inválida")
    if normalized["section"] and normalized["section"] not in SECTIONS:
        raise ValueError("Seção documental inválida")
    return normalized["category"], normalized["section"]
