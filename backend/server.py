from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ================== MODELS ==================
class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str  # acai, acerola, juices, coconut, nuts
    hs_code: str = ""
    description_pt: str = ""
    description_en: str = ""
    moq: str = ""
    packaging: str = ""
    certifications: List[str] = []
    specs: str = ""
    price_range: str = ""
    image_url: str = ""
    created_at: str = Field(default_factory=now_iso)


class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company: str
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    country_code: str = ""  # ISO 2 letter
    industry: str = "beverage"  # beverage, cosmetics, food_service, distributor
    stage: str = "new_lead"  # new_lead, initial_contact, sample_sent, negotiation, closed_won, closed_lost
    interested_products: List[str] = []
    deal_value: float = 0.0
    notes: str = ""
    source: str = "manual"  # manual, trade_data
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class LeadStageUpdate(BaseModel):
    stage: str


class Interaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    type: str  # email, call, whatsapp, meeting, sample
    subject: str = ""
    content: str = ""
    created_at: str = Field(default_factory=now_iso)


class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: Optional[str] = None
    title: str
    description: str = ""
    due_date: str = ""
    completed: bool = False
    created_at: str = Field(default_factory=now_iso)


class MessageTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name_pt: str
    name_en: str
    category: str  # intro, follow_up, sample, quotation
    language: str  # pt or en
    subject: str = ""
    body: str
    created_at: str = Field(default_factory=now_iso)


class TradeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    importer_company: str
    importer_country: str
    country_code: str
    hs_code: str
    product_description: str
    volume_kg: float
    value_usd: float
    exporter_country: str = "Brazil"
    industry_segment: str = "food_service"
    last_shipment_date: str
    contact_hint: str = ""


# ================== PRODUCTS ==================
@api_router.get("/products", response_model=List[Product])
async def list_products(category: Optional[str] = None):
    query = {"category": category} if category else {}
    docs = await db.products.find(query, {"_id": 0}).to_list(500)
    return docs


@api_router.post("/products", response_model=Product)
async def create_product(p: Product):
    await db.products.insert_one(p.model_dump())
    return p


@api_router.delete("/products/{pid}")
async def delete_product(pid: str):
    r = await db.products.delete_one({"id": pid})
    return {"deleted": r.deleted_count}


# ================== LEADS ==================
@api_router.get("/leads", response_model=List[Lead])
async def list_leads(stage: Optional[str] = None, industry: Optional[str] = None):
    q = {}
    if stage: q["stage"] = stage
    if industry: q["industry"] = industry
    docs = await db.leads.find(q, {"_id": 0}).to_list(1000)
    return docs


@api_router.post("/leads", response_model=Lead)
async def create_lead(lead: Lead):
    await db.leads.insert_one(lead.model_dump())
    return lead


