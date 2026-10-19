import ast
import json
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import FastAPI, UploadFile, File
from starlette.responses import JSONResponse
import starlette.formparsers as multipart
from request_body_limits import RequestBodyLimits, RequestBodyTooLarge, UPLOAD_BODY_BYTES


async def drive(target, chunks, headers=(), path="/api/echo", limit=16, upload_limits=None):
    sent=[]
    calls=0
    iterator=iter(enumerate(chunks))
    async def receive():
        nonlocal calls
        calls+=1
        try: index,body=next(iterator)
        except StopIteration: return {"type":"http.disconnect"}
        return {"type":"http.request","body":body,"more_body":index<len(chunks)-1}
    async def send(message): sent.append(message)
    scope={"type":"http","method":"POST","path":path,"root_path":"","query_string":b"",
           "headers":list(headers),"http_version":"1.1","scheme":"http","server":("test",80),"client":("127.0.0.1",1)}
    await RequestBodyLimits(target,json_limit=limit,upload_limits=upload_limits or {},allowed_origins=["https://allowed.example"])(scope,receive,send)
    return sent,calls


class RequestBodyLimitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.delivered=[]
        self.entered=False
        async def consume(scope,receive,send):
            self.entered=True
            while True:
                message=await receive()
                if message["type"]=="http.disconnect": break
                self.delivered.append(message.get("body",b""))
                if not message.get("more_body",False): break
            await JSONResponse({"bytes":sum(map(len,self.delivered))})(scope,receive,send)
        self.consume=consume

    async def test_declared_oversize_rejected_before_application_or_body_with_safe_cors(self):
        for origin,allowed in ((b"https://allowed.example",True),(b"https://foreign.example",False)):
            sent,calls=await drive(self.consume,[b"private-canary"],[(b"content-length",b"17"),(b"origin",origin)])
            self.assertEqual(sent[0]["status"],413)
            self.assertEqual(calls,0)
            self.assertFalse(self.entered)
            headers=dict(sent[0]["headers"])
            self.assertEqual(headers[b"cache-control"],b"no-store")
            self.assertEqual(headers[b"x-content-type-options"],b"nosniff")
            self.assertEqual(b"access-control-allow-origin" in headers,allowed)
            self.assertNotIn(b"private-canary",sent[-1]["body"])

    async def test_exact_boundary_is_accepted(self):
        sent,_=await drive(self.consume,[b"x"*16],[(b"content-length",b"16")])
        self.assertEqual(sent[0]["status"],200)
        self.assertEqual(json.loads(sent[-1]["body"]),{"bytes":16})

    async def test_chunked_oversize_stops_before_delivering_offending_chunk(self):
        sent,_=await drive(self.consume,[b"a"*8,b"b"*9],[(b"transfer-encoding",b"chunked")])
        self.assertEqual(sent[0]["status"],413)
        self.assertEqual(self.delivered,[b"a"*8])

    async def test_small_declared_length_cannot_bypass_actual_byte_count(self):
        sent,_=await drive(self.consume,[b"a"*8,b"b"*9],[(b"content-length",b"1")])
        self.assertEqual(sent[0]["status"],413)
        self.assertEqual(self.delivered,[b"a"*8])

    async def test_invalid_or_ambiguous_length_headers_are_static_without_read(self):
        cases=[[(b"content-length",value)] for value in (b"-1",b"+1",b"",b"private-canary",b"1,1",b"1"*21)]
        cases += [[(b"content-length",b"4"),(b"content-length",b"4")],
                  [(b"content-length",b"4"),(b"transfer-encoding",b"chunked")]]
        for headers in cases:
            sent,calls=await drive(self.consume,[b"body"],headers)
            self.assertEqual(sent[0]["status"],400)
            self.assertEqual(calls,0)
            self.assertFalse(self.entered)
            self.assertNotIn(b"private-canary",sent[-1]["body"])

    async def test_upload_budget_includes_trailing_slash_and_other_paths_fail_closed(self):
        for path,expected in (("/api/upload",200),("/api/upload/",200),("/api/new-upload",413)):
            self.delivered=[]
            sent,_=await drive(self.consume,[b"x"*12],[(b"content-length",b"12")],path=path,limit=8,upload_limits={"/api/upload":16})
            self.assertEqual(sent[0]["status"],expected)

    async def test_downstream_error_response_is_replaced_after_limit_exceeded(self):
        async def target(scope,receive,send):
            try: await receive()
            except RequestBodyTooLarge:
                await JSONResponse({"error":"private-canary"},status_code=400)(scope,receive,send)
        sent,_=await drive(target,[b"x"*17])
        self.assertEqual(sent[0]["status"],413)
        self.assertNotIn(b"private-canary",sent[-1]["body"])
        self.assertEqual(sum(m["type"]=="http.response.start" for m in sent),1)

    async def test_already_started_response_is_interrupted_with_static_exception(self):
        async def target(scope,receive,send):
            await send({"type":"http.response.start","status":200,"headers":[]})
            await send({"type":"http.response.body","body":b"partial","more_body":True})
            try: await receive()
            except RequestBodyTooLarge: raise ValueError("private-canary")
        try: await drive(target,[b"x"*17])
        except RuntimeError as error:
            self.assertEqual(str(error),"Request body limit exceeded after response started")
            self.assertNotIn("private-canary","".join(traceback.format_exception(error)))
        else: self.fail("An already-started response must be interrupted")

    async def test_non_api_and_non_http_scopes_pass_through(self):
        async def target(scope,receive,send): self.entered=True
        async def unused(): raise AssertionError("receive must not run")
        async def send(message): pass
        for scope in ({"type":"lifespan"},{"type":"http","path":"/static/file"}):
            self.entered=False
            await RequestBodyLimits(target)(scope,unused,send)
            self.assertTrue(self.entered)

    async def test_invalid_configuration_fails_closed(self):
        for value in (0,-1,True,"16"):
            with self.assertRaises(ValueError): RequestBodyLimits(self.consume,json_limit=value)

    async def test_all_current_upload_routes_have_explicit_body_budgets(self):
        tree=ast.parse(Path(__file__).with_name("server.py").read_text())
        paths=set()
        for function in tree.body:
            if isinstance(function,ast.AsyncFunctionDef) and any(argument.annotation and "UploadFile" in ast.unparse(argument.annotation) for argument in function.args.args):
                for decorator in function.decorator_list:
                    if isinstance(decorator,ast.Call) and isinstance(decorator.func,ast.Attribute):
                        paths.add("/api"+ast.literal_eval(decorator.args[0]))
        self.assertEqual(paths,set(UPLOAD_BODY_BYTES))


