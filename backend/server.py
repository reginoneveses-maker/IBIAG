import math
import zipfile, json, hashlib, mimetypes
from dotenv import load_dotenv
from pathlib import Path
import asyncio, shutil, tempfile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, Response, BackgroundTasks, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os, logging, uuid, bcrypt, jwt, requests, io, re, unicodedata
from comexstat_client import ncm_search, general as comex_general
from comexstat_market import normalize_markets
from buyer_discovery import discover_buyers, discover_decision_maker, enrich_company, DISCOVERY_VERSION
from discovery_jobs import MARKETS, REGIONS, resolve_markets, run_discovery_job
from spec_library import supplier_spec_library, is_spec_document
from document_categories import normalize_document, matches_document, validate_classification
from finance_reporting import cashflow_rows, pending_totals, currency_code, month_keys
from pricing import decimal_number, calculate_price
from business_workflow import normalize_order, normalize_purchase, inventory_balances, validate_balances, linked_finance
from order_shipments import build_shipment, allowed_statuses as shipment_statuses, SUMMARY_FIELDS as SHIPMENT_SUMMARY_FIELDS
from commercial_quotations import QuotationCreate, QuotationEdit, QuotationState, TERMS as QUOTE_TERMS, SUMMARY as QUOTE_SUMMARY, validate_terms as validate_quote_terms, quotation_event
from commercial_invoices import InvoiceCreate as CommercialInvoiceCreate, InvoiceEdit as CommercialInvoiceEdit, InvoiceDecision as CommercialInvoiceDecision, SUMMARY as COMMERCIAL_INVOICE_SUMMARY, DETAILS as COMMERCIAL_INVOICE_DETAILS, commercial_snapshot, revision as invoice_revision, validate_details as validate_invoice_details, invoice_event
from commercial_invoice_pdf import render_invoice as render_commercial_invoice, InvoiceRenderingError
from reportlab.platypus.doctemplate import LayoutError
from contextlib import asynccontextmanager
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from api_security import cors_origins_from, validate_jwt_secret, documentation_options, SecurityResponseMiddleware
from safe_errors import install_error_handlers, failure_response
from upload_limits import read_import
from tabular_imports import read_table
from request_body_limits import RequestBodyLimits
from invoice_xml import parse_invoice_xml
from password_inputs import password_bytes, auth_validation_error
from fastapi.exceptions import RequestValidationError
from crm_access import lead_scope, require_lead, visible_lead_ids, document_scope, private_file_paths, shared_file_scope, authorize_crm_file
from discovery_permissions import paid_discovery_enabled, require_paid_discovery
from pydantic import BaseModel, Field, ConfigDict, EmailStr, ValidationError, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta

# ----- Config -----
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000, socketTimeoutMS=45000)
db = client[os.environ['DB_NAME']]
gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="ibiag_files")

JWT_SECRET = validate_jwt_secret(os.environ["JWT_SECRET"])
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
def hash_pw(pw): return bcrypt.hashpw(password_bytes(pw, minimum=8), bcrypt.gensalt()).decode()
def verify_pw(pw, h):
    try: return bcrypt.checkpw(password_bytes(pw), h.encode())
    except Exception: return False

def create_token(uid, email, session_version=0):
    return jwt.encode({"sub": uid, "email": email, "jti": str(uuid.uuid4()),
                       "sv": session_version,
                       "exp": datetime.now(timezone.utc) + timedelta(days=7)},
                      JWT_SECRET, algorithm=JWT_ALG)

async def get_current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if not isinstance(payload.get("sub"), str) or not payload["sub"] or type(payload.get("sv", 0)) is not int:
            raise jwt.InvalidTokenError()
        # Store only a one-way digest, never a bearer token, in the denylist.
        token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if await db.revoked_access_tokens.find_one({"_id": token_digest}):
            raise HTTPException(401, "Session ended")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(401, "User not found")
        if user.get("active", True) is not True or payload.get("sv", 0) != user.get("session_version", 0):
            raise HTTPException(401, "Session ended")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

def now_iso(): return datetime.now(timezone.utc).isoformat()

# ----- App -----
app = FastAPI(title="IBIAG", version="1.0.0", **documentation_options(os.environ))
install_error_handlers(app)
app.add_exception_handler(RequestValidationError, auth_validation_error)

# Explicit origins and headers; bearer authentication does not use cookies.
cors_origins = cors_origins_from(os.environ)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins,
    allow_credentials=False, allow_methods=["GET","HEAD","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type"], expose_headers=["Retry-After","Content-Disposition"])
app.add_middleware(SecurityResponseMiddleware, error_response=failure_response, allowed_origins=cors_origins)
app.add_middleware(RequestBodyLimits, allowed_origins=cors_origins)

api = APIRouter(prefix="/api")

# ----- Models -----
class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def bcrypt_password(cls, value):
        password_bytes(value)
        return value

class RegisterBody(LoginBody):
    password: str = Field(min_length=8, max_length=72)
    name: str = ""

class UserCreateBody(RegisterBody):
    role: str = "user"

class AccountActiveBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    active: bool

class PasswordChangeBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("current_password", "new_password")
    @classmethod
    def valid_password_bytes(cls, value):
        password_bytes(value)
        return value

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
    stock_reserved: float = 0
    stock_available: float = 0
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
    owner_id: str = ""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company: str
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    linkedin: str = ""
    country: str = ""
    country_code: str = ""
    search_country: str = ""
    industry: str = "beverage"
    stage: str = "new_lead"
    interested_products: List[str] = []
    product_interest: str = ""
    product_relationship: str = ""
    product_evidence: str = ""
    relationship_verified: bool = False
    decision_maker: str = ""
    decision_maker_title: str = ""
    decision_maker_email: str = ""
    decision_maker_phone: str = ""
    current_supplier: str = ""
    validation_status: str = "needs_validation"
    evidence_urls: List[str] = []
    contact_candidates: dict = Field(default_factory=dict)
    enrichment_status: str = ""
    enrichment_message: str = ""
    contact_source_urls: List[str] = []
    priority: str = "normal"
    source_url: str = ""
    decision_source_url: str = ""
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
    owner_id: str = ""
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

class OrderItem(BaseModel):
    product_id: str
    product_name: str = ""
    offer_id: str
    supplier_id: str = ""
    supplier_name: str = ""
    quantity: float
    unit: str = "kg"
    unit_price: float

class SalesOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: str = ""
    customer: str
    customer_country: str = ""
    lead_id: str = Field(default="", max_length=200, pattern=r"^[^\x00]*$")
    source_price_id: str = Field(default="", max_length=200, pattern=r"^[^\x00]*$")
    source_price_revision: str = Field(default="", max_length=64, pattern=r"^(?:[0-9a-f]{64})?$")
    source_price_snapshot: dict = Field(default_factory=dict)
    source_quote_id: str = Field(default="", max_length=80, pattern=r"^[A-Za-z0-9_-]*$")
    source_quote_revision: int = Field(default=0, strict=True, ge=0)
    source_quote_snapshot: dict = Field(default_factory=dict)
    shipment: dict = Field(default_factory=dict)
    products: str = ""
    incoterm: str = "FOB"
    total_usd: float = 0
    status: str = "draft"  # draft, confirmed, shipped, delivered, cancelled
    order_date: str = ""
    delivery_date: str = ""
    notes: str = ""
    created_at: str = Field(default_factory=now_iso)
    items: List[OrderItem] = []
    track_stock: bool = False
    receivable_due_date: str = ""
    workflow_enabled: bool = False
    finance_paid: bool = False
    finance_paid_date: str = ""
    version: int = 0
    deleted_at: str = ""

class ShipmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    version: int = Field(ge=0)
    status: Literal["planned", "booked", "in_transit", "arrived", "delivered", "cancelled"]
    mode: Literal["sea", "air", "road", "rail", "multimodal"]
    reference: str = Field(min_length=1, max_length=120, pattern=r"^[^\x00]*$")
    origin: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00]*$")
    destination: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00]*$")
    responsible_id: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00]*$")
    carrier: str = Field(default="", min_length=0, max_length=160, pattern=r"^[^\x00]*$")
    booking_reference: str = Field(default="", min_length=0, max_length=120, pattern=r"^[^\x00]*$")
    transport_reference: str = Field(default="", min_length=0, max_length=160, pattern=r"^[^\x00]*$")
    planned_departure: str = Field(min_length=10, max_length=10, pattern=r"^[^\x00]*$")
    planned_arrival: str = Field(min_length=10, max_length=10, pattern=r"^[^\x00]*$")
    actual_departure: str = Field(default="", min_length=0, max_length=10, pattern=r"^[^\x00]*$")
    actual_arrival: str = Field(default="", min_length=0, max_length=10, pattern=r"^[^\x00]*$")
    actual_delivery: str = Field(default="", min_length=0, max_length=10, pattern=r"^[^\x00]*$")
    notes: str = Field(default="", min_length=0, max_length=2000, pattern=r"^[^\x00]*$")
    change_note: str = Field(min_length=3, max_length=300, pattern=r"^[^\x00]*$")

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
    source_order_id: str = ""
    source_purchase_id: str = ""

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
    section: str = ""
    deleted_at: str = ""
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
    document_type: str = ""
    certificate_type: str = ""
    folder_path: str = ""
    lead_id: str = ""
    lead_name: str = ""
    owner_id: str = ""
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
    product_id: str = ""
    track_stock: bool = False
    stock_received: bool = False
    due_date: str = ""
    workflow_enabled: bool = False
    finance_paid: bool = False
    finance_paid_date: str = ""
    version: int = 0
    deleted_at: str = ""

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
    product_id: str = ""
    offer_id: str = ""
    quantity: float = Field(default=1, gt=0, allow_inf_nan=False)
    unit: str = "kg"
    supplier_price: float = Field(default=0, allow_inf_nan=False)  # BRL por unidade
    extra_costs: float = Field(default=0, allow_inf_nan=False)  # BRL por unidade (frete, embalagem, etc)
    extras: List[dict] = []
    taxes: List[dict] = []
    taxes_pct: float = Field(default=0, allow_inf_nan=False)
    margin_pct: float = Field(default=0, allow_inf_nan=False)
    margin_mode: Literal["margin", "markup"] = "margin"  # margin (sobre venda) ou markup (sobre custo)
    currency: Literal["BRL", "USD"] = "BRL"
    exchange_rate: float = Field(default=5.0, allow_inf_nan=False)
    sell_price_brl: float = 0
    sell_price_usd: float = 0
    notes: str = ""
    updated_at: str = Field(default_factory=now_iso)
    created_at: str = Field(default_factory=now_iso)

    supplier_total: float = 0
    extras_total: float = 0
    cost_total: float = 0
    sale_total_brl: float = 0
    sale_total_usd: float = 0
    tax_total: float = 0
    profit_total: float = 0
    calculation_error: str = ""

    @model_validator(mode="before")
    @classmethod
    def legacy_quantity(cls, values):
        values = dict(values)
        match = re.fullmatch(r"(kg|l|un|t)\s*([\d.,]+)", str(values.get("unit", "")), re.I)
        if match and "quantity" not in values:
            values["unit"] = match[1].lower()
            values["quantity"] = float(decimal_number(match[2], quantity=True))
        return values

    @field_validator("quantity", "supplier_price", "extra_costs", "taxes_pct", "margin_pct", "exchange_rate", mode="before")
    @classmethod
    def localized_numbers(cls, value, info):
        return float(decimal_number(value, quantity=info.field_name == "quantity"))


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
    commission_text: str = ""
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

async def get_admin_user(user=Depends(get_current_user)):
    return require_admin(user)

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
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    record = {"id": str(uuid.uuid4()), "email": email,
              "name": body.name or email.split("@")[0],
              "password_hash": hash_pw(body.password), "role": body.role,
              "created_at": now_iso()}
    await db.users.insert_one(record)
    record.pop("password_hash", None)
    record.pop("_id", None)
    return record

@api.patch("/auth/users/{uid}/active")
async def set_account_active(uid: str, body: AccountActiveBody, user=Depends(get_admin_user)):
    # Administrative recovery requires a separate policy; never disable an
    # administrator or let concurrent role changes bypass this restriction.
    if uid == user["id"]:
        raise HTTPException(403, "Administrator accounts cannot be suspended here")
    record = await db.users.find_one_and_update(
        {"id": uid, "role": "user"},
        {"$set": {"active": body.active, "access_changed_by": user["id"], "access_changed_at": now_iso()},
         "$inc": {"session_version": 1}}, return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "password_hash": 0})
    if not record:
        if await db.users.find_one({"id": uid}, {"id": 1}):
            raise HTTPException(403, "Administrator accounts cannot be suspended here")
        raise HTTPException(404, "User not found")
    return record

# Shared MongoDB limiter: one atomic counter per email per fixed 15-minute
# window, across application workers. Never store the plaintext email here.
LOGIN_WINDOW_SECONDS = 900
LOGIN_MAX_ATTEMPTS = 5
LOGIN_IP_MAX_ATTEMPTS = 30