@api_router.get("/leads/{lid}", response_model=Lead)
async def get_lead(lid: str):
    doc = await db.leads.find_one({"id": lid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Lead not found")
    return doc


@api_router.patch("/leads/{lid}/stage", response_model=Lead)
async def update_lead_stage(lid: str, upd: LeadStageUpdate):
    await db.leads.update_one({"id": lid}, {"$set": {"stage": upd.stage, "updated_at": now_iso()}})
    doc = await db.leads.find_one({"id": lid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Lead not found")
    return doc


@api_router.put("/leads/{lid}", response_model=Lead)
async def update_lead(lid: str, lead: Lead):
    lead.id = lid
    lead.updated_at = now_iso()
    await db.leads.replace_one({"id": lid}, lead.model_dump())
    return lead


@api_router.delete("/leads/{lid}")
async def delete_lead(lid: str):
    r = await db.leads.delete_one({"id": lid})
    await db.interactions.delete_many({"lead_id": lid})
    await db.tasks.delete_many({"lead_id": lid})
    return {"deleted": r.deleted_count}


# ================== INTERACTIONS ==================
@api_router.get("/interactions", response_model=List[Interaction])
async def list_interactions(lead_id: Optional[str] = None):
    q = {"lead_id": lead_id} if lead_id else {}
    docs = await db.interactions.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.post("/interactions", response_model=Interaction)
async def create_interaction(i: Interaction):
    await db.interactions.insert_one(i.model_dump())
    return i


# ================== TASKS ==================
@api_router.get("/tasks", response_model=List[Task])
async def list_tasks(completed: Optional[bool] = None):
    q = {}
    if completed is not None:
        q["completed"] = completed
    docs = await db.tasks.find(q, {"_id": 0}).to_list(500)
    return docs


@api_router.post("/tasks", response_model=Task)
async def create_task(t: Task):
    await db.tasks.insert_one(t.model_dump())
    return t


@api_router.patch("/tasks/{tid}/toggle", response_model=Task)
async def toggle_task(tid: str):
    doc = await db.tasks.find_one({"id": tid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Task not found")
    new_val = not doc["completed"]
    await db.tasks.update_one({"id": tid}, {"$set": {"completed": new_val}})
    doc["completed"] = new_val
    return doc


@api_router.delete("/tasks/{tid}")
async def delete_task(tid: str):
    r = await db.tasks.delete_one({"id": tid})
    return {"deleted": r.deleted_count}


# ================== TEMPLATES ==================
@api_router.get("/templates", response_model=List[MessageTemplate])
async def list_templates(language: Optional[str] = None, category: Optional[str] = None):
    q = {}
    if language: q["language"] = language
    if category: q["category"] = category
    docs = await db.templates.find(q, {"_id": 0}).to_list(200)
    return docs


@api_router.post("/templates", response_model=MessageTemplate)
async def create_template(t: MessageTemplate):
    await db.templates.insert_one(t.model_dump())
    return t


@api_router.delete("/templates/{tid}")
async def delete_template(tid: str):
    r = await db.templates.delete_one({"id": tid})
    return {"deleted": r.deleted_count}


# ================== TRADE DATA ==================
@api_router.get("/trade-data", response_model=List[TradeRecord])
async def list_trade_data(
    country: Optional[str] = None,
    hs_code: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
):
    q = {}
    if country: q["country_code"] = country
    if hs_code: q["hs_code"] = hs_code
    if industry: q["industry_segment"] = industry
    if search:
        q["$or"] = [
            {"importer_company": {"$regex": search, "$options": "i"}},
            {"product_description": {"$regex": search, "$options": "i"}},
        ]
    docs = await db.trade_data.find(q, {"_id": 0}).to_list(500)
    return docs


@api_router.post("/trade-data/{tid}/add-to-crm", response_model=Lead)
async def add_trade_to_crm(tid: str):
    tr = await db.trade_data.find_one({"id": tid}, {"_id": 0})
    if not tr:
        raise HTTPException(404, "Trade record not found")
    existing = await db.leads.find_one({"company": tr["importer_company"]}, {"_id": 0})
    if existing:
        return existing
    lead = Lead(
        company=tr["importer_company"],
        country=tr["importer_country"],
        country_code=tr["country_code"],
        industry=tr["industry_segment"],
        stage="new_lead",
        notes=f"Imported from Trade Intelligence. HS {tr['hs_code']}. Vol: {tr['volume_kg']:.0f} kg, USD {tr['value_usd']:.0f}. Last: {tr['last_shipment_date']}",
        source="trade_data",
        deal_value=tr["value_usd"],
    )
    await db.leads.insert_one(lead.model_dump())
    return lead


# ================== DASHBOARD ==================
@api_router.get("/dashboard/stats")
async def dashboard_stats():
    total_leads = await db.leads.count_documents({})
    active = await db.leads.count_documents({"stage": {"$nin": ["closed_won", "closed_lost"]}})
    won = await db.leads.count_documents({"stage": "closed_won"})
    lost = await db.leads.count_documents({"stage": "closed_lost"})
    samples = await db.leads.count_documents({"stage": "sample_sent"})
    conversion_rate = round((won / (won + lost)) * 100, 1) if (won + lost) > 0 else 0.0

    pipeline_pipeline = [
        {"$match": {"stage": {"$nin": ["closed_won", "closed_lost"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$deal_value"}}}
    ]
    pipeline_cur = db.leads.aggregate(pipeline_pipeline)
    pipeline_value = 0.0
    async for doc in pipeline_cur:
        pipeline_value = doc.get("total", 0.0)

    stage_pipeline = [{"$group": {"_id": "$stage", "count": {"$sum": 1}}}]
    stage_cur = db.leads.aggregate(stage_pipeline)
    by_stage = {}
    async for d in stage_cur:
        by_stage[d["_id"]] = d["count"]

    industry_cur = db.leads.aggregate([{"$group": {"_id": "$industry", "count": {"$sum": 1}}}])
    by_industry = {}
    async for d in industry_cur:
        by_industry[d["_id"]] = d["count"]

    return {
        "total_leads": total_leads,
        "active_leads": active,
        "samples_sent": samples,
        "won": won,
        "lost": lost,
        "conversion_rate": conversion_rate,
        "pipeline_value": pipeline_value,
        "by_stage": by_stage,
        "by_industry": by_industry,
    }


# ================== SEED ==================
@api_router.post("/seed")
async def seed_data():
    # Only seed if empty
    products_count = await db.products.count_documents({})
    if products_count == 0:
        products = [
            Product(name="Organic Açaí Freeze-Dried Powder", category="acai",
                    hs_code="2008.99.90",
                    description_pt="Pó de açaí orgânico liofilizado, colheita amazônica sustentável. Alto teor de antocianinas.",
                    description_en="Organic freeze-dried Açaí powder from sustainable Amazonian harvest. High anthocyanin content.",
                    moq="500 kg", packaging="Aluminum-lined bags, 10-25 kg / Bulk bags",
                    certifications=["USDA Organic", "EU Organic", "Kosher", "Halal", "FSSC 22000"],
                    specs="Purity: 100% | Moisture: <5% | Anthocyanins: >1,500 mg/100g",
                    price_range="USD 28-42 / kg FOB Santos",
                    image_url="https://images.unsplash.com/photo-1698610641100-565cc749fc60?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwxfHxhY2FpJTIwZnJ1aXR8ZW58MHx8fHwxNzkwNjc1OTY4fDA&ixlib=rb-4.1.0&q=85"),
            Product(name="Açaí Pulp Puree Industrial Grade", category="acai",
                    hs_code="2008.99.90",
                    description_pt="Polpa de açaí puro industrial. Ideal para bebidas, sorvetes e formulações premium.",
                    description_en="Pure industrial Açaí puree. Ideal for beverages, ice cream, and premium formulations.",
                    moq="1 Metric Ton", packaging="Aseptic Drums 200 L / Flexitanks 22 MT",
                    certifications=["FSSC 22000", "Kosher", "Halal"],
                    specs="Brix: 14° | Fat: 5% | Pasteurized HTST",
                    price_range="USD 4.20-5.80 / kg CIF",
                    image_url="https://images.unsplash.com/photo-1709139068234-f83a548f3bec?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHw0fHxhY2FpJTIwZnJ1aXR8ZW58MHx8fHwxNzkwNjc1OTY4fDA&ixlib=rb-4.1.0&q=85"),
            Product(name="Organic Acerola Powder 17% Vit-C", category="acerola",
                    hs_code="2106.90.90",
                    description_pt="Pó de acerola natural com alto teor de Vitamina C. Fonte natural de antioxidantes.",
                    description_en="Natural Acerola powder with high Vitamin C content. Natural antioxidant source.",
                    moq="200 kg", packaging="Aluminum bags 20 kg / Fiber drums",
                    certifications=["USDA Organic", "Kosher", "Halal", "Non-GMO"],
                    specs="Vit-C: 17% min | Moisture: <5% | Free-flowing spray-dried",
                    price_range="USD 22-30 / kg FOB",
                    image_url="https://images.unsplash.com/photo-1610441009633-b6ca9c6d4be2?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwzfHxhY2FpJTIwZnJ1aXR8ZW58MHx8fHwxNzkwNjc1OTY4fDA&ixlib=rb-4.1.0&q=85"),
            Product(name="Passion Fruit Puree Concentrate", category="juices",
                    hs_code="2009.89.90",
                    description_pt="Concentrado de maracujá amarelo. Aroma e sabor tropical intenso.",
                    description_en="Yellow passion fruit puree concentrate. Intense tropical aroma and flavor.",
                    moq="1 MT", packaging="Aseptic bags 200 kg / Flexitanks",
                    certifications=["FSSC 22000", "Kosher", "SGF-IRMA"],
                    specs="Brix: 14° / 50° concentrate | Acidity: 3.8% | Frozen or Aseptic",
                    price_range="USD 3.50-6.20 / kg CIF Hamburg",
                    image_url="https://images.pexels.com/photos/17612801/pexels-photo-17612801.jpeg"),
            Product(name="Pure Coconut Water NFC", category="coconut",
                    hs_code="2009.89.90",
                    description_pt="Água de coco pura NFC (Not From Concentrate), embalagem asséptica.",
                    description_en="Pure coconut water NFC (Not From Concentrate), aseptic packaging.",
                    moq="20 ft FCL (18,000 L)", packaging="Aseptic BIB 220 L / Tetra 200 mL",
                    certifications=["FSSC 22000", "Halal", "Kosher"],
                    specs="Brix: 5.0-5.5° | pH: 5.0-5.4 | Pasteurized",
                    price_range="USD 0.85-1.20 / L FOB",
                    image_url="https://images.unsplash.com/photo-1628692945318-f44a3c346afb?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHw0fHxjb2NvbnV0JTIwd2F0ZXJ8ZW58MHx8fHwxNzkwNjc1OTY4fDA&ixlib=rb-4.1.0&q=85"),
            Product(name="Green Coconut Concentrate 5X", category="coconut",
                    hs_code="2009.89.90",
                    description_pt="Concentrado de água de coco 5X para reconstituição em bebidas.",
                    description_en="5X concentrated coconut water for beverage reconstitution.",
                    moq="500 kg", packaging="Frozen drums 200 kg",
                    certifications=["FSSC 22000", "Halal"],
                    specs="Brix: 25° | Frozen at -18°C",
                    price_range="USD 2.80-3.90 / kg FOB",
                    image_url="https://images.unsplash.com/photo-1537191072641-5e19cc173c6a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwxfHxjb2NvbnV0JTIwd2F0ZXJ8ZW58MHx8fHwxNzkwNjc1OTY4fDA&ixlib=rb-4.1.0&q=85"),
            Product(name="Brazil Nuts Whole Premium Export", category="nuts",
                    hs_code="0801.22.00",
                    description_pt="Castanha-do-Pará inteira grau exportação premium. Colheita silvestre da Amazônia.",
                    description_en="Whole premium export-grade Brazil nuts. Wild-harvested from the Amazon.",
                    moq="1 MT", packaging="Vacuum bags 25 kg in cartons",
                    certifications=["USDA Organic", "Rainforest Alliance", "Kosher", "Fair Trade"],
                    specs="Sizes: L/M/S | Moisture: <5% | Aflatoxin: EU compliant",
                    price_range="USD 8.50-13.00 / kg FOB Manaus",
                    image_url="https://images.unsplash.com/photo-1723466998040-78d7e2ef6d72?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzV8MHwxfHNlYXJjaHw0fHxjYXNoZXclMjBudXRzfGVufDB8fHx8MTc5MDY3NTkyfDA&ixlib=rb-4.1.0&q=85"),
            Product(name="Cashew Nuts W240 Whole", category="nuts",
                    hs_code="0801.32.00",
                    description_pt="Castanha de caju W240 inteira. Padrão internacional de exportação.",
                    description_en="Cashew nuts W240 whole. International export standard.",
                    moq="1 MT", packaging="Vacuum-sealed tins 22.68 kg",
                    certifications=["FSSC 22000", "BRC", "Kosher", "Halal"],
                    specs="Grade: W240 | Moisture: <5% | Broken: <5%",
                    price_range="USD 6.80-9.50 / kg FOB",
                    image_url="https://images.unsplash.com/photo-1615485925873-7ecbbe90a866?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzV8MHwxfHNlYXJjaHwxfHxjYXNoZXclMjBudXRzfGVufDB8fHx8MTc5MDY3NTkyfDA&ixlib=rb-4.1.0&q=85"),
        ]
        await db.products.insert_many([p.model_dump() for p in products])

    templates_count = await db.templates.count_documents({})
    if templates_count == 0:
        templates = [
            MessageTemplate(name_pt="Email Introdução", name_en="Introduction Email", category="intro", language="en",
                subject="Premium Brazilian Ingredients — Introduction from [Your Company]",
                body="Dear [Contact Name],\n\nI hope this message finds you well. My name is [Your Name] and I represent [Your Company], a Brazilian exporter of premium tropical ingredients including Açaí, Acerola, Coconut Water, Tropical Fruit Purees, and Brazil Nuts.\n\nWe noticed that [Client Company] operates in the [Industry] segment and thought our high-purity, certified (USDA Organic / FSSC 22000 / Kosher) product line could add value to your formulations.\n\nWould you be open to a 15-min introduction call this week? I can also share our full technical catalog and COA on request.\n\nBest regards,\n[Your Name]\n[Your Company] | Brazil"),
            MessageTemplate(name_pt="Email Introdução", name_en="Introduction Email", category="intro", language="pt",
                subject="Ingredientes Brasileiros Premium — Apresentação da [Sua Empresa]",
                body="Prezado(a) [Nome do Contato],\n\nEspero que esteja bem. Meu nome é [Seu Nome] e represento a [Sua Empresa], exportadora brasileira de ingredientes tropicais premium: Açaí, Acerola, Água de Coco, Polpas de Frutas Tropicais e Castanhas do Brasil.\n\nNotamos que a [Empresa do Cliente] atua no segmento de [Indústria] e acreditamos que nossa linha certificada (USDA Organic / FSSC 22000 / Kosher) pode agregar valor a suas formulações.\n\nPodemos agendar uma call de 15 minutos esta semana? Posso enviar nosso catálogo técnico e COA sob demanda.\n\nAtenciosamente,\n[Seu Nome]\n[Sua Empresa] | Brasil"),
            MessageTemplate(name_pt="Envio de Amostra", name_en="Sample Dispatch", category="sample", language="en",
                subject="Your Sample from Brazil — Tracking Info Enclosed",
                body="Hi [Contact Name],\n\nGreat news! Your sample of [Product] (net weight [X] g) has been dispatched from Brazil today via [Carrier]. Tracking number: [XXXXXX].\n\nEstimated delivery: [Date]. COA and technical specification sheet attached.\n\nOnce received, we'd love to schedule a follow-up call to discuss your application and next steps toward a commercial order.\n\nBest regards,\n[Your Name]"),
            MessageTemplate(name_pt="Envio de Amostra", name_en="Sample Dispatch", category="sample", language="pt",
                subject="Sua Amostra do Brasil — Rastreio em Anexo",
                body="Olá [Nome do Contato],\n\nBoa notícia! Sua amostra de [Produto] (peso líquido [X] g) foi despachada do Brasil hoje via [Transportadora]. Rastreio: [XXXXXX].\n\nEntrega prevista: [Data]. COA e ficha técnica em anexo.\n\nApós o recebimento, gostaria de agendar uma call de follow-up para discutir a aplicação e próximos passos rumo a um pedido comercial.\n\nAbraço,\n[Seu Nome]"),
            MessageTemplate(name_pt="Follow-up", name_en="Follow-up", category="follow_up", language="en",
                subject="Following Up — Brazilian [Product] Proposal",
                body="Hi [Contact Name],\n\nJust checking in on the proposal we shared for [Product] on [Date]. I'd love to hear your thoughts and answer any technical or commercial questions.\n\nIf helpful, I can send additional documentation (COA, allergen statement, sustainability report) or arrange a call with our QA team.\n\nLooking forward to hearing from you.\n\nBest,\n[Your Name]"),
            MessageTemplate(name_pt="Follow-up", name_en="Follow-up", category="follow_up", language="pt",
                subject="Retomando Contato — Proposta [Produto] Brasil",
                body="Olá [Nome do Contato],\n\nEstou retomando contato sobre a proposta que enviamos para [Produto] em [Data]. Gostaria de saber suas impressões e esclarecer qualquer dúvida técnica ou comercial.\n\nCaso ajude, posso enviar documentação adicional (COA, declaração de alergênicos, relatório de sustentabilidade) ou marcar uma call com nossa equipe de QA.\n\nAguardo seu retorno.\n\nAbraço,\n[Seu Nome]"),
            MessageTemplate(name_pt="Cotação CIF/FOB", name_en="CIF/FOB Quotation", category="quotation", language="en",
                subject="Commercial Quotation — [Product] — Ref [Number]",
                body="Dear [Contact Name],\n\nAs requested, please find below our commercial quotation:\n\n• Product: [Product Name]\n• HS Code: [XXXX.XX.XX]\n• Quantity: [X] MT\n• Packaging: [Type]\n• Price: USD [X.XX] / kg [FOB Santos / CIF Destination]\n• Incoterms: [FOB / CIF / CFR]\n• Payment: [Terms — LC at sight / 30% advance + 70% BL / Open Account]\n• Delivery: [X] weeks after order confirmation\n• Validity: [30 days]\n\nCertifications & COA attached. Ready to answer any questions.\n\nRegards,\n[Your Name]"),
            MessageTemplate(name_pt="Cotação CIF/FOB", name_en="CIF/FOB Quotation", category="quotation", language="pt",
                subject="Cotação Comercial — [Produto] — Ref [Número]",
                body="Prezado(a) [Nome do Contato],\n\nConforme solicitado, segue nossa cotação comercial:\n\n• Produto: [Nome do Produto]\n• NCM/HS: [XXXX.XX.XX]\n• Quantidade: [X] TM\n• Embalagem: [Tipo]\n• Preço: USD [X,XX] / kg [FOB Santos / CIF Destino]\n• Incoterms: [FOB / CIF / CFR]\n• Pagamento: [Condições — LC à vista / 30% adiant. + 70% BL / Open Account]\n• Prazo de entrega: [X] semanas após confirmação\n• Validade: [30 dias]\n\nCertificações e COA em anexo. À disposição para dúvidas.\n\nAtenciosamente,\n[Seu Nome]"),
        ]
        await db.templates.insert_many([t.model_dump() for t in templates])

    trade_count = await db.trade_data.count_documents({})
    if trade_count == 0:
        trade_records = [
            TradeRecord(importer_company="Green Nordic Beverages AB", importer_country="Sweden", country_code="SE",
                        hs_code="2008.99.90", product_description="Açaí Puree Aseptic",
                        volume_kg=48000, value_usd=192000, industry_segment="beverage",
                        last_shipment_date="2025-11-14", contact_hint="procurement@greenordic.example"),
            TradeRecord(importer_company="Pura Vida Organics LLC", importer_country="United States", country_code="US",
                        hs_code="2008.99.90", product_description="Freeze-dried Açaí Powder Organic",
                        volume_kg=12000, value_usd=384000, industry_segment="food_service",
                        last_shipment_date="2025-12-02", contact_hint="sourcing@puravida.example"),
            TradeRecord(importer_company="Bio Cosmétique Paris SAS", importer_country="France", country_code="FR",
                        hs_code="2106.90.90", product_description="Acerola Powder 17% Vit C",
                        volume_kg=6000, value_usd=156000, industry_segment="cosmetics",
                        last_shipment_date="2026-01-08", contact_hint="achats@biocosmetique.example"),
            TradeRecord(importer_company="Deutsche Naturkraft GmbH", importer_country="Germany", country_code="DE",
                        hs_code="2106.90.90", product_description="Organic Acerola Extract 25%",
                        volume_kg=3500, value_usd=98000, industry_segment="cosmetics",
                        last_shipment_date="2025-12-20", contact_hint="einkauf@naturkraft.example"),
            TradeRecord(importer_company="Sakura Wellness Co Ltd", importer_country="Japan", country_code="JP",
                        hs_code="2009.89.90", product_description="Passion Fruit Puree Concentrate",
                        volume_kg=22000, value_usd=110000, industry_segment="beverage",
                        last_shipment_date="2025-11-28", contact_hint="import@sakurawellness.example"),
            TradeRecord(importer_company="Emirates Tropical Trading LLC", importer_country="UAE", country_code="AE",
                        hs_code="2009.89.90", product_description="Coconut Water NFC Aseptic",
                        volume_kg=180000, value_usd=162000, industry_segment="distributor",
                        last_shipment_date="2025-12-10", contact_hint="trade@emiratestropical.example"),
            TradeRecord(importer_company="Nordic Nut House A/S", importer_country="Denmark", country_code="DK",
                        hs_code="0801.22.00", product_description="Brazil Nuts Whole Premium",
                        volume_kg=25000, value_usd=275000, industry_segment="food_service",
                        last_shipment_date="2026-01-15", contact_hint="import@nordicnut.example"),
            TradeRecord(importer_company="Umi Foods UK Ltd", importer_country="United Kingdom", country_code="GB",
                        hs_code="0801.32.00", product_description="Cashew Nuts W240",
                        volume_kg=40000, value_usd=320000, industry_segment="distributor",
                        last_shipment_date="2025-12-18", contact_hint="buying@umifoods.example"),
            TradeRecord(importer_company="Amazonia Cosmetics Korea", importer_country="South Korea", country_code="KR",
                        hs_code="2008.99.90", product_description="Açaí Oil Cold Pressed",
                        volume_kg=1500, value_usd=68000, industry_segment="cosmetics",
                        last_shipment_date="2026-01-22", contact_hint="rd@amazoniakr.example"),
            TradeRecord(importer_company="Milano Beverage Innovation Srl", importer_country="Italy", country_code="IT",
                        hs_code="2009.89.90", product_description="Guaraná Extract Powder",
                        volume_kg=4200, value_usd=54600, industry_segment="beverage",
                        last_shipment_date="2025-11-05", contact_hint="rd@milanobev.example"),
            TradeRecord(importer_company="Toronto Health Foods Co", importer_country="Canada", country_code="CA",
                        hs_code="2008.99.90", product_description="Açaí Puree Frozen",
                        volume_kg=30000, value_usd=126000, industry_segment="food_service",
                        last_shipment_date="2025-12-27", contact_hint="purchasing@torontohf.example"),
            TradeRecord(importer_company="Sydney Organic Distributors Pty", importer_country="Australia", country_code="AU",
                        hs_code="0801.22.00", product_description="Brazil Nuts Organic",
                        volume_kg=9500, value_usd=118750, industry_segment="distributor",
                        last_shipment_date="2026-01-30", contact_hint="orders@sydneyorganic.example"),
        ]
        await db.trade_data.insert_many([t.model_dump() for t in trade_records])

    leads_count = await db.leads.count_documents({})
    if leads_count == 0:
        leads = [
            Lead(company="Green Nordic Beverages AB", contact_name="Erik Lindqvist", email="erik@greenordic.example",
                 country="Sweden", country_code="SE", industry="beverage", stage="negotiation",
                 deal_value=45000, notes="Interested in Açaí Puree aseptic 200L drums. LC 30/60 days."),
            Lead(company="Bio Cosmétique Paris SAS", contact_name="Sophie Martin", email="sophie@biocosmetique.example",
                 country="France", country_code="FR", industry="cosmetics", stage="sample_sent",
                 deal_value=28000, notes="Sample of Acerola powder 500g sent 15-Jan. Waiting feedback."),
            Lead(company="Pura Vida Organics LLC", contact_name="Michael Chen", email="mike@puravida.example",
                 country="United States", country_code="US", industry="food_service", stage="initial_contact",
                 deal_value=120000, notes="Large potential order for Açaí freeze-dried powder USDA Organic."),
        ]
        await db.leads.insert_many([l.model_dump() for l in leads])

    return {"seeded": True,
            "products": await db.products.count_documents({}),
            "templates": await db.templates.count_documents({}),
            "trade_data": await db.trade_data.count_documents({}),
            "leads": await db.leads.count_documents({})}


@api_router.get("/")
async def root():
    return {"message": "AgroBrasil Export CRM API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    await seed_data()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