class Chunks(httpx.AsyncByteStream):
    def __init__(self,chunks): self.chunks=chunks
    async def __aiter__(self):
        for chunk in self.chunks: yield chunk


class MultipartCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_streaming_multipart_overflow_closes_partial_file_before_endpoint(self):
        app=FastAPI()
        entered=[]
        @app.post("/api/upload")
        async def upload(file: UploadFile=File(...)):
            entered.append(True)
            return {"size":len(await file.read())}
        app.add_middleware(RequestBodyLimits,upload_limits={"/api/upload":300})
        body=(b'--test\r\nContent-Disposition: form-data; name="file"; filename="synthetic.txt"\r\n'
              b'Content-Type: text/plain\r\n\r\n'+b"x"*500+b"\r\n--test--\r\n")
        original=multipart.SpooledTemporaryFile
        files=[]
        def track(*args,**kwargs):
            kwargs["max_size"]=1
            file=original(*args,**kwargs)
            files.append(file)
            return file
        with patch.object(multipart,"SpooledTemporaryFile",side_effect=track):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
                response=await client.post("/api/upload",content=Chunks([body[:250],body[250:]]),
                                           headers={"Content-Type":"multipart/form-data; boundary=test"})
        self.assertEqual(response.status_code,413,response.text)
        self.assertEqual(entered,[])
        self.assertTrue(files)
        self.assertTrue(all(file.closed for file in files))
        self.assertTrue(any(file._rolled for file in files))

    async def test_streaming_json_is_rejected_before_endpoint_execution(self):
        app=FastAPI()
        entered=[]
        @app.post("/api/echo")
        async def echo(body:dict): entered.append(True);return body
        app.add_middleware(RequestBodyLimits,json_limit=16,upload_limits={})
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
            response=await client.post("/api/echo",content=Chunks([b'{"text":"',b'x'*20,b'"}']),headers={"Content-Type":"application/json"})
        self.assertEqual(response.status_code,413,response.text)
        self.assertEqual(entered,[])
