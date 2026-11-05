import os, csv, tempfile, contextlib, io
from unittest.mock import patch
from test_workflows import WorkflowCase
import server,manage
class InvestorRelease(WorkflowCase):
 def demo(self,role='Super Organiser',cookie=None):
  status,data,new=self.req('auth/demo',{'role':role},cookie);self.assertEqual(status,200,data);return new
 def test_visitors_have_isolated_sample_data(self):
  a=self.demo();b=self.demo();sa=self.req('state',cookie=a)[1];sb=self.req('state',cookie=b)[1]
  self.assertNotEqual(sa['event'][0]['id'],sb['event'][0]['id']);self.assertEqual(len(sa['guests']),12);self.assertEqual(len(sb['guests']),12)
  ga=sa['guests'][0];ga['name']='Private edit';self.assertEqual(self.req('save',{'kind':'guests','item':ga},a)[0],200)
  self.assertNotEqual(self.req('state',cookie=b)[1]['guests'][0]['name'],'Private edit')
  self.assertEqual(self.req('events/select',{'eventId':sa['event'][0]['id']},b)[0],403)
 def test_role_switch_reuses_only_own_workspace(self):
  owner=self.demo();event=self.req('state',cookie=owner)[1]['event'][0]['id']
  guest=self.demo('Guest',owner);data=self.req('state',cookie=guest)[1]
  self.assertEqual(data['event'][0]['id'],event);self.assertEqual(len(data['guests']),1);self.assertNotIn('expenses',data);self.assertNotIn('budget',data['event'][0])
  self.assertEqual(self.req('state',cookie=owner)[0],401)
 def test_reset_preserves_feedback_and_does_not_change_other_visitors(self):
  owner=self.demo();other=self.demo();before=self.req('state',cookie=owner)[1]['event'][0]['id'];otherid=self.req('state',cookie=other)[1]['event'][0]['id']
  payload={'rating':5,'usefulness':4,'willingness':'Maybe','persona':'Investor','comments':'Useful concept','consent':True}
  self.assertEqual(self.req('feedback',payload,owner)[0],200)
  status,data,new=self.req('demo/reset',{},owner);self.assertEqual(status,200,data)
  self.assertNotEqual(self.req('state',cookie=new)[1]['event'][0]['id'],before);self.assertEqual(self.req('state',cookie=other)[1]['event'][0]['id'],otherid)
  with server.conn() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM feedback').fetchone()['n'],1)
 def test_feedback_consent_validation_and_private_export(self):
  a=self.demo();payload={'rating':5,'usefulness':5,'willingness':'Yes','persona':'Family organiser','comments':'=not a formula','consent':False}
  self.assertEqual(self.req('feedback',payload,a)[0],400);payload['consent']=True;payload['rating']=7;self.assertEqual(self.req('feedback',payload,a)[0],400);payload['rating']=5
  self.assertEqual(self.req('feedback',payload,a)[0],200);self.assertEqual(self.req('feedback',payload,a)[0],200)
  self.assertEqual(self.req('feedback',cookie=a)[0],404)
  with server.conn() as c:
   rows=c.execute('SELECT * FROM feedback').fetchall();self.assertEqual(len(rows),1);self.assertNotIn('phone',dict(rows[0]));self.assertNotIn('email',dict(rows[0]))
  with tempfile.TemporaryDirectory() as tmp,patch('sys.argv',['manage.py','feedback-export',tmp+'/feedback.csv']),contextlib.redirect_stdout(io.StringIO()):
   manage.main()
   with open(tmp+'/feedback.csv') as f:data=list(csv.DictReader(f))
   self.assertEqual(data[0]['comments'],"'=not a formula")
   self.assertEqual(os.stat(tmp+'/feedback.csv').st_mode&0o777,0o600)
 def test_future_connections_never_return_credentials(self):
  owner=self.demo();status,data,_=self.req('integrations',cookie=owner);self.assertEqual(status,200);self.assertEqual(len(data['services']),4)
  with patch.dict(os.environ,{'TWILIO_AUTH_TOKEN':'do-not-expose-this-fixture'}):self.assertNotIn('do-not-expose',str(self.req('integrations',cookie=owner)[1]))
  guest=self.demo('Guest',owner);self.assertEqual(self.req('integrations',cookie=guest)[0],403)
 def test_demo_creation_isolated_and_full_feature_preview(self):
  a=self.demo();eid=self.event(a,'Sample personalised event');data=self.req('state',cookie=a)[1]
  self.assertEqual(data['event'][0]['plan'],'Event Pass');self.assertTrue(data['event'][0]['demoWorkspace']);self.assertEqual(len(data['events']),2)
  unrelated=self.account('9888888811');self.assertEqual(self.req('events/select',{'eventId':eid},unrelated)[0],403)
 def test_public_demo_has_no_unverified_phone_access(self):
  with patch.dict(os.environ,{'ALLOW_SANDBOX_OTP':'0'}):
   self.assertEqual(self.req('auth/otp',{'phone':'9000000000'})[0],403)
   self.assertFalse(self.req('bootstrap')[1]['sandboxOtpAvailable'])
