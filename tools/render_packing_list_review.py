"""Pure synthetic packing PDFs: no DB, environment credentials or network."""
import argparse
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from packing_lists import validate_details
from packing_list_pdf import render_packing_list
from datetime import date

def review_record():
    record={"id":"synthetic","reference":"PL-SYNTHETIC-ONLY","issue_date":"2026-10-19","seller_name":"IBIAG - TEST DOCUMENT",
      "seller_address":"100 Example Street","seller_country":"Brazil","buyer_address":"200 Example Avenue","buyer_country":"Portugal",
      "delivery_same_as_buyer":True,"ship_to_name":"","ship_to_address":"","ship_to_country":"",
      "notes":"SYNTHETIC VALIDATION DOCUMENT. NOT FOR COMMERCIAL USE.","signatory":"Synthetic Operator","status":"approved","version":2,"updated_at":"2026-10-20T00:00:00+00:00",
      "source_order_snapshot":{"customer":"Example Buyer - TEST DOCUMENT","number":"SO-SYNTHETIC-ONLY","customer_country":"Portugal","order_date":"2026-10-19","incoterm":"FOB","items":[{"product_name":"AÇAÍ EXTRACT POWDER","quantity":250,"unit":"kg"}]},
      "packages":[{"marks":"BOXES 1-10","packaging":"Cartons","package_count":10,"net_kg":"250","gross_kg":"260","volume_m3":"1.25","allocations":[{"index":0,"quantity":"250"}]}]}
    validate_details(record,date(2026,10,20),approval=True)
    return record

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output-dir",type=Path,required=True);args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    normal=review_record();(args.output_dir/"packing-list-synthetic.pdf").write_bytes(render_packing_list(normal))
    stress=copy.deepcopy(normal);stress["status"]="draft"
    stress["packages"]=[{**copy.deepcopy(normal["packages"][0]),"marks":f"GROUP {i:02d}","packaging":"Food ingredient cartons - organic powder","net_kg":"10","gross_kg":"11","allocations":[{"index":0,"quantity":"10"}]} for i in range(25)]
    stress["seller_address"]="Example long address in São Paulo, Brazil. "*8;stress["buyer_address"]="Example long address in Porto, Portugal. "*8
    stress["notes"]+="\n"+"Long packing notes, açaí, São Paulo.\n"*20
    validate_details(stress,date(2026,10,20));(args.output_dir/"packing-list-stress-draft.pdf").write_bytes(render_packing_list(stress))
if __name__=="__main__":main()
