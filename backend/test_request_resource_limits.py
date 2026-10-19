"""Slow request bodies, shared worker capacity and multipart cleanup."""
import asyncio
import json
import traceback
import unittest
from unittest.mock import patch
import httpx
from fastapi import FastAPI, UploadFile, File
from starlette.responses import JSONResponse
import starlette.formparsers as multipart
from request_body_limits import RequestBodyLimits, RequestBodyTimedOut


def scope():
    return {"type":"http","method":"POST","path":"/api/upload","root_path":"","query_string":b"",
            "headers":[(b"origin",b"https://allowed.example")],"http_version":"1.1","scheme":"http",
            "server":("test",80),"client":("127.0.0.1",1)}


class RequestResourceLimitTests(unittest.IsolatedAsyncioTestCase):
    async def run_app(self, target, receive, **options):
        sent=[]
        async def send(message): sent.append(message)
        middleware=RequestBodyLimits(target,allowed_origins=["https://allowed.example"],**options)
        await middleware(scope(),receive,send)
        self.assertEqual(middleware.active,0)
        return sent

    async def test_idle_body_timeout_cancels_pending_read_and_returns_static_private_response(self):
        cancelled=[]
        async def receive():
            try: await asyncio.sleep(1)
            finally: cancelled.append(True)
        async def target(scope,receive,send): await receive()
        sent=await self.run_app(target,receive,idle_read_timeout=.02)
        self.assertEqual(sent[0]["status"],408)
        headers=dict(sent[0]["headers"])
        self.assertEqual(headers[b"cache-control"],b"no-store")
        self.assertEqual(headers[b"access-control-allow-origin"],b"https://allowed.example")
        self.assertEqual(json.loads(sent[-1]["body"]),{"detail":"Tempo limite de recebimento excedido"})
        self.assertTrue(cancelled)

    async def test_drip_feed_cannot_extend_total_body_deadline(self):
        consumed=[]
        async def receive():
            await asyncio.sleep(.02)
            return {"type":"http.request","body":b"x","more_body":True}
        async def target(scope,receive,send):
            while True: consumed.append(await receive())
        sent=await self.run_app(target,receive,idle_read_timeout=.2,body_read_timeout=.07)
        self.assertEqual(sent[0]["status"],408)
        self.assertLess(len(consumed),10)

    async def test_shared_capacity_rejects_before_application_and_recovers_when_released(self):
        release=asyncio.Event();ready=asyncio.Event();entered=[]
        async def target(scope,receive,send):
            entered.append(True)
            if len(entered)==2: ready.set()
            await release.wait()
            await JSONResponse({"ok":True})(scope,receive,send)
        async def receive(): raise AssertionError("No body should be consumed")
        middleware=RequestBodyLimits(target,active_limit=2)
        async def request():
            sent=[]
            async def send(message): sent.append(message)
            await middleware(scope(),receive,send)
            return sent
        tasks=[asyncio.create_task(request()) for _ in range(2)]
        try:
            await asyncio.wait_for(ready.wait(),5)
            response=await request()
            self.assertEqual(response[0]["status"],503)
            self.assertEqual(dict(response[0]["headers"])[b"retry-after"],b"1")
            self.assertEqual(len(entered),2)
        finally:
            release.set()
            await asyncio.gather(*tasks)
        self.assertEqual(middleware.active,0)
        self.assertEqual((await request())[0]["status"],200)

    async def test_capacity_released_after_application_error_and_external_cancellation(self):
        entered=asyncio.Event()
        async def target(scope,receive,send):
            entered.set();await asyncio.sleep(10)
        async def unused(): pass
        middleware=RequestBodyLimits(target,active_limit=1)
        task=asyncio.create_task(middleware(scope(),unused,unused))
        await asyncio.wait_for(entered.wait(),5)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(middleware.active,0)
        async def failure(scope,receive,send): raise ValueError("synthetic-failure")
        middleware.app=failure
        with self.assertRaises(ValueError): await middleware(scope(),unused,unused)
        self.assertEqual(middleware.active,0)

    async def test_completed_body_does_not_timeout_stream_disconnect_listener(self):
        calls=0
        async def receive():
            nonlocal calls
            calls+=1
            if calls==1: return {"type":"http.request","body":b"","more_body":False}
            await asyncio.sleep(.08)
            return {"type":"http.disconnect"}
        async def target(scope,receive,send):
            await receive();await receive()
            await JSONResponse({"ok":True})(scope,receive,send)
        sent=await self.run_app(target,receive,idle_read_timeout=.02,body_read_timeout=.04)
        self.assertEqual(sent[0]["status"],200)

    async def test_downstream_timeout_error_is_replaced_once_without_private_detail(self):
        async def receive(): await asyncio.sleep(1)
        async def target(scope,receive,send):
            try: await receive()
            except RequestBodyTimedOut:
                await JSONResponse({"detail":"private-canary"},status_code=400)(scope,receive,send)
        sent=await self.run_app(target,receive,idle_read_timeout=.02)
        self.assertEqual(sum(m["type"]=="http.response.start" for m in sent),1)
        self.assertEqual(sent[0]["status"],408)
        self.assertNotIn(b"private-canary",sent[-1]["body"])

    async def test_timeout_after_response_start_hides_original_exception(self):
        async def receive(): await asyncio.sleep(1)
        async def target(scope,receive,send):
            await send({"type":"http.response.start","status":200,"headers":[]})
            try: await receive()
            except RequestBodyTimedOut: raise ValueError("private-canary")
        with self.assertRaises(RuntimeError) as caught:
            await self.run_app(target,receive,idle_read_timeout=.02)
        self.assertNotIn("private-canary","".join(traceback.format_exception(caught.exception)))

    async def test_unsafe_limit_configuration_fails_closed(self):
        for active in (0,-1,True,1.5,"16"):
            with self.assertRaises(ValueError): RequestBodyLimits(None,active_limit=active)
        for seconds in (0,-1,True,"30",float("nan"),float("inf")):
            for key in ("idle_read_timeout","body_read_timeout"):
                with self.assertRaises(ValueError): RequestBodyLimits(None,**{key:seconds})

    async def test_slow_multipart_closes_spooled_file_and_never_enters_endpoint(self):
        app=FastAPI();entered=[];files=[]
        @app.post("/api/upload")
        async def upload(file:UploadFile=File(...)):
            entered.append(True);return {"ok":True}
        app.add_middleware(RequestBodyLimits,idle_read_timeout=.02,body_read_timeout=10)
        body=(b'--test\r\nContent-Disposition: form-data; name="file"; filename="synthetic.txt"\r\n'
              b'Content-Type: text/plain\r\n\r\n'+b"x"*500+b"\r\n--test--\r\n")
        class Slow(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield body[:250]
                await asyncio.sleep(.2)
                yield body[250:]
        original=multipart.SpooledTemporaryFile
        def track(*args,**kwargs):
            kwargs["max_size"]=1
            file=original(*args,**kwargs);files.append(file);return file
        with patch.object(multipart,"SpooledTemporaryFile",side_effect=track):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as client:
                response=await client.post("/api/upload",content=Slow(),headers={"Content-Type":"multipart/form-data; boundary=test"})
        self.assertEqual(response.status_code,408,response.text)
        self.assertEqual(entered,[])
        self.assertTrue(files)
        self.assertTrue(all(file.closed for file in files))
        self.assertTrue(any(file._rolled for file in files))
