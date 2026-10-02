from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os, logging, uuid, bcrypt, jwt, requests, io, re, unicodedata
import pandas as pd
from comexstat_client import ncm_search, general as comex_general
from comexstat_market import normalize_markets
from buyer_discovery import discover_buyers, discover_decision_maker
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

# ----- Config -----
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="ibiag_files")

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
APP_NAME = os.environ.get("APP_NAME", "agrobrasil")
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
STORAGE_PROVIDER = os.environ.get("STORAGE_PROVIDER", "gridfs").strip().lower()
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_REGION = os.environ.get("S3_REGION", "")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
s3_client = None

def _s3():
    global s3_client
    if s3_client: return s3_client
    if not S3_BUCKET or not S3_ACCESS_KEY or not S3_SECRET_KEY: return None
    import boto3
    s3_client = boto3.client("s3", region_name=S3_REGION or None, endpoint_url=S3_ENDPOINT or None,
        aws_access_key_id=S3_ACCESS_KEY, aws_secret_access_key=S3_SECRET_KEY)
    return s3_client

def init_storage(force=False):
    return STORAGE_PROVIDER

async def put_object(path: str, data: bytes, content_type: str) -> dict:
    if STORAGE_PROVIDER == "gridfs":
        old = await db["ibiag_files.files"].find_one({"filename": path})
        if old: await gridfs.delete(old["_id"])
        await gridfs.upload_from_stream(path, data, metadata={"content_type": content_type})
        return {"path": path, "size": len(data), "content_type": content_type}
    if STORAGE_PROVIDER == "s3":
        c = _s3()
        if not c: raise HTTPException(500, "S3 storage is not configured")
        c.put_object(Bucket=S3_BUCKET, Key=path, Body=data, ContentType=content_type)
        return {"path": path, "size": len(data), "content_type": content_type}
    raise HTTPException(500, "Storage provider is not configured")

async def get_object(path: str):
    if STORAGE_PROVIDER == "gridfs":
        try:
            stream = await gridfs.open_download_stream_by_name(path)
            data = await stream.read()
            return data, (stream.metadata or {}).get("content_type", "application/octet-stream")
        except Exception:
            raise HTTPException(404, "Arquivo não encontrado")
    if STORAGE_PROVIDER == "s3":
        c = _s3()
        if not c: raise HTTPException(500, "S3 storage is not configured")
        obj = c.get_object(Bucket=S3_BUCKET, Key=path)
        return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")
    raise HTTPException(500, "Storage provider is not configured")

async def delete_object(path: str):
    if not path:
        return
    if STORAGE_PROVIDER == "gridfs":
        old = await db["ibiag_files.files"].find_one({"filename": path})
        if old:
            await gridfs.delete(old["_id"])
        return
    if STORAGE_PROVIDER == "s3":
        client = _s3()
        if client:
            client.delete_object(Bucket=S3_BUCKET, Key=path)
        return

# ----- Auth helpers -----
def hash_pw(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_pw(pw, h): 
    try: return bcrypt.checkpw(pw.encode(), h.encode())
    except Exception: return False

def create_token(uid, email):
    return jwt.encode({"sub": uid, "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=7)},
                      JWT_SECRET, algorithm=JWT_ALG)

async def get_current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

def now_iso(): return datetime.now(timezone.utc).isoformat()

# ----- App -----
app = FastAPI(title="IBIAG", version="1.0.0")

# Production CORS. Keep this explicit in production; "*" is only a development fallback.
cors_origins = [x.strip() for x in os.environ.get("CORS_ORIGINS", "").split(",") if x.strip()]
if not cors_origins:
    cors_origins = ["http://localhost:3000", "http://localhost:80"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")

# ----- Models -----
class LoginBody(BaseModel):
    email: EmailStr
    password: str

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    name: str = ""

class UserCreateBody(BaseModel):
    email: EmailStr
    password: str
    name: str = ""
    role: str = "user"

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str = "acai"
    hs_code: str = ""
    description_pt: str = ""
    description_en: str = ""
    moq: str = ""
    packaging: str = ""
    certifications: List[str] = []
    specs: str = ""
    price_range: str = ""
    image_url: str = ""
    sku: str = ""
    stock: float = 0
    origin: str = ""
    ncm: str = ""
    technical_name: str = ""
    available_capacity: str = ""
    incoterm: str = ""
    lead_time: str = ""
    payment_terms: str = ""
    current_customers: str = ""
    target_markets: str = ""
    price_history_notes: str = ""
    unit: str = "kg"
    created_at: str = Field(default_factory=now_iso)

class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company: str
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    linkedin: str = ""
    country: str = ""
    country_code: str = ""
    industry: str = "beverage"
    stage: str = "new_lead"
    interested_products: List[str] = []
    product_interest: str = ""
    decision_maker: str = ""
    decision_maker_title: str = ""
    decision_maker_email: str = ""
    decision_maker_phone: str = ""
    current_supplier: str = ""
    priority: str = "normal"
    source_url: str = ""
    deal_value: float = 0.0
    notes: str = ""
    source: str = "manual"
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class StageUpd(BaseModel): stage: str

class Interaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    type: str = "email"
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

class Supplier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    cnpj: str = ""
    contact: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    products: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: str
    kind: str = "entrada"  # entrada ou saida
    party_name: str = ""  # fornecedor ou cliente
    party_cnpj: str = ""
    issue_date: str = ""
    total: float = 0
    description: str = ""
    file_path: str = ""
    file_name: str = ""
    created_at: str = Field(default_factory=now_iso)

class SalesOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: str = ""
    customer: str
    customer_country: str = ""
    products: str = ""
    incoterm: str = "FOB"
    total_usd: float = 0
    status: str = "draft"  # draft, confirmed, shipped, delivered, cancelled
    order_date: str = ""
    delivery_date: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)

class FinanceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = "receivable"  # receivable ou payable
    description: str
    party: str = ""
    amount: float = 0
    currency: str = "BRL"
    due_date: str = ""
    paid: bool = False
    paid_date: str = ""
    category: str = ""
    created_at: str = Field(default_factory=now_iso)

class Contract(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    kind: str = "contract"  # contract ou certification
    party: str = ""
    supplier_id: str = ""
    start_date: str = ""
    end_date: str = ""
    value: float = 0
    file_path: str = ""
    file_name: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)

class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    category: str = "general"
    file_path: str
    file_name: str
    content_type: str = ""
    size: int = 0
    tags: List[str] = []
    notes: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    product_id: str = ""
    product_name: str = ""
    created_at: str = Field(default_factory=now_iso)

class Certification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supplier_id: str
    supplier_name: str = ""
    name: str
    kind: str = "organic"  # organic ou other
    issuer: str = ""
    number: str = ""
    issue_date: str = ""
    expiry_date: str = ""
    alert_days: int = 30
    file_path: str = ""
    file_name: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)

class Purchase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supplier_id: str = ""
    supplier_name: str = ""
    product: str
    quantity: float = 0
    unit: str = "kg"
    unit_price: float = 0
    total: float = 0
    currency: str = "BRL"
    date: str = ""
    status: str = "ordered"  # ordered, received, paid, cancelled
    invoice_number: str = ""
    file_path: str = ""
    file_name: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)

class Spec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supplier_id: str
    supplier_name: str = ""
    product_name: str
    code: str = ""
    version: str = "1.0"
    description: str = ""
    original_file_path: str = ""
    original_file_name: str = ""
    ibiag_file_path: str = ""
    ibiag_file_name: str = ""
    notes: str = ""
    updated_at: str = Field(default_factory=now_iso)
    created_at: str = Field(default_factory=now_iso)

class PriceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_name: str
    supplier_id: str = ""
    supplier_name: str = ""
    unit: str = "kg"
    supplier_price: float = 0  # BRL por unidade
    extra_costs: float = 0  # BRL por unidade (frete, embalagem, etc)
    extras: List[dict] = []
    taxes: List[dict] = []
    taxes_pct: float = 0
    margin_pct: float = 0
    margin_mode: str = "margin"  # margin (sobre venda) ou markup (sobre custo)
    currency: str = "BRL"
    exchange_rate: float = 5.0
    sell_price_brl: float = 0
    sell_price_usd: float = 0
    notes: str = ""
    updated_at: str = Field(default_factory=now_iso)
    created_at: str = Field(default_factory=now_iso)


