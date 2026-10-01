    password: str
    name: str = ""

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