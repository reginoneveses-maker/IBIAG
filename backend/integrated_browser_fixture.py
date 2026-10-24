"""Loopback-only synthetic server for the integrated screen; never imports real data."""
import asyncio
import os
asyncio.set_event_loop(asyncio.new_event_loop())
os.environ.update(MONGO_URL="mongodb://127.0.0.1:27017", DB_NAME="ibiag_integrated_browser_fake",
 JWT_SECRET="synthetic-integration-only-32-characters")
from mongomock_motor import AsyncMongoMockClient
import server
server.db=AsyncMongoMockClient()["ibiag_integrated_browser_fake"]
from io import BytesIO
from reportlab.pdfgen import canvas
synthetic_pdf=BytesIO()
page=canvas.Canvas(synthetic_pdf);page.drawString(60,760,"IBIAG - SYNTHETIC TECHNICAL SHEET - NOT FOR COMMERCIAL USE");page.save()
objects={"fixture/ibiag.pdf":synthetic_pdf.getvalue(),"fixture/certificate.pdf":synthetic_pdf.getvalue()}
async def fixture_object(path):
    if path not in objects: raise server.HTTPException(404,"Synthetic file not found")
    return objects[path],"application/pdf"
server.get_object=fixture_object
async def seed():
    await server.db.users.insert_one({"id":"demo","email":"synthetic@example.com","role":"user","commercial_profile":"commercial-operator-v1","name":"Operadora fictícia"})
    await server.db.leads.insert_one({"id":"buyer","company":"Synthetic Buyer Portugal","country":"Portugal","owner_id":"demo"})
    await server.db.products.insert_one({"id":"ingredient","name":"Synthetic Acerola Powder","unit":"kg"})
    await server.db.suppliers.insert_one({"id":"supplier","name":"Synthetic Supplier","email":"supplier@example.test","phone":"+55 0000"})
    await server.db.product_offers.insert_one({"id":"offer","product_id":"ingredient","supplier_id":"supplier",
      "product_name":"Synthetic Acerola Powder","supplier_name":"Synthetic Supplier","active":True,"unit":"kg",
      "supplier_price":17.5,"spec_ids":["spec"],"certification_ids":["certificate"]})
    await server.db.specs.insert_one({"id":"spec","product_id":"ingredient","supplier_id":"supplier","product_name":"Synthetic Acerola Powder","ibiag_file_path":"fixture/ibiag.pdf","ibiag_file_name":"synthetic-ibiag.pdf"})
    await server.db.certifications.insert_one({"id":"certificate","supplier_id":"supplier","name":"Synthetic expired certificate","expiry_date":"2000-01-01","file_path":"fixture/certificate.pdf","file_name":"synthetic-certificate.pdf"})
server.app.router.on_startup=[seed]
server.app.router.on_shutdown=[]
@server.app.get("/fixture-token")
async def token(): return {"token":server.create_token("demo","synthetic@example.com")}
if __name__=="__main__":
    import uvicorn
    uvicorn.run(server.app,host="127.0.0.1",port=8766,log_level="error")
