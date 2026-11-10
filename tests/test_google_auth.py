import os,uuid,urllib.request,urllib.error,hashlib,base64
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
from test_workflows import WorkflowCase
import server,google_auth
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class GoogleSignIn(WorkflowCase):
 def setUp(self):
  super().setUp();self.config=patch.dict(os.environ,{'APP_MODE':'user','AUTH_PROVIDER':'google','SUPABASE_URL':'https://example.supabase.co','SUPABASE_PUBLISHABLE_KEY':'public-fixture-key','PUBLIC_BASE_URL':self.url});self.config.start();server.initialize();self.opener=urllib.request.build_opener(NoRedirect())
 def tearDown(self):self.config.stop();super().tearDown()
 def get(self,path,cookie=None):
  request=urllib.request.Request(self.url+path,headers={'Cookie':cookie} if cookie else {})
  try:
   response=self.opener.open(request)
  except urllib.error.HTTPError as e:response=e
  return response.code,response.headers,response.read()
 def profile(self,address,subject):return {'id':subject,'email':address,'email_confirmed_at':'2026-01-01','identities':[{'provider':'google','identity_data':{'email_verified':True}}],'user_metadata':{'full_name':'Google user'}}
 def sign_in(self,address='owner@example.com',subject='11111111-1111-4111-8111-111111111111'):
  status,headers,_=self.get('/api/auth/google');self.assertEqual(status,303);attempt=headers['Set-Cookie'].split(';')[0]
  with patch('google_auth.request',side_effect=[{'access_token':'verified-provider-token'},self.profile(address,subject)]):status,headers,_=self.get('/auth/callback?code=provider-code',attempt)
  self.assertEqual(status,303);self.assertEqual(headers['Location'],'/');cookie=next(c.split(';')[0] for c in headers.get_all('Set-Cookie') if c.startswith('session='));state=self.req('state',cookie=cookie)[1];self.csrf[cookie]=state['csrf'];return cookie,state
 def test_server_pkce_cookie_and_private_session(self):
  status,headers,_=self.get('/api/auth/google');self.assertEqual(status,303);query=parse_qs(urlparse(headers['Location']).query);self.assertEqual(query['provider'],['google']);self.assertEqual(query['redirect_to'],[self.url+'/auth/callback']);self.assertEqual(query['code_challenge_method'],['s256']);self.assertNotIn('verifier',headers['Location']);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Lax',headers['Set-Cookie'])
  with server.conn() as c:verifier=c.execute('SELECT verifier FROM oauth_attempts').fetchone()['verifier']
  self.assertEqual(query['code_challenge'][0],base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('='))
  cookie,state=self.sign_in();self.assertTrue(state['user']['google']);self.assertEqual(state['user']['email'],'owner@example.com');self.assertEqual(state['events'],[]);self.assertTrue(state['user']['phone'].startswith('google:'))
  cookie2,state2=self.sign_in();self.assertEqual(state['user']['phone'],state2['user']['phone']);self.assertEqual(self.req('auth/otp',{'phone':'9888888800'})[0],410)
 def test_callback_csrf_replay_and_wrong_identity(self):
  with patch('google_auth.request') as api:
   _,headers,_=self.get('/auth/callback?code=anything');self.assertIn('signin_error',headers['Location']);api.assert_not_called()
  _,headers,_=self.get('/api/auth/google');attempt=headers['Set-Cookie'].split(';')[0];user=self.profile('owner@example.com',str(uuid.uuid4()));user['identities'][0]['identity_data']['email_verified']=False
  with patch('google_auth.request',side_effect=[{'access_token':'token'},user]) as api:
   _,headers,_=self.get('/auth/callback?code=code',attempt);self.assertIn('signin_error',headers['Location']);self.assertFalse(any(c.startswith('session=') for c in headers.get_all('Set-Cookie')))
   self.get('/auth/callback?code=code',attempt);self.assertEqual(api.call_count,2)
 def test_email_guest_access_and_revocation(self):
  owner,_=self.sign_in();eid=self.event(owner)
  status,data,_=self.req('save',{'kind':'guests','item':{'name':'Guest','email':'guest@example.com','status':'Invited','plusOnes':1}},owner);self.assertEqual(status,200,data);gid=data['id']
  guest,state=self.sign_in('guest@example.com','22222222-2222-4222-8222-222222222222');self.assertEqual(state['user']['role'],'Guest');self.assertEqual(state['guests'][0]['id'],gid)
  key=state['user']['phone'];self.assertEqual(self.req('members/revoke',{'phone':key},owner)[0],200)
  guest,state=self.sign_in('guest@example.com','22222222-2222-4222-8222-222222222222');self.assertEqual(state['events'],[])
 def test_pending_team_invite_and_join_request(self):
  owner,_=self.sign_in();eid=self.event(owner)
  result=self.req('save',{'kind':'members','item':{'name':'Planner','email':'planner@example.com','role':'Co-Organiser','permissions':['timeline','songs']}},owner);self.assertEqual(result[0],200,result)
  planner,state=self.sign_in('planner@example.com','33333333-3333-4333-8333-333333333333');self.assertEqual(state['user']['role'],'Co-Organiser');self.assertEqual(state['user']['permissions'],['timeline','songs'])
  guest,state=self.sign_in('newguest@example.com','44444444-4444-4444-8444-444444444444');code=self.req('state',cookie=owner)[1]['event'][0]['code']
  self.assertEqual(self.req('join',{'code':code,'name':'New guest','phone':''},guest)[0],201);join=self.req('state',cookie=owner)[1]['joins'][0];self.assertEqual(join['accountId'],state['user']['phone']);self.assertEqual(self.req('joins/approve',{'id':join['id']},owner)[0],200)
  self.assertEqual(self.req('events/select',{'eventId':eid},guest)[0],200);self.assertEqual(self.req('state',cookie=guest)[1]['user']['role'],'Guest')
  self.assertEqual(self.req('join',{'code':code,'name':'Owner'},owner)[0],409)
 def test_google_email_does_not_claim_phone_accounts(self):
  with server.conn(True) as c:
   c.execute('INSERT INTO users VALUES(?,?,?)',('9888888800','Existing user',0));event=server.insert(c,'event',{'name':'Private old wedding','date':'2027-02-01','code':'OLD','plan':'Wedding'},0);c.execute('UPDATE records SET event_id=? WHERE id=?',(event,event));c.execute('INSERT INTO memberships VALUES(?,?,?,?,?,?)',(event,'9888888800','Super Organiser',None,'[]',0))
  _,state=self.sign_in();self.assertEqual(state['events'],[]);self.assertEqual(state['user']['contactPhone'],'')
 def test_contact_number_does_not_grant_email_invitation(self):
  owner,_=self.sign_in();self.event(owner)
  result=self.req('save',{'kind':'guests','item':{'name':'Invited Google guest','email':'guest@example.com','phone':'9777777700','status':'Invited'}},owner);self.assertEqual(result[0],200,result)
  with patch.dict(os.environ,{'AUTH_PROVIDER':'phone'}),patch('providers.sms_ready',return_value=True),patch('providers.sms_send'),patch('providers.sms_check',return_value=True):
   legacy=self.account('9777777700');self.assertEqual(self.req('state',cookie=legacy)[1]['events'],[])
 def test_revoked_email_invitation_stays_revoked_on_first_google_login(self):
  owner,_=self.sign_in();self.event(owner);self.req('save',{'kind':'guests','item':{'name':'Guest','email':'guest@example.com','status':'Invited'}},owner)
  self.assertEqual(self.req('members/revoke',{'phone':'email:guest@example.com'},owner)[0],200)
  _,state=self.sign_in('guest@example.com','22222222-2222-4222-8222-222222222222');self.assertEqual(state['events'],[])
