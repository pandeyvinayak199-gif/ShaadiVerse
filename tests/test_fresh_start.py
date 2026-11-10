import json,os,urllib.request,urllib.error
from unittest.mock import patch
from test_workflows import WorkflowCase
import server
class FreshStart(WorkflowCase):
 def setUp(self):
  super().setUp();self.production=patch.dict(os.environ,{'APP_MODE':'user','DEMO_MODE':'1','ALLOW_SANDBOX_OTP':'1','DEMO_ACCESS_PASSWORD':'obsolete-password'});self.production.start();server.initialize()
  self.sms_ready=patch('providers.sms_ready',return_value=True);self.sms_send=patch('providers.sms_send',return_value={'status':'pending'});self.sms_check=patch('providers.sms_check',side_effect=lambda phone,code:code=='123456')
  for mock in [self.sms_ready,self.sms_send,self.sms_check]:mock.start()
 def tearDown(self):
  for mock in [self.sms_check,self.sms_send,self.sms_ready]:mock.stop()
  self.production.stop();super().tearDown()
 def test_blank_account_and_wedding_have_no_preloaded_records(self):
  owner=self.account();data=self.req('state',cookie=owner)[1];self.assertEqual(data['events'],[]);self.assertEqual(data['event'],[])
  result=self.req('events/create',{'name':'Our own wedding','date':'2027-08-12','budget':0,'venue':''},owner);self.assertEqual(result[0],201,result)
  data=self.req('state',cookie=owner)[1];self.assertEqual(data['event'][0]['plan'],'Wedding');self.assertEqual(data['event'][0]['venue'],'');self.assertEqual(data['event'][0]['hashtag'],'');self.assertEqual(data['event'][0]['budget'],0)
  for kind in ['guests','timeline','hotels','vendors','expenses','songs','polls','tasks','transport','gifts']:self.assertEqual(data[kind],[],kind)
  self.assertEqual(self.req('memories/member',cookie=owner)[1]['album'],None)
  self.assertEqual(self.req('save',{'kind':'vendors','item':{'name':'My vendor','quote':1000,'paid':0}},owner)[0],200)
 def test_old_demo_environment_cannot_enable_roles_sandbox_or_surveys(self):
  self.assertFalse(self.req('bootstrap')[1]['demoMode']);self.assertFalse(self.req('bootstrap')[1]['sandboxOtpAvailable']);self.assertEqual(self.req('auth/demo',{'role':'Guest'})[0],403);self.assertEqual(self.req('feedback',{})[0],404)
  response=self.req('auth/otp',{'phone':'9888888811'});self.assertEqual(response[0],200);self.assertNotIn('sandboxCode',response[1]);self.assertEqual(self.req('auth/verify',{'phone':'9888888811','code':'000000','name':'User'})[0],400)
  with patch('providers.sms_ready',return_value=False):self.assertEqual(self.req('auth/otp',{'phone':'9888888812'})[0],503)
 def test_only_marked_samples_and_their_files_are_removed(self):
  owner=self.account();real_id=self.event(owner,'Rahul & Priya')
  with patch.dict(os.environ,{'APP_MODE':'test','DEMO_MODE':'1','DEMO_ACCESS_PASSWORD':''}):
   demo=self.req('auth/demo',{'role':'Super Organiser'})[2];sample_id=self.req('state',cookie=demo)[1]['event'][0]['id'];self.req('memories/manage',{'action':'create'},demo)
  server.initialize();self.assertEqual(self.req('state',cookie=demo)[0],401);self.assertEqual(self.req('state',cookie=owner)[1]['event'][0]['id'],real_id)
  with server.conn() as c:
   self.assertEqual(c.execute('SELECT count(*) AS n FROM records WHERE event_id=?',(sample_id,)).fetchone()['n'],0);self.assertEqual(c.execute('SELECT count(*) AS n FROM memory_albums WHERE event_id=?',(sample_id,)).fetchone()['n'],0)
 def test_served_shell_has_no_survey_or_sample_entry_points(self):
  for path in ['/','/onboarding.js','/app.js','/features.js','/install.js','/help.js']:
   with urllib.request.urlopen(self.url+path) as r:content=r.read().decode()
   for forbidden in ['Rahul','Priya','pilot survey','feedbackForm','Switch demo role','Explore Rahul']:
    self.assertNotIn(forbidden,content,(path,forbidden))
  with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/pilot.js')
  self.assertEqual(error.exception.code,404)
