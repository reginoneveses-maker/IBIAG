"""Local-only browser test server: isolated database/storage and fixed discovery responses."""
import os
from pathlib import Path
os.environ.update(MONGO_URL="mongodb://localhost:27017", DB_NAME="ibiag_browser_test", JWT_SECRET="browser-test-only-secret-32-characters")
from mongomock_motor import AsyncMongoMockClient
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import server
import buyer_discovery

server.db = AsyncMongoMockClient()["browser_test"]
objects = {}
async def put(path, data, content_type):
    objects[path] = (data, content_type)
    return {"path": path, "size": len(data), "content_type": content_type}
async def get(path):
    if path not in objects: raise server.HTTPException(404, "Arquivo não encontrado")
    return objects[path]
async def delete(path): objects.pop(path, None)
server.put_object, server.get_object, server.delete_object = put, get, delete
def fixture_search(query, limit):
    product = "Acerola" if "acerola" in query.lower() else "Manga"
    return [{"url":"https://example.com/company", "title":f"Organic {product} Extract 32%", "description":f"We supply {product} ingredients."},
            {"url":"https://books.google.com/books/fixture", "title":f"{product} research book"},
            {"url":"https://health.test/article", "title":f"{product} health benefits"}]
def fixture_business_page(url, product):
    company = "ABC-Ingredients" if product == "Acerola" else "Manga Company"
    identity = f"{company} is a food manufacturer."
    evidence = f"We supply {product} ingredients."
    return {"markdown":identity+"\n"+evidence, "json":{"company":company,"is_company":True,"is_directory":False,
            "page_type":"other" if "health.test" in url else "company_product", "relationship":"seller",
            "company_quote":identity,"product_quote":evidence}}
buyer_discovery._search, buyer_discovery._scrape_business = fixture_search, fixture_business_page
server.discover_decision_maker = lambda *args: {"decision_maker": "Ana Silva", "decision_maker_title": "Procurement Manager", "decision_maker_email": "ana@example.com", "decision_source_url": "https://example.com/team", "validation_status": "needs_validation"}
server.enrich_company = lambda candidate: {"email":"info@example.com", "phone":"+351 210 123 456", "enrichment_status":"complete", "contact_source_urls":["https://example.com/contact"]}
async def seed_fixture():
    await server.db.users.insert_one({"id":"u", "email":"test@example.com", "name":"Teste", "role":"admin", "password_hash":server.hash_pw("browser-test")})
    photo_names = ["AÇAÍ EXTRACT POWDER", "ACEROLA POWDER", "AÇAÍ PULP ORGANIC", "CASTANHA DE CAJU W320",
                   "BRAZILIAN NUTS", "GUARANÁ EM PÓ", "AÇAÍ FREEZE DRIED", "CAMU CAMU EXTRACT POWDER",
                   "GUARANA SEED", "MUIRAPUAMA POWDER", "MORINGA POWDER - ORGANIC", "PAU DA'ARCO POWDER",
                   "CATUABA POWDER", "PAU DA'ARCO CUT", "COCONUT WATER", "CASHEW JUICE CLARIFIED",
                   "ACEROLA CLARIFIED CONCENTRATE 50 BRIX", "ACEROLA EXTRACT POWDER"]
    await server.db.products.insert_many([server.Product(id=f"photo-{i}", name=name, category="Herbs and Roots").model_dump() for i, name in enumerate(photo_names)])
    await server.db.products.insert_one(server.Product(id="photo-broken",name="AÇAÍ FREEZE DRIED - ORGANIC",image_url="/missing-photo.jpg").model_dump())
    await server.db.products.insert_one(server.Product(id="photo-unknown",name="Produto sem ingrediente identificado").model_dump())
    await server.db.suppliers.insert_many([{"id":"s1","name":"Nossa Fruta"},{"id":"s2","name":"Itaueira"}])
    await server.db.documents.insert_many([
        {"id":"spec-a","title":"Ficha técnica Acerola","category":"Produtos","supplier_id":"s1","supplier_name":"Nossa Fruta","product_name":"Acerola","document_type":"Ficha Técnica","file_path":"fixture/spec-a.pdf","file_name":"spec-acerola.pdf"},
        {"id":"spec-b","title":"Ficha técnica Manga","category":"Produtos","product_name":"Manga","document_type":"Ficha Técnica","file_path":"fixture/spec-b.pdf","file_name":"spec-manga.pdf"},
        {"id":"spec-u","title":"Ficha técnica Guaraná","category":"Produtos","product_name":"Guaraná","document_type":"Ficha Técnica","file_path":"fixture/spec-u.pdf","file_name":"spec-guarana.pdf"}])
    await server.db.product_offers.insert_one({"id":"offer-b","supplier_id":"s2","product_name":"Manga","spec_document_ids":["spec-b"]})
    for path in ["fixture/spec-a.pdf","fixture/spec-b.pdf","fixture/spec-u.pdf"]:
        objects[path]=(b"%PDF-1.4 fixture spec","application/pdf")
server.app.router.on_startup = [seed_fixture]
server.app.router.on_shutdown = []
build = Path(__file__).resolve().parents[1] / "frontend" / "build"
server.app.mount("/static", StaticFiles(directory=build / "static"), name="test_static")
@server.app.get("/{path:path}")
async def spa(path: str): return FileResponse(build / "index.html")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(server.app, host="127.0.0.1", port=8765, log_level="error")
