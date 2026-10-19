import io
import os
import unittest
from unittest.mock import patch, AsyncMock
from fastapi import UploadFile, HTTPException
import httpx
from mongomock_motor import AsyncMongoMockClient
import invoice_xml

with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"invoice_xml_test",
                            "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server

VALID = '''<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>
<ide><tpNF>1</tpNF><nNF>123</nNF><dhEmi>2026-10-18T10:00:00-03:00</dhEmi></ide>
<emit><xNome>IBIAG</xNome><CNPJ>11111111111111</CNPJ></emit>
<dest><xNome>Cliente Açúcar</xNome><CPF>22222222222</CPF></dest>
<total><ICMSTot><vNF>17500.50</vNF></ICMSTot></total>
</infNFe></NFe></nfeProc>'''

async def parse(raw):
    return await invoice_xml.parse_invoice_xml(UploadFile(io.BytesIO(raw),filename="invoice.xml"))


class InvoiceXmlTests(unittest.IsolatedAsyncioTestCase):
    async def test_namespaced_output_invoice_preserves_fields(self):
        result = await parse(VALID.encode())
        self.assertEqual(result,{"number":"123","kind":"saida","party_name":"Cliente Açúcar",
            "party_cnpj":"22222222222","issue_date":"2026-10-18","total":17500.5,
            "description":"NF-e 123 — IBIAG → Cliente Açúcar"})

    async def test_prefixes_and_declared_encoding_are_respected_for_input_invoice(self):
        import re
        text = VALID.replace('xmlns="','xmlns:n="').replace('<tpNF>1</tpNF>','<tpNF>0</tpNF>')
        text = re.sub(r'<(/?)([A-Za-z][A-Za-z0-9]*)',r'<\1n:\2',text)
        result = await parse(('<?xml version="1.0" encoding="ISO-8859-1"?>'+text).encode("iso-8859-1"))
        self.assertEqual(result["party_name"],"IBIAG")
        self.assertEqual(result["party_cnpj"],"11111111111111")
        self.assertIn("Açúcar",result["description"])

    async def test_dtd_and_entity_inputs_are_forbidden_without_fetching_resources(self):
        payloads = [b'<!DOCTYPE nfeProc [<!ENTITY x "PRIVATE-CANARY">]><nfeProc>&x;</nfeProc>',
                    b'<!DOCTYPE nfeProc SYSTEM "https://must-not-fetch.invalid/private.dtd"><nfeProc/>',
                    b'<!DOCTYPE nfeProc [<!ENTITY x SYSTEM "file:///not-a-real-private-file">]><nfeProc>&x;</nfeProc>']
        with patch("urllib.request.urlopen",side_effect=AssertionError("network must not run")):
            for data in payloads:
                with self.assertRaises(HTTPException) as error: await parse(data)
                self.assertEqual(error.exception.status_code,400)
                self.assertEqual(error.exception.detail,invoice_xml.INVALID_XML)

    async def test_depth_and_element_budgets_are_enforced(self):
        with patch.object(invoice_xml,"MAX_XML_DEPTH",8):
            with self.assertRaises(HTTPException) as error: await parse(b"<x>"*9+b"</x>"*9)
            self.assertEqual(error.exception.status_code,413)
        with patch.object(invoice_xml,"MAX_XML_ELEMENTS",10):
            with self.assertRaises(HTTPException) as error: await parse(b"<root>"+b"<x/>"*10+b"</root>")
            self.assertEqual(error.exception.status_code,413)

    async def test_byte_budget_is_checked_before_parser(self):
        with patch.object(invoice_xml,"MAX_XML_BYTES",16),patch.object(invoice_xml,"bounded_xml",side_effect=AssertionError("parser must not run")):
            with self.assertRaises(HTTPException) as error: await parse(b"x"*17)
            self.assertEqual(error.exception.status_code,413)

    async def test_malformed_or_unrelated_xml_and_nonfinite_totals_have_static_errors(self):
        data = [b'<private-canary></wrong>',b'<arbitrary/>',b'<infNFe/>',
                ('<?xml version="1.0" encoding="UTF-8"?>'+VALID).encode()+b'\xff']
        data += [VALID.replace('17500.50',value).encode() for value in ('NaN','Infinity','-1','','private-canary')]
        for raw in data:
            with self.assertRaises(HTTPException) as error: await parse(raw)
            self.assertEqual(error.exception.status_code,400)
            self.assertEqual(error.exception.detail,invoice_xml.INVALID_XML)

    async def test_route_keeps_admin_gate_and_does_not_persist_uploads(self):
        db = AsyncMongoMockClient()["isolated"]
        await db.users.insert_many([{"id":"admin","role":"admin"},{"id":"member","role":"user"}])
        with patch.object(server,"db",db):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test") as client:
                for user,code in ((None,401),("member",403),("admin",200)):
                    headers={"Authorization":"Bearer "+server.create_token(user,"test@example.com")} if user else {}
                    response=await client.post("/api/invoices/parse-xml",headers=headers,files={"file":("invoice.xml",VALID.encode(),"application/xml")})
                    self.assertEqual(response.status_code,code,response.text)
                headers={"Authorization":"Bearer "+server.create_token("admin","test@example.com")}
                response=await client.post("/api/invoices/parse-xml",headers=headers,files={"file":("bad.xml",b'<private-canary></wrong>')})
                self.assertEqual(response.status_code,400)
                self.assertEqual(response.json(),{"detail":invoice_xml.INVALID_XML})
        self.assertEqual(await db.invoices.count_documents({}),0)
        self.assertEqual(await db.documents.count_documents({}),0)