class ProductOffer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str = ""
    form: str = ""
    supplier_id: str = ""
    supplier_name: str = ""
    supplier_price: float = 0
    sale_price_brl: float = 0
    sale_price_usd: float = 0
    unit: str = "kg"
    capacity: str = ""
    moq: str = ""
    ncm: str = ""
    hs_code: str = ""
    active: bool = True
    spec_document_ids: List[str] = []
    certificate_document_ids: List[str] = []
    other_document_ids: List[str] = []
    spec_ids: List[str] = []
    certification_ids: List[str] = []
    notes: str = ""
    packaging_type: str = ""
    packaging: str = ""
    palletization: str = ""
    export_price_text: str = ""
    fob_price_text: str = ""
    organic_version: str = ""
    commission: float = 0
    certifications_text: str = ""
    spec_url: str = ""
    marketing_claim: str = ""
    harvest: str = ""
    checked: str = ""
    source: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

# ============ AUTH ============
def require_admin(user):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin permission required")
    return user

@api.post("/auth/register")
async def register(body: RegisterBody):
    if os.environ.get("ALLOW_PUBLIC_REGISTRATION", "false").lower() != "true":
        raise HTTPException(403, "Public registration is disabled. Ask an administrator to create your user.")
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4())
    await db.users.insert_one({
        "id": uid, "email": email, "name": body.name or email.split("@")[0],
        "password_hash": hash_pw(body.password), "role": "user",
        "created_at": now_iso()
    })
    token = create_token(uid, email)
    return {"access_token": token, "user": {"id": uid, "email": email, "name": body.name, "role": "user"}}

@api.get("/auth/users")
async def list_users(user=Depends(get_current_user)):
    require_admin(user)
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", 1).to_list(500)

@api.post("/auth/users")
async def create_user(body: UserCreateBody, user=Depends(get_current_user)):
    require_admin(user)
    email = body.email.lower().strip()
    if body.role not in {"admin", "user"}:
        raise HTTPException(400, "Invalid role")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must have at least 8 characters")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    record = {"id": str(uuid.uuid4()), "email": email,
              "name": body.name or email.split("@")[0],
              "password_hash": hash_pw(body.password), "role": body.role,
              "created_at": now_iso()}
    await db.users.insert_one(record)
    record.pop("password_hash", None)
    return record

@api.post("/auth/login")
async def login(body: LoginBody):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_pw(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user["id"], email)
    return {"access_token": token, "user": {"id": user["id"], "email": email, "name": user.get("name", ""), "role": user.get("role", "user")}}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user

@api.post("/auth/logout")
async def logout(): return {"ok": True}

# Deployment sync: document storage cleanup enabled.
# ============ FILES / STORAGE ============
@api.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    ct = file.content_type or "application/octet-stream"
    result = await put_object(path, data, ct)
    return {"path": result["path"], "name": file.filename, "size": result.get("size", len(data)), "content_type": ct}

@api.get("/files/{full_path:path}")
async def download_file(full_path: str, user=Depends(get_current_user)):
    data, ct = await get_object(full_path)
    return Response(content=data, media_type=ct)

# ============ DOCUMENTS ============
@api.get("/documents", response_model=List[Document])
async def list_docs(category: Optional[str] = None, user=Depends(get_current_user)):
    q = {"category": category} if category else {}
    return await db.documents.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.post("/documents", response_model=Document)
async def create_doc(d: Document, user=Depends(get_current_user)):
    await db.documents.insert_one(d.model_dump())
    return d

