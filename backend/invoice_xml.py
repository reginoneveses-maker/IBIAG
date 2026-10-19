"""Bound untrusted NF-e XML before extracting invoice fields; no network or writes."""
import io
import math
from defusedxml.ElementTree import iterparse, ParseError
from defusedxml.common import DefusedXmlException
from fastapi import HTTPException
from upload_limits import read_import

MAX_XML_BYTES = 5 * 1024 * 1024
MAX_XML_DEPTH = 64
MAX_XML_ELEMENTS = 50000
INVALID_XML = "XML de NF-e inválido ou não permitido"


def bounded_xml(data):
    depth = count = 0
    root = None
    for event, element in iterparse(io.BytesIO(data), events=("start", "end"),
                                   forbid_dtd=True, forbid_entities=True, forbid_external=True):
        if event == "start":
            depth += 1
            count += 1
            if depth > MAX_XML_DEPTH or count > MAX_XML_ELEMENTS:
                raise HTTPException(413, "Estrutura XML acima do limite permitido")
            if root is None:
                root = element
        else:
            # Normalize completed elements, preserving declaration/encoding
            # and avoiding source-text substitutions.
            element.tag = element.tag.rsplit("}", 1)[-1]
            depth -= 1
    return root


async def parse_invoice_xml(file):
    data = await read_import(file, max_bytes=MAX_XML_BYTES)
    try:
        root = bounded_xml(data)
        if root is None:
            raise ValueError()
        info = root if root.tag == "infNFe" else root.find(".//infNFe")
        if info is None:
            raise ValueError()
        ide, emit, dest, total = info.find("ide"), info.find("emit"), info.find("dest"), info.find(".//ICMSTot")
        if ide is None or emit is None or total is None:
            raise ValueError()
        def text(element, path):
            node = element.find(path) if element is not None else None
            return (node.text or "").strip() if node is not None else ""
        number = text(ide, "nNF")
        amount = float(text(total, "vNF"))
        if not number or not math.isfinite(amount) or amount < 0:
            raise ValueError()
        kind = "saida" if text(ide, "tpNF") == "1" else "entrada"
        party = dest if kind == "saida" else emit
        issue = text(ide, "dhEmi") or text(ide, "dEmi")
        return {"number": number, "kind": kind, "party_name": text(party, "xNome"),
                "party_cnpj": text(party, "CNPJ") or text(party, "CPF"),
                "issue_date": issue[:10], "total": amount,
                "description": f"NF-e {number} — {text(emit, 'xNome')} → {text(dest, 'xNome')}"}
    except HTTPException:
        raise
    except (DefusedXmlException, ParseError, ValueError, TypeError, LookupError):
        raise HTTPException(400, INVALID_XML) from None
