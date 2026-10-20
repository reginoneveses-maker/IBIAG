"""Render synthetic QA PDFs without database, credentials, network or startup."""
import argparse
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from commercial_invoice_pdf import render_invoice

def review_record():
    return {"reference":"CI-SYNTHETIC-ONLY", "issue_date":"2026-10-19", "seller_name":"IBIAG - TEST DOCUMENT",
        "seller_tax_id":"TEST ONLY - INVALID", "seller_address":"100 Example Street", "seller_country":"Brazil",
        "buyer_address":"200 Example Avenue", "buyer_country":"Portugal", "buyer_tax_id":"",
        "delivery_same_as_buyer":True, "ship_to_name":"", "ship_to_address":"", "ship_to_country":"",
        "incoterm_place":"Santos", "payment_terms":"Prepaid", "delivery_terms":"Santos port, 30 days",
        "buyer_reference":"DEMO-ONLY", "notes":"SYNTHETIC VALIDATION DOCUMENT. NOT FOR COMMERCIAL USE.",
        "declaration":"", "signatory":"Synthetic Operator", "status":"approved", "version":2,
        "updated_at":"2026-10-20T00:00:00+00:00", "customs":[{"index":0,"origin_country":"Brazil","hs_code":"11063010"}],
        "source_order_snapshot":{"customer":"Example Buyer - TEST DOCUMENT", "number":"SO-SYNTHETIC-ONLY", "incoterm":"FOB", "total_usd":1065.38,
            "items":[{"product_name":"AÇAÍ EXTRACT POWDER", "quantity":250,"unit":"kg","unit_price":4.2615,"line_total":1065.38}]}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    normal=review_record()
    (args.output_dir/"commercial-invoice-synthetic.pdf").write_bytes(render_invoice(normal))
    stress=copy.deepcopy(normal);stress["status"]="draft"
    stress["source_order_snapshot"]["items"]=[{**normal["source_order_snapshot"]["items"][0],"product_name":("AÇAÍ EXTRACT POWDER - ORGANIC INGREDIENT "+str(i)+" - ")*4} for i in range(25)]
    stress["source_order_snapshot"]["total_usd"]=26634.50
    stress["customs"]=[{"index":i,"origin_country":"Brazil","hs_code":"11063010"} for i in range(25)]
    stress["seller_address"]="Example of a long address in São Paulo, Brazil. "*8
    stress["buyer_address"]="Example buyer address, Porto, Portugal. "*9
    stress["notes"]="SYNTHETIC STRESS TEST. NOT FOR COMMERCIAL USE.\n"+("Long operational notes with accents: São Paulo, açaí, condições.\n"*20)
    (args.output_dir/"commercial-invoice-stress-draft.pdf").write_bytes(render_invoice(stress))

if __name__=="__main__":main()
