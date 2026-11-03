import unittest, tempfile, os, threading, json, urllib.request, urllib.error
import server
from unittest.mock import patch
import base64
class AppTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();server.DB=os.path.join(cls.temp.name,'test.sqlite3');server.initialize()
  cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);cls.base='http://127.0.0.1:'+str(cls.http.server_port)
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.temp.cleanup()
 def req(self,path,body=None,cookie=None):
  headers={'Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  r=urllib.request.Request(self.base+'/api/'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(r) as res:return res.status,json.load(res),res.headers.get('Set-Cookie')
  except urllib.error.HTTPError as e:return e.code,json.load(e),None
 def login(self,role):return self.req('auth/demo',{'role':role})[2].split(';')[0]
 def test_hosted_demo_password(self):
  with patch.dict(os.environ,{'DEMO_ACCESS_PASSWORD':'unit-test-password'}):
   self.assertEqual(self.req('health')[0],200)
   try:urllib.request.urlopen(self.base+'/');self.fail('Demo page should require password')
   except urllib.error.HTTPError as e:self.assertEqual(e.code,401)
   token=base64.b64encode(b'demo:unit-test-password').decode()
   request=urllib.request.Request(self.base+'/',headers={'Authorization':'Basic '+token})
   with urllib.request.urlopen(request) as response:self.assertEqual(response.status,200)
 def test_auth_required(self):self.assertEqual(self.req('state')[0],401)
 def test_guest_privacy_and_write_rejection(self):
  cookie=self.login('Guest');code,data,_=self.req('state',cookie=cookie)
  self.assertEqual(code,200);self.assertNotIn('expenses',data);self.assertNotIn('budget',data['event'][0]);self.assertEqual(len(data['guests']),1);self.assertNotIn('hotels',data);self.assertEqual({t['name'] for t in data['timeline']},{'Wedding','Sangeet'})
  self.assertEqual(self.req('save',{'kind':'guests','item':{'name':'Intruder'}},cookie)[0],403)
 def test_vendor_scope(self):
  _,data,_=self.req('state',cookie=self.login('Vendor'));self.assertEqual(len(data['vendors']),1);self.assertNotIn('guests',data);self.assertNotIn('expenses',data)
 def test_finance_cap(self):
  cookie=self.login('Super Organiser')
  for i in range(5):self.assertEqual(self.req('save',{'kind':'members','item':{'name':str(i),'role':'Finance Team'}},cookie)[0],200)
  self.assertEqual(self.req('save',{'kind':'members','item':{'name':'sixth','role':'Finance Team'}},cookie)[0],400)
 def test_checkin_duplicate(self):
  cookie=self.login('Super Organiser');g=next(x for x in server.rows('guests') if x['status']=='Confirmed')
  self.assertEqual(self.req('checkin',{'guestId':g['id']},cookie)[0],200);self.assertEqual(self.req('checkin',{'guestId':g['id']},cookie)[0],409)
 def test_join_is_not_access(self):
  n=len(server.rows('guests'));self.assertEqual(self.req('join',{'code':'RAHUL-PRIYA-2026','name':'New Guest','phone':'9999999999'})[0],201);self.assertEqual(len(server.rows('guests')),n)
 def test_rsvp_limit(self):
  self.assertEqual(self.req('rsvp',{'status':'Confirmed','plusOnes':9,'consent':True},self.login('Guest'))[0],400)
 def test_finance_approval(self):
  cookie=self.login('Finance Team');self.assertEqual(self.req('save',{'kind':'expenses','item':{'name':'Large','amount':200000,'paid':0}},cookie)[0],200);self.assertEqual(server.rows('expenses')[-1]['status'],'Needs Approval')
 def test_travel_requires_consent(self):
  cookie=self.login('Guest')
  self.assertEqual(self.req('guest-update',{'travel':'Landed','consent':False},cookie)[0],400)
  self.assertEqual(self.req('guest-update',{'travel':'Landed','consent':True},cookie)[0],200)
 def test_one_vote_per_guest(self):
  cookie=self.login('Guest');poll=server.rows('polls')[0];payload={'id':poll['id'],'option':'Team Bride'}
  self.assertEqual(self.req('vote',payload,cookie)[0],200)
  self.assertEqual(self.req('vote',payload,cookie)[0],409)
  _,data,_=self.req('state',cookie=cookie);self.assertNotIn('voters',data['polls'][0])
 def test_audit_is_restricted(self):
  self.assertEqual(self.req('audit',cookie=self.login('Guest'))[0],403)
  self.assertEqual(self.req('audit',cookie=self.login('Finance Team'))[0],200)
 def test_logout_invalidates_session(self):
  cookie=self.login('Super Organiser');self.req('auth/logout',{},cookie)
  self.assertEqual(self.req('state',cookie=cookie)[0],401)
 def test_static_no_source_disclosure(self):
  try:urllib.request.urlopen(self.base+'/../server.py');self.fail('source disclosed')
  except urllib.error.HTTPError as e:self.assertEqual(e.code,404)
if __name__=='__main__':unittest.main()
