"""Render only explicitly selected invoice fields; no URLs, uploads or HTML input."""
import io
import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

class InvoiceRenderingError(ValueError):
    pass

FONT_DIR = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Invoice", str(FONT_DIR / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("InvoiceBold", str(FONT_DIR / "VeraBd.ttf")))
pdfmetrics.registerFontFamily("Invoice", normal="Invoice", bold="InvoiceBold")
LOGO = json.loads(Path(__file__).with_name("brand_logo.json").read_text())
BLUE = colors.HexColor("#1B4496")
LIME = colors.HexColor("#CAD51E")
WIDTH = A4[0] - 84


def public_invoice(record):
    source = record["source_order_snapshot"]
    keys = ("reference", "issue_date", "seller_name", "seller_tax_id", "seller_address", "seller_country",
            "buyer_address", "buyer_country", "buyer_tax_id", "incoterm_place", "payment_terms", "delivery_terms",
            "buyer_reference", "notes", "declaration", "signatory", "status", "version")
    data = {k: record.get(k, "") for k in keys}
    data.update(customer=source["customer"], order_number=source.get("number", ""), incoterm=source["incoterm"],
                total_usd=source["total_usd"], currency="USD")
    data["items"] = [{**{k: item[k] for k in ("product_name", "quantity", "unit", "unit_price", "line_total")},
                       "origin_country": record["customs"][i]["origin_country"], "hs_code": record["customs"][i]["hs_code"]}
                      for i, item in enumerate(source["items"])]
    if record["delivery_same_as_buyer"]:
        data.update(ship_to_name=data["customer"], ship_to_address=data["buyer_address"], ship_to_country=data["buyer_country"])
    else:
        data.update({k: record[k] for k in ("ship_to_name", "ship_to_address", "ship_to_country")})
    return data


def check_text(value):
    if isinstance(value, dict):
        for item in value.values(): check_text(item)
    elif isinstance(value, list):
        for item in value: check_text(item)
    elif isinstance(value, str):
        glyphs = pdfmetrics.getFont("Invoice").face.charToGlyph
        if any((ord(c) < 32 and c != "\n") or ord(c) == 127 or (c != "\n" and ord(c) not in glyphs) for c in value):
            raise InvoiceRenderingError("O PDF contém caracteres não suportados. Revise a grafia em alfabeto latino antes de aprovar.")


def draw_logo(canvas, x, y, width=145):
    bx, by, bw, bh = LOGO["viewbox"]
    scale = width / bw
    canvas.saveState(); canvas.translate(x, y + bh*scale); canvas.scale(scale, -scale); canvas.translate(-bx, -by)
    for shape in LOGO["paths"]:
        p = canvas.beginPath()
        for op in shape["ops"]:
            {"M": p.moveTo, "L": p.lineTo, "C": p.curveTo, "Z": p.close}[op[0]](*op[1:])
        canvas.setFillColor(colors.HexColor(shape["fill"])); canvas.drawPath(p, stroke=0, fill=1, fillMode=1)
    canvas.restoreState()


def precise(value, minimum=0):
    text=format(Decimal(str(value)), "f")
    if "." in text:
        text=text.rstrip("0").rstrip(".")
    if minimum:
        whole, _, fraction=text.partition(".")
        text=whole+"."+fraction.ljust(minimum,"0")
    return text

def render_invoice(record):
    data = public_invoice(record)
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
    parties = Table([[block("SELLER / EXPORTER", [data["seller_name"], data["seller_address"], data["seller_country"], "Tax ID: " + (data["seller_tax_id"] or "Not provided")]),
                      block("BUYER", [data["customer"], data["buyer_address"], data["buyer_country"], "Tax ID: " + (data["buyer_tax_id"] or "Not provided")])]], colWidths=[WIDTH/2]*2)
    parties.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F3F6FA")),("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#DDE5EF")),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    story.extend([parties, Spacer(1,14), p("SHIP TO", label), p(data["ship_to_name"]), p(data["ship_to_address"]), p(data["ship_to_country"]), Spacer(1,12)])
    meta = f"Incoterm: {data['incoterm']} - {data['incoterm_place'] or 'Not provided'}\nBuyer reference: {data['buyer_reference'] or 'Not provided'}\nOrder reference: {data['order_number'] or 'Not provided'}\nCurrency: USD"
    story.extend([p(meta), Spacer(1,14)])
    rows = [[p(t,label) for t in ("GOODS / ORIGIN / HS", "QUANTITY", "UNIT USD", "AMOUNT USD")]]
    for item in data["items"]:
        desc=f"{item['product_name']}\nOrigin: {item['origin_country'] or 'Not provided'}\nHS/NCM: {item['hs_code'] or 'Not provided'}"
        rows.append([p(desc),p(f"{precise(item['quantity'])} {item['unit']}", right),p(precise(item["unit_price"],2),right),p(f"{item['line_total']:,.2f}",right)])
    table = Table(rows, colWidths=[WIDTH*.49,WIDTH*.17,WIDTH*.17,WIDTH*.17], repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EBF0F8")),("LINEBELOW",(0,0),(-1,0),1,BLUE),("LINEBELOW",(0,1),(-1,-1),0.3,colors.HexColor("#DDE5EF")),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story.extend([table, Spacer(1,12), p(f"TOTAL USD  {data['total_usd']:,.2f}", ParagraphStyle("total",parent=right,fontName="InvoiceBold",fontSize=13,leading=18,textColor=BLUE)), Spacer(1,18)])
    for title, key in (("PAYMENT TERMS","payment_terms"),("DELIVERY TERMS","delivery_terms"),("COMMERCIAL NOTES","notes"),("DECLARATION","declaration")):
        if data[key]: story.extend([KeepTogether([p(title,label),p(data[key])]),Spacer(1,12)])
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
        title=p("COMMERCIAL INVOICE",ParagraphStyle("title2",parent=right,fontName="InvoiceBold",fontSize=14,leading=18,textColor=BLUE));w,h=title.wrap(300,40);title.drawOn(canvas,A4[0]-342,A4[1]-44-h)
        header=p(f"{data['reference']} | {data['issue_date']}",right);w,h=header.wrap(300,55);header.drawOn(canvas,A4[0]-342,A4[1]-68-h)
        canvas.setFillColor(LIME);canvas.rect(42,A4[1]-105,WIDTH,3,fill=1,stroke=0)
        footer=p(f"{data['reference']} | {data['status'].upper()} | Revision {data['version']} | Page {doc.page}",small);w,h=footer.wrap(WIDTH,35);footer.drawOn(canvas,42,26)
        canvas.restoreState()
    doc=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=122,bottomMargin=52,
                          title="Commercial Invoice "+data["reference"],author="IBIAG",invariant=1,pageCompression=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)
    result=buffer.getvalue()
    if len(result)>2*1024*1024: raise InvoiceRenderingError("O PDF excede o limite de tamanho.")
    return result
