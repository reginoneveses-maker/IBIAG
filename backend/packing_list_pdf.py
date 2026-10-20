"""Private packing PDF. Only approved public fields, no prices or supplier data."""
import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from commercial_invoice_pdf import InvoiceRenderingError, check_text, draw_logo, precise, BLUE, LIME, WIDTH

def public_packing(record):
    source=record["source_order_snapshot"]
    keys=("reference","issue_date","seller_name","seller_address","seller_country","buyer_address","buyer_country","notes","signatory","status","version")
    data={k:record.get(k,"") for k in keys}
    data.update(customer=source["customer"],order_number=source.get("number",""),incoterm=source["incoterm"])
    if record["delivery_same_as_buyer"]:
        data.update(ship_to_name=data["customer"],ship_to_address=data["buyer_address"],ship_to_country=data["buyer_country"])
    else:
        data.update({k:record[k] for k in ("ship_to_name","ship_to_address","ship_to_country")})
    data["items"]=[{k:i[k] for k in ("product_name","quantity","unit")} for i in source["items"]]
    data["packages"]=[{**{k:g[k] for k in ("marks","packaging","package_count","net_kg","gross_kg","volume_m3")},
        "allocations":[{k:a[k] for k in ("index","quantity")} for a in g["allocations"]]} for g in record["packages"]]
    data["totals"]={k:record["totals"][k] for k in ("package_count","net_kg","gross_kg","volume_m3")}
    return data


def render_packing_list(record):
    data = public_packing(record)
    check_text(data)
    buffer = io.BytesIO()
    style = ParagraphStyle("body", fontName="Invoice", fontSize=8.5, leading=12, textColor=colors.HexColor("#102D3A"), splitLongWords=1)
    small = ParagraphStyle("small", parent=style, fontSize=7, leading=10)
    label = ParagraphStyle("label", parent=style, fontName="InvoiceBold", textColor=BLUE, spaceAfter=6)
    right = ParagraphStyle("right", parent=style, alignment=TA_RIGHT)
    def p(value, st=style):
        # Every dynamic string is escaped. Paragraph cannot load an image/link.
        return Paragraph(escape(str(value or "Not provided")).replace("\n", "<br/>"), st)
    def block(title, values): return [p(title, label), *[p(v) for v in values]]
    story = []
    parties = Table([[block("SELLER / EXPORTER", [data["seller_name"], data["seller_address"], data["seller_country"]]),
                      block("BUYER", [data["customer"], data["buyer_address"], data["buyer_country"]])]], colWidths=[WIDTH/2]*2)
    parties.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F3F6FA")),("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#DDE5EF")),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    story.extend([parties, Spacer(1,14), p("SHIP TO", label), p(data["ship_to_name"]), p(data["ship_to_address"]), p(data["ship_to_country"]), Spacer(1,12),
        p("Order: "+(data["order_number"] or "Not provided")+" | Incoterm: "+data["incoterm"]),Spacer(1,12),
        p("Weights, volume and allocated quantities below are TOTALS for each group, not per package.",small),Spacer(1,10)])
    rows=[[p(t,label) for t in ("MARKS / PACKAGING / GOODS", "PACKAGES", "NET KG", "GROSS KG")]]
    for group in data["packages"]:
        desc=group["marks"]+" / "+group["packaging"]
        for allocation in group["allocations"]:
            item=data["items"][allocation["index"]]
            desc+="\n"+item["product_name"]+": "+(precise(allocation["quantity"]) if allocation["quantity"] else "Not provided")+" "+item["unit"]
        desc+="\nVolume m3: "+(precise(group["volume_m3"]) if group["volume_m3"] else "Not provided")
        rows.append([p(desc),p(group["package_count"],right),p(precise(group["net_kg"]) if group["net_kg"] else "Not provided",right),p(precise(group["gross_kg"]) if group["gross_kg"] else "Not provided",right)])
    table=Table(rows,colWidths=[WIDTH*.52,WIDTH*.16,WIDTH*.16,WIDTH*.16],repeatRows=1,hAlign="LEFT",splitByRow=1)
    table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EBF0F8")),("LINEBELOW",(0,0),(-1,0),1,BLUE),("LINEBELOW",(0,1),(-1,-1),0.3,colors.HexColor("#DDE5EF")),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    totals=data["totals"]
    story.extend([table,Spacer(1,14),p("TOTAL PACKAGES: "+str(totals["package_count"]),label),
        p("Net weight kg: "+(precise(totals["net_kg"]) if totals["net_kg"] is not None else "Not provided for all groups")+" | Gross weight kg: "+(precise(totals["gross_kg"]) if totals["gross_kg"] is not None else "Not provided for all groups")),
        p("Total volume m3: "+(precise(totals["volume_m3"]) if totals["volume_m3"] is not None else "Not provided for all groups")),Spacer(1,14)])
    if data["notes"]: story.extend([p("PACKING NOTES",label),p(data["notes"]),Spacer(1,12)])
    story.extend([p("AUTHORIZED REPRESENTATIVE",label),p(data["signatory"]),p("Typed name. No electronic or handwritten signature is generated.",small)])
    stamp=datetime.fromisoformat(record["updated_at"]).astimezone(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    pages = {"count":0}
    def page(canvas, doc):
        pages["count"] += 1
        if pages["count"] > 30: raise InvoiceRenderingError("O documento excede o limite de30 páginas.")
        canvas.setDateFormatter(lambda *_: stamp)
        canvas.saveState()
        if data["status"] != "approved":
            canvas.saveState();canvas.setFillColor(colors.HexColor("#E3E7EC"));canvas.setFont("InvoiceBold",55);canvas.translate(A4[0]/2,A4[1]/2);canvas.rotate(40)
            canvas.drawCentredString(0,0,"CANCELLED" if data["status"]=="cancelled" else "DRAFT");canvas.restoreState()
        draw_logo(canvas,42,A4[1]-72)
        title=p("PACKING LIST",ParagraphStyle("title2",parent=right,fontName="InvoiceBold",fontSize=14,leading=18,textColor=BLUE));w,h=title.wrap(300,40);title.drawOn(canvas,A4[0]-342,A4[1]-44-h)
        header=p(f"{data['reference']} | {data['issue_date']}",right);w,h=header.wrap(300,55);header.drawOn(canvas,A4[0]-342,A4[1]-68-h)
        canvas.setFillColor(LIME);canvas.rect(42,A4[1]-105,WIDTH,3,fill=1,stroke=0)
        footer=p(f"{data['reference']} | {data['status'].upper()} | Revision {data['version']} | Page {doc.page}",small);w,h=footer.wrap(WIDTH,35);footer.drawOn(canvas,42,26)
        canvas.restoreState()
    doc=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=122,bottomMargin=52,
                          title="Packing List "+data["reference"],author="IBIAG",invariant=1,pageCompression=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)
    result=buffer.getvalue()
    if len(result)>2*1024*1024: raise InvoiceRenderingError("O PDF excede o limite de tamanho.")
    return result
