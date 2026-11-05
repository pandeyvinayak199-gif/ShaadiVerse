import concurrent.futures, hashlib, hmac, json, os, sqlite3, tempfile, threading, unittest
import urllib.request, urllib.error
from unittest.mock import patch
import server

class WorkflowCase(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old_db=server.DB;server.DB=self.tmp.name+'/app.sqlite3'
  self.env=patch.dict(os.environ,{'DEMO_MODE':'1','DEMO_ACCESS_PASSWORD':'','COOKIE_SECURE':'0','DATABASE_URL':''});self.env.start()
  server.initialize();self.csrf={}
  self.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.url='http://127.0.0.1:'+str(self.http.server_port)
  threading.Thread(target=self.http.serve_forever,daemon=True).start()
 def tearDown(self):
  self.http.shutdown();self.http.server_close();self.env.stop();server.DB=self.old_db;self.tmp.cleanup()
 def req(self,path,data=None,cookie=None,extra=None):
  headers={'Content-Type':'application/json'}
  if cookie:headers.update({'Cookie':cookie,'X-CSRF-Token':self.csrf.get(cookie,'')})
  if extra:headers.update(extra)
  request=urllib.request.Request(self.url+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
  try:
   with urllib.request.urlopen(request) as r:
    result=json.load(r);header=r.headers.get('Set-Cookie')
    if header and result.get('csrf'):self.csrf[header.split(';')[0]]=result['csrf']
    return r.status,result,header.split(';')[0] if header else None
  except urllib.error.HTTPError as e:return e.code,json.load(e),None
 def account(self,phone='9888888800',name='Event owner'):
  code,data,_=self.req('auth/otp',{'phone':phone});self.assertEqual(code,200,data)
  code,data,cookie=self.req('auth/verify',{'phone':phone,'name':name,'code':data.get('sandboxCode','123456')});self.assertEqual(code,200,data)
  return cookie
 def event(self,cookie,name='A & B'):
  status,data,_=self.req('events/create',{'name':name,'date':'2027-02-12','venue':'Jaipur','budget':1000000},cookie);self.assertEqual(status,201,data);return data['eventId']
 def guest(self,cookie,phone='9777777700',status='Confirmed'):
  code,data,_=self.req('save',{'kind':'guests','item':{'name':'Guest','phone':phone,'status':status,'plusOnes':1,'events':['Wedding']}},cookie);self.assertEqual(code,200,data);return data['id']
 def premium(self,eid):
  with server.conn(True) as c:
   e=server.rows('event',eid,c)[0];e['plan']='Event Pass';server.update(c,'event',e,eid)
class Workflows(WorkflowCase):
 def test_event_isolation_and_no_plan_escalation(self):
  a=self.account();ea=self.event(a);gid=self.guest(a)
  b=self.account('9888888801');eb=self.event(b,'C & D')
  self.assertNotEqual(ea,eb)
  self.assertEqual(self.req('events/select',{'eventId':ea},b)[0],403)
  self.assertEqual(self.req('save',{'kind':'guests','item':{'id':gid,'name':'Hacked'}},b)[0],404)
  event=self.req('state',cookie=a)[1]['event'][0];event['plan']='Event Pass'
  self.assertEqual(self.req('save',{'kind':'event','item':event},a)[0],200)
  self.assertEqual(self.req('state',cookie=a)[1]['event'][0]['plan'],'Free')
 def test_durable_sessions_and_additive_initialization(self):
  cookie=self.account();eid=self.event(cookie);gid=self.guest(cookie)
  server.initialize();status,data,_=self.req('state',cookie=cookie)
  self.assertEqual(status,200);self.assertEqual(data['event'][0]['id'],eid);self.assertEqual(data['guests'][0]['id'],gid)
  with server.conn() as c:self.assertEqual(len(c.execute('SELECT * FROM sessions').fetchall()),1)
 def test_production_rejects_demo_and_sandbox_sessions(self):
  demo=self.req('auth/demo',{'role':'Super Organiser'})[2]
  sandbox=self.account()
  with patch.dict(os.environ,{'DEMO_MODE':'0','TWILIO_ACCOUNT_SID':'','TWILIO_AUTH_TOKEN':'','TWILIO_VERIFY_SERVICE_SID':''}):
   self.assertEqual(self.req('auth/demo',{'role':'Super Organiser'})[0],403)
   self.assertEqual(self.req('state',cookie=demo)[0],401);self.assertEqual(self.req('state',cookie=sandbox)[0],401)
   status,data,_=self.req('auth/otp',{'phone':'9888888802'});self.assertEqual(status,503);self.assertNotIn('sandboxCode',data)
 def test_otp_one_use_and_attempt_limit(self):
  phone='9888888803';_,data,_=self.req('auth/otp',{'phone':phone});right=data['sandboxCode'];wrong='000000' if right!='000000' else '111111'
  for _ in range(5):self.assertEqual(self.req('auth/verify',{'phone':phone,'code':wrong})[0],400)
  self.assertEqual(self.req('auth/verify',{'phone':phone,'code':right})[0],400)
  phone='9888888804';_,data,_=self.req('auth/otp',{'phone':phone})
  self.assertEqual(self.req('auth/verify',{'phone':phone,'code':data['sandboxCode']})[0],200)
  self.assertEqual(self.req('auth/verify',{'phone':phone,'code':data['sandboxCode']})[0],400)
 def test_csrf_and_origin(self):
  cookie=self.account();self.event(cookie)
  self.assertEqual(self.req('events/create',{'name':'X'},cookie,{'X-CSRF-Token':''})[0],403)
  self.assertEqual(self.req('events/create',{'name':'X'},cookie,{'Origin':'https://evil.example'})[0],403)
 def test_join_approval_still_requires_phone_ownership(self):
  owner=self.account();eid=self.event(owner);event=self.req('state',cookie=owner)[1]['event'][0]
  self.assertEqual(self.req('join',{'name':'New guest','phone':'9777777705','code':event['code']})[0],201)
  outsider=self.account('9777777705');self.assertEqual(self.req('events/select',{'eventId':eid},outsider)[0],403)
  join=self.req('state',cookie=owner)[1]['joins'][0]
  self.assertEqual(self.req('joins/approve',{'id':join['id']},owner)[0],200)
  self.assertEqual(self.req('events/select',{'eventId':eid},outsider)[0],200)
  data=self.req('state',cookie=outsider)[1];self.assertEqual(data['user']['role'],'Guest');self.assertNotIn('budget',data['event'][0]);self.assertEqual(len(data['guests']),1)
 def test_signed_qr_revocation_and_atomic_duplicate_detection(self):
  owner=self.account();eid=self.event(owner);self.premium(eid);gid=self.guest(owner)
  status,pas,_=self.req('pass?guestId='+str(gid),cookie=owner);self.assertEqual(status,200);self.assertIn('<svg',pas['qrSvg']);server.initialize()
  self.assertEqual(self.req('checkin',{'token':pas['token'][:-1]+'x'},owner)[0],400)
  def check(n):return self.req('checkin',{'token':pas['token'],'requestId':'attempt-'+str(n)},owner)[0]
  with concurrent.futures.ThreadPoolExecutor(2) as pool:statuses=list(pool.map(check,[1,2]))
  self.assertEqual(sorted(statuses),[200,409])
  # Editing the RSVP cannot reset the authoritative entry history.
  g=self.req('state',cookie=owner)[1]['guests'][0];g['status']='Confirmed';self.req('save',{'kind':'guests','item':g},owner)
  self.assertEqual(self.req('checkin',{'token':pas['token']},owner)[0],409)
  self.assertEqual(self.req('members/revoke',{'phone':'9777777700'},owner)[0],200)
  self.assertEqual(self.req('checkin',{'token':pas['token']},owner)[0],400)
 def test_gate_idempotency_and_plus_one_enforcement(self):
  owner=self.account();eid=self.event(owner);self.premium(eid);gid=self.guest(owner)
  token=self.req('pass?guestId='+str(gid),cookie=owner)[1]['token']
  self.assertEqual(self.req('checkin',{'token':token,'plusOnes':2},owner)[0],400)
  payload={'token':token,'requestId':'offline-request-id'}
  self.assertEqual(self.req('checkin',payload,owner)[0],200)
  self.assertTrue(self.req('checkin',payload,owner)[1]['replayed'])
 def test_guest_pass_privacy_and_membership_revocation(self):
  owner=self.account();eid=self.event(owner);self.premium(eid);first=self.guest(owner);second=self.guest(owner,'9777777701')
  guest=self.account('9777777700');self.assertEqual(self.req('pass?guestId='+str(first),cookie=guest)[0],200)
  self.assertEqual(self.req('pass?guestId='+str(second),cookie=guest)[0],404)
  self.req('members/revoke',{'phone':'9777777700'},owner)
  self.assertEqual(self.req('pass?guestId='+str(first),cookie=guest)[0],403)
  self.assertEqual(self.req('events/select',{'eventId':eid},guest)[0],403)
 def test_real_staff_roles_are_bound_to_phone(self):
  owner=self.account();eid=self.event(owner)
  self.assertEqual(self.req('save',{'kind':'members','item':{'name':'Planner','phone':'9666666600','role':'Co-Organiser','permissions':['tasks']}},owner)[0],200)
  planner=self.account('9666666600');self.assertEqual(self.req('state',cookie=planner)[1]['user']['role'],'Co-Organiser')
  self.assertEqual(self.req('save',{'kind':'tasks','item':{'name':'Allowed','owner':'Planner','due':'2027-01-01','status':'To Do'}},planner)[0],200)
  self.assertEqual(self.req('save',{'kind':'guests','item':{'name':'Forbidden'}},planner)[0],403)
  self.assertEqual(self.req('save',{'kind':'members','item':{'name':'Self','phone':'9666666600','role':'Super Organiser'}},planner)[0],403)
 def test_free_guest_limit(self):
  owner=self.account();eid=self.event(owner)
  with server.conn(True) as c:
   for i in range(50):server.insert(c,'guests',{'name':str(i),'phone':'95555555'+f'{i:02}','status':'Invited'},eid)
  self.assertEqual(self.req('save',{'kind':'guests','item':{'name':'Over cap','phone':'9777777711','status':'Invited'}},owner)[0],402)
 def test_legacy_database_migration_preserves_data(self):
  path=self.tmp.name+'/legacy.sqlite3';c=sqlite3.connect(path);c.executescript('CREATE TABLE records(id INTEGER PRIMARY KEY,kind TEXT,data TEXT);CREATE TABLE audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,created REAL);');c.execute('INSERT INTO records VALUES(1,?,?)',('event','{"name":"Preserve me","code":"OLD"}'));c.commit();c.close()
  old=server.DB;server.DB=path
  try:server.initialize();self.assertEqual(server.rows('event')[0]['name'],'Preserve me')
  finally:server.DB=old

class LiveProviders(WorkflowCase):
 def setUp(self):
  super().setUp();self.live=patch.dict(os.environ,{'DEMO_MODE':'0','TWILIO_ACCOUNT_SID':'test-account','TWILIO_AUTH_TOKEN':'test-token','TWILIO_VERIFY_SERVICE_SID':'test-service','RAZORPAY_KEY_ID':'rzp_test_fixture','RAZORPAY_KEY_SECRET':'fixture-key-secret','RAZORPAY_WEBHOOK_SECRET':'fixture-webhook','WHATSAPP_ACCESS_TOKEN':'fixture-token','WHATSAPP_PHONE_NUMBER_ID':'123456','WHATSAPP_TEMPLATE_NAME':'wedding_invitation','WHATSAPP_APP_SECRET':'fixture-meta-secret'});self.live.start()
  self.send=patch('providers.sms_send',return_value={'status':'pending'});self.check=patch('providers.sms_check',return_value=True);self.send.start();self.check.start()
 def tearDown(self):self.check.stop();self.send.stop();self.live.stop();super().tearDown()
 def test_twilio_denied_verification_is_not_a_login(self):
  self.req('auth/otp',{'phone':'9888888833'})
  with patch('providers.sms_check',return_value=False):self.assertEqual(self.req('auth/verify',{'phone':'9888888833','code':'123456'})[0],400)
 def test_live_otp_never_discloses_code(self):
  code,data,_=self.req('auth/otp',{'phone':'9888888806'});self.assertEqual(code,200);self.assertNotIn('sandboxCode',data)
 def test_payment_is_captured_and_amount_verified(self):
  owner=self.account();eid=self.event(owner)
  with patch('providers.payment_request',return_value={'id':'order_fixture','amount':299900,'currency':'INR'}) as provider:
   status,data,_=self.req('payments/order',{'plan':'Event Pass','amount':1},owner);self.assertEqual(status,200);self.assertEqual(data['amount'],299900)
   self.assertEqual(provider.call_args.args[1]['amount'],299900)
  payload={'razorpay_order_id':'order_fixture','razorpay_payment_id':'pay_fixture','razorpay_signature':'bad'}
  self.assertEqual(self.req('payments/verify',payload,owner)[0],400)
  payload['razorpay_signature']=hmac.new(b'fixture-key-secret',b'order_fixture|pay_fixture',hashlib.sha256).hexdigest()
  with patch('providers.payment_request',return_value={'id':'pay_fixture','order_id':'order_fixture','status':'authorized','amount':299900,'currency':'INR'}):self.assertEqual(self.req('payments/verify',payload,owner)[0],400)
  payment={'id':'pay_fixture','order_id':'order_fixture','status':'captured','amount':299900,'currency':'INR'}
  with patch('providers.payment_request',return_value=payment):self.assertEqual(self.req('payments/verify',payload,owner)[0],200)
  self.assertEqual(self.req('state',cookie=owner)[1]['event'][0]['plan'],'Event Pass')
  self.assertEqual(self.req('invoice',cookie=owner)[1]['receipt']['payment_id'],'pay_fixture')
 def test_signed_payment_webhook_and_replay(self):
  owner=self.account();eid=self.event(owner)
  with server.conn(True) as c:c.execute('INSERT INTO purchases VALUES(?,?,?,?,?,?,?,?,?)',('order_hook',eid,'9888888800','Event Pass',299900,'INR','Pending',None,1))
  body={'event':'payment.captured','payload':{'payment':{'entity':{'id':'pay_hook','order_id':'order_hook','status':'captured','amount':299900,'currency':'INR'}}}}
  raw=json.dumps(body).encode();signature=hmac.new(b'fixture-webhook',raw,hashlib.sha256).hexdigest()
  self.assertEqual(self.req('webhooks/razorpay',body,extra={'X-Razorpay-Signature':'bad'})[0],403)
  for _ in range(2):self.assertEqual(self.req('webhooks/razorpay',body,extra={'X-Razorpay-Signature':signature})[0],200)
  self.assertEqual(self.req('state',cookie=owner)[1]['event'][0]['plan'],'Event Pass')
 def test_whatsapp_consent_dispatch_and_inbound_rsvp(self):
  owner=self.account();eid=self.event(owner);gid=self.guest(owner,status='Invited');guest=self.account('9777777700')
  self.assertEqual(self.req('whatsapp',{'guestIds':[gid]},owner)[0],400)
  self.req('rsvp',{'status':'Maybe','consent':True,'whatsappConsent':True},guest)
  self.assertEqual(self.req('whatsapp',{'guestIds':[gid]},owner)[0],200)
  with patch('providers.whatsapp_send',return_value={'messages':[{'id':'wamid.fixture'}]}) as send:
   self.assertEqual(self.req('messages/dispatch',{},owner)[0],200);self.assertEqual(send.call_count,1)
  body={'entry':[{'changes':[{'value':{'messages':[{'id':'inbound.fixture','from':'919777777700','context':{'id':'wamid.fixture'},'button':{'payload':'RSVP_YES'}}]}}]}]}
  signature='sha256='+hmac.new(b'fixture-meta-secret',json.dumps(body).encode(),hashlib.sha256).hexdigest()
  for _ in range(2):self.assertEqual(self.req('webhooks/whatsapp',body,extra={'X-Hub-Signature-256':signature})[0],200)
  self.assertEqual(self.req('state',cookie=guest)[1]['guests'][0]['status'],'Confirmed')

if __name__=='__main__':unittest.main()