@api.delete("/documents/{did}")
async def delete_doc(did: str, user=Depends(get_current_user)):
    doc = await db.documents.find_one({"id": did}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    path = doc.get("path") or doc.get("file_path") or ""
    r = await db.documents.delete_one({"id": did})
    if r.deleted_count and path:
        await delete_object(path)
    return {"deleted": r.deleted_count, "file_deleted": bool(path)}

# ============ SUPPLIERS ============
@api.get("/suppliers", response_model=List[Supplier])
async def list_sup(user=Depends(get_current_user)):
    return await db.suppliers.find({}, {"_id": 0}).to_list(1000)

@api.post("/suppliers", response_model=Supplier)
async def create_sup(s: Supplier, user=Depends(get_current_user)):
    await db.suppliers.insert_one(s.model_dump()); return s

@api.put("/suppliers/{sid}", response_model=Supplier)
async def upd_sup(sid: str, s: Supplier, user=Depends(get_current_user)):
    s.id = sid; await db.suppliers.replace_one({"id": sid}, s.model_dump()); return s

@api.delete("/suppliers/{sid}")
async def del_sup(sid: str, user=Depends(get_current_user)):
    r = await db.suppliers.delete_one({"id": sid}); return {"deleted": r.deleted_count}

# ============ INVOICES ============
@api.get("/invoices", response_model=List[Invoice])
async def list_inv(kind: Optional[str] = None, user=Depends(get_current_user)):
    q = {"kind": kind} if kind else {}
    return await db.invoices.find(q, {"_id": 0}).sort("issue_date", -1).to_list(1000)

@api.post("/invoices", response_model=Invoice)
async def create_inv(i: Invoice, user=Depends(get_current_user)):
    await db.invoices.insert_one(i.model_dump()); return i

@api.delete("/invoices/{iid}")
async def del_inv(iid: str, user=Depends(get_current_user)):
    r = await db.invoices.delete_one({"id": iid}); return {"deleted": r.deleted_count}

@api.post("/invoices/parse-xml")
async def parse_nfe_xml(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Parse Brazilian NF-e XML and extract main fields."""
    data = await file.read()
    try:
        text = data.decode("utf-8", errors="ignore")
        # Strip namespaces
        import re
        text_nons = re.sub(r' xmlns="[^"]+"', "", text, count=1)
        root = ET.fromstring(text_nons)
        def find_txt(el, path):
            n = el.find(path)
            return (n.text or "").strip() if n is not None and n.text else ""
        infNFe = root.find(".//infNFe") or root
        ide = infNFe.find("ide")
        emit = infNFe.find("emit")
        dest = infNFe.find("dest")
        total = infNFe.find(".//ICMSTot")
        tp = find_txt(ide, "tpNF") if ide is not None else ""  # 0=entrada, 1=saida
        number = find_txt(ide, "nNF") if ide is not None else ""
        issue = find_txt(ide, "dhEmi") if ide is not None else find_txt(ide, "dEmi") if ide is not None else ""
        emit_name = find_txt(emit, "xNome") if emit is not None else ""
        emit_cnpj = find_txt(emit, "CNPJ") if emit is not None else ""
        dest_name = find_txt(dest, "xNome") if dest is not None else ""
        dest_cnpj = (find_txt(dest, "CNPJ") if dest is not None else "") or (find_txt(dest, "CPF") if dest is not None else "")
        vNF = find_txt(total, "vNF") if total is not None else "0"
        kind = "saida" if tp == "1" else "entrada"
        party_name = dest_name if kind == "saida" else emit_name
        party_cnpj = dest_cnpj if kind == "saida" else emit_cnpj
        return {
            "number": number, "kind": kind,
            "party_name": party_name, "party_cnpj": party_cnpj,
            "issue_date": issue[:10] if issue else "",
            "total": float(vNF) if vNF else 0,
            "description": f"NF-e {number} — {emit_name} → {dest_name}"
        }
    except Exception as e:
        raise HTTPException(400, f"XML inválido: {str(e)[:150]}")

# ============ SALES ORDERS ============
@api.get("/orders", response_model=List[SalesOrder])
async def list_ord(status: Optional[str] = None, user=Depends(get_current_user)):
    q = {"status": status} if status else {}
    return await db.orders.find(q, {"_id": 0}).sort("order_date", -1).to_list(1000)

@api.post("/orders", response_model=SalesOrder)
async def create_ord(o: SalesOrder, user=Depends(get_current_user)):
    await db.orders.insert_one(o.model_dump()); return o

@api.put("/orders/{oid}", response_model=SalesOrder)
async def upd_ord(oid: str, o: SalesOrder, user=Depends(get_current_user)):
    o.id = oid; await db.orders.replace_one({"id": oid}, o.model_dump()); return o

@api.delete("/orders/{oid}")
async def del_ord(oid: str, user=Depends(get_current_user)):
    r = await db.orders.delete_one({"id": oid}); return {"deleted": r.deleted_count}

# ============ FINANCE ============
@api.get("/finance", response_model=List[FinanceEntry])
async def list_fin(kind: Optional[str] = None, paid: Optional[bool] = None, user=Depends(get_current_user)):
    q = {}
    if kind: q["kind"] = kind
    if paid is not None: q["paid"] = paid
    return await db.finance.find(q, {"_id": 0}).sort("due_date", 1).to_list(1000)

@api.post("/finance", response_model=FinanceEntry)
async def create_fin(f: FinanceEntry, user=Depends(get_current_user)):
    await db.finance.insert_one(f.model_dump()); return f

@api.patch("/finance/{fid}/toggle-paid", response_model=FinanceEntry)
async def toggle_paid(fid: str, user=Depends(get_current_user)):
    doc = await db.finance.find_one({"id": fid}, {"_id": 0})
    if not doc: raise HTTPException(404, "Not found")
    doc["paid"] = not doc["paid"]
    doc["paid_date"] = now_iso() if doc["paid"] else ""
    await db.finance.update_one({"id": fid}, {"$set": {"paid": doc["paid"], "paid_date": doc["paid_date"]}})
    return doc

@api.delete("/finance/{fid}")
async def del_fin(fid: str, user=Depends(get_current_user)):
    r = await db.finance.delete_one({"id": fid}); return {"deleted": r.deleted_count}

# ============ CONTRACTS ============
@api.get("/contracts", response_model=List[Contract])
async def list_con(kind: Optional[str] = None, user=Depends(get_current_user)):
    q = {"kind": kind} if kind else {}
    return await db.contracts.find(q, {"_id": 0}).sort("end_date", 1).to_list(1000)

@api.post("/contracts", response_model=Contract)
async def create_con(c: Contract, user=Depends(get_current_user)):
    await db.contracts.insert_one(c.model_dump()); return c

@api.put("/contracts/{cid}", response_model=Contract)
async def upd_con(cid: str, c: Contract, user=Depends(get_current_user)):
    c.id = cid; await db.contracts.replace_one({"id": cid}, c.model_dump()); return c

@api.delete("/contracts/{cid}")
async def del_con(cid: str, user=Depends(get_current_user)):
    r = await db.contracts.delete_one({"id": cid}); return {"deleted": r.deleted_count}

# ============ CERTIFICATIONS (por fornecedor) ============
@api.get("/certifications", response_model=List[Certification])
async def list_cert(supplier_id: Optional[str] = None, user=Depends(get_current_user)):
    q = {"supplier_id": supplier_id} if supplier_id else {}
    return await db.certifications.find(q, {"_id": 0}).sort("expiry_date", 1).to_list(1000)

@api.post("/certifications", response_model=Certification)
async def create_cert(c: Certification, user=Depends(get_current_user)):
    await db.certifications.insert_one(c.model_dump()); return c

@api.put("/certifications/{cid}", response_model=Certification)
async def upd_cert(cid: str, c: Certification, user=Depends(get_current_user)):
    c.id = cid; await db.certifications.replace_one({"id": cid}, c.model_dump()); return c

@api.delete("/certifications/{cid}")
async def del_cert(cid: str, user=Depends(get_current_user)):
    r = await db.certifications.delete_one({"id": cid}); return {"deleted": r.deleted_count}

# ============ PURCHASES (Compras) ============
@api.get("/purchases", response_model=List[Purchase])
async def list_pur(status: Optional[str] = None, supplier_id: Optional[str] = None, user=Depends(get_current_user)):
    q = {}
    if status: q["status"] = status
    if supplier_id: q["supplier_id"] = supplier_id
    return await db.purchases.find(q, {"_id": 0}).sort("date", -1).to_list(1000)

@api.post("/purchases", response_model=Purchase)
async def create_pur(p: Purchase, user=Depends(get_current_user)):
    p.total = round(p.quantity * p.unit_price, 2) if not p.total else p.total
    await db.purchases.insert_one(p.model_dump()); return p

@api.put("/purchases/{pid}", response_model=Purchase)
async def upd_pur(pid: str, p: Purchase, user=Depends(get_current_user)):
    p.id = pid
    p.total = round(p.quantity * p.unit_price, 2) if not p.total else p.total
    await db.purchases.replace_one({"id": pid}, p.model_dump()); return p

@api.delete("/purchases/{pid}")
async def del_pur(pid: str, user=Depends(get_current_user)):
    r = await db.purchases.delete_one({"id": pid}); return {"deleted": r.deleted_count}

# ============ SPECS (Prospecção IBIAG) ============
@api.get("/specs", response_model=List[Spec])
async def list_specs(supplier_id: Optional[str] = None, user=Depends(get_current_user)):
    q = {"supplier_id": supplier_id} if supplier_id else {}
    return await db.specs.find(q, {"_id": 0}).sort("product_name", 1).to_list(1000)

@api.post("/specs", response_model=Spec)
async def create_spec(s: Spec, user=Depends(get_current_user)):
    await db.specs.insert_one(s.model_dump()); return s

@api.put("/specs/{sid}", response_model=Spec)
async def upd_spec(sid: str, s: Spec, user=Depends(get_current_user)):
    s.id = sid; s.updated_at = now_iso()
    await db.specs.replace_one({"id": sid}, s.model_dump()); return s

@api.delete("/specs/{sid}")
async def del_spec(sid: str, user=Depends(get_current_user)):
    r = await db.specs.delete_one({"id": sid}); return {"deleted": r.deleted_count}

# ============ PRICES ============
def compute_price(p: PriceEntry) -> PriceEntry:
    extras_sum = sum(float(e.get("value", 0) or 0) for e in p.extras) if p.extras else p.extra_costs
    p.extra_costs = round(extras_sum, 4)
    taxes_pct = sum(float(t.get("pct", 0) or 0) for t in p.taxes) if p.taxes else p.taxes_pct
    p.taxes_pct = round(taxes_pct, 4)
    cost = p.supplier_price + p.extra_costs
    if p.margin_mode == "markup":
        base = cost * (1 + p.margin_pct / 100)
        price = base / (1 - taxes_pct / 100) if taxes_pct < 100 else base
    else:
        divisor = 1 - (p.margin_pct + taxes_pct) / 100
        price = cost / divisor if divisor > 0 else cost
    p.sell_price_brl = round(price, 4)
    p.sell_price_usd = round(price / p.exchange_rate, 4) if p.exchange_rate > 0 else 0
    return p

@api.get("/prices", response_model=List[PriceEntry])
async def list_prices(user=Depends(get_current_user)):
    return await db.prices.find({}, {"_id": 0}).sort("product_name", 1).to_list(1000)

@api.post("/prices/calculate", response_model=PriceEntry)
async def calc_price(p: PriceEntry, user=Depends(get_current_user)):
    return compute_price(p)

@api.post("/prices", response_model=PriceEntry)
async def create_price(p: PriceEntry, user=Depends(get_current_user)):
    p = compute_price(p)
    await db.prices.insert_one(p.model_dump()); return p

@api.put("/prices/{pid}", response_model=PriceEntry)
async def upd_price(pid: str, p: PriceEntry, user=Depends(get_current_user)):
    p.id = pid; p.updated_at = now_iso(); p = compute_price(p)
    await db.prices.replace_one({"id": pid}, p.model_dump()); return p

@api.delete("/prices/{pid}")
async def del_price(pid: str, user=Depends(get_current_user)):
    r = await db.prices.delete_one({"id": pid}); return {"deleted": r.deleted_count}

# ============ CASHFLOW ============
@api.get("/finance/cashflow")
async def cashflow(months: int = 12, user=Depends(get_current_user)):
    today = datetime.now(timezone.utc)
    keys = []
    y, m = today.year, today.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0: m = 12; y -= 1
    keys.reverse()
    data = {k: {"month": k, "receivable": 0.0, "payable": 0.0, "received": 0.0, "paid": 0.0, "nf_saida": 0.0, "nf_entrada": 0.0} for k in keys}
    async for f in db.finance.find({}, {"_id": 0}):
        k = (f.get("due_date") or "")[:7]
        if k not in data: continue
        amt = float(f.get("amount", 0) or 0)
        if f.get("kind") == "receivable":
            data[k]["receivable"] += amt
            if f.get("paid"): data[k]["received"] += amt
        else:
            data[k]["payable"] += amt
            if f.get("paid"): data[k]["paid"] += amt
    async for i in db.invoices.find({}, {"_id": 0}):
        k = (i.get("issue_date") or "")[:7]
        if k not in data: continue
        amt = float(i.get("total", 0) or 0)
        if i.get("kind") == "saida": data[k]["nf_saida"] += amt
        else: data[k]["nf_entrada"] += amt
    out = []
    running = 0.0
    for k in keys:
        d = data[k]
        d["balance"] = round(d["receivable"] - d["payable"], 2)
        running += d["balance"]
        d["cumulative"] = round(running, 2)
        for f in ("receivable", "payable", "received", "paid", "nf_saida", "nf_entrada"):
            d[f] = round(d[f], 2)
        out.append(d)
    return out

# ============ GESTÃO STATS ============
@api.get("/gestao/stats")
async def gestao_stats(user=Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    certs = await db.certifications.find({}, {"_id": 0}).to_list(2000)
    expiring, expired = [], []
    for c in certs:
        if not c.get("expiry_date"): continue
        try: exp = datetime.strptime(c["expiry_date"][:10], "%Y-%m-%d").date()
        except ValueError: continue
        days = (exp - today).days
        item = {"id": c["id"], "name": c["name"], "supplier_name": c.get("supplier_name", ""), "supplier_id": c.get("supplier_id", ""), "expiry_date": c["expiry_date"], "days": days}
        if days < 0: expired.append(item)
        elif days <= int(c.get("alert_days", 30) or 30): expiring.append(item)
    soon = (today + timedelta(days=30)).isoformat()
    contracts_expiring = await db.contracts.count_documents({"end_date": {"$gte": today.isoformat(), "$lte": soon}})
    fin_recv = 0.0; fin_pay = 0.0
    async for d in db.finance.aggregate([{"$match": {"paid": False}}, {"$group": {"_id": "$kind", "total": {"$sum": "$amount"}}}]):
        if d["_id"] == "receivable": fin_recv = d["total"]
        else: fin_pay = d["total"]
    return {
        "certs_total": len(certs), "certs_expiring": sorted(expiring, key=lambda x: x["days"]),
        "certs_expired": sorted(expired, key=lambda x: x["days"]),
        "contracts_expiring": contracts_expiring,
        "purchases_open": await db.purchases.count_documents({"status": {"$in": ["ordered", "received"]}}),
        "suppliers": await db.suppliers.count_documents({}),
        "specs": await db.specs.count_documents({}),
        "prices": await db.prices.count_documents({}),
        "pops": await db.documents.count_documents({"category": {"$in": ["pop", "pop_signed"]}}),
        "invoices_in": await db.invoices.count_documents({"kind": "entrada"}),
        "invoices_out": await db.invoices.count_documents({"kind": "saida"}),
        "finance_receivable": fin_recv, "finance_payable": fin_pay,
    }

# ============ INVENTORY ============
class StockUpd(BaseModel):
    stock: float

@api.patch("/products/{pid}/stock", response_model=Product)
async def upd_stock(pid: str, body: StockUpd, user=Depends(get_current_user)):
    await db.products.update_one({"id": pid}, {"$set": {"stock": body.stock}})
    doc = await db.products.find_one({"id": pid}, {"_id": 0})
    if not doc: raise HTTPException(404, "Not found")
    return doc


# ============ PRODUCT PORTFOLIO OFFERS ============
@api.get("/product-offers", response_model=List[ProductOffer])
async def list_product_offers(product_id: Optional[str] = None, supplier_id: Optional[str] = None, active: Optional[bool] = None, user=Depends(get_current_user)):
    q = {}
    if product_id: q["product_id"] = product_id
    if supplier_id: q["supplier_id"] = supplier_id
    if active is not None: q["active"] = active
    return await db.product_offers.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)

@api.post("/product-offers", response_model=ProductOffer)
async def create_product_offer(o: ProductOffer, user=Depends(get_current_user)):
    if not await db.products.find_one({"id": o.product_id}):
        raise HTTPException(404, "Produto não encontrado")
    if o.supplier_id and not await db.suppliers.find_one({"id": o.supplier_id}):
        raise HTTPException(404, "Fornecedor não encontrado")
    if not o.product_name:
        product = await db.products.find_one({"id": o.product_id}, {"_id": 0, "name": 1})
        o.product_name = product.get("name", "") if product else ""
    if o.supplier_id and not o.supplier_name:
        supplier = await db.suppliers.find_one({"id": o.supplier_id}, {"_id": 0, "name": 1})
        o.supplier_name = supplier.get("name", "") if supplier else ""
    await db.product_offers.insert_one(o.model_dump())
    return o

@api.put("/product-offers/{oid}", response_model=ProductOffer)
async def update_product_offer(oid: str, o: ProductOffer, user=Depends(get_current_user)):
    if not await db.product_offers.find_one({"id": oid}):
        raise HTTPException(404, "Oferta não encontrada")
    o.id = oid
    o.updated_at = now_iso()
    if not o.product_name:
        product = await db.products.find_one({"id": o.product_id}, {"_id": 0, "name": 1})
        o.product_name = product.get("name", "") if product else ""
    if o.supplier_id:
        supplier = await db.suppliers.find_one({"id": o.supplier_id}, {"_id": 0, "name": 1})
        if not supplier:
            raise HTTPException(404, "Fornecedor não encontrado")
        o.supplier_name = supplier.get("name", "")
    else:
        o.supplier_name = ""
    await db.product_offers.replace_one({"id": oid}, o.model_dump())
    return o

@api.delete("/product-offers/{oid}")
async def delete_product_offer(oid: str, user=Depends(get_current_user)):
    r = await db.product_offers.delete_one({"id": oid})
    return {"deleted": r.deleted_count}

@api.get("/product-offers/{oid}/documents")
async def product_offer_documents(oid: str, user=Depends(get_current_user)):
    offer = await db.product_offers.find_one({"id": oid}, {"_id": 0})
    if not offer:
        raise HTTPException(404, "Oferta não encontrada")
    ids = list(dict.fromkeys(offer.get("spec_document_ids", []) + offer.get("certificate_document_ids", []) + offer.get("other_document_ids", [])))
    result = []
    if ids:
        docs = await db.documents.find({"id": {"$in": ids}}, {"_id": 0}).to_list(200)
        result.extend([{**d, "link_type": "document"} for d in docs])
    spec_ids = offer.get("spec_ids", [])
    if spec_ids:
        specs = await db.specs.find({"id": {"$in": spec_ids}}, {"_id": 0}).to_list(200)
        result.extend([{**x, "link_type": "spec"} for x in specs])
    cert_ids = offer.get("certification_ids", [])
    if cert_ids:
        certs = await db.certifications.find({"id": {"$in": cert_ids}}, {"_id": 0}).to_list(200)
        result.extend([{**x, "link_type": "certification"} for x in certs])
    return result

# ============ PRODUCTS (public read + auth write) ============
@api.get("/products", response_model=List[Product])
async def list_products(category: Optional[str] = None):
    q = {"category": category} if category else {}
    return await db.products.find(q, {"_id": 0}).to_list(500)

@api.post("/products", response_model=Product)
async def create_product(p: Product, user=Depends(get_current_user)):
    await db.products.insert_one(p.model_dump()); return p

@api.put("/products/{pid}", response_model=Product)
async def upd_product(pid: str, p: Product, user=Depends(get_current_user)):
    p.id = pid; await db.products.replace_one({"id": pid}, p.model_dump()); return p

@api.delete("/products/{pid}")
async def del_product(pid: str, user=Depends(get_current_user)):
    r = await db.products.delete_one({"id": pid}); return {"deleted": r.deleted_count}


class PortfolioImportResult(BaseModel):
    products: int
    suppliers: int
    offers: int
    source_rows: int

@api.post("/portfolio/import-xlsx", response_model=PortfolioImportResult)
async def import_portfolio_xlsx(file: UploadFile = File(...), replace: bool = True, dry_run: bool = False, user=Depends(get_current_user)):
    """Import the official IBIAG product/supplier matrix. Sheet IBIAG, header row 3."""
    require_admin(user)
    raw = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(raw), sheet_name="IBIAG", header=2, dtype=object).fillna("")
    except Exception as e:
        raise HTTPException(400, f"Não foi possível ler a aba IBIAG: {e}")

    def clean(v):
        if v is None: return ""
        if isinstance(v, float) and v.is_integer(): return str(int(v))
        return str(v).strip()

    required = {"Produto", "Fornecedor"}
    if not required.issubset(set(df.columns)):
        raise HTTPException(400, "Planilha sem as colunas Produto/Fornecedor esperadas")

    rows = []
    for _, row in df.iterrows():
        name = clean(row.get("Produto"))
        if not name:
            continue
        rows.append({str(k).strip(): clean(v) for k, v in row.to_dict().items()})

    supplier_names = sorted({r.get("Fornecedor","") for r in rows if r.get("Fornecedor","")})
    product_names = {re.sub(r"\\s+", " ", r.get("Produto","")).strip().casefold() for r in rows if r.get("Produto","").strip()}
    if dry_run:
        return PortfolioImportResult(products=len(product_names), suppliers=len(supplier_names), offers=len(rows), source_rows=len(rows))

    if replace:
        await db.products.delete_many({})
        await db.product_offers.delete_many({})
    supplier_map = {}
    for name in supplier_names:
        existing = await db.suppliers.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}, {"_id": 0})
        if not existing:
            s = Supplier(name=name, notes="Importado da Tabela Produtos IBIAG 2026")
            await db.suppliers.insert_one(s.model_dump())
            existing = s.model_dump()
        supplier_map[name] = existing

    product_map = {}
    for r in rows:
        name = re.sub(r"\\s+", " ", r.get("Produto","")).strip()
        key = name.casefold()
        if key in product_map:
            continue
        ncm = r.get("NCM/HS","")
        p = Product(
            name=name,
            category=r.get("Linha","") or "portfolio",
            hs_code=ncm,
            ncm=ncm,
            sku=r.get("SKU",""),
            packaging=" · ".join(x for x in [r.get("Tipo Embalagem",""), r.get("Embalagem","")] if x),
            available_capacity=r.get("Capacidade de Produção",""),
            price_range=r.get("Preço Exportação",""),
            specs=r.get("Spec",""),
            price_history_notes=r.get("Observações",""),
            description_pt="Produto do portfólio operacional IBIAG 2026",
        )
        await db.products.insert_one(p.model_dump())
        product_map[key] = p.model_dump()

    offer_count = 0
    for r in rows:
        name = re.sub(r"\\s+", " ", r.get("Produto","")).strip()
        p = product_map[name.casefold()]
        supplier_name = r.get("Fornecedor","")
        supplier = supplier_map.get(supplier_name, {})
        commission_raw = r.get("Comissão","")
        try:
            commission = float(str(commission_raw).replace(",", ".")) if commission_raw else 0
        except Exception:
            commission = 0
        offer = ProductOffer(
            product_id=p["id"], product_name=p["name"], form=p["name"],
            supplier_id=supplier.get("id",""), supplier_name=supplier_name,
            capacity=r.get("Capacidade de Produção",""), ncm=r.get("NCM/HS",""), hs_code=r.get("NCM/HS",""),
            packaging_type=r.get("Tipo Embalagem",""), packaging=r.get("Embalagem",""),
            palletization=r.get("Palletização",""), export_price_text=r.get("Preço Exportação",""),
            fob_price_text="" if r.get("Preço FOB","") == "#VALUE!" else r.get("Preço FOB",""),
            organic_version=r.get("Versão Orgânica",""), commission=commission,
            certifications_text=r.get("Certificações",""), spec_url=r.get("Spec",""),
            marketing_claim=r.get("Apelo MKT",""), harvest=r.get("Safra",""),
            checked=r.get("Conferido",""), notes=r.get("Observações",""),
            source="Tabela Produtos Ibiag 2026 - COMPLETA / aba IBIAG"
        )
        await db.product_offers.insert_one(offer.model_dump())
        offer_count += 1

    # Refresh each supplier's product summary without inventing contact data.
    for name, supplier in supplier_map.items():
        supplied = sorted({r.get("Produto","").strip() for r in rows if r.get("Fornecedor","") == name and r.get("Produto","").strip()})
        await db.suppliers.update_one({"id": supplier["id"]}, {"$set": {"products": ", ".join(supplied)}})

    await db.settings.update_one({"key":"portfolio_source"}, {"$set":{
        "key":"portfolio_source","value":"Tabela Produtos Ibiag 2026 - COMPLETA (1).xlsx",
        "source_rows":len(rows),"products":len(product_map),"suppliers":len(supplier_map),
        "offers":offer_count,"updated_at":now_iso()
    }}, upsert=True)
    return PortfolioImportResult(products=len(product_map), suppliers=len(supplier_map), offers=offer_count, source_rows=len(rows))

# ============ LEADS (CRM) ============
class LeadImportResult(BaseModel):
    imported: int
    updated: int
    skipped: int
    errors: List[str] = []

def _norm_text(value: str) -> str:
    text = "" if value is None else str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))

def _norm_col(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm_text(value).lower()).strip("_")

def _clean_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()

def _pick(row: dict, aliases: List[str]) -> str:
    for alias in aliases:
        key = _norm_col(alias)
        if key in row and row[key] not in (None, ""):
            return _clean_value(row[key])
    return ""

def _parse_number(value) -> float:
    raw = _clean_value(value).replace("R$", "").replace("$", "").replace(" ", "")
    if not raw:
        return 0.0
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0

def _norm_company(value: str) -> str:
    text = _norm_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

@api.post("/leads/import", response_model=LeadImportResult)
async def import_leads(file: UploadFile = File(...), user=Depends(get_current_user)):
    name = (file.filename or "").lower()
    raw = await file.read()
    try:
        if name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(raw))
        elif name.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(raw), sep=None, engine="python")
            except Exception:
                df = pd.read_csv(io.BytesIO(raw), sep=";")
        else:
            raise HTTPException(400, "Use CSV or XLSX")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {e}")

    df = df.fillna("")
    df.columns = [_norm_col(c) for c in df.columns]
    imported = updated = skipped = 0
    errors = []
    # Load existing CRM records once; avoids one database scan per imported row.
    # No artificial CRM-size cap: load all existing lead keys for conservative deduplication.\n    candidates = await db.leads.find({}, {"_id": 0}).to_list(None)

    aliases = {
        "company": ["company","empresa","razao_social","razão_social","nome_empresa","cliente"],
        "contact_name": ["contact_name","contato","nome_contato","contato_nome","comprador"],
        "email": ["email","e_mail","email_comercial","commercial_email"],
        "phone": ["phone","telefone","celular","whatsapp"],
        "website": ["website","site","url"],
        "linkedin": ["linkedin","linkedin_url"],
        "country": ["country","pais","país"],
        "country_code": ["country_code","pais_codigo","iso"],
        "industry": ["industry","industria","setor"],
        "stage": ["stage","estagio","etapa"],
        "product_interest": ["product_interest","produto","produto_interesse","ingrediente"],
        "decision_maker": ["decision_maker","decisor","decisor_compras","comprador_decisor"],
        "decision_maker_title": ["decision_maker_title","cargo","cargo_decisor"],
        "decision_maker_email": ["decision_maker_email","email_decisor"],
        "decision_maker_phone": ["decision_maker_phone","telefone_decisor","celular_decisor"],
        "current_supplier": ["current_supplier","fornecedor_atual","fornecedor"],
        "priority": ["priority","prioridade"],
        "source_url": ["source_url","fonte","url_fonte"],
        "deal_value": ["deal_value","valor_negocio","valor"],
        "notes": ["notes","observacoes","observações","notas"],
    }

    for idx, raw_row in enumerate(df.to_dict(orient="records"), start=2):
        row = {_norm_col(k): v for k, v in raw_row.items()}
        company = _pick(row, aliases["company"])
        if not company:
            skipped += 1
            errors.append(f"Linha {idx}: empresa vazia")
            continue
        data = {"company": company}
        for field, names in aliases.items():
            if field == "company": continue
            value = _pick(row, names)
            if field == "deal_value":
                try: value = _parse_number(value)
                except Exception: value = 0.0
            if value != "":
                data[field] = value

        # Match legacy CRM records using normalized company/country values.
        # Keep the match conservative: no fuzzy merge is done.
        existing = None
        company_norm = _norm_company(company)
        country_norm = _norm_company(data.get("country", ""))
        for candidate in candidates:
            if _norm_company(candidate.get("company", "")) != company_norm:
                continue
            if country_norm and _norm_company(candidate.get("country", "")) != country_norm:
                continue
            existing = candidate
            break
        if existing:
            updates = {k:v for k,v in data.items() if v not in ("", None) and not existing.get(k)}
            if updates:
                updates["updated_at"] = now_iso()
                await db.leads.update_one({"id": existing["id"]}, {"$set": updates})
                updated += 1
            else:
                skipped += 1
        else:
            lead = Lead(**data)
            lead_doc = lead.model_dump()
            await db.leads.insert_one(lead_doc)
            candidates.append(lead_doc)
            imported += 1

    return LeadImportResult(imported=imported, updated=updated, skipped=skipped, errors=errors[:100])

@api.get("/leads", response_model=List[Lead])
async def list_leads(
    stage: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 250,
):
    """List CRM leads with pagination; there is no registration/storage cap."""
    q = {}
    if stage:
        q["stage"] = stage
    if industry:
        q["industry"] = industry
    skip = max(0, skip)
    limit = min(max(1, limit), 250)
    return await db.leads.find(q, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)

@api.get("/leads/count")
async def count_leads(stage: Optional[str] = None, industry: Optional[str] = None, user=Depends(get_current_user)):
    q = {}
    if stage:
        q["stage"] = stage
    if industry:
        q["industry"] = industry
    return {"total": await db.leads.count_documents(q)}

@api.post("/leads", response_model=Lead)
async def create_lead(lead: Lead, user=Depends(get_current_user)):
    await db.leads.insert_one(lead.model_dump()); return lead

@api.patch("/leads/{lid}/stage", response_model=Lead)
async def upd_stage(lid: str, upd: StageUpd, user=Depends(get_current_user)):
    await db.leads.update_one({"id": lid}, {"$set": {"stage": upd.stage, "updated_at": now_iso()}})
    doc = await db.leads.find_one({"id": lid}, {"_id": 0})
    if not doc: raise HTTPException(404, "Not found")
    return doc

@api.put("/leads/{lid}", response_model=Lead)
async def upd_lead(lid: str, lead: Lead, user=Depends(get_current_user)):
    lead.id = lid; lead.updated_at = now_iso()
    await db.leads.replace_one({"id": lid}, lead.model_dump()); return lead

@api.delete("/leads/{lid}")
async def del_lead(lid: str, user=Depends(get_current_user)):
    r = await db.leads.delete_one({"id": lid})
    await db.interactions.delete_many({"lead_id": lid})
    return {"deleted": r.deleted_count}

@api.get("/interactions", response_model=List[Interaction])
async def list_int(lead_id: Optional[str] = None):
    q = {"lead_id": lead_id} if lead_id else {}
    return await db.interactions.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)

@api.post("/interactions", response_model=Interaction)
async def create_int(i: Interaction, user=Depends(get_current_user)):
    await db.interactions.insert_one(i.model_dump()); return i

# ============ TASKS ============
@api.get("/tasks", response_model=List[Task])
async def list_tasks(user=Depends(get_current_user)):
    return await db.tasks.find({}, {"_id": 0}).to_list(500)

@api.post("/tasks", response_model=Task)
async def create_task(t: Task, user=Depends(get_current_user)):
    await db.tasks.insert_one(t.model_dump()); return t

@api.patch("/tasks/{tid}/toggle", response_model=Task)
async def toggle_task(tid: str, user=Depends(get_current_user)):
    doc = await db.tasks.find_one({"id": tid}, {"_id": 0})
    if not doc: raise HTTPException(404, "Not found")
    nv = not doc["completed"]
    await db.tasks.update_one({"id": tid}, {"$set": {"completed": nv}})
    doc["completed"] = nv; return doc

@api.delete("/tasks/{tid}")
async def del_task(tid: str, user=Depends(get_current_user)):
    r = await db.tasks.delete_one({"id": tid}); return {"deleted": r.deleted_count}

# ============ TEMPLATES (public) ============
class MessageTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name_pt: str
    name_en: str
    category: str
    language: str
    subject: str = ""
    body: str

@api.get("/templates", response_model=List[MessageTemplate])
async def list_tpl(language: Optional[str] = None, category: Optional[str] = None):
    q = {}
    if language: q["language"] = language
    if category: q["category"] = category
    return await db.templates.find(q, {"_id": 0}).to_list(200)

# ============ COMEX STAT / MDIC ============
@api.get("/comexstat/ncm")
async def comexstat_ncm(search: str = "", page: int = 1, per_page: int = 50, user=Depends(get_current_user)):
    try:
        return ncm_search(search=search, page=page, per_page=per_page)
    except requests.RequestException as e:
        logging.exception("Comex Stat NCM search failed")
        raise HTTPException(502, f"Comex Stat indisponível: {str(e)[:180]}")

@api.post("/comexstat/prospect")
async def comexstat_prospect(payload: dict, user=Depends(get_current_user)):
    """Build a prospecting snapshot from official Comex Stat aggregates."""
    try:
        flow = payload.get("flow", "export")
        period = payload.get("period") or {"from": "2026-01", "to": "2026-08"}
        ncm = str(payload.get("ncm", "")).strip()
        details = ["country"]
        filters = []
        if ncm:
            details.insert(0, "ncm")
            filters.append({"filter": "ncm", "values": [int(ncm)]})
        query = {
            "flow": flow,
            "monthDetail": False,
            "period": period,
            "filters": filters,
            "details": details,
            "metrics": ["metricFOB", "metricKG"],
        }
        data = comex_general(query)
        markets = normalize_markets(data)
        return {"flow": flow, "period": period, "ncm": ncm, "query": query, "data": data, "markets": markets}
    except (requests.RequestException, ValueError) as e:
        logging.exception("Comex Stat prospect query failed")
        raise HTTPException(502, f"Não foi possível montar o prospecting snapshot: {str(e)[:180]}")

@api.post("/comexstat/markets")
async def comexstat_markets(payload: dict, user=Depends(get_current_user)):
    """Return normalized country-market aggregates for a product/NCM."""
    try:
        flow = payload.get("flow", "export")
        period = payload.get("period") or {"from": "2026-01", "to": "2026-08"}
        ncm = str(payload.get("ncm", "")).strip()
        filters = []
        if ncm:
            filters.append({"filter": "ncm", "values": [int(ncm)]})
        query = {
            "flow": flow,
            "monthDetail": False,
            "period": period,
            "filters": filters,
            "details": ["country"],
            "metrics": ["metricFOB", "metricKG"],
        }
        data = comex_general(query)
        return {
            "flow": flow,
            "period": period,
            "ncm": ncm,
            "source": "Comex Stat / MDIC",
            "markets": normalize_markets(data),
        }
    except (requests.RequestException, ValueError) as e:
        logging.exception("Comex Stat markets query failed")
        raise HTTPException(502, f"Não foi possível montar os mercados: {str(e)[:180]}")

@api.post("/comexstat/general")
async def comexstat_general(payload: dict, user=Depends(get_current_user)):
    try:
        return comex_general(payload)
    except requests.RequestException as e:
        logging.exception("Comex Stat general query failed")
        raise HTTPException(502, f"Comex Stat indisponível: {str(e)[:180]}")

# ============ TRADE (public) ============
class TradeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
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

@api.get("/trade-data", response_model=List[TradeRecord])
async def list_trade(country: Optional[str] = None, industry: Optional[str] = None, search: Optional[str] = None):
    q = {}
    if country: q["country_code"] = country
    if industry: q["industry_segment"] = industry
    if search:
        q["$or"] = [{"importer_company": {"$regex": search, "$options": "i"}},
                    {"product_description": {"$regex": search, "$options": "i"}}]
    return await db.trade_data.find(q, {"_id": 0}).to_list(500)

@api.post("/trade-data/{tid}/add-to-crm", response_model=Lead)
async def trade_to_crm(tid: str, user=Depends(get_current_user)):
    tr = await db.trade_data.find_one({"id": tid}, {"_id": 0})
    if not tr: raise HTTPException(404, "Not found")
    existing = await db.leads.find_one({"company": tr["importer_company"]}, {"_id": 0})
    if existing: return existing
    lead = Lead(company=tr["importer_company"], country=tr["importer_country"],
                country_code=tr["country_code"], industry=tr["industry_segment"],
                stage="new_lead", source="trade_data", deal_value=tr["value_usd"],
                notes=f"From Trade Intel. HS {tr['hs_code']}. {tr['volume_kg']:.0f} kg / USD {tr['value_usd']:.0f}")
    await db.leads.insert_one(lead.model_dump())
    return lead


# ============ BUYER DISCOVERY ============
class BuyerDiscoveryRequest(BaseModel):
    product: str
    country: str
    country_code: str = ""
    limit: int = 8

@api.post("/buyer-discovery/search")
async def buyer_discovery_search(body: BuyerDiscoveryRequest, user=Depends(get_current_user)):
    product = body.product.strip()
    country = body.country.strip()
    if not product or not country:
        raise HTTPException(400, "Informe produto e país.")
    try:
        buyers = discover_buyers(product, country, max(1, min(body.limit, 20)))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except requests.RequestException as e:
        logging.exception("Buyer discovery provider error")
        raise HTTPException(502, f"Provedor de pesquisa indisponível: {e}")
    return {"product": product, "country": country, "results": buyers, "source": "web_discovery"}

@api.post("/buyer-discovery/{company}/decision-maker")
async def buyer_discovery_decision_maker(company: str, product: str = "", country: str = "", user=Depends(get_current_user)):
    if not company.strip():
        raise HTTPException(400, "Empresa obrigatória.")
    try:
        import asyncio
        return await asyncio.to_thread(discover_decision_maker, company, country, product)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except requests.RequestException as e:
        logging.exception("Decision maker discovery provider error")
        raise HTTPException(502, f"Provedor de pesquisa indisponível: {e}")

@api.post("/buyer-discovery/to-crm")
async def buyer_discovery_to_crm(payload: dict, user=Depends(get_current_user)):
    company = str(payload.get("company", "")).strip()
    if not company:
        raise HTTPException(400, "Empresa obrigatória.")
    country = str(payload.get("country", ""))
    data = {
        "company": company,
        "country": country,
        "country_code": str(payload.get("country_code", "")),
        "website": str(payload.get("website", "")),
        "linkedin": str(payload.get("linkedin", "")),
        "product_interest": str(payload.get("product_interest", "")),
        "source_url": str(payload.get("source_url", "")),
        "source": "buyer_discovery",
        "priority": "high" if float(payload.get("priority_score", 0) or 0) >= 70 else "normal",
        "notes": f"Descoberto via inteligência web. Score: {payload.get('priority_score', 0)}",
        "updated_at": now_iso(),
    }
    existing = await db.leads.find_one({"company": {"$regex": f"^{re.escape(company)}$", "$options": "i"}, "country": {"$regex": f"^{re.escape(country)}$", "$options": "i"}}, {"_id": 0})
    if existing:
        merged = dict(existing)
        for k, v in data.items():
            if v and not merged.get(k):
                merged[k] = v
        merged["updated_at"] = now_iso()
        await db.leads.replace_one({"id": existing["id"]}, merged)
        return merged
    lead = Lead(**data)
    await db.leads.insert_one(lead.model_dump())
    return lead

# ============ DASHBOARD ============
@api.get("/dashboard/stats")
async def dashboard():
    total_leads = await db.leads.count_documents({})
    active = await db.leads.count_documents({"stage": {"$nin": ["closed_won", "closed_lost"]}})
    won = await db.leads.count_documents({"stage": "closed_won"})
    lost = await db.leads.count_documents({"stage": "closed_lost"})
    samples = await db.leads.count_documents({"stage": {"$in": ["sample_quote", "sample_sent"]}})
    conv = round((won / (won + lost)) * 100, 1) if (won + lost) > 0 else 0.0
    pipeline_value = 0.0
    async for d in db.leads.aggregate([
        {"$match": {"stage": {"$nin": ["closed_won", "closed_lost"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$deal_value"}}}]):
        pipeline_value = d.get("total", 0.0)
    by_stage = {}
    async for d in db.leads.aggregate([{"$group": {"_id": "$stage", "count": {"$sum": 1}}}]):
        by_stage[d["_id"]] = d["count"]
    by_industry = {}
    async for d in db.leads.aggregate([{"$group": {"_id": "$industry", "count": {"$sum": 1}}}]):
        by_industry[d["_id"]] = d["count"]
    # ERP stats
    docs_count = await db.documents.count_documents({})
    invoices_count = await db.invoices.count_documents({})
    suppliers_count = await db.suppliers.count_documents({})
    orders_pending = await db.orders.count_documents({"status": {"$in": ["draft", "confirmed"]}})
    fin_receivable = 0.0
    async for d in db.finance.aggregate([{"$match": {"kind": "receivable", "paid": False}},
                                         {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]):
        fin_receivable = d.get("total", 0.0)
    fin_payable = 0.0
    async for d in db.finance.aggregate([{"$match": {"kind": "payable", "paid": False}},
                                         {"$group": {"_id": None, "total": {"$sum": "$amount"}}}]):
        fin_payable = d.get("total", 0.0)
    today = datetime.now(timezone.utc).date().isoformat()
    soon = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    expiring = await db.contracts.count_documents({"end_date": {"$gte": today, "$lte": soon}})
    return {
        "total_leads": total_leads, "active_leads": active, "samples_sent": samples,
        "won": won, "lost": lost, "conversion_rate": conv, "pipeline_value": pipeline_value,
        "by_stage": by_stage, "by_industry": by_industry,
        "documents": docs_count, "invoices": invoices_count, "suppliers": suppliers_count,
        "orders_pending": orders_pending, "finance_receivable": fin_receivable,
        "finance_payable": fin_payable, "contracts_expiring": expiring
    }

@api.post("/admin/migrate-crm-stages")
async def migrate_crm_stages(user=Depends(get_current_user)):
    require_admin(user)
    legacy = await db.leads.update_many({"stage": "sample_sent"}, {"$set": {"stage": "sample_quote", "updated_at": now_iso()}})
    return {"migrated_sample_sent_to_sample_quote": legacy.modified_count}

@api.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "database": "ok", "timestamp": now_iso()}
    except Exception:
        logging.exception("Health check failed")
        raise HTTPException(503, "Database unavailable")

@api.get("/")
async def root(): return {"message": "IBIAG API", "status": "ok"}

app.include_router(api)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- SEED -----
async def seed_all():
    # Admin
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if admin_email and admin_pw:
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            await db.users.insert_one({"id": str(uuid.uuid4()), "email": admin_email,
                                        "name": "Administrador IBIAG", "password_hash": hash_pw(admin_pw),
                                        "role": "admin", "created_at": now_iso()})
        elif not verify_pw(admin_pw, existing["password_hash"]):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_pw(admin_pw)}})
    await db.users.create_index("email", unique=True)

    # Products & templates & trade & leads seed (kept same as before)
    # Official IBIAG Ingredients portfolio 2026. Keep demo records out of production.
    portfolio_version = "IBIAG-2026-10-01"
    if await db.settings.find_one({"key": "portfolio_version"}) is None:
        # The previous installation contained demonstration products. Replace them once with the official portfolio.
        await db.products.delete_many({})
        prods = [
            Product(name="Açaí Extract Powder", category="superfruits", moq="100 KG", specs="Powder extract; organic available", sku="IB-001", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Açaí Freeze Dried", category="superfruits", moq="10 KG", specs="Freeze dried; organic available", sku="IB-002", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Açaí Pulp (8%, 12%, 14% solids)", category="superfruits", moq="Please request", specs="Single strength / puree; organic available", sku="IB-003", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Açaí Soft Mix", category="superfruits", moq="Please request", specs="UHT", sku="IB-004", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Açaí Sorbet", category="superfruits", moq="Please request", specs="Organic available", sku="IB-005", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Acerola Dry Extract Powder (17%, 21%, 25% Native Vit C)", category="superfruits", moq="20 KG", specs="Powder extract; organic available", sku="IB-006", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Acerola Freeze Dried (17%, 30%, 40% Native Vit C)", category="superfruits", moq="10 KG", specs="Freeze dried; organic available", sku="IB-007", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Acerola Juice", category="superfruits", moq="Please request", specs="Single strength / clarified-concentrated; organic available", sku="IB-008", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Apple Powder", category="superfruits", moq="3 KG", specs="Powder; organic available", sku="IB-009", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Artichoke Extract Powder", category="herbs_roots", moq="100 KG", specs="Extract powder", sku="IB-010", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Babassu Flour", category="specialties", moq="25 KG", specs="Flour", sku="IB-011", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Cajá / Cajá Umbu", category="superfruits", moq="Please request", specs="Juice / puree", sku="IB-012", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Camu Camu Extract Powder", category="superfruits", moq="100 KG", specs="Extract powder; organic available", sku="IB-013", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Camu Camu Freeze Dried Powder", category="superfruits", moq="10 KG", specs="Freeze dried powder; organic available", sku="IB-014", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Cashew Juice", category="juices", moq="Please request", specs="Juice / clarified-concentrated", sku="IB-015", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Cashew Nuts", category="nuts_seeds", moq="7,938 KG", specs="Nuts; organic available", sku="IB-016", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Catuaba", category="herbs_roots", moq="100 KG", specs="Powder / extract / cut", sku="IB-017", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Coconut Flour (Degreased Desiccated)", category="specialties", moq="25 KG", specs="Flour", sku="IB-018", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Coconut Milk Concentrated", category="specialties", moq="20 KG", specs="Concentrated coconut milk", sku="IB-019", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Coconut Pulp Green Integral", category="specialties", moq="20 KG", specs="Integral green coconut pulp; organic available", sku="IB-020", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Coconut Water", category="juices", moq="Please request", specs="Single strength / clarified-concentrated; organic available", sku="IB-021", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Grape Seed Powder", category="superfruits", moq="3 KG", specs="Powder; organic available", sku="IB-022", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Grape Skin Powder", category="superfruits", moq="3 KG", specs="Powder; organic available", sku="IB-023", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Graviola (Soursop)", category="herbs_roots", moq="Please request", specs="Juice / powder / cut", sku="IB-024", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Green Coffee Complex Powder", category="superfruits", moq="5 KG", specs="Powder", sku="IB-025", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Green Coffee Dry Extract 10% Caffeine", category="superfruits", moq="100 KG", specs="Dry extract", sku="IB-026", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Green Coffee Oil", category="specialties", moq="5 KG", specs="Vegetal oil", sku="IB-027", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Guaraná Extract Powder (10%, 22% Caffeine)", category="superfruits", moq="100 KG", specs="Extract powder; organic available", sku="IB-028", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Guaraná Fluid Extract (1.2%, 4-6% Caffeine)", category="superfruits", moq="100 KG", specs="Fluid extract; organic available", sku="IB-029", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Guaraná Powder", category="superfruits", moq="100 KG", specs="Powder; organic available", sku="IB-030", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Guaraná Seed", category="nuts_seeds", moq="100 KG", specs="Grains; organic available", sku="IB-031", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Guava", category="juices", moq="Please request", specs="Single strength / clarified-concentrated / powder; organic available", sku="IB-032", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Hibiscus Soluble Tea", category="herbs_roots", moq="100 KG", specs="Soluble tea", sku="IB-033", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Jambu (Paracress)", category="herbs_roots", moq="10 KG", specs="Powder / cut", sku="IB-034", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Lime", category="juices", moq="Please request", specs="Single strength / clarified-concentrated / powder; organic available", sku="IB-035", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Lithothamnion Algae Powder", category="specialties", moq="25 KG", specs="Mineral algae powder", sku="IB-036", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Mandarin Juice", category="juices", moq="Please request", specs="Juice / clarified-concentrated", sku="IB-037", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Melon Juice", category="juices", moq="Please request", specs="Juice / clarified-concentrated", sku="IB-038", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Moringa Powder", category="herbs_roots", moq="20 KG", specs="Powder; organic available", sku="IB-039", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Muirapuama", category="herbs_roots", moq="100 KG", specs="Extract / powder / cut", sku="IB-040", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Ora Pro Nobis (Lemon Vine)", category="herbs_roots", moq="10 KG", specs="Powder / freeze dried; organic available", sku="IB-041", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Orange", category="juices", moq="Please request", specs="Single strength / clarified-concentrated / powder; organic available", sku="IB-042", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Papaya Pulp", category="juices", moq="Please request", specs="Pulp; organic available", sku="IB-043", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Passion Fruit Pulp", category="juices", moq="Please request", specs="Pulp", sku="IB-044", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Pau D'Arco", category="herbs_roots", moq="100 KG", specs="Powder / cut", sku="IB-045", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Pfaffia Paniculata (Brazilian Ginseng) Powder", category="herbs_roots", moq="100 KG", specs="Powder / cut", sku="IB-046", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Pineapple Juice", category="juices", moq="Please request", specs="Juice / clarified-concentrated", sku="IB-047", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Pitaya (Dragon Fruit)", category="superfruits", moq="Please request", specs="Juice / powder", sku="IB-048", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Quercetin", category="specialties", moq="100 KG", specs="Powder", sku="IB-049", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Rutin 70%", category="specialties", moq="100 KG", specs="Powder", sku="IB-050", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Strawberry Juice", category="juices", moq="Please request", specs="Single strength juice", sku="IB-051", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Tamarind Juice", category="juices", moq="Please request", specs="Single strength juice", sku="IB-052", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Tangerine Juice", category="juices", moq="Please request", specs="Single strength juice", sku="IB-053", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Watermelon Juice", category="juices", moq="Please request", specs="Juice / clarified-concentrated", sku="IB-054", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Yerba Mate 5/10 Green / Roasted", category="herbs_roots", moq="100 KG", specs="Cut; organic available", sku="IB-055", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Yerba Mate Dry Extract 8-10%", category="herbs_roots", moq="100 KG", specs="Dry extract", sku="IB-056", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Yerba Mate Leaves and Stems", category="herbs_roots", moq="100 KG", specs="Cut; organic available", sku="IB-057", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026"),
            Product(name="Yerba Mate Soluble Tea Green / Roasted", category="herbs_roots", moq="100 KG", specs="Soluble tea; organic available", sku="IB-058", certifications=[], description_en="IBIAG commercial portfolio 2026", description_pt="Portfólio comercial IBIAG 2026")
        ]
        await db.products.insert_many([p.model_dump() for p in prods])
        await db.settings.update_one({"key": "portfolio_version"}, {"$set": {"key": "portfolio_version", "value": portfolio_version, "updated_at": now_iso()}}, upsert=True)

    if await db.templates.count_documents({}) == 0:
        tps = [
            MessageTemplate(name_pt="Email Introdução", name_en="Introduction Email", category="intro", language="en",
                subject="Premium Brazilian Ingredients", body="Dear [Contact],\n\nWe are a Brazilian exporter of premium tropical ingredients (Açaí, Acerola, Coconut Water, Brazil Nuts). Would you be open to a 15-min call?\n\nBest,\n[You]"),
            MessageTemplate(name_pt="Email Introdução", name_en="Introduction Email", category="intro", language="pt",
                subject="Ingredientes Brasileiros Premium", body="Prezado(a) [Contato],\n\nSomos exportadores brasileiros de ingredientes tropicais premium. Podemos agendar uma call de 15 min?\n\nAtenciosamente,\n[Você]"),
            MessageTemplate(name_pt="Follow-up", name_en="Follow-up", category="follow_up", language="en",
                subject="Following up", body="Hi [Contact],\n\nJust checking in on our last conversation. Any questions I can help with?\n\nBest,\n[You]"),
            MessageTemplate(name_pt="Follow-up", name_en="Follow-up", category="follow_up", language="pt",
                subject="Retomando contato", body="Olá [Contato],\n\nRetomando nossa conversa. Alguma dúvida em que posso ajudar?\n\nAbraço,\n[Você]"),
            MessageTemplate(name_pt="Cotação", name_en="Quotation", category="quotation", language="en",
                subject="Commercial Quotation", body="Product: [X]\nQty: [X] MT\nPrice: USD [X.XX]/kg FOB Santos\nPayment: [Terms]\nDelivery: [X] weeks"),
            MessageTemplate(name_pt="Cotação", name_en="Quotation", category="quotation", language="pt",
                subject="Cotação Comercial", body="Produto: [X]\nQtd: [X] TM\nPreço: USD [X,XX]/kg FOB Santos\nPagamento: [Cond.]\nEntrega: [X] semanas"),
        ]
        await db.templates.insert_many([t.model_dump() for t in tps])

    # Production safety: purge the legacy demonstration prospecting dataset once.
    demo_cleanup_version = "prospecting-demo-cleanup-v1"
    if await db.settings.find_one({"key": demo_cleanup_version}) is None:
        await db.trade_data.delete_many({})
        await db.leads.delete_many({"$or": [
            {"email": {"$regex": "@.*\\.example$", "$options": "i"}},
            {"source": "trade_data", "company": {"$in": [
                "Green Nordic Beverages AB", "Bio Cosmétique Paris SAS"
            ]}}
        ]})
        await db.settings.update_one(
            {"key": demo_cleanup_version},
            {"$set": {"key": demo_cleanup_version, "value": "done", "updated_at": now_iso()}},
            upsert=True
        )

@app.on_event("startup")
async def startup():
    await seed_all()

@app.on_event("shutdown")
async def shutdown(): client.close()
