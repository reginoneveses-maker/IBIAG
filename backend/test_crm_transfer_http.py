import unittest
import test_crm_access as support
class CRMTransferHTTPTests(unittest.IsolatedAsyncioTestCase):
    make_database=support.CrmAccessTests.make_database
    asyncSetUp=support.CrmAccessTests.asyncSetUp
    asyncTearDown=support.CrmAccessTests.asyncTearDown
    request=support.CrmAccessTests.request
    headers=support.CrmAccessTests.headers
    create=support.CrmAccessTests.create
    async def test_private_read_only_admin_export(self):
        lead=await self.create('alice',country='Portugal',notes='PRIVATE',deal_value=99)
        before=await self.db.leads.find_one({'id':lead['id']})
        for user in ('alice','bob'):
            self.assertEqual((await self.request(user,'POST','/crm-transfer/export',json={'ids':[lead['id']]})).status_code,403)
        response=await self.request('admin','POST','/crm-transfer/export',json={'ids':[lead['id']]})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertNotIn('PRIVATE',response.text)
        self.assertNotIn('owner_id',response.text)
        self.assertEqual(response.json()['companies'][0]['sourceId'],lead['id'])
        self.assertEqual(await self.db.leads.find_one({'id':lead['id']}),before)
    async def test_strict_ids_and_no_partial_export(self):
        lead=await self.create('alice')
        for ids in ([],[1],[{'$ne':''}],[lead['id'],lead['id']],['x']*26):
            self.assertEqual((await self.request('admin','POST','/crm-transfer/export',json={'ids':ids})).status_code,422)
        self.assertEqual((await self.request('admin','POST','/crm-transfer/export',json={'ids':[lead['id'],'missing']})).status_code,409)
        self.assertIn((await self.client.post('/api/crm-transfer/export',json={'ids':[lead['id']]})).status_code,(401,403))
    async def test_order_and_extra_fields(self):
        a,b=await self.create('alice'),await self.create('bob')
        response=await self.request('admin','POST','/crm-transfer/export',json={'ids':[b['id'],a['id']]})
        self.assertEqual([r['sourceId'] for r in response.json()['companies']],[b['id'],a['id']])
        self.assertEqual((await self.request('admin','POST','/crm-transfer/export',json={'ids':[a['id']],'owner_id':'alice'})).status_code,422)
@unittest.skipUnless(support.os.environ.get('TEST_MONGO_URL'),'Disposable MongoDB not configured')
class CRMTransferMongoTests(CRMTransferHTTPTests):
    make_database=support.CrmAccessMongoTests.make_database
    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