@api.post("/auth/login")
async def login(body: LoginBody, request: Request):
    email = body.email.lower().strip()
    now = datetime.now(timezone.utc)
    window = int(now.timestamp()) // LOGIN_WINDOW_SECONDS
    limiter_key = hashlib.sha256(f"{window}:{email}".encode("utf-8")).hexdigest()
    # Trust the socket peer, not client-controlled forwarded headers.
    peer = request.client.host if request.client else "unknown"
    peer_key = hashlib.sha256(f"peer:{window}:{peer}".encode("utf-8")).hexdigest()
    peer_attempt = await db.login_attempts.find_one_and_update(
        {"_id": peer_key},
        {"$inc": {"count": 1}, "$setOnInsert": {
            "expires_at": datetime.fromtimestamp((window + 2) * LOGIN_WINDOW_SECONDS, tz=timezone.utc)
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if peer_attempt["count"] > LOGIN_IP_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many login attempts. Try again later.",
                            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)})
    # Count attempts before credential verification, preventing concurrent
    # requests from bypassing the threshold. MongoDB $inc is atomic.
    attempt = await db.login_attempts.find_one_and_update(
        {"_id": limiter_key},
        {"$inc": {"count": 1}, "$setOnInsert": {
            "expires_at": datetime.fromtimestamp((window + 2) * LOGIN_WINDOW_SECONDS, tz=timezone.utc)
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    if attempt["count"] > LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many login attempts. Try again later.", headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)})
    user = await db.users.find_one({"email": email})
    if not user or not verify_pw(body.password, user["password_hash"]) or user.get("active", True) is not True:
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user["id"], email, user.get("session_version", 0))
    return {"access_token": token, "user": {"id": user["id"], "email": email, "name": user.get("name", ""), "role": user.get("role", "user")}}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user

@api.post("/auth/password")
async def change_password(body: PasswordChangeBody, user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    window = int(now.timestamp()) // LOGIN_WINDOW_SECONDS
    key = hashlib.sha256(f"password-change:{window}:{user['id']}".encode()).hexdigest()
    attempt = await db.login_attempts.find_one_and_update(
        {"_id": key}, {"$inc": {"count": 1}, "$setOnInsert": {
            "expires_at": datetime.fromtimestamp((window + 2) * LOGIN_WINDOW_SECONDS, tz=timezone.utc)}},
        upsert=True, return_document=ReturnDocument.AFTER)
    if attempt["count"] > LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many attempts. Try again later.", headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)})
    record = await db.users.find_one({"id": user["id"]})
    if not record or record.get("active", True) is not True or record.get("session_version", 0) != user.get("session_version", 0):
        raise HTTPException(401, "Session ended")
    if not verify_pw(body.current_password, record["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(400, "Choose a different password")
    # Compare both the hash and generation: concurrent password changes or
    # suspensions cannot overwrite newer credentials or revive a session.
    version_filter = record["session_version"] if "session_version" in record else {"$exists": False}
    result = await db.users.update_one(
        {"id": user["id"], "password_hash": record["password_hash"], "session_version": version_filter,
         "active": {"$ne": False}},
        {"$set": {"password_hash": hash_pw(body.new_password), "password_changed_at": now_iso()},
         "$inc": {"session_version": 1}})
    if not result.modified_count:
        raise HTTPException(409, "Account changed. Sign in again before retrying.")
    return {"ok": True}

@api.post("/auth/logout")
async def logout(request: Request, user=Depends(get_current_user)):
    # The current token is valid (checked by dependency). Invalidate it
    # server-side until its original expiration, including across workers.
    token = request.headers["Authorization"][7:]
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    await db.revoked_access_tokens.update_one(
        {"_id": token_digest},
        {"$setOnInsert": {"user_id": user["id"], "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc)}},
        upsert=True,
    )
    return {"ok": True}

# Deployment sync: document storage cleanup enabled.
# ============ FILES / STORAGE ============
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

@api.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Arquivo vazio ou acima do limite de 50 MB")
    ct = file.content_type or "application/octet-stream"
    result = await put_object(path, data, ct)
    return {"path": result["path"], "name": file.filename, "size": result.get("size", len(data)), "content_type": ct}

@api.get("/files/{full_path:path}")
async def download_file(full_path: str, user=Depends(get_current_user)):
    await authorize_crm_file(db, user, full_path)
    allowed_prefix = f"{APP_NAME}/uploads/{user['id']}/"
    if user.get("role") != "admin" and not full_path.startswith(allowed_prefix):
        # Published documents are shared with authenticated IBIAG team members;
        # unregistered uploads and trashed documents remain private.
        published = await db.documents.find_one({"file_path": full_path, "deleted_at": {"$in": [None, ""]}})
        if not published:
            published = await db.specs.find_one({"$or": [{"original_file_path": full_path}, {"ibiag_file_path": full_path}], "deleted_at": {"$in": [None, ""]}})
        if not published:
            raise HTTPException(403, "Sem permissão para acessar este arquivo")
    data, ct = await get_object(full_path)
    return Response(content=data, media_type="application/octet-stream", headers={
        "Content-Disposition": "attachment; filename=download",
        "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'none'; base-uri 'none'"})

# ============ DOCUMENTS ============
@api.post("/documents/link-batch")
async def link_document_batch(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_admin(user)
    raw = await file.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise HTTPException(413, "Plano de vínculos excede 1 MB")
    try:
        items = json.loads(raw)
        if not isinstance(items, list) or not 1 <= len(items) <= 500:
            raise ValueError("Plano deve conter de 1 a 500 vínculos")
        plan = []
        for item in items:
            digest = item["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Hash inválido")
            doc = await db.documents.find_one({"source_sha256": digest})
            supplier_name = str(item["supplier_name"]).strip()
            supplier = await db.suppliers.find_one({"name": {"$regex": f"^{re.escape(supplier_name)}$", "$options": "i"}})
            if not doc or not supplier:
                raise ValueError(f"Documento ou fornecedor não encontrado: {supplier_name}")
            if doc.get("supplier_id") and doc["supplier_id"] != supplier["id"]:
                raise ValueError("Documento já vinculado a outro fornecedor")
            product_name = str(item.get("product_name") or "").strip()
            product = None
            offers = []
            if product_name:
                product = await db.products.find_one({"name": {"$regex": f"^{re.escape(product_name)}$", "$options": "i"}})
                if not product or (doc.get("product_id") and doc["product_id"] != product["id"]):
                    raise ValueError(f"Produto não encontrado ou vínculo conflitante: {product_name}")
                offers = await db.product_offers.find({"product_id": product["id"], "supplier_id": supplier["id"]}).to_list(100)
                if not offers:
                    raise ValueError(f"Oferta produto/fornecedor não encontrada: {product_name} / {supplier_name}")
            kind = item.get("kind", "spec")
            if kind not in {"spec", "other"}:
                raise ValueError("Tipo de vínculo inválido")
            plan.append((doc, supplier, product, offers, kind))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, f"Plano não aplicado: {exc}")
    linked_offers = set()
    for doc, supplier, product, offers, kind in plan:
        fields = {"supplier_id": supplier["id"], "supplier_name": supplier["name"]}
        if product:
            fields.update(product_id=product["id"], product_name=product["name"])
        await db.documents.update_one({"id": doc["id"]}, {"$set": fields})
        for offer in offers:
            key = "spec_document_ids" if kind == "spec" else "other_document_ids"
            await db.product_offers.update_one({"id": offer["id"]}, {"$addToSet": {key: doc["id"]}})
            linked_offers.add(offer["id"])
    return {"documents": len(plan), "offers": len(linked_offers)}

@api.post("/documents/metadata-batch")
async def update_document_metadata_batch(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_admin(user)
    raw = await file.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "Plano de metadados excede 2 MB")
    categories = {"Produtos", "Fornecedores", "Qualidade & Compliance", "Clientes & Comercial", "Financeiro & Fiscal", "Societário", "Exportação & Logística"}
    try:
        items = json.loads(raw)
        if not isinstance(items, list) or not 1 <= len(items) <= 1000:
            raise ValueError("Plano deve conter de 1 a 1000 documentos")
        plan, not_found = [], []
        for item in items:
            digest = str(item["sha256"]).lower().strip()
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Hash inválido")
            doc = await db.documents.find_one({"source_sha256": digest})
            if not doc:
                not_found.append(digest)
                continue
            fields = {}
            if item.get("category"):
                category = str(item["category"]).strip()
                if category not in categories:
                    raise ValueError(f"Categoria inválida: {category}")
                fields["category"] = category
            for key in ("title", "notes", "document_type", "certificate_type"):
                if key in item:
                    fields[key] = str(item.get(key) or "").strip()
            if "folder_path" in item:
                folder_path = "/".join(p.strip() for p in str(item.get("folder_path") or "").replace("\\", "/").split("/") if p.strip())
                if ".." in folder_path.split("/"):
                    raise ValueError("Caminho de pasta inválido")
                fields["folder_path"] = folder_path[:500]
            for entity, collection in (("supplier", db.suppliers), ("product", db.products)):
                name_key, id_key = f"{entity}_name", f"{entity}_id"
                if item.get(name_key):
                    requested = str(item[name_key]).strip()
                    found = await collection.find_one({"name": {"$regex": f"^{re.escape(requested)}$", "$options": "i"}})
                    if found:
                        fields[id_key], fields[name_key] = found["id"], found["name"]
                    else:
                        fields[name_key] = requested
            plan.append((doc["id"], fields))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, f"Plano de metadados inválido: {exc}")
    for doc_id, fields in plan:
        if fields:
            await db.documents.update_one({"id": doc_id}, {"$set": fields})
    return {"updated": len(plan), "not_found": len(not_found), "not_found_sha256": not_found[:100]}

@api.post("/documents/import-batch")
async def import_document_batch(file: UploadFile = File(...), user=Depends(get_current_user)):
    require_admin(user)
    raw = await file.read(50 * 1024 * 1024 + 1)
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(413, "Lote excede 50 MB")
    categories = {"Produtos", "Fornecedores", "Qualidade & Compliance", "Clientes & Comercial", "Financeiro & Fiscal", "Societário", "Exportação & Logística"}
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        entries = archive.infolist()
        if len(entries) > 101 or len({x.filename for x in entries}) != len(entries):
            raise ValueError("Lote inválido ou com entradas duplicadas")
        if any(x.file_size > 48 * 1024 * 1024 for x in entries) or sum(x.file_size for x in entries) > 80 * 1024 * 1024:
            raise ValueError("Arquivos excedem o limite")
        manifest = json.loads(archive.read("manifest.json"))
        if not isinstance(manifest, list) or not 1 <= len(manifest) <= 100:
            raise ValueError("Manifesto deve conter de 1 a 100 documentos")
        plan = []
        seen = set()
        for item in manifest:
            path = item["path"]
            if not re.fullmatch(r"files/[0-9]+\.pdf", path) or path in seen:
                raise ValueError("Caminho inválido ou repetido")
            seen.add(path)
            data = archive.read(path)
            if not data.startswith(b"%PDF-"):
                raise ValueError("Somente PDFs válidos são aceitos")
            name = str(item["file_name"]).replace("\\", "/").split("/")[-1]
            category = item["category"]
            if category not in categories or not name.lower().endswith(".pdf"):
                raise ValueError("Nome ou categoria inválidos")
            item["folder_path"] = normalize_folder_path(item.get("folder_path"))
            plan.append((item, name, category, data, hashlib.sha256(data).hexdigest()))
    except (ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as exc:
        raise HTTPException(400, f"Lote inválido: {exc}")
    # Validate the entire archive before storing anything. Exact hashes allow safe retries.
    imported = skipped = 0
    for item, name, category, data, digest in plan:
        existing = await db.documents.find_one({"source_sha256": digest})
        if existing:
            skipped += 1
            continue
        path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.pdf"
        await put_object(path, data, "application/pdf")
        folder_path = item["folder_path"]
        document = Document(title=str(item.get("title") or name), category=category,
                            file_path=path, file_name=name, content_type="application/pdf", size=len(data),
                            tags=["importado", "arquivo original"], notes=str(item.get("notes") or ""),
                            supplier_id=str(item.get("supplier_id") or ""), supplier_name=str(item.get("supplier_name") or ""),
                            product_id=str(item.get("product_id") or ""), product_name=str(item.get("product_name") or ""),
                            document_type=str(item.get("document_type") or ""), certificate_type=str(item.get("certificate_type") or ""),
                            folder_path=folder_path[:500])
        record = document.model_dump()
        record.update(source_sha256=digest, owner_id=user["id"])
        try:
            await register_folder_path(folder_path, user)
            await db.documents.insert_one(record)
        except Exception:
            await delete_object(path)
            raise
        imported += 1
    return {"imported": imported, "skipped": skipped, "total": len(plan)}

def normalize_folder_path(value):
    parts = str(value or "").replace("\\", "/").split("/")
    if any(p.strip() in {".", ".."} or any(ord(c) < 32 for c in p) for p in parts):
        raise HTTPException(400, "Caminho de pasta inválido")
    path = "/".join(p.strip() for p in parts if p.strip())
    if len(path) > 500:
        raise HTTPException(400, "Caminho de pasta acima de 500 caracteres")
    return path

async def register_folder_path(path, user=None):
    parts = path.split("/") if path else []
    for i in range(1, len(parts) + 1):
        parent = "/".join(parts[:i])
        owner_id = user["id"] if user else ""
        key = hashlib.sha256((owner_id + "\0" + parent).encode()).hexdigest()
        await db.document_folders.update_one({"_id": key}, {"$setOnInsert": {"path": parent, "owner_id": owner_id}}, upsert=True)

class DocumentFolderBody(BaseModel):
    path: str

@api.get("/document-folders")
async def list_document_folders(user=Depends(get_current_user)):
    paths = set()
    async for record in db.document_folders.find(lead_scope(user), {"_id": 0}):
        paths.add(record["path"])
    async for record in db.documents.find(await document_scope(db, user, {"deleted_at": {"$in": [None, ""]}}), {"folder_path": 1}):
        path = record.get("folder_path", "")
        parts = path.split("/") if path else []
        paths.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
    return sorted(paths)

@api.post("/document-folders")
async def create_document_folder(body: DocumentFolderBody, user=Depends(get_current_user)):
    path = normalize_folder_path(body.path)
    if not path:
        raise HTTPException(400, "Informe o nome da pasta")
    await register_folder_path(path, user)
    return {"path": path}

async def document_records(user, category=None, section=None, search="", lead_id=None, trash=False):
    query = {"deleted_at": {"$exists": True, "$nin": [None, ""]}} if trash else {"deleted_at": {"$in": [None, ""]}}
    if lead_id:
        await require_lead(db, user, lead_id)
        query["lead_id"] = lead_id
    query = await document_scope(db, user, query)
    async for raw in db.documents.find(query, {"_id": 0}).sort([("created_at", -1), ("id", 1)]):
        record = normalize_document(raw)
        if not trash and not matches_document(record, category, section):
            continue
        text = " ".join(str(record.get(k, "")) for k in ("title", "file_name", "category", "notes", "tags", "folder_path", "product_name", "supplier_name", "lead_name"))
        if search and search.casefold() not in text.casefold():
            continue
        yield record

@api.get("/documents/page")
async def documents_page(category: Optional[str] = None, section: Optional[str] = None,
                         search: str = "", lead_id: Optional[str] = None, trash: bool = False,
                         skip: int = 0, limit: int = 250, user=Depends(get_current_user)):
    if trash:
        require_admin(user)
    skip, limit = max(0, skip), min(500, max(1, limit))
    items, total = [], 0
    async for record in document_records(user, category, section, search, lead_id, trash):
        if skip <= total < skip + limit:
            items.append(record)
        total += 1
    return {"items": items, "total": total, "skip": skip, "limit": limit}

@api.get("/documents", response_model=List[Document])
async def list_docs(category: Optional[str] = None, section: Optional[str] = None,
                    lead_id: Optional[str] = None, user=Depends(get_current_user)):
    # Retain the list contract used by portfolio and legacy panels without silently truncating.
    return [d async for d in document_records(user, category, section, lead_id=lead_id)]

async def validate_document_metadata(d, user):
    try:
        d.category, d.section = validate_classification(d.category, d.section)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if user.get("role") != "admin" and (not d.lead_id or d.category in {"Financeiro & Fiscal", "Societário"}):
        raise HTTPException(403, "Publicação de documentos da empresa exige administrador")
    if not d.title.strip():
        raise HTTPException(400, "Título obrigatório")
    d.title = d.title.strip()
    d.folder_path = normalize_folder_path(d.folder_path)
    for field, name, collection in [("product_id", "product_name", db.products), ("supplier_id", "supplier_name", db.suppliers), ("lead_id", "lead_name", db.leads)]:
        value = getattr(d, field)
        if value:
            record = await collection.find_one(lead_scope(user, {"id": value}) if field == "lead_id" else {"id": value})
            if not record:
                raise HTTPException(400, "Vínculo não encontrado: " + field)
            setattr(d, name, record.get("company", record.get("name", "")))
        else:
            setattr(d, name, "")
    d.owner_id = user["id"]
    d.deleted_at = ""

@api.post("/documents", response_model=Document)
async def create_doc(d: Document, user=Depends(get_current_user)):
    await validate_document_metadata(d, user)
    if not d.file_path.startswith(f"{APP_NAME}/uploads/{user['id']}/"):
        raise HTTPException(403, "O arquivo deve pertencer ao usuário que o enviou")
    await authorize_crm_file(db, user, d.file_path)
    _, d.content_type = await get_object(d.file_path)
    if await db.documents.find_one({"id": d.id}):
        raise HTTPException(409, "Documento já cadastrado")
    await register_folder_path(d.folder_path, user)
    await db.documents.insert_one(d.model_dump())
    return d

@api.post("/documents/upload", response_model=Document)
async def upload_document(file: UploadFile = File(...), metadata: str = Form(...), user=Depends(get_current_user)):
    import json
    try:
        values = json.loads(metadata)
        if not isinstance(values, dict):
            raise ValueError("Metadados inválidos")
        d = Document(**{**values, "id": str(uuid.uuid4()), "file_path": "pending", "file_name": file.filename or "arquivo"})
    except (ValueError, TypeError):
        raise HTTPException(400, "Metadados do documento inválidos")
    await validate_document_metadata(d, user)
    upload = await upload_file(file, user)
    d.file_path, d.content_type, d.size = upload["path"], upload["content_type"], upload["size"]
    try:
        await register_folder_path(d.folder_path, user)
        await db.documents.insert_one(d.model_dump())
    except Exception:
        await delete_object(d.file_path)
        raise
    return d

class DocumentClassification(BaseModel):
    category: str
    section: str = ""
    title: Optional[str] = None
    notes: Optional[str] = None
    document_type: Optional[str] = None
    certificate_type: Optional[str] = None
    folder_path: Optional[str] = None

@api.get("/documents/trash", response_model=List[Document])
async def document_trash(user=Depends(get_current_user)):
    require_admin(user)
    records = await db.documents.find({"deleted_at": {"$exists": True, "$nin": [None, ""]}}, {"_id": 0}).sort("deleted_at", -1).to_list(10000)
    return [normalize_document(d) for d in records]

@api.patch("/documents/{did}/classification", response_model=Document)
async def classify_document(did: str, body: DocumentClassification, user=Depends(get_current_user)):
    require_admin(user)
    try:
        category, section = validate_classification(body.category, body.section)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    changes = {"category": category, "section": section, "updated_at": now_iso()}
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(400, "Título obrigatório")
        changes["title"] = body.title.strip()
    if body.notes is not None:
        changes["notes"] = body.notes
    if body.document_type is not None:
        changes["document_type"] = body.document_type.strip()
    if body.certificate_type is not None:
        changes["certificate_type"] = body.certificate_type.strip()
    if body.folder_path is not None:
        changes["folder_path"] = normalize_folder_path(body.folder_path)
        await register_folder_path(changes["folder_path"], user)
    result = await db.documents.update_one({"id": did}, {"$set": changes})
    if not result.matched_count:
        raise HTTPException(404, "Documento não encontrado")
    return normalize_document(await db.documents.find_one({"id": did}, {"_id": 0}))

@api.post("/documents/{did}/restore", response_model=Document)
async def restore_document(did: str, user=Depends(get_current_user)):
    require_admin(user)
    result = await db.documents.update_one({"id": did}, {"$unset": {"deleted_at": "", "deleted_by": ""}})
    if not result.matched_count:
        raise HTTPException(404, "Documento não encontrado")
    return normalize_document(await db.documents.find_one({"id": did}, {"_id": 0}))

@api.delete("/documents/{did}")
async def delete_doc(did: str, user=Depends(get_current_user)):
    require_admin(user)
    doc = await db.documents.find_one({"id": did}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    await db.documents.update_one({"id": did}, {"$set": {"deleted_at": now_iso(), "deleted_by": user["id"]}})
    return {"deleted": 1, "file_deleted": False, "restorable": True}

# ============ SUPPLIERS ============
@api.get("/suppliers", response_model=List[Supplier])
async def list_sup(user=Depends(get_current_user)):
    return await db.suppliers.find({}, {"_id": 0}).to_list(1000)

@api.post("/suppliers", response_model=Supplier)
async def create_sup(s: Supplier, user=Depends(get_admin_user)):
    await db.suppliers.insert_one(s.model_dump()); return s

@api.put("/suppliers/{sid}", response_model=Supplier)
async def upd_sup(sid: str, s: Supplier, user=Depends(get_admin_user)):
    s.id = sid; await db.suppliers.replace_one({"id": sid}, s.model_dump()); return s

@api.delete("/suppliers/{sid}")
async def del_sup(sid: str, user=Depends(get_admin_user)):
    require_admin(user)
    async with business_write_lock() as ensure_owned:
        supplier = await db.suppliers.find_one({"id": sid}, {"_id": 0})
        if not supplier:
            raise HTTPException(404, "Fornecedor não encontrado")
        checks = [
            (db.product_offers, {"supplier_id": sid}),
            (db.purchases, {"supplier_id": sid}),
            (db.orders, {"items.supplier_id": sid}),
            (db.quotations, {"items.supplier_id": sid}),
            (db.contracts, {"supplier_id": sid}),
            (db.certifications, {"supplier_id": sid}),
            (db.documents, {"supplier_id": sid}),
            (db.specs, {"supplier_id": sid}),
        ]
        for collection, query in checks:
            if await collection.find_one(query, {"_id": 1}):
                raise HTTPException(409, "Fornecedor vinculado ao histórico comercial não pode ser excluído.")
        await ensure_owned()
        r = await db.suppliers.delete_one({"id": sid})
        return {"deleted": r.deleted_count}

# ============ INVOICES ============
@api.get("/invoices", response_model=List[Invoice])
async def list_inv(kind: Optional[str] = None, user=Depends(get_admin_user)):
    q = {"kind": kind} if kind else {}
    return await db.invoices.find(q, {"_id": 0}).sort("issue_date", -1).to_list(1000)

@api.post("/invoices", response_model=Invoice)
async def create_inv(i: Invoice, user=Depends(get_admin_user)):
    await db.invoices.insert_one(i.model_dump()); return i

@api.delete("/invoices/{iid}")
async def del_inv(iid: str, user=Depends(get_admin_user)):
    r = await db.invoices.delete_one({"id": iid}); return {"deleted": r.deleted_count}

@api.post("/invoices/parse-xml")
async def parse_nfe_xml(file: UploadFile = File(...), user=Depends(get_admin_user)):
    """Parse Brazilian NF-e XML and extract main fields."""
    return await parse_invoice_xml(file)

@asynccontextmanager
async def business_write_lock():
    """Serialize stock-affecting writes across API processes on standalone MongoDB.

    One order/purchase document is committed atomically. Stock and linked accounts
    are derived from that ledger, so a process crash cannot leave half a movement.
    """
    key = "business-workflow-lock"
    try:
        await db.workflow_locks.update_one({"_id": key}, {"$setOnInsert": {"_id": key, "locked_until": ""}}, upsert=True)
    except DuplicateKeyError:
        # Another process created the unique lock document first.
        pass
    owner = str(uuid.uuid4())
    now = now_iso()
    lock = await db.workflow_locks.find_one_and_update(
        {"_id": key, "locked_until": {"$lte": now}},
        {"$set": {"lock_owner": owner, "locked_until": (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()}},
        return_document=ReturnDocument.AFTER)
    if not lock:
        raise HTTPException(409, "Outra operação de estoque está em andamento. Tente novamente.")
    async def ensure_owned():
        threshold = (datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat()
        if not await db.workflow_locks.find_one({"_id": key, "lock_owner": owner, "locked_until": {"$gt": threshold}}):
            raise HTTPException(409, "A operação demorou mais que o permitido. Recarregue e tente novamente.")
    try:
        yield ensure_owned
    finally:
        await db.workflow_locks.update_one({"_id": key, "lock_owner": owner}, {"$set": {"locked_until": ""}, "$unset": {"lock_owner": ""}})

async def business_snapshot():
    active = {"deleted_at": {"$in": [None, ""]}}
    products = await db.products.find({}, {"_id": 0}).to_list(None)
    orders = await db.orders.find(active, {"_id": 0}).to_list(None)
    purchases = await db.purchases.find(active, {"_id": 0}).to_list(None)
    return products, orders, purchases

async def all_finance_entries():
    _, orders, purchases = await business_snapshot()
    manual = await db.finance.find({}, {"_id": 0}).to_list(None)
    return manual + linked_finance(orders, purchases)

def version_query(record):
    version = int(record.get("version") or 0)
    if version:
        return {"id": record["id"], "version": version}
    return {"id": record["id"], "version": {"$in": [None, 0]}}

async def save_order_workflow(order, create=False, shipment_input=None, shipment_actor=None):
    quote_source = None
    async with business_write_lock() as ensure_owned:
        previous = await db.orders.find_one({"id": order.id}, {"_id": 0})
        if not create and not previous:
            raise HTTPException(404, "Pedido não encontrado")
        if create and previous:
            raise HTTPException(409, "Registro já existente. Recarregue para verificar o resultado anterior.")
        if previous and previous.get("deleted_at"):
            raise HTTPException(409, "Pedido arquivado")
        if previous and int(order.version or 0) != int(previous.get("version") or 0):
            raise HTTPException(409, "Pedido alterado por outra operação. Recarregue antes de salvar.")
        stored_shipment = (previous or {}).get("shipment") or {}
        if shipment_input is not None:
            require_admin(shipment_actor)
            try:
                # Read the commercial fields from the locked current record,
                # never from a second pre-lock read or the logistics request.
                order = SalesOrder(**previous)
                responsibles = await db.users.find({"id": shipment_input.responsible_id},
                    {"id": 1, "name": 1, "email": 1, "active": 1, "role": 1}).to_list(2)
                responsible = responsibles[0] if len(responsibles) == 1 else None
                order.shipment, order.status = build_shipment(previous,
                    shipment_input.model_dump(exclude={"version", "change_note"}), shipment_actor,
                    responsible, shipment_input.change_note, now_iso(), datetime.now(timezone.utc).date())
            except OverflowError as exc:
                raise HTTPException(413, str(exc)) from None
            except (ValueError, TypeError):
                raise HTTPException(400, "Revise situação, responsável, datas e regras do embarque.") from None
        else:
            order.shipment = stored_shipment
            if stored_shipment and order.status != previous.get("status"):
                if stored_shipment.get("status") != "cancelled" or order.status not in {"draft", "confirmed", "cancelled"}:
                    raise HTTPException(409, "Use o fluxo de embarque para alterar a situação deste pedido.")
        if previous:
            stored_quote = previous.get("source_quote_id", "")
            if "source_quote_id" in order.model_fields_set and order.source_quote_id != stored_quote:
                raise HTTPException(409, "A origem da cotação não pode ser trocada.")
            if stored_quote and (order.incoterm != previous.get("incoterm") or
                                ("lead_id" in order.model_fields_set and order.lead_id != previous.get("lead_id"))):
                raise HTTPException(409, "Cliente e Incoterm da cotação devem ser preservados.")
            for key, default in (("source_quote_id", ""), ("source_quote_revision", 0), ("source_quote_snapshot", {})):
                setattr(order, key, previous.get(key, default))
            stored_source = previous.get("source_price_id", "")
            if "source_price_id" in order.model_fields_set and order.source_price_id != stored_source:
                raise HTTPException(409, "A origem do cálculo não pode ser trocada. Crie outro rascunho.")
            for key in ("source_price_id", "source_price_revision", "source_price_snapshot"):
                setattr(order, key, previous.get(key, {} if key.endswith("snapshot") else ""))
            if stored_source or stored_quote:
                if [item.model_dump() for item in order.items] != previous.get("items", []):
                    raise HTTPException(409, "Itens de cálculo vinculado não podem ser alterados. Recalcule e crie outro rascunho.")
        elif order.source_quote_id:
            if order.status != "draft" or order.source_price_id:
                raise HTTPException(400, "Cotação gera somente rascunho, sem outra origem de cálculo.")
            quote_source = await order_quote_source(order.source_quote_id)
            if order.source_quote_revision != quote_source["source_quote_revision"]:
                raise HTTPException(409, "A cotação mudou. Reabra a conferência.")
            for key in ("lead_id", "customer", "customer_country", "incoterm", "source_quote_snapshot"):
                setattr(order, key, quote_source[key])
            order.items = [OrderItem(**item) for item in quote_source["items"]]
            order.source_price_revision = ""
            order.source_price_snapshot = {}
        elif order.source_price_id:
            order.source_quote_revision = 0
            order.source_quote_snapshot = {}
            if order.status != "draft":
                raise HTTPException(400, "Pedido a partir de cálculo deve começar em rascunho.")
            source = await order_price_source(order.source_price_id)
            if order.source_price_revision != source["source_price_revision"]:
                raise HTTPException(409, "O cálculo mudou. Abra novamente a origem e confira antes de salvar.")
            order.items = [OrderItem(**item) for item in source["items"]]
            order.source_price_snapshot = source["source_price_snapshot"]
        else:
            order.source_price_revision = ""
            order.source_price_snapshot = {}
            order.source_quote_revision = 0
            order.source_quote_snapshot = {}
        # Older API clients may omit the new relationship. Never erase it as a
        # side effect of an unrelated update, nor rewrite a commercial snapshot.
        if previous and "lead_id" not in order.model_fields_set:
            order.lead_id = previous.get("lead_id", "")
        previous_lead = (previous or {}).get("lead_id", "")
        if previous and previous.get("status") != "draft" and order.lead_id != previous_lead:
            raise HTTPException(409, "O cliente do CRM só pode ser alterado em rascunho.")
        if order.lead_id:
            matches = await db.leads.find({"id": order.lead_id}, {"company": 1, "country": 1}).limit(2).to_list(2)
            if not matches:
                raise HTTPException(404, "Empresa do CRM não encontrada")
            if len(matches) != 1:
                raise HTTPException(409, "Identificador duplicado no CRM. Revise o cadastro antes de vincular.")
            lead = matches[0]
            if previous and previous_lead == order.lead_id:
                order.customer = previous["customer"]
                order.customer_country = previous.get("customer_country", "")
            elif quote_source:
                order.customer = quote_source["customer"]
                order.customer_country = quote_source["customer_country"]
            else:
                if not isinstance(lead.get("company"), str) or not lead["company"].strip() or not isinstance(lead.get("country", ""), str):
                    raise HTTPException(400, "Revise nome e país da empresa no CRM antes de vincular.")
                order.customer = lead["company"]
                order.customer_country = lead.get("country", "")
        products, orders, purchases = await business_snapshot()
        offers = await db.product_offers.find({}, {"_id": 0}).to_list(None)
        try:
            result = normalize_order(order.model_dump(), previous, {p["id"]:p for p in products}, {o["id"]:o for o in offers},
                                     frozen_items=order.source_quote_snapshot.get("items") if order.source_quote_id else None)
            validate_balances(inventory_balances(products, [o for o in orders if o["id"] != order.id]+[result], purchases))
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        if order.source_quote_id:
            expected_items = (order.source_quote_snapshot or {}).get("items")
            if result["items"] != expected_items:
                raise HTTPException(409, "O cadastro comercial mudou. Revise a cotação antes de continuar.")
        if previous and await db.commercial_invoices.find_one({"order_id": order.id, "status": {"$in": ["draft", "approved"]}}, {"_id": 1}):
            try:
                unchanged = invoice_revision(commercial_snapshot(result)) == invoice_revision(commercial_snapshot(previous))
            except (TypeError, ValueError):
                unchanged = False
            if result["status"] not in {"confirmed", "shipped", "delivered"} or not unchanged:
                raise HTTPException(409, "Pedido vinculado a Commercial Invoice ativa. Cancele o documento antes de alterar a venda.")
        result.update(version=int((previous or {}).get("version") or 0)+1, updated_at=now_iso())
        await ensure_owned()
        if previous:
            saved = await db.orders.replace_one(version_query(previous), result)
            if not saved.matched_count:
                raise HTTPException(409, "Pedido alterado. Recarregue e tente novamente.")
        else:
            await db.orders.insert_one(result)
        return result

async def save_purchase_workflow(purchase, create=False):
    async with business_write_lock() as ensure_owned:
        previous = await db.purchases.find_one({"id": purchase.id}, {"_id": 0})
        if not create and not previous:
            raise HTTPException(404, "Compra não encontrada")
        if create and previous:
            raise HTTPException(409, "Registro já existente. Recarregue para verificar o resultado anterior.")
        if previous and previous.get("deleted_at"):
            raise HTTPException(409, "Compra arquivada")
        if previous and int(purchase.version or 0) != int(previous.get("version") or 0):
            raise HTTPException(409, "Compra alterada por outra operação. Recarregue antes de salvar.")
        products, orders, purchases = await business_snapshot()
        suppliers = await db.suppliers.find({}, {"_id": 0}).to_list(None)
        try:
            body = purchase.model_dump()
            body["updated_at"] = now_iso()
            result = normalize_purchase(body, previous, {p["id"]:p for p in products}, {s["id"]:s for s in suppliers})
            validate_balances(inventory_balances(products, orders, [p for p in purchases if p["id"] != purchase.id]+[result]))
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        result.update(version=int((previous or {}).get("version") or 0)+1)
        await ensure_owned()
        if previous:
            saved = await db.purchases.replace_one(version_query(previous), result)
            if not saved.matched_count:
                raise HTTPException(409, "Compra alterada. Recarregue e tente novamente.")
        else:
            await db.purchases.insert_one(result)
        return result

# ============ SALES ORDERS ============
@api.get("/orders", response_model=List[SalesOrder])
async def list_ord(status: Optional[str] = None, archived: bool = False, user=Depends(get_admin_user)):
    if archived: require_admin(user)
    q = {"deleted_at": {"$nin": [None, ""]}} if archived else {"deleted_at": {"$in": [None, ""]}}
    if status: q["status"] = status
    return await db.orders.find(q, {"_id": 0}).sort("order_date", -1).to_list(1000)

@api.post("/orders", response_model=SalesOrder)
async def create_ord(o: SalesOrder, user=Depends(get_admin_user)):
    return await save_order_workflow(o, create=True)

@api.put("/orders/{oid}", response_model=SalesOrder)
async def upd_ord(oid: str, o: SalesOrder, user=Depends(get_admin_user)):
    o.id = oid
    return await save_order_workflow(o)

def shipment_order_view(record):
    return {**{key: record.get(key) for key in ("id", "number", "customer", "status", "version")},
            "shipment": record.get("shipment") or {}, "allowed_statuses": shipment_statuses(record)}

@api.get("/orders/{oid}/shipment")
async def get_order_shipment(oid: str, user=Depends(get_admin_user)):
    record = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Pedido não encontrado")
    return shipment_order_view(record)

@api.put("/orders/{oid}/shipment")
async def put_order_shipment(oid: str, body: ShipmentInput, user=Depends(get_admin_user)):
    record = await save_order_workflow(SalesOrder(id=oid, customer="", version=body.version),
                                       shipment_input=body, shipment_actor=user)
    return shipment_order_view(record)

@api.get("/shipments")
async def list_shipments(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=250),
                         status: Optional[Literal["planned", "booked", "in_transit", "arrived", "delivered", "cancelled"]] = None,
                         archived: bool = False, user=Depends(get_admin_user)):
    query = {"shipment.status": status if status else {"$exists": True},
             "deleted_at": {"$nin": [None, ""]} if archived else {"$in": [None, ""]}}
    projection = {"_id": 0, **{key: 1 for key in ("id", "number", "customer", "status", "version")},
                  **{"shipment." + key: 1 for key in SHIPMENT_SUMMARY_FIELDS}}
    return await db.orders.find(query, projection).sort("id", 1).skip(skip).limit(limit).to_list(limit)

@api.delete("/orders/{oid}")
async def del_ord(oid: str, user=Depends(get_admin_user)):
    require_admin(user)
    async with business_write_lock() as ensure_owned:
        record = await db.orders.find_one({"id": oid}, {"_id": 0})
        if not record: raise HTTPException(404, "Pedido não encontrado")
        if record.get("status") not in {"draft", "cancelled"}:
            raise HTTPException(400, "Cancele o pedido antes de arquivá-lo")
        if await db.commercial_invoices.find_one({"order_id": oid, "status": {"$in": ["draft", "approved"]}}, {"_id": 1}):
            raise HTTPException(409, "Commercial Invoice ativa impede arquivar o pedido.")
        await ensure_owned()
        await db.orders.update_one({"id": oid}, {"$set": {"deleted_at": now_iso()}})
        return {"deleted": 1, "restorable": True}

async def restore_business_record(collection, rid, user):
    require_admin(user)
    async with business_write_lock() as ensure_owned:
        record = await collection.find_one({"id": rid}, {"_id": 0})
        if not record: raise HTTPException(404, "Registro não encontrado")
        if record.get("status") not in {"draft", "cancelled"}:
            raise HTTPException(400, "Registro com movimentação não pode ser restaurado por esta ação")
        await ensure_owned()
        await collection.update_one(version_query(record), {"$set": {"deleted_at": "", "version": int(record.get("version") or 0)+1}})
        return {"restored": True}

@api.post("/orders/{oid}/restore")
async def restore_order(oid: str, user=Depends(get_admin_user)):
    return await restore_business_record(db.orders, oid, user)

@api.post("/purchases/{pid}/restore")
async def restore_purchase(pid: str, user=Depends(get_admin_user)):
    return await restore_business_record(db.purchases, pid, user)

# ============ COMMERCIAL INVOICES (NOT NF-e) ============
async def invoice_order(oid):
    records = await db.orders.find({"id": oid}, {"_id": 0}).limit(2).to_list(2)
    if not records: raise HTTPException(404, "Pedido não encontrado")
    if len(records) != 1: raise HTTPException(409, "Pedido ambíguo. Solicite revisão.")
    order = records[0]
    if order.get("deleted_at") or order.get("workflow_enabled") is not True or order.get("status") not in {"confirmed", "shipped", "delivered"}:
        raise HTTPException(409, "Commercial Invoice exige pedido confirmado, embarcado ou entregue e não arquivado.")
    return order

async def invoice_source(oid):
    order = await invoice_order(oid)
    try: snapshot = commercial_snapshot(order)
    except (TypeError, ValueError): raise HTTPException(400, "Revise cliente, itens, valores e Incoterm no pedido.") from None
    return {"order_id": oid, "source_order_version": order["version"], "source_order_revision": invoice_revision(snapshot),
            "source_order_snapshot": snapshot}

async def invoice_record(iid):
    records = await db.commercial_invoices.find({"id": iid}, {"_id": 0}).limit(2).to_list(2)
    if not records: raise HTTPException(404, "Commercial Invoice não encontrada")
    if len(records) != 1: raise HTTPException(409, "Commercial Invoice ambígua. Solicite revisão.")
    return records[0]

async def invoice_view(record):
    changed = False
    try:
        source = await invoice_source(record["order_id"])
        changed = source["source_order_revision"] != record["source_order_revision"]
    except HTTPException:
        changed = True
    return {**{k: v for k, v in record.items() if k != "_id"}, "source_changed": changed}

def check_invoice_details(record, approval=False):
    try: validate_invoice_details(record, datetime.now(timezone.utc).date(), approval)
    except (TypeError, ValueError) as exc: raise HTTPException(400, str(exc)) from None

def checked_invoice_event(record, previous, actor, reason):
    try: return invoice_event(record, previous, actor, reason, now_iso())
    except OverflowError as exc: raise HTTPException(413, str(exc)) from None
    except (TypeError, ValueError): raise HTTPException(400, "Revise o documento e o limite de histórico da invoice.") from None

async def invoice_pdf_bytes(record):
    try: return await asyncio.to_thread(render_commercial_invoice, record)
    except InvoiceRenderingError as exc: raise HTTPException(400, str(exc)) from None
    except (TypeError, ValueError, LayoutError): raise HTTPException(400, "Não foi possível renderizar o PDF. Revise tamanho, datas e conteúdo do documento.") from None

@api.get("/orders/{oid}/commercial-invoice-draft")
async def commercial_invoice_draft(oid: str, user=Depends(get_admin_user)):
    source = await invoice_source(oid)
    linked = await db.commercial_invoices.find_one({"order_id": oid, "status": {"$in": ["draft", "approved"]}}, {"_id": 0, "id": 1})
    return {**source, "active_invoice_id": linked["id"] if linked else ""}

@api.get("/commercial-invoices")
async def list_commercial_invoices(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=250),
    status: Optional[Literal["draft", "approved", "cancelled"]] = None,
    order_id: str = Query("", max_length=200, pattern=r"^[^\x00]*$"), user=Depends(get_admin_user)):
    query = {}
    if status: query["status"] = status
    if order_id: query["order_id"] = order_id
    return await db.commercial_invoices.find(query, {"_id": 0, **{k: 1 for k in COMMERCIAL_INVOICE_SUMMARY}}).sort("id", 1).skip(skip).limit(limit).to_list(limit)

@api.get("/commercial-invoices/{iid}")
async def get_commercial_invoice(iid: str, user=Depends(get_admin_user)):
    return await invoice_view(await invoice_record(iid))

@api.post("/commercial-invoices")
async def create_commercial_invoice(body: CommercialInvoiceCreate, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        if await db.commercial_invoices.find_one({"$or": [{"id": body.id}, {"reference": body.reference},
                {"order_id": body.order_id, "status": {"$in": ["draft", "approved"]}}]}, {"_id": 1}):
            raise HTTPException(409, "Pedido já possui invoice ativa ou referência/identificador já utilizado. Confira a lista.")
        source = await invoice_source(body.order_id)
        if source["source_order_version"] != body.source_order_version:
            raise HTTPException(409, "Pedido alterado. Reabra a conferência antes de salvar a invoice.")
        values = body.model_dump(exclude={"change_note"})
        values.update(source, status="draft", customer=source["source_order_snapshot"]["customer"], total_usd=source["source_order_snapshot"]["total_usd"])
        check_invoice_details(values)
        record = checked_invoice_event(values, None, user, body.change_note)
        await ensure_owned()
        await db.commercial_invoices.insert_one(dict(record))
        return await invoice_view(record)

@api.put("/commercial-invoices/{iid}")
async def edit_commercial_invoice(iid: str, body: CommercialInvoiceEdit, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        previous = await invoice_record(iid)
        if previous["version"] != body.version: raise HTTPException(409, "Invoice alterada. Recarregue antes de salvar.")
        if previous["status"] != "draft": raise HTTPException(409, "Somente rascunhos podem ser editados. Cancele e crie outro documento.")
        values = {**previous, **body.model_dump(exclude={"version", "change_note"})}
        check_invoice_details(values)
        record = checked_invoice_event(values, previous, user, body.change_note)
        await ensure_owned()
        result = await db.commercial_invoices.replace_one(version_query(previous), record)
        if not result.matched_count: raise HTTPException(409, "Invoice alterada. Recarregue antes de salvar.")
        return await invoice_view(record)

@api.post("/commercial-invoices/{iid}/status")
async def decide_commercial_invoice(iid: str, body: CommercialInvoiceDecision, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        previous = await invoice_record(iid)
        if previous["version"] != body.version: raise HTTPException(409, "Invoice alterada. Recarregue antes da decisão.")
        if previous["status"] == "cancelled" or previous["status"] == body.status:
            raise HTTPException(409, "Transição da invoice não permitida.")
        values = {**previous, "status": body.status}
        if body.status == "approved":
            if not body.details_confirmed: raise HTTPException(400, "Confirme a conferência cadastral, comercial e aduaneira antes de aprovar.")
            source = await invoice_source(previous["order_id"])
            if source["source_order_revision"] != previous["source_order_revision"]:
                raise HTTPException(409, "O pedido comercial mudou. Cancele o rascunho e prepare outra invoice.")
            check_invoice_details(values, approval=True)
            values.update(approved_by=user["id"], approved_at=now_iso())
            # Refuse unsupported glyphs/layout before committing an approved record.
            await invoice_pdf_bytes(values)
        record = checked_invoice_event(values, previous, user, body.change_note)
        await ensure_owned()
        result = await db.commercial_invoices.replace_one(version_query(previous), record)
        if not result.matched_count: raise HTTPException(409, "Invoice alterada. Recarregue antes da decisão.")
        return await invoice_view(record)

@api.get("/commercial-invoices/{iid}/pdf")
async def download_commercial_invoice(iid: str, user=Depends(get_admin_user)):
    record = await invoice_record(iid)
    if record["status"] == "approved" and (await invoice_view(record))["source_changed"]:
        raise HTTPException(409, "Pedido incompatível com a invoice. Revise a operação antes de baixar.")
    data = await invoice_pdf_bytes(record)
    current = await invoice_record(iid)
    if current["version"] != record["version"]:
        raise HTTPException(409, "Invoice alterada durante a geração. Recarregue antes de baixar.")
    # Filename comes from a validated stored ID, never a user filename/path/URL.
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(record["id"]))[:80]
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="Commercial-Invoice-{safe_id}-{record["status"]}-v{record["version"]}.pdf"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


# ============ FINANCE ============
@api.get("/finance", response_model=List[FinanceEntry])
async def list_fin(kind: Optional[str] = None, paid: Optional[bool] = None, user=Depends(get_admin_user)):
    entries = await all_finance_entries()
    return sorted([f for f in entries if (not kind or f["kind"] == kind) and (paid is None or f.get("paid", False) == paid)], key=lambda f:f.get("due_date", ""))

@api.post("/finance", response_model=FinanceEntry)
async def create_fin(f: FinanceEntry, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        if f.id.startswith(("order:", "purchase:")) or f.source_order_id or f.source_purchase_id:
            raise HTTPException(400, "Lançamentos de pedidos e compras são gerados pela operação de origem")
        if f.kind not in {"receivable", "payable"} or not math.isfinite(f.amount) or f.amount <= 0:
            raise HTTPException(400, "Informe tipo válido e valor maior que zero")
        f.currency = currency_code(f.currency)
        if f.currency not in {"BRL", "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"}:
            raise HTTPException(400, "Moeda não suportada")
        if not f.description.strip(): raise HTTPException(400, "Descrição obrigatória")
        if not f.due_date: raise HTTPException(400, "Vencimento obrigatório")
        if f.due_date:
            try:
                datetime.strptime(f.due_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(400, "Data de vencimento inválida")
        if await db.finance.find_one({"id": f.id}): raise HTTPException(409, "Lançamento já registrado. Recarregue para verificar.")
        f.paid = False
        f.paid_date = ""
        await ensure_owned()
        await db.finance.insert_one(f.model_dump()); return f

@api.patch("/finance/{fid}/toggle-paid", response_model=FinanceEntry)
async def toggle_paid(fid: str, body: Optional[dict] = None, user=Depends(get_admin_user)):
    if body is not None and not isinstance(body.get("paid"), bool):
        raise HTTPException(400, "Informe o estado de pagamento")
    if fid.startswith(("order:", "purchase:")):
        source, source_id = fid.split(":", 1)
        collection = db.orders if source == "order" else db.purchases
        async with business_write_lock() as ensure_owned:
            record = await collection.find_one({"id": source_id}, {"_id": 0})
            if not record or not record.get("workflow_enabled") or record.get("deleted_at") or record.get("status") in {"draft", "cancelled"}:
                raise HTTPException(404, "Operação financeira não encontrada")
            paid = body["paid"] if body is not None else not bool(record.get("finance_paid"))
            if paid == bool(record.get("finance_paid")):
                return linked_finance([record] if source=="order" else [], [record] if source=="purchase" else [])[0]
            changes = {"finance_paid": paid, "finance_paid_date": now_iso() if paid else "", "version": int(record.get("version") or 0)+1}
            if source == "purchase":
                changes["status"] = "paid" if paid else ("received" if record.get("stock_received") else "ordered")
            await ensure_owned()
            changed = await collection.update_one(version_query(record), {"$set": changes})
            if not changed.matched_count:
                raise HTTPException(409, "Operação alterada. Recarregue e tente novamente.")
            record.update(changes)
            return linked_finance([record] if source=="order" else [], [record] if source=="purchase" else [])[0]
    doc = await db.finance.find_one({"id": fid}, {"_id": 0})
    if not doc: raise HTTPException(404, "Not found")
    new_paid = body["paid"] if body is not None else not doc["paid"]
    if new_paid == bool(doc.get("paid")): return doc
    doc["paid"] = new_paid
    doc["paid_date"] = now_iso() if doc["paid"] else ""
    await db.finance.update_one({"id": fid}, {"$set": {"paid": doc["paid"], "paid_date": doc["paid_date"]}})
    return doc

@api.delete("/finance/{fid}")
async def del_fin(fid: str, user=Depends(get_admin_user)):
    if fid.startswith(("order:", "purchase:")):
        raise HTTPException(400, "Cancele o pedido ou a compra de origem para retirar este lançamento")
    r = await db.finance.delete_one({"id": fid}); return {"deleted": r.deleted_count}

# ============ CONTRACTS ============
@api.get("/contracts", response_model=List[Contract])
async def list_con(kind: Optional[str] = None, user=Depends(get_admin_user)):
    q = {"kind": kind} if kind else {}
    return await db.contracts.find(q, {"_id": 0}).sort("end_date", 1).to_list(1000)

@api.post("/contracts", response_model=Contract)
async def create_con(c: Contract, user=Depends(get_admin_user)):
    await db.contracts.insert_one(c.model_dump()); return c

@api.put("/contracts/{cid}", response_model=Contract)
async def upd_con(cid: str, c: Contract, user=Depends(get_admin_user)):
    c.id = cid; await db.contracts.replace_one({"id": cid}, c.model_dump()); return c

@api.delete("/contracts/{cid}")
async def del_con(cid: str, user=Depends(get_admin_user)):
    r = await db.contracts.delete_one({"id": cid}); return {"deleted": r.deleted_count}

# ============ CERTIFICATIONS (por fornecedor) ============
@api.get("/certifications", response_model=List[Certification])
async def list_cert(supplier_id: Optional[str] = None, user=Depends(get_current_user)):
    q = {"supplier_id": supplier_id} if supplier_id else {}
    return await db.certifications.find(await shared_file_scope(db, user, q), {"_id": 0}).sort("expiry_date", 1).to_list(1000)

@api.post("/certifications", response_model=Certification)
async def create_cert(c: Certification, user=Depends(get_admin_user)):
    await authorize_crm_file(db, user, c.file_path)
    c.id = str(uuid.uuid4())
    await db.certifications.insert_one(c.model_dump()); return c

@api.put("/certifications/{cid}", response_model=Certification)
async def upd_cert(cid: str, c: Certification, user=Depends(get_admin_user)):
    await authorize_crm_file(db, user, c.file_path)
    c.id = cid
    result = await db.certifications.replace_one(await shared_file_scope(db, user, {"id": cid}), c.model_dump())
    if not result.matched_count: raise HTTPException(404, "Certificado não encontrado")
    return c

@api.delete("/certifications/{cid}")
async def del_cert(cid: str, user=Depends(get_admin_user)):
    r = await db.certifications.delete_one(await shared_file_scope(db, user, {"id": cid}))
    if not r.deleted_count: raise HTTPException(404, "Certificado não encontrado")
    return {"deleted": 1}

# ============ PURCHASES (Compras) ============
@api.get("/purchases", response_model=List[Purchase])
async def list_pur(status: Optional[str] = None, supplier_id: Optional[str] = None, archived: bool = False, user=Depends(get_admin_user)):
    if archived: require_admin(user)
    q = {"deleted_at": {"$nin": [None, ""]}} if archived else {"deleted_at": {"$in": [None, ""]}}
    if status: q["status"] = status
    if supplier_id: q["supplier_id"] = supplier_id
    return await db.purchases.find(q, {"_id": 0}).sort("date", -1).to_list(1000)

@api.post("/purchases", response_model=Purchase)
async def create_pur(p: Purchase, user=Depends(get_admin_user)):
    return await save_purchase_workflow(p, create=True)

@api.put("/purchases/{pid}", response_model=Purchase)
async def upd_pur(pid: str, p: Purchase, user=Depends(get_admin_user)):
    p.id = pid
    return await save_purchase_workflow(p)

@api.delete("/purchases/{pid}")
async def del_pur(pid: str, user=Depends(get_admin_user)):
    require_admin(user)
    async with business_write_lock() as ensure_owned:
        record = await db.purchases.find_one({"id": pid}, {"_id": 0})
        if not record: raise HTTPException(404, "Compra não encontrada")
        if record.get("status") != "cancelled":
            raise HTTPException(400, "Cancele a compra antes de arquivá-la")
        await ensure_owned()
        await db.purchases.update_one({"id": pid}, {"$set": {"deleted_at": now_iso()}})
        return {"deleted": 1, "restorable": True}

# ============ SPECS (Prospecção IBIAG) ============
@api.get("/specs/library")
async def get_supplier_spec_library(user=Depends(get_current_user)):
    return await supplier_spec_library(db, await document_scope(db, user), await private_file_paths(db, user))

class SpecDocumentSupplier(BaseModel):
    supplier_id: str

@api.patch("/specs/documents/{did}/supplier")
async def assign_spec_document_supplier(did: str, body: SpecDocumentSupplier, user=Depends(get_admin_user)):
    require_admin(user)
    supplier = await db.suppliers.find_one({"id": body.supplier_id}, {"_id": 0})
    if not supplier:
        raise HTTPException(404, "Fornecedor não encontrado")
    doc = await db.documents.find_one({"id": did, "deleted_at": {"$in": [None, ""]}}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    linked = await db.product_offers.find_one({"spec_document_ids": did})
    if not is_spec_document(doc) and not linked:
        raise HTTPException(400, "Documento não classificado como spec")
    if doc.get("supplier_id") and doc["supplier_id"] != body.supplier_id and await db.suppliers.find_one({"id": doc["supplier_id"]}):
        raise HTTPException(409, "Documento já vinculado a outro fornecedor")
    updated = await db.documents.update_one({"id": did, "supplier_id": doc.get("supplier_id"), "deleted_at": {"$in": [None, ""]}}, {"$set": {"supplier_id": supplier["id"], "supplier_name": supplier["name"], "updated_at": now_iso()}})
    if not updated.matched_count:
        raise HTTPException(409, "Documento mudou durante a vinculação; atualize os specs")
    await db.product_offers.update_many({"spec_document_ids": did, "supplier_id": {"$ne": supplier["id"]}}, {"$pull": {"spec_document_ids": did}})
    if doc.get("product_id"):
        await db.product_offers.update_many({"product_id": doc["product_id"], "supplier_id": supplier["id"]}, {"$addToSet": {"spec_document_ids": did}})
    return {"document_id": did, "supplier_id": supplier["id"], "supplier_name": supplier["name"]}

async def validate_spec_supplier(spec, user, existing=None):
    supplier = await db.suppliers.find_one({"id": spec.supplier_id}, {"_id": 0})
    if not supplier:
        raise HTTPException(400, "Selecione um fornecedor cadastrado")
    if not spec.product_name.strip():
        raise HTTPException(400, "Nome do produto obrigatório")
    spec.supplier_name = supplier["name"]
    spec.product_name = spec.product_name.strip()
    for slot in ("original", "ibiag"):
        path = getattr(spec, slot + "_file_path")
        await authorize_crm_file(db, user, path)
        if not path or existing and path == existing.get(slot + "_file_path"):
            continue
        if user.get("role") != "admin" and not path.startswith(f"{APP_NAME}/uploads/{user['id']}/"):
            published = await db.documents.find_one({"file_path": path, "deleted_at": {"$in": [None, ""]}})
            if not published:
                raise HTTPException(403, "Arquivo de spec não autorizado")
        await get_object(path)

@api.get("/specs", response_model=List[Spec])
async def list_specs(supplier_id: Optional[str] = None, user=Depends(get_current_user)):
    q = {"supplier_id": supplier_id} if supplier_id else {}
    return await db.specs.find(await shared_file_scope(db, user, q, ("original_file_path", "ibiag_file_path")), {"_id": 0}).sort("product_name", 1).to_list(1000)

@api.post("/specs", response_model=Spec)
async def create_spec(s: Spec, user=Depends(get_admin_user)):
    await validate_spec_supplier(s, user)
    if await db.specs.find_one({"id": s.id}):
        raise HTTPException(409, "Spec já cadastrada")
    await db.specs.insert_one(s.model_dump()); return s

@api.put("/specs/{sid}", response_model=Spec)
async def upd_spec(sid: str, s: Spec, user=Depends(get_admin_user)):
    existing = await db.specs.find_one(await shared_file_scope(db, user, {"id": sid}, ("original_file_path", "ibiag_file_path")), {"_id": 0})
    if not existing:
        raise HTTPException(404, "Spec não encontrada")
    await validate_spec_supplier(s, user, existing)
    s.id = sid; s.updated_at = now_iso()
    result = await db.specs.replace_one(await shared_file_scope(db, user, {"id": sid}, ("original_file_path", "ibiag_file_path")), s.model_dump())
    if not result.matched_count: raise HTTPException(404, "Spec não encontrada")
    return s

@api.delete("/specs/{sid}")
async def del_spec(sid: str, user=Depends(get_admin_user)):
    r = await db.specs.delete_one(await shared_file_scope(db, user, {"id": sid}, ("original_file_path", "ibiag_file_path")))
    if not r.deleted_count: raise HTTPException(404, "Spec não encontrada")
    return {"deleted": 1}

# ============ PRICES ============
async def order_price_source(pid):
    records = await db.prices.find({"id": pid}, {"_id": 0}).limit(2).to_list(2)
    if not records:
        raise HTTPException(404, "Cálculo não encontrado")
    if len(records) != 1:
        raise HTTPException(409, "Identificador duplicado de cálculo. Revise o cadastro.")
    raw = records[0]
    try:
        price = PriceEntry(**raw)
    except (ValidationError, TypeError, ValueError):
        raise HTTPException(400, "Revise o cálculo salvo antes de criar um pedido.") from None
    if not price.offer_id:
        raise HTTPException(400, "Vincule o cálculo a uma oferta de produto e fornecedor antes de criar um pedido.")
    await validate_price_offer(price)
    for collection, rid in ((db.product_offers, price.offer_id), (db.products, price.product_id),
                            (db.suppliers, price.supplier_id)):
        references = await collection.find({"id": rid}, {"_id": 1}).limit(2).to_list(2)
        if len(references) != 1:
            raise HTTPException(409, "Referência ambígua de produto, oferta ou fornecedor. Revise o cadastro.")
    price = compute_price(price)
    if price.exchange_rate <= 0 or price.sell_price_usd <= 0 or price.sale_total_usd <= 0:
        raise HTTPException(400, "Informe câmbio e valor de venda positivos em USD no cálculo.")
    snapshot = price.model_dump()
    # Legacy records without timestamps must yield the same revision on every
    # read. Only persisted timestamps participate, never model defaults (now).
    snapshot["created_at"] = raw.get("created_at", "")
    snapshot["updated_at"] = raw.get("updated_at", "")
    try:
        revision = hashlib.sha256(json.dumps(snapshot, ensure_ascii=True, sort_keys=True,
                                            separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    except (ValueError, TypeError):
        raise HTTPException(400, "Revise os dados do cálculo salvo antes de criar um pedido.") from None
    return {"source_price_id": pid, "source_price_revision": revision,
            "source_price_snapshot": snapshot, "total_usd": price.sale_total_usd,
            "items": [{"product_id": price.product_id, "offer_id": price.offer_id,
                       "product_name": price.product_name, "supplier_id": price.supplier_id,
                       "supplier_name": price.supplier_name, "quantity": price.quantity,
                       "unit": price.unit, "unit_price": price.sell_price_usd}]}

# ============ COMMERCIAL QUOTATIONS (INTERNAL APPROVAL) ============
async def quote_record(qid):
    records = await db.quotations.find({"id": qid}, {"_id": 0}).limit(2).to_list(2)
    if not records: raise HTTPException(404, "Cotação não encontrada")
    if len(records) != 1: raise HTTPException(409, "Identificador de cotação ambíguo. Solicite revisão.")
    return records[0]

async def quote_references(record):
    leads = await db.leads.find({"id": record["lead_id"]}, {"_id": 0}).limit(2).to_list(2)
    if len(leads) != 1: raise HTTPException(409, "Revise a empresa vinculada à cotação.")
    item = record["items"][0]
    for collection, rid in ((db.products, item["product_id"]), (db.suppliers, item["supplier_id"]),
                            (db.product_offers, item["offer_id"])):
        matches = await collection.find({"id": rid}, {"_id": 0}).limit(2).to_list(2)
        if len(matches) != 1: raise HTTPException(409, "Revise produto, fornecedor e oferta da cotação.")
        if collection.name == "product_offers":
            offer = matches[0]
            if offer.get("active", True) is not True or offer.get("product_id") != item["product_id"] or offer.get("supplier_id") != item["supplier_id"] or (offer.get("unit") and offer["unit"] != item["unit"]):
                raise HTTPException(409, "A oferta da cotação mudou ou está inativa. Revise a operação.")

async def quotation_view(record):
    linked = await db.orders.find_one({"source_quote_id": record["id"]}, {"_id": 0, "id": 1})
    expired = record["valid_until"] < datetime.now(timezone.utc).date().isoformat()
    return {**{k: v for k, v in record.items() if k != "_id"}, "linked_order_id": linked["id"] if linked else "", "expired": expired,
            "can_order": record["status"] == "approved" and not expired and not linked}

def checked_quote_event(record, previous, actor, note):
    try:
        return quotation_event(record, previous, actor, note, now_iso())
    except OverflowError as exc:
        raise HTTPException(413, str(exc)) from None
    except (TypeError, ValueError):
        raise HTTPException(400, "Revise os dados e o limite do histórico da cotação.") from None

def check_quotation_terms(record):
    try: validate_quote_terms(record, datetime.now(timezone.utc).date())
    except (TypeError, ValueError) as exc: raise HTTPException(400, str(exc)) from None

async def order_quote_source(qid):
    quote = await quote_record(qid)
    if quote["status"] != "approved" or quote["valid_until"] < datetime.now(timezone.utc).date().isoformat():
        raise HTTPException(409, "A cotação precisa estar aprovada internamente e dentro da validade.")
    if await db.orders.find_one({"source_quote_id": qid}, {"_id": 1}):
        raise HTTPException(409, "A cotação já possui pedido, inclusive se cancelado ou arquivado.")
    await quote_references(quote)
    snapshot = {key: value for key, value in quote.items() if key != "history"}
    return {"source_quote_id": qid, "source_quote_revision": quote["version"], "source_quote_snapshot": snapshot,
            **{key: quote[key] for key in ("lead_id", "customer", "customer_country", "incoterm", "items", "total_usd")}}

@api.get("/quotations")
async def list_quotations(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=250),
    status: Optional[Literal["draft", "approved", "cancelled"]] = None,
    lead_id: str = Query("", max_length=200, pattern=r"^[^\x00]*$"), user=Depends(get_admin_user)):
    query = {}
    if status: query["status"] = status
    if lead_id: query["lead_id"] = lead_id
    records = await db.quotations.find(query, {"_id": 0, **{k: 1 for k in QUOTE_SUMMARY}}).sort("id", 1).skip(skip).limit(limit).to_list(limit)
    links = await db.orders.find({"source_quote_id": {"$in": [q["id"] for q in records]}},
                                 {"_id": 0, "id": 1, "source_quote_id": 1}).to_list(limit)
    mapped = {o["source_quote_id"]: o["id"] for o in links}
    return [{**q, "linked_order_id": mapped.get(q["id"], "")} for q in records]

@api.get("/quotations/{qid}/order-draft")
async def quotation_order_draft(qid: str, user=Depends(get_admin_user)):
    return await order_quote_source(qid)

@api.get("/quotations/{qid}")
async def get_quotation(qid: str, user=Depends(get_admin_user)):
    return await quotation_view(await quote_record(qid))

@api.post("/quotations")
async def create_quotation(body: QuotationCreate, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        if await db.quotations.find_one({"$or": [{"id": body.id}, {"reference": body.reference}]}, {"_id": 1}):
            raise HTTPException(409, "Identificador ou referência da cotação já utilizado. Confira a lista.")
        values = body.model_dump(exclude={"change_note"})
        check_quotation_terms(values)
        source = await order_price_source(body.source_price_id)
        if source["source_price_revision"] != body.source_price_revision:
            raise HTTPException(409, "O cálculo mudou. Abra e confira novamente antes de criar a cotação.")
        leads = await db.leads.find({"id": body.lead_id}, {"_id": 0}).limit(2).to_list(2)
        if len(leads) != 1 or not isinstance(leads[0].get("company"), str) or not leads[0]["company"].strip() or not isinstance(leads[0].get("country", ""), str):
            raise HTTPException(400, "Selecione uma empresa única e válida do CRM.")
        values.update(source, customer=leads[0]["company"], customer_country=leads[0].get("country", ""), status="draft")
        record = checked_quote_event(values, None, user, body.change_note)
        await ensure_owned()
        await db.quotations.insert_one(dict(record))
        return await quotation_view(record)

@api.put("/quotations/{qid}")
async def edit_quotation(qid: str, body: QuotationEdit, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        previous = await quote_record(qid)
        if previous["version"] != body.version: raise HTTPException(409, "Cotação alterada. Recarregue antes de salvar.")
        if previous["status"] != "draft": raise HTTPException(409, "Condições só podem ser alteradas em rascunho. Crie outra cotação.")
        values = {**previous, **body.model_dump(exclude={"version", "change_note"})}
        check_quotation_terms(values)
        record = checked_quote_event(values, previous, user, body.change_note)
        await ensure_owned()
        saved = await db.quotations.replace_one(version_query(previous), record)
        if not saved.matched_count: raise HTTPException(409, "Cotação alterada. Recarregue antes de salvar.")
        return await quotation_view(record)

@api.post("/quotations/{qid}/status")
async def change_quotation_status(qid: str, body: QuotationState, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        previous = await quote_record(qid)
        if previous["version"] != body.version: raise HTTPException(409, "Cotação alterada. Recarregue antes de aprovar ou cancelar.")
        if previous["status"] == "cancelled" or previous["status"] == body.status:
            raise HTTPException(409, "Transição de cotação não permitida.")
        if await db.orders.find_one({"source_quote_id": qid}, {"_id": 1}):
            raise HTTPException(409, "Cotação vinculada a pedido deve manter sua memória aprovada.")
        values = {**previous, "status": body.status}
        if body.status == "approved":
            if previous["status"] != "draft": raise HTTPException(409, "Cotação já aprovada.")
            check_quotation_terms(values)
            await quote_references(values)
            values.update(approved_by=user["id"], approved_at=now_iso())
        record = checked_quote_event(values, previous, user, body.change_note)
        await ensure_owned()
        saved = await db.quotations.replace_one(version_query(previous), record)
        if not saved.matched_count: raise HTTPException(409, "Cotação alterada. Recarregue antes de continuar.")
        return await quotation_view(record)


@api.get("/prices/{pid}/order-draft")
async def price_order_draft(pid: str, user=Depends(get_admin_user)):
    return await order_price_source(pid)

def compute_price(p: PriceEntry) -> PriceEntry:
    try:
        for key, value in calculate_price(p).items():
            setattr(p, key, value)
        p.calculation_error = ""
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(400, str(exc))
    return p

async def validate_price_offer(p):
    if not p.offer_id:
        return
    offer = await db.product_offers.find_one({"id": p.offer_id})
    if not offer or offer.get("active") is False or offer.get("supplier_id") != p.supplier_id:
        raise HTTPException(400, "Produto não disponível para o fornecedor selecionado.")
    if p.product_id and p.product_id != offer.get("product_id"):
        raise HTTPException(400, "Produto não corresponde à oferta selecionada.")
    supplier = await db.suppliers.find_one({"id": p.supplier_id})
    product = await db.products.find_one({"id": offer.get("product_id")})
    if not supplier or not product:
        raise HTTPException(400, "Fornecedor ou produto não disponível.")
    p.product_id = product["id"]
    p.product_name = offer.get("product_name") or product.get("name", "")
    p.supplier_name = supplier["name"]
    p.unit = offer.get("unit") or product.get("unit") or "kg"

@api.get("/prices", response_model=List[PriceEntry])
async def list_prices(user=Depends(get_admin_user)):
    records = await db.prices.find({}, {"_id": 0}).sort("product_name", 1).to_list(1000)
    result = []
    for record in records:
        p = PriceEntry(**record)
        try:
            result.append(compute_price(p))
        except HTTPException as exc:
            # Keep old saved calculations visible so the user can correct them.
            p.calculation_error = str(exc.detail)
            p.supplier_total = round(p.supplier_price * p.quantity, 2)
            p.cost_total = round((p.supplier_price + p.extra_costs) * p.quantity, 2)
            p.sale_total_brl = round(p.sell_price_brl * p.quantity, 2)
            p.sale_total_usd = round(p.sell_price_usd * p.quantity, 2)
            result.append(p)
    return result

@api.post("/prices/calculate", response_model=PriceEntry)
async def calc_price(p: PriceEntry, user=Depends(get_current_user)):
    await validate_price_offer(p)
    return compute_price(p)

@api.post("/prices", response_model=PriceEntry)
async def create_price(p: PriceEntry, user=Depends(get_admin_user)):
    await validate_price_offer(p)
    p = compute_price(p)
    await db.prices.insert_one(p.model_dump()); return p

@api.put("/prices/{pid}", response_model=PriceEntry)
async def upd_price(pid: str, p: PriceEntry, user=Depends(get_admin_user)):
    await validate_price_offer(p)
    p.id = pid; p.updated_at = now_iso(); p = compute_price(p)
    await db.prices.replace_one({"id": pid}, p.model_dump()); return p

@api.delete("/prices/{pid}")
async def del_price(pid: str, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        if await db.orders.find_one({"source_price_id": pid}, {"_id": 1}):
            raise HTTPException(409, "Cálculo vinculado a pedido não pode ser excluído.")
        if await db.quotations.find_one({"source_price_id": pid}, {"_id": 1}):
            raise HTTPException(409, "Cálculo vinculado a cotação não pode ser excluído.")
        await ensure_owned()
        r = await db.prices.delete_one({"id": pid})
        return {"deleted": r.deleted_count}

# ============ CASHFLOW ============
@api.get("/finance/cashflow")
async def cashflow(months: int = 12, currency: str = "BRL", period: str = "history", user=Depends(get_admin_user)):
    if months < 1 or months > 60:
        raise HTTPException(400, "Informe de 1 a 60 meses")
    currency = currency_code(currency)
    if currency not in {"BRL", "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"}:
        raise HTTPException(400, "Moeda não suportada")
    today = datetime.now(timezone.utc)
    try:
        keys = month_keys(datetime.now(timezone.utc).date(), months, period)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    entries = await all_finance_entries()
    invoices = await db.invoices.find({}, {"_id": 0}).to_list(10000)
    return cashflow_rows(entries, invoices, keys, currency)

# ============ GESTÃO STATS ============
@api.get("/gestao/stats")
async def gestao_stats(user=Depends(get_admin_user)):
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
    totals = pending_totals(await all_finance_entries())
    brl = next((row for row in totals if row["currency"] == "BRL"), {})
    fin_recv, fin_pay = brl.get("receivable", 0.0), brl.get("payable", 0.0)
    documents = await db.documents.find({}, {"_id": 0}).to_list(10000)
    return {
        "certs_total": len(certs), "certs_expiring": sorted(expiring, key=lambda x: x["days"]),
        "certs_expired": sorted(expired, key=lambda x: x["days"]),
        "contracts_expiring": contracts_expiring,
        "purchases_open": await db.purchases.count_documents({"status": {"$in": ["ordered", "received"]}}),
        "suppliers": await db.suppliers.count_documents({}),
        "specs": await db.specs.count_documents({}),
        "prices": await db.prices.count_documents({}),
        "pops": sum(matches_document(d, section="pop") or matches_document(d, section="pop_signed") for d in documents),
        "invoices_in": await db.invoices.count_documents({"kind": "entrada"}),
        "invoices_out": await db.invoices.count_documents({"kind": "saida"}),
        "finance_receivable": fin_recv, "finance_payable": fin_pay, "finance_by_currency": totals,
    }

# ============ INVENTORY ============
class StockUpd(BaseModel):
    stock: float

@api.patch("/products/{pid}/stock", response_model=Product)
async def upd_stock(pid: str, body: StockUpd, user=Depends(get_admin_user)):
    require_admin(user)
    if not math.isfinite(body.stock) or body.stock < 0:
        raise HTTPException(400, "Saldo de estoque deve ser zero ou positivo")
    async with business_write_lock() as ensure_owned:
        products, orders, purchases = await business_snapshot()
        balances = inventory_balances(products, orders, purchases)
        doc = balances.get(pid)
        if not doc: raise HTTPException(404, "Produto não encontrado")
        if body.stock < doc["stock_reserved"]:
            raise HTTPException(400, "O saldo não pode ser menor que a quantidade reservada")
        base = round(body.stock - doc["stock_movement"], 6)
        await ensure_owned()
        await db.products.update_one({"id": pid}, {"$set": {"stock": base, "stock_adjusted_at": now_iso(), "stock_adjusted_by": user["id"]}})
        doc.update(stock=body.stock, stock_available=round(body.stock-doc["stock_reserved"], 6))
        return doc


# ============ PRODUCT PORTFOLIO OFFERS ============
@api.get("/product-offers", response_model=List[ProductOffer])
async def list_product_offers(product_id: Optional[str] = None, supplier_id: Optional[str] = None, active: Optional[bool] = None, user=Depends(get_admin_user)):
    q = {}
    if product_id: q["product_id"] = product_id
    if supplier_id: q["supplier_id"] = supplier_id
    if active is not None: q["active"] = active
    return await db.product_offers.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)

async def validate_offer_documents(o):
    document_ids = set(o.spec_document_ids + o.certificate_document_ids + o.other_document_ids)
    for collection, ids in [(db.documents, document_ids), (db.specs, set(o.spec_ids)), (db.certifications, set(o.certification_ids))]:
        for identifier in ids:
            record = await collection.find_one({"id": identifier})
            if not record or record.get("deleted_at"):
                raise HTTPException(400, "Documento, especificação ou certificado não disponível: " + identifier)

@api.post("/product-offers", response_model=ProductOffer)
async def create_product_offer(o: ProductOffer, user=Depends(get_admin_user)):
    await validate_offer_documents(o)
    async with business_write_lock() as ensure_owned:
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
async def update_product_offer(oid: str, o: ProductOffer, user=Depends(get_admin_user)):
    await validate_offer_documents(o)
    async with business_write_lock() as ensure_owned:
        existing = await db.product_offers.find_one({"id": oid}, {"_id": 0})
        if not existing: raise HTTPException(404, "Oferta não encontrada")
        product = await db.products.find_one({"id": o.product_id}, {"_id": 0})
        if not product: raise HTTPException(404, "Produto não encontrado")
        supplier = await db.suppliers.find_one({"id": o.supplier_id}, {"_id": 0}) if o.supplier_id else None
        if o.supplier_id and not supplier: raise HTTPException(404, "Fornecedor não encontrado")
        if await db.orders.find_one({"items.offer_id": oid}):
            if any(getattr(o, field) != existing.get(field, "") for field in ("product_id", "supplier_id", "unit")):
                raise HTTPException(400, "Oferta com pedidos vinculados não pode trocar produto, fornecedor ou unidade")
        o.id = oid
        o.product_name = product["name"]
        o.supplier_name = supplier["name"] if supplier else ""
        o.updated_at = now_iso()
        await ensure_owned()
        await db.product_offers.replace_one({"id": oid}, o.model_dump())
        return o

@api.delete("/product-offers/{oid}")
async def delete_product_offer(oid: str, user=Depends(get_admin_user)):
    require_admin(user)
    async with business_write_lock() as ensure_owned:
        if await db.orders.find_one({"items.offer_id": oid}) or await db.documents.find_one({"offer_id": oid}) or await db.quotations.find_one({"items.offer_id": oid}):
            raise HTTPException(400, "Oferta vinculada não pode ser excluída. Marque-a como inativa.")
        await ensure_owned()
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
        docs = await db.documents.find(await document_scope(db, user, {"id": {"$in": ids}, "deleted_at": {"$in": [None, ""]}}), {"_id": 0}).to_list(200)
        result.extend([{**d, "link_type": "document"} for d in docs])
    spec_ids = offer.get("spec_ids", [])
    if spec_ids:
        specs = await db.specs.find(await shared_file_scope(db, user, {"id": {"$in": spec_ids}}, ("original_file_path", "ibiag_file_path")), {"_id": 0}).to_list(200)
        result.extend([{**x, "link_type": "spec"} for x in specs])
    cert_ids = offer.get("certification_ids", [])
    if cert_ids:
        certs = await db.certifications.find(await shared_file_scope(db, user, {"id": {"$in": cert_ids}}), {"_id": 0}).to_list(200)
        result.extend([{**x, "link_type": "certification"} for x in certs])
    return result

# ============ PRODUCTS (public read + auth write) ============
@api.get("/products", response_model=List[Product])
async def list_products(category: Optional[str] = None, user=Depends(get_current_user)):
    products, orders, purchases = await business_snapshot()
    balances = inventory_balances(products, orders, purchases)
    return [p for p in balances.values() if not category or p.get("category") == category]

@api.post("/products", response_model=Product)
async def create_product(p: Product, user=Depends(get_admin_user)):
    require_admin(user)
    if not math.isfinite(p.stock) or p.stock < 0: raise HTTPException(400, "Estoque inicial inválido")
    body = p.model_dump()
    body.update(stock_reserved=0, stock_available=p.stock)
    await db.products.insert_one(body)
    return body

@api.put("/products/{pid}", response_model=Product)
async def upd_product(pid: str, p: Product, user=Depends(get_admin_user)):
    async with business_write_lock() as ensure_owned:
        existing = await db.products.find_one({"id": pid}, {"_id": 0})
        if not existing: raise HTTPException(404, "Produto não encontrado")
        if p.unit != existing.get("unit", "kg"):
            _, orders, purchases = await business_snapshot()
            referenced = any(any(i.get("product_id")==pid for i in o.get("items", [])) for o in orders) or any(c.get("product_id")==pid for c in purchases)
            if referenced: raise HTTPException(400, "Unidade de produto com operações registradas não pode ser alterada")
        p.id = pid
        changes = p.model_dump()
        changes.pop("stock", None); changes.pop("stock_reserved", None); changes.pop("stock_available", None)
        await ensure_owned()
        await db.products.update_one({"id": pid}, {"$set": changes})
        products, orders, purchases = await business_snapshot()
        return inventory_balances(products, orders, purchases)[pid]

@api.delete("/products/{pid}")
async def del_product(pid: str, user=Depends(get_admin_user)):
    require_admin(user)
    async with business_write_lock() as ensure_owned:
        checks = [
            (db.product_offers, {"product_id": pid}),
            (db.orders, {"items.product_id": pid}),
            (db.quotations, {"items.product_id": pid}),
            (db.purchases, {"product_id": pid}),
            (db.documents, {"product_id": pid}),
        ]
        for collection, query in checks:
            if await collection.find_one(query):
                raise HTTPException(400, "Produto vinculado a ofertas, documentos ou operações não pode ser excluído")
        await ensure_owned()
        r = await db.products.delete_one({"id": pid})
        return {"deleted": r.deleted_count}


class PortfolioImportResult(BaseModel):
    products: int
    suppliers: int
    offers: int
    source_rows: int

@api.post("/portfolio/import-xlsx", response_model=PortfolioImportResult)
async def import_portfolio_xlsx(file: UploadFile = File(...), replace: bool = True, dry_run: bool = False, user=Depends(get_current_user)):
    """Import the official IBIAG product/supplier matrix. Sheet IBIAG, header row 3."""
    require_admin(user)
    df = (await read_table(file, sheet_name="IBIAG", header=2)).fillna("")

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

    async with business_write_lock() as ensure_owned:
        if replace and (await db.quotations.find_one({}) or await db.orders.find_one({"items.0": {"$exists": True}}) or await db.purchases.find_one({"product_id": {"$nin": [None, ""]}})):
            raise HTTPException(400, "Portfólio com operações vinculadas não pode ser substituído. Use importação incremental.")
        await ensure_owned()
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
            commission_value = commission_raw.strip().replace(",", ".")
            try:
                commission = float(commission_value.rstrip("%")) if commission_value else 0
                if commission_value.endswith("%"):
                    commission /= 100
                if not math.isfinite(commission):
                    commission = 0
            except (ValueError, TypeError):
                commission = 0
            offer = ProductOffer(
                product_id=p["id"], product_name=p["name"], form=p["name"],
                supplier_id=supplier.get("id",""), supplier_name=supplier_name,
                capacity=r.get("Capacidade de Produção",""), ncm=r.get("NCM/HS",""), hs_code=r.get("NCM/HS",""),
                packaging_type=r.get("Tipo Embalagem",""), packaging=r.get("Embalagem",""),
                palletization=r.get("Palletização",""), export_price_text=r.get("Preço Exportação",""),
                fob_price_text="" if r.get("Preço FOB","") == "#VALUE!" else r.get("Preço FOB",""),
                organic_version=r.get("Versão Orgânica",""), commission=commission, commission_text=commission_raw,
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
@api.post("/portfolio/restore-commissions")
async def restore_portfolio_commissions(file: UploadFile = File(...), dry_run: bool = True, user=Depends(get_current_user)):
    """Restore only commission fields; preserve IDs, prices and document links."""
    require_admin(user)
    df = (await read_table(file, sheet_name="IBIAG", header=2)).fillna("")

    df.columns = [str(c).strip() for c in df.columns]
    if not {"Produto", "Fornecedor", "Comissão"}.issubset(df.columns):
        raise HTTPException(400, "Planilha sem Produto, Fornecedor ou Comissão")
    def clean(value):
        if value is None: return ""
        if isinstance(value, float) and value.is_integer(): return str(int(value))
        return str(value).strip()
    def key(name, supplier):
        return (clean(name).casefold(), clean(supplier).casefold())
    source = {}
    for _, row in df.iterrows():
        if not clean(row["Produto"]): continue
        k = key(row["Produto"], row["Fornecedor"])
        raw = clean(row["Comissão"])
        value = raw.replace(",", ".")
        try:
            number = float(value.rstrip("%")) if value else 0
            if value.endswith("%"): number /= 100
            if not math.isfinite(number): number = 0
        except (ValueError, TypeError): number = 0
        source.setdefault(k, []).append((number, raw))
    offers = await db.product_offers.find({"source": "Tabela Produtos Ibiag 2026 - COMPLETA / aba IBIAG"}, {"_id": 0}).to_list(None)
    groups = {}
    for offer in offers:
        groups.setdefault(key(offer.get("product_name"), offer.get("supplier_name")), []).append(offer)
    updates = []
    conflicts = []
    for k, values in source.items():
        targets = groups.get(k, [])
        unique = set(values)
        if not targets or (len(unique) > 1):
            conflicts.append(" / ".join(k))
            continue
        number, raw = values[0]
        if len(targets) != len(values):
            conflicts.append(" / ".join(k))
            continue
        for offer in targets:
            if offer.get("commission", 0) != number or offer.get("commission_text", "") != raw:
                updates.append((offer["id"], number, raw))
    if conflicts:
        raise HTTPException(409, {"message": "Nenhum dado alterado: há vínculos ausentes ou comissões ambíguas", "conflicts": conflicts})
    if not dry_run:
        for oid, number, raw in updates:
            await db.product_offers.update_one({"id": oid}, {"$set": {"commission": number, "commission_text": raw, "updated_at": now_iso()}})
    return {"matched": sum(len(x) for x in groups.values()), "updated": 0 if dry_run else len(updates), "planned_updates": len(updates), "dry_run": dry_run}

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
    df = await read_table(file)

    df = df.fillna("")
    df.columns = [_norm_col(c) for c in df.columns]
    imported = updated = skipped = 0
    errors = []
    # Load existing CRM records once; avoids one database scan per imported row.
    # No artificial CRM-size cap: load all existing lead keys for conservative deduplication.
    candidates = await db.leads.find(lead_scope(user), {"_id": 0}).to_list(None)

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
                await db.leads.update_one(lead_scope(user, {"id": existing["id"]}), {"$set": updates})
                updated += 1
            else:
                skipped += 1
        else:
            lead = Lead(**data, owner_id=user["id"])
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
    user=Depends(get_current_user),
):
    """List CRM leads with pagination; there is no registration/storage cap."""
    q = {}
    if stage:
        q["stage"] = stage
    if industry:
        q["industry"] = industry
    skip = max(0, skip)
    limit = min(max(1, limit), 250)
    return await db.leads.find(lead_scope(user, q), {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)

@api.get("/leads/count")
async def count_leads(stage: Optional[str] = None, industry: Optional[str] = None, user=Depends(get_current_user)):
    q = {}
    if stage:
        q["stage"] = stage
    if industry:
        q["industry"] = industry
    return {"total": await db.leads.count_documents(lead_scope(user, q))}

@api.get("/leads/{lid}", response_model=Lead)
async def get_lead(lid: str, user=Depends(get_current_user)):
    return await require_lead(db, user, lid)

@api.post("/leads", response_model=Lead)
async def create_lead(lead: Lead, user=Depends(get_current_user)):
    lead.id = str(uuid.uuid4())
    lead.owner_id = user["id"]
    lead.created_at = lead.updated_at = now_iso()
    await db.leads.insert_one(lead.model_dump())
    return lead

@api.patch("/leads/{lid}/stage", response_model=Lead)
async def upd_stage(lid: str, upd: StageUpd, user=Depends(get_current_user)):
    doc = await db.leads.find_one_and_update(lead_scope(user, {"id": lid}),
        {"$set": {"stage": upd.stage, "updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not doc: raise HTTPException(404, "Empresa não encontrada")
    return doc

@api.put("/leads/{lid}", response_model=Lead)
async def upd_lead(lid: str, lead: Lead, user=Depends(get_current_user)):
    # Update editable fields, preserving ownership and internal discovery keys.
    changes = lead.model_dump(exclude={"id", "owner_id", "created_at"})
    changes["updated_at"] = now_iso()
    doc = await db.leads.find_one_and_update(lead_scope(user, {"id": lid}), {"$set": changes, "$unset": {"discovery_key": ""}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not doc: raise HTTPException(404, "Empresa não encontrada")
    return doc

class LeadOwnerBody(BaseModel):
    owner_id: str = Field(min_length=1, max_length=200)

@api.patch("/leads/{lid}/owner", response_model=Lead)
async def assign_lead_owner(lid: str, body: LeadOwnerBody, user=Depends(get_current_user)):
    require_admin(user)
    owner = await db.users.find_one({"id": body.owner_id}, {"id": 1, "active": 1})
    if not owner or owner.get("active", True) is not True:
        raise HTTPException(400, "Usuário ativo não encontrado")
    # Release the old owner's creation-deduplication key on transfer. The lead
    # ID remains stable; linked history and documents follow its access scope.
    doc = await db.leads.find_one_and_update({"id": lid},
        {"$set": {"owner_id": body.owner_id, "updated_at": now_iso(),
                  "owner_updated_by": user["id"], "owner_updated_at": now_iso()},
         "$unset": {"discovery_key": ""}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not doc: raise HTTPException(404, "Empresa não encontrada")
    return doc

@api.delete("/leads/{lid}")
async def del_lead(lid: str, user=Depends(get_current_user)):
    # Reject unrelated CRM users before acquiring a shared ERP write lock.
    await require_lead(db, user, lid)
    # Serialize with order saves so deletion cannot race relationship creation.
    async with business_write_lock() as ensure_owned:
        await require_lead(db, user, lid)
        if await db.orders.find_one({"lead_id": lid}, {"_id": 1}):
            raise HTTPException(409, "Empresa vinculada a pedido não pode ser excluída.")
        if await db.quotations.find_one({"lead_id": lid}, {"_id": 1}):
            raise HTTPException(409, "Empresa vinculada a cotação não pode ser excluída.")
        await ensure_owned()
        result = await db.leads.delete_one(lead_scope(user, {"id": lid}))
        if not result.deleted_count: raise HTTPException(404, "Empresa não encontrada")
        await db.interactions.delete_many({"lead_id": lid})
        return {"deleted": 1}

@api.get("/interactions", response_model=List[Interaction])
async def list_int(lead_id: Optional[str] = None, user=Depends(get_current_user)):
    if lead_id:
        await require_lead(db, user, lead_id)
        query = {"lead_id": lead_id}
    elif user.get("role") == "admin":
        query = {}
    else:
        query = {"lead_id": {"$in": await visible_lead_ids(db, user)}}
    return await db.interactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)

@api.post("/interactions", response_model=Interaction)
async def create_int(i: Interaction, user=Depends(get_current_user)):
    await require_lead(db, user, i.lead_id)
    i.id = str(uuid.uuid4())
    i.created_at = now_iso()
    await db.interactions.insert_one(i.model_dump())
    return i

# ============ TASKS ============
def task_access_query(user, task_id=None):
    # Ownership comes from the authenticated database user, never request data.
    # Legacy tasks without an owner remain administrator-only until assigned.
    query = {} if user.get("role") == "admin" else {"owner_id": user["id"]}
    if task_id is not None:
        query["id"] = task_id
    return query

@api.get("/tasks", response_model=List[Task])
async def list_tasks(user=Depends(get_current_user)):
    return await db.tasks.find(task_access_query(user), {"_id": 0}).to_list(500)

@api.post("/tasks", response_model=Task)
async def create_task(t: Task, user=Depends(get_current_user)):
    if not t.title.strip():
        raise HTTPException(400, "Título obrigatório")
    t.id = str(uuid.uuid4())
    t.owner_id = user["id"]
    t.created_at = now_iso()
    t.title = t.title.strip()
    if t.lead_id:
        await require_lead(db, user, t.lead_id)
    await db.tasks.insert_one(t.model_dump()); return t

@api.patch("/tasks/{tid}/toggle", response_model=Task)
async def toggle_task(tid: str, user=Depends(get_current_user)):
    # Match authorization and change state atomically, including concurrent tabs.
    doc = await db.tasks.find_one_and_update(
        task_access_query(user, tid),
        [{"$set": {"completed": {"$eq": [{"$ifNull": ["$completed", False]}, False]}}}],
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not doc: raise HTTPException(404, "Not found")
    return doc

@api.delete("/tasks/{tid}")
async def del_task(tid: str, user=Depends(get_current_user)):
    r = await db.tasks.delete_one(task_access_query(user, tid))
    if not r.deleted_count: raise HTTPException(404, "Not found")
    return {"deleted": r.deleted_count}

class TaskOwnerBody(BaseModel):
    owner_id: str = Field(min_length=1, max_length=200)

@api.patch("/tasks/{tid}/owner", response_model=Task)
async def assign_task_owner(tid: str, body: TaskOwnerBody, user=Depends(get_current_user)):
    require_admin(user)
    owner = await db.users.find_one({"id": body.owner_id}, {"id": 1, "active": 1})
    if not owner or owner.get("active", True) is not True:
        raise HTTPException(400, "Usuário ativo não encontrado")
    doc = await db.tasks.find_one_and_update(
        {"id": tid}, {"$set": {"owner_id": body.owner_id,
                               "owner_updated_by": user["id"], "owner_updated_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not doc: raise HTTPException(404, "Not found")
    return doc

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
async def list_tpl(language: Optional[str] = None, category: Optional[str] = None, user=Depends(get_current_user)):
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
        logging.error("Comex Stat NCM search failed")
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
        logging.error("Comex Stat prospect query failed")
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
        logging.error("Comex Stat markets query failed")
        raise HTTPException(502, f"Não foi possível montar os mercados: {str(e)[:180]}")

@api.post("/comexstat/general")
async def comexstat_general(payload: dict, user=Depends(get_current_user)):
    try:
        return comex_general(payload)
    except requests.RequestException as e:
        logging.error("Comex Stat general query failed")
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
async def list_trade(country: Optional[str] = Query(None, max_length=8),
                     industry: Optional[str] = Query(None, max_length=64),
                     search: Optional[str] = Query(None, max_length=128, pattern=r"^[^\x00]*$"),
                     user=Depends(get_current_user)):
    q = {}
    if country: q["country_code"] = country
    if industry: q["industry_segment"] = industry
    if search:
        literal = re.escape(search)
        q["$or"] = [{"importer_company": {"$regex": literal, "$options": "i"}},
                    {"product_description": {"$regex": literal, "$options": "i"}}]
    return await db.trade_data.find(q, {"_id": 0}).to_list(500)

@api.post("/trade-data/{tid}/add-to-crm", response_model=Lead)
async def trade_to_crm(tid: str, user=Depends(get_current_user)):
    tr = await db.trade_data.find_one({"id": tid}, {"_id": 0})
    if not tr: raise HTTPException(404, "Not found")
    existing = await db.leads.find_one(lead_scope(user, {"company": tr["importer_company"]}), {"_id": 0})
    if existing: return existing
    lead = Lead(company=tr["importer_company"], country=tr["importer_country"],
                country_code=tr["country_code"], industry=tr["industry_segment"],
                stage="new_lead", source="trade_data", deal_value=tr["value_usd"],
                notes=f"From Trade Intel. HS {tr['hs_code']}. {tr['volume_kg']:.0f} kg / USD {tr['value_usd']:.0f}")
    lead.owner_id = user["id"]
    await db.leads.insert_one(lead.model_dump())
    return lead


# ============ BUYER DISCOVERY ============
class BuyerDiscoveryRequest(BaseModel):
    product: str
    country: str = ""
    countries: List[str] = Field(default_factory=list)
    region: str = ""
    country_code: str = ""
    limit: int = Field(default=10, ge=1, le=20)
    replace_previous: bool = False

@api.get("/buyer-discovery/markets")
async def buyer_discovery_markets(user=Depends(get_current_user)):
    return {"countries": MARKETS, "regions": [{"id": key, "name": value["name"], "countries": value["countries"]} for key, value in REGIONS.items()]}

@api.post("/buyer-discovery/search-jobs")
async def create_buyer_search_job(body: BuyerDiscoveryRequest, tasks: BackgroundTasks, user=Depends(get_current_user)):
    require_paid_discovery()
    if not body.product.strip():
        raise HTTPException(400, "Informe o produto.")
    try:
        targets = resolve_markets(body.country, body.countries, body.region)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    active_jobs = {"owner_id": user["id"], "status": {"$in": ["pending", "running"]}, "cancel_requested": {"$ne": True}}
    if body.replace_previous:
        await db.buyer_search_jobs.update_many(active_jobs, {"$set": {"cancel_requested": True, "updated_at": now_iso()}})
    if await db.buyer_search_jobs.count_documents(active_jobs):
        raise HTTPException(409, "Há uma pesquisa em andamento. Aguarde ou interrompa antes de iniciar outra.")
    job = {"id": str(uuid.uuid4()), "owner_id": user["id"], "product": body.product.strip(), "targets": targets, "region": body.region,
           "label": next((r["name"] for key, r in REGIONS.items() if key == body.region), ", ".join(x["name"] for x in targets)),
           "limit": body.limit, "discovery_version": DISCOVERY_VERSION, "status": "pending", "total": len(targets), "completed": 0, "failures": 0,
           "results": [], "created_at": now_iso(), "updated_at": now_iso(), "cancel_requested": False,
           "progress": {x["code"]: {"country": x["name"], "status": "pending", "count": 0, "error": ""} for x in targets}}
    await db.buyer_search_jobs.insert_one(dict(job))
    tasks.add_task(run_discovery_job, db, job, discover_buyers)
    return job

async def authorized_buyer_job(job_id, user):
    job = await db.buyer_search_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Pesquisa não encontrada")
    if job["owner_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Pesquisa pertence a outro usuário")
    return job

@api.get("/buyer-discovery/search-jobs/{job_id}")
async def get_buyer_search_job(job_id: str, user=Depends(get_current_user)):
    job = await authorized_buyer_job(job_id, user)
    if job.get("discovery_version", 0) < DISCOVERY_VERSION:
        return {**job, "results": [], "status": "outdated", "validation_message": "Esta pesquisa usava o filtro anterior. Limpe a pesquisa e busque novamente para conferir empresas e sua relação com o produto."}
    return job

@api.post("/buyer-discovery/search-jobs/{job_id}/retry")
async def retry_buyer_search_job(job_id: str, tasks: BackgroundTasks, user=Depends(get_current_user)):
    require_paid_discovery()
    previous = await authorized_buyer_job(job_id, user)
    if previous.get("discovery_version", 0) < DISCOVERY_VERSION:
        raise HTTPException(400, "Esta pesquisa usa o filtro anterior. Inicie uma nova pesquisa.")
    if previous["status"] in ("pending", "running"):
        raise HTTPException(409, "A pesquisa ainda está em andamento.")
    failed = {code for code, progress in previous.get("progress", {}).items() if progress.get("status") in ("failed", "partial", "blocked")}
    targets = [market for market in previous["targets"] if market["code"] in failed]
    if not targets:
        raise HTTPException(400, "Não há países com falha para repetir.")
    if await db.buyer_search_jobs.count_documents({"owner_id":user["id"], "status":{"$in":["pending","running"]}, "cancel_requested":{"$ne":True}}):
        raise HTTPException(409, "Há outra pesquisa em andamento. Aguarde ou interrompa antes de repetir.")
    job = {**previous, "id":str(uuid.uuid4()), "owner_id":user["id"], "targets":targets,
           "result_targets":previous.get("result_targets", previous["targets"]),
           "base_results":previous.get("results", []), "retry_of":job_id,
           "status":"pending", "total":len(targets), "completed":0, "failures":0, "cancel_requested":False,
           "service_error":"", "service_error_code":"", "created_at":now_iso(), "updated_at":now_iso(),
           "progress":{x["code"]:{"country":x["name"], "status":"pending", "count":0, "error":""} for x in targets}}
    await db.buyer_search_jobs.insert_one(dict(job))
    tasks.add_task(run_discovery_job, db, job, discover_buyers)
    return job

@api.post("/buyer-discovery/search-jobs/{job_id}/cancel")
async def cancel_buyer_search_job(job_id: str, user=Depends(get_current_user)):
    job = await authorized_buyer_job(job_id, user)
    if job["status"] in ("pending", "running"):
        await db.buyer_search_jobs.update_one({"id": job_id}, {"$set": {"cancel_requested": True}})
    return {"cancel_requested": True}

@api.post("/buyer-discovery/search")
async def buyer_discovery_search(body: BuyerDiscoveryRequest, user=Depends(get_current_user)):
    require_paid_discovery()
    if body.countries or body.region or any(separator in body.country for separator in [",", ";", "\n"]):
        raise HTTPException(400, "Para vários países ou regiões, use a pesquisa por mercados.")
    product = body.product.strip()
    country = body.country.strip()
    if not product or not country:
        raise HTTPException(400, "Informe produto e país.")
    try:
        buyers = await asyncio.to_thread(discover_buyers, product, country, max(1, min(body.limit, 20)))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except requests.RequestException as e:
        logging.error("Buyer discovery provider error")
        raise HTTPException(502, f"Provedor de pesquisa indisponível: {e}")
    return {"product": product, "country": country, "results": buyers, "warnings": getattr(buyers, "warnings", []), "source": "web_discovery"}

@api.post("/buyer-discovery/{company}/decision-maker")
async def buyer_discovery_decision_maker(company: str, product: str = "", country: str = "", user=Depends(get_current_user)):
    require_paid_discovery()
    if not company.strip():
        raise HTTPException(400, "Empresa obrigatória.")
    try:
        import asyncio
        return await asyncio.to_thread(discover_decision_maker, company, country, product)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except requests.RequestException as e:
        logging.error("Decision maker discovery provider error")
        raise HTTPException(502, f"Provedor de pesquisa indisponível: {e}")

@api.post("/buyer-discovery/to-crm")
async def buyer_discovery_to_crm(payload: dict, user=Depends(get_current_user)):
    company = str(payload.get("company", "")).strip()
    if not company:
        raise HTTPException(400, "Empresa obrigatória.")
    original_company = company
    original_country = str(payload.get("country", ""))
    try:
        score = float(payload.get("priority_score", 0) or 0)
        if not 0 <= score <= 100:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(400, "Score deve ser um número entre 0 e 100")
    enriched = (await asyncio.to_thread(enrich_company, payload)) if paid_discovery_enabled() else {
        "enrichment_status": "paused", "enrichment_message": "Enriquecimento externo pausado."}
    # Preserve the identity already grounded on the product page; contact
    # enrichment must not replace it with a homepage's product/article title.
    payload = {**payload, **{k: v for k, v in enriched.items() if v and not (k == "company" and payload.get("relationship_verified") is True)}}
    company = str(payload.get("company", company)).strip()
    country = str(payload.get("country", ""))
    data = {
        "company": company,
        "country": country,
        "country_code": str(payload.get("country_code", "")),
        "search_country": str(payload.get("search_country", "")),
        "website": str(payload.get("website", "")),
        "email": str(payload.get("email", "")),
        "phone": str(payload.get("phone", "")),
        "enrichment_status": payload.get("enrichment_status", ""),
        "enrichment_message": payload.get("enrichment_message", ""),
        "contact_source_urls": payload.get("contact_source_urls", []),
        "linkedin": str(payload.get("linkedin", "")),
        "product_interest": str(payload.get("product_interest", "")),
        "product_relationship": str(payload.get("product_relationship", "")),
        "product_evidence": str(payload.get("product_evidence", "")),
        "relationship_verified": payload.get("relationship_verified") is True,
        "source_url": str(payload.get("source_url", "")),
        "decision_source_url": str(payload.get("decision_source_url", "")),
        "source": "buyer_discovery",
        "priority": "high" if score >= 70 else "normal",
        "notes": (f"Relação publicada no site: {payload.get('product_evidence')}. Compra/importação e contatos ainda exigem validação."
                  if payload.get("relationship_verified") is True else "Candidato encontrado na web; empresa, atividade de compra e contatos exigem validação.") + f" Score de pesquisa: {payload.get('priority_score', 0)}",
        "decision_maker": str(payload.get("decision_maker", "")),
        "decision_maker_title": str(payload.get("decision_maker_title", "")),
        "decision_maker_email": str(payload.get("decision_maker_email", "")),
        "decision_maker_phone": str(payload.get("decision_maker_phone", "")),
        "validation_status": "needs_validation",
        "evidence_urls": [url for url in (payload.get("evidence_urls") if isinstance(payload.get("evidence_urls"), list) else []) if isinstance(url, str)][:20],
        "contact_candidates": payload.get("contact_candidates") if isinstance(payload.get("contact_candidates"), dict) else {},
        "updated_at": now_iso(),
    }
    existing = await db.leads.find_one(lead_scope(user, {"company": {"$regex": f"^{re.escape(original_company)}$", "$options": "i"}, "country": {"$regex": f"^{re.escape(original_country)}$", "$options": "i"}}), {"_id": 0})
    if not existing:
        existing = await db.leads.find_one(lead_scope(user, {"company": company, "country": country}), {"_id": 0})
    if existing:
        changes = {k: v for k, v in data.items() if v and not existing.get(k) and k != "evidence_urls"}
        if existing.get("source") == "buyer_discovery":
            for field in ("company", "country", "website", "enrichment_status", "enrichment_message", "contact_source_urls"):
                if data.get(field):
                    changes[field] = data[field]
        changes["updated_at"] = now_iso()
        update = {"$set": changes}
        if data["evidence_urls"]:
            update["$addToSet"] = {"evidence_urls": {"$each": data["evidence_urls"]}}
        await db.leads.update_one(lead_scope(user, {"id": existing["id"]}), update)
        return await require_lead(db, user, existing["id"])
    lead = Lead(**data)
    lead.owner_id = user["id"]
    key = hashlib.sha256((user["id"] + "\0" + company.casefold() + "\0" + country.strip().casefold()).encode()).hexdigest()
    record = {**lead.model_dump(), "discovery_key": key}
    try:
        return await db.leads.find_one_and_update({"discovery_key": key, "owner_id": user["id"]}, {"$setOnInsert": record}, upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0})
    except DuplicateKeyError:
        return await db.leads.find_one({"discovery_key": key, "owner_id": user["id"]}, {"_id": 0})

@api.post("/leads/{lid}/enrich")
async def enrich_existing_lead(lid: str, user=Depends(get_current_user)):
    lead = await require_lead(db, user, lid)
    if not lead:
        raise HTTPException(404, "Empresa não encontrada")
    require_paid_discovery()
    return await buyer_discovery_to_crm(lead, user)

# ============ DASHBOARD ============
@api.get("/dashboard/stats")
async def dashboard(user=Depends(get_current_user)):
    total_leads = await db.leads.count_documents(lead_scope(user))
    active = await db.leads.count_documents(lead_scope(user, {"stage": {"$nin": ["closed_won", "closed_lost"]}}))
    won = await db.leads.count_documents(lead_scope(user, {"stage": "closed_won"}))
    lost = await db.leads.count_documents(lead_scope(user, {"stage": "closed_lost"}))
    samples = await db.leads.count_documents(lead_scope(user, {"stage": {"$in": ["sample_quote", "sample_sent"]}}))
    conv = round((won / (won + lost)) * 100, 1) if (won + lost) > 0 else 0.0
    pipeline_value = 0.0
    async for d in db.leads.aggregate([
        {"$match": lead_scope(user, {"stage": {"$nin": ["closed_won", "closed_lost"]}})},
        {"$group": {"_id": None, "total": {"$sum": "$deal_value"}}}]):
        pipeline_value = d.get("total", 0.0)
    by_stage = {}
    async for d in db.leads.aggregate([{"$match": lead_scope(user)}, {"$group": {"_id": "$stage", "count": {"$sum": 1}}}]):
        by_stage[d["_id"]] = d["count"]
    by_industry = {}
    async for d in db.leads.aggregate([{"$match": lead_scope(user)}, {"$group": {"_id": "$industry", "count": {"$sum": 1}}}]):
        by_industry[d["_id"]] = d["count"]
    # ERP stats
    docs_count = await db.documents.count_documents(await document_scope(db, user, {"deleted_at": {"$in": [None, ""]}}))
    can_view_erp = user.get("role") == "admin"
    invoices_count = await db.invoices.count_documents({}) if can_view_erp else None
    suppliers_count = await db.suppliers.count_documents({})
    orders_pending = await db.orders.count_documents({"status": {"$in": ["draft", "confirmed"]}, "deleted_at": {"$in": [None, ""]}}) if can_view_erp else None
    finance_by_currency = pending_totals(await all_finance_entries()) if can_view_erp else []
    brl = next((row for row in finance_by_currency if row["currency"] == "BRL"), {})
    fin_receivable = brl.get("receivable", 0) if can_view_erp else None
    fin_payable = brl.get("payable", 0) if can_view_erp else None
    today = datetime.now(timezone.utc).date().isoformat()
    soon = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    expiring = await db.contracts.count_documents({"end_date": {"$gte": today, "$lte": soon}}) if can_view_erp else None
    return {
        "total_leads": total_leads, "active_leads": active, "samples_sent": samples,
        "won": won, "lost": lost, "conversion_rate": conv, "pipeline_value": pipeline_value,
        "by_stage": by_stage, "by_industry": by_industry,
        "can_view_erp": can_view_erp, "documents": docs_count, "invoices": invoices_count, "suppliers": suppliers_count,
        "orders_pending": orders_pending, "finance_receivable": fin_receivable,
        "finance_payable": fin_payable, "finance_by_currency": finance_by_currency, "contracts_expiring": expiring
    }

@api.post("/admin/migrate-crm-stages")
async def migrate_crm_stages(user=Depends(get_current_user)):
    require_admin(user)
    legacy = await db.leads.update_many({"stage": "sample_sent"}, {"$set": {"stage": "sample_quote", "updated_at": now_iso()}})
    return {"migrated_sample_sent_to_sample_quote": legacy.modified_count}

@api.get("/admin/backup")
async def download_database_backup(user=Depends(get_current_user)):
    require_admin(user)
    from backup import create_backup
    work = Path(tempfile.mkdtemp(prefix="ibiag-backup-download-"))
    try:
        async with business_write_lock() as ensure_owned:
            archive = await asyncio.to_thread(create_backup, work)
            await ensure_owned()
        return FileResponse(archive, filename=archive.name, media_type="application/gzip",
                            background=BackgroundTask(shutil.rmtree, work, ignore_errors=True))
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise

@api.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "database": "ok", "timestamp": now_iso()}
    except Exception:
        logging.error("Health check failed")
        raise HTTPException(503, "Database unavailable")

@api.get("/")
async def root(): return {"message": "IBIAG API", "status": "ok"}

app.include_router(api)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- SEED -----
async def seed_admin():
    # Bootstrap creates only: a restart must not restore a stale environment
    # password over credentials already stored by an authenticated user.
    await db.users.create_index("email", unique=True)
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if admin_email and admin_pw:
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            try:
                await db.users.update_one({"email": admin_email}, {"$setOnInsert": {
                    "id": str(uuid.uuid4()), "email": admin_email, "name": "Administrador IBIAG",
                    "password_hash": hash_pw(admin_pw), "role": "admin", "created_at": now_iso()}}, upsert=True)
            except DuplicateKeyError:
                if not await db.users.find_one({"email": admin_email}, {"id": 1}):
                    raise

@app.on_event("startup")
async def startup():
    # Expired revocations are deleted by MongoDB automatically. TTL cleanup
    # may be delayed, but JWT expiration remains enforced independently.
    await db.revoked_access_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("expires_at", expireAfterSeconds=0)
    await db.buyer_search_jobs.update_many({"status": {"$in": ["pending", "running"]}}, {"$set": {"status": "interrupted", "updated_at": now_iso()}})
    await db.leads.create_index("discovery_key", unique=True, sparse=True)
    # Startup is not authorization to replace a catalog or purge legacy CRM.
    # Keep create-only access bootstrap separate from business migrations.
    await seed_admin()

@app.on_event("shutdown")
async def shutdown(): client.close()
