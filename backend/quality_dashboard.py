"""Read-only metadata checks. These findings never approve a document or release stock."""
from collections import Counter
from datetime import date

FLAGS=("expired","expiring","missing_expiry","invalid_dates","missing_file","missing_supplier","missing_product","data_review")
DOC_TYPES=("Ficha Técnica","COA / Laudo","Certificado","FISPQ / SDS")
FIELDS={"certification":("id","supplier_id","name","issue_date","expiry_date","alert_days","file_path"),
        "document":("id","supplier_id","product_id","title","document_type","file_path")}

def text(value,limit=300):
    return value.strip()[:limit] if isinstance(value,str) else ""

def calendar(value):
    if not isinstance(value,str) or len(value)!=10 or value[4:5]!="-" or value[7:8]!="-":
        raise ValueError("Invalid date")
    result=date.fromisoformat(value)
    if result.isoformat()!=value: raise ValueError("Invalid date")
    return result

def reference_index(records):
    grouped={}
    for r in records:
        rid=r.get("id")
        if isinstance(rid,str) and rid: grouped.setdefault(rid,[]).append(r)
    return grouped

def quality_rows(certifications,documents,suppliers,products,today):
    supplier_index=reference_index(suppliers); product_index=reference_index(products)
    rows=[]
    for source,records in (("certification",certifications),("document",documents)):
        seen=set()
        for record in records:
            rid=record.get("id")
            if not isinstance(rid,str) or not rid or len(rid)>200 or any(ord(c)<32 for c in rid) or rid in seen:
                raise ValueError("Identificadores de qualidade inconsistentes. Revise os cadastros.")
            seen.add(rid)
            findings=[]
            supplier_id=record.get("supplier_id") if isinstance(record.get("supplier_id"),str) else ""
            product_id=record.get("product_id") if isinstance(record.get("product_id"),str) else ""
            supplier=supplier_index.get(supplier_id,[]); product=product_index.get(product_id,[])
            if len(supplier)!=1: findings.append("missing_supplier" if not supplier else "data_review")
            if source=="document" and (product_id or record.get("document_type") in ("Ficha Técnica","COA / Laudo","FISPQ / SDS")) and len(product)!=1: findings.append("missing_product" if not product else "data_review")
            supplier_name=text(supplier[0].get("name")) if len(supplier)==1 else ""
            product_name=text(product[0].get("name")) if len(product)==1 else ""
            title=text(record.get("name" if source=="certification" else "title"))
            if not title or (len(supplier)==1 and not supplier_name) or (len(product)==1 and not product_name):
                findings.append("data_review")
            path=record.get("file_path")
            file_declared=isinstance(path,str) and bool(path.strip())
            if not file_declared: findings.append("missing_file")
            expiry=""; issue=""; days_remaining=None; alert_days=None
            if source=="certification":
                expiry=text(record.get("expiry_date"),100); issue=text(record.get("issue_date"),100)
                try:
                    if not expiry: findings.append("missing_expiry")
                    else:
                        end=calendar(expiry); days_remaining=(end-today).days
                        if days_remaining<0: findings.append("expired")
                    start=calendar(issue) if issue else None
                    if (start and start>today) or (start and expiry and start>calendar(expiry)): findings.append("invalid_dates")
                except (ValueError,TypeError): findings.append("invalid_dates")
                alert=record.get("alert_days",30)
                if type(alert) is not int or not 0<=alert<=365:
                    findings.append("data_review")
                else:
                    alert_days=alert
                    if days_remaining is not None and 0<=days_remaining<=alert: findings.append("expiring")
            rows.append({"id":rid,"source":source,"title":title or "Título não informado",
                "supplier_id":supplier_id,"supplier_name":supplier_name,"product_id":product_id,"product_name":product_name,
                "document_type":text(record.get("document_type")) if source=="document" else "Certificação de fornecedor",
                "issue_date":issue,"expiry_date":expiry,"days_remaining":days_remaining,"alert_days":alert_days,
                "file_declared":file_declared,"flags":[flag for flag in FLAGS if flag in findings]})
    rank={flag:i for i,flag in enumerate(FLAGS)}
    return sorted(rows,key=lambda row:(min((rank[f] for f in row["flags"]),default=len(FLAGS)),row["expiry_date"],row["source"],row["id"]))

def quality_summary(rows):
    counts=Counter(flag for row in rows for flag in row["flags"])
    return {"total":len(rows),"needs_attention":sum(bool(row["flags"]) for row in rows),
            "without_findings":sum(not row["flags"] for row in rows),
            "by_source":{source:sum(r["source"]==source for r in rows) for source in ("certification","document")},
            "flags":{flag:counts[flag] for flag in FLAGS}}
