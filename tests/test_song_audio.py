import base64,io,os,shutil,subprocess,tempfile,urllib.request,urllib.error,wave
from unittest.mock import patch
from test_workflows import WorkflowCase
import server,song_audio

def audio_bytes(seconds=1):
 out=io.BytesIO()
 with wave.open(out,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\x00\x00'*int(8000*seconds))
 return out.getvalue()
class Mashups(WorkflowCase):
 def prepare(self):
  self.owner=self.account();self.eid=self.event(self.owner);self.guest(self.owner,'9777777700');self.guest(self.owner,'9777777701')
  self.guest_cookie=self.account('9777777700');self.other=self.account('9777777701')
  self.sid=self.req('song',{'name':'Our mashup'},self.guest_cookie)[1]['id']
 def upload(self,cookie=None,raw=None,consent=True):
  return self.req('song-audio',{'songId':self.sid,'filename':'our-mashup.wav','data':base64.b64encode(raw or audio_bytes()).decode(),'consent':consent},cookie or self.guest_cookie)
 def binary(self,extra=None,cookie=None):
  headers={'Cookie':cookie or self.guest_cookie,**(extra or {})}
  try:
   with urllib.request.urlopen(urllib.request.Request(self.url+'/api/song-audio/'+str(self.sid),headers=headers)) as r:return r.status,r.read(),dict(r.headers)
  except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
 def test_upload_play_ranges_metadata_and_persistence(self):
  self.prepare();raw=audio_bytes();status,data,_=self.upload(raw=raw);self.assertEqual(status,201,data)
  info=self.req('state',cookie=self.guest_cookie)[1]['songs'][0]['audio'];self.assertEqual(info['mime'],'audio/wav');self.assertEqual(info['filename'],'our-mashup.wav');self.assertAlmostEqual(info['duration'],1);self.assertNotIn('content',info)
  status,data,headers=self.binary();self.assertEqual(status,200);self.assertEqual(data,raw);self.assertEqual(headers['Cache-Control'],'private, no-store')
  for value,expected in [('bytes=0-99',raw[:100]),('bytes=100-',raw[100:]),('bytes=-50',raw[-50:])]:
   status,data,headers=self.binary({'Range':value});self.assertEqual(status,206);self.assertEqual(data,expected);self.assertIn('Content-Range',headers)
  self.assertEqual(self.binary({'Range':'bytes=999999-'})[0],416);self.assertEqual(self.binary({'Range':'bytes=0-1,4-5'})[0],416)
  server.initialize();self.assertEqual(self.binary()[1],raw)
 def test_access_and_role_permissions(self):
  self.prepare();self.assertEqual(self.upload()[0],201);self.assertEqual(self.binary(cookie=self.other)[0],403);self.assertEqual(self.binary(cookie=self.owner)[0],200)
  self.assertEqual(self.upload(self.other)[0],403);self.assertEqual(self.req('song',{'id':self.sid,'name':'Hijack'},self.other)[0],403)
  self.req('save',{'kind':'members','item':{'name':'Planner','phone':'9666666600','role':'Co-Organiser','permissions':['songs']}},self.owner);co=self.account('9666666600');self.assertEqual(self.upload(co)[0],201)
  self.req('save',{'kind':'members','item':{'name':'Other planner','phone':'9666666601','role':'Co-Organiser','permissions':['tasks']}},self.owner);no=self.account('9666666601');self.assertEqual(self.binary(cookie=no)[0],403)
  foreign=self.account('9888888801');self.event(foreign);self.assertEqual(self.binary(cookie=foreign)[0],404)
  self.assertEqual(self.req('song-audio',{'songId':self.sid})[0],401)
 def test_invalid_audio_consent_limits_replace_remove(self):
  self.prepare();self.assertEqual(self.upload(consent=False)[0],400);self.assertEqual(self.upload(raw=b'<script>bad</script>')[0],400)
  self.assertEqual(self.upload()[0],201);self.assertEqual(self.upload(raw=audio_bytes(2))[0],201)
  with server.conn() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM song_audio').fetchone()['n'],1)
  self.assertEqual(self.req('song-audio/remove',{'songId':self.sid},self.other)[0],403)
  self.assertEqual(self.req('song-audio/remove',{'songId':self.sid},self.guest_cookie)[0],200);self.assertEqual(self.binary()[0],404);self.assertNotIn('audio',self.req('state',cookie=self.guest_cookie)[1]['songs'][0])
  with patch('song_audio.MAX_BYTES',5):self.assertEqual(self.upload()[0],413)
  with patch('song_audio.quota',return_value=10):self.assertEqual(self.upload()[0],413)
 def test_csrf_and_guest_retry_update_same_request(self):
  self.prepare();body={'songId':self.sid,'filename':'audio.wav','data':base64.b64encode(audio_bytes()).decode(),'consent':True}
  self.assertEqual(self.req('song-audio',body,self.guest_cookie,{'X-CSRF-Token':'bad'})[0],403)
  self.assertEqual(self.req('song',{'id':self.sid,'name':'Updated mashup'},self.guest_cookie)[1]['id'],self.sid);self.assertEqual(len(self.req('state',cookie=self.guest_cookie)[1]['songs']),1)
  self.assertEqual(self.upload()[0],201)
  with server.conn(True) as c:c.execute('DELETE FROM records WHERE id=?',(self.sid,))
  with server.conn() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM song_audio').fetchone()['n'],0)
 def test_formats(self):
  if not shutil.which('ffmpeg'):self.skipTest('Optional fixture encoder is not installed')
  with tempfile.TemporaryDirectory() as d:
   source=d+'/input.wav'
   with open(source,'wb') as f:f.write(audio_bytes())
   for extension in ['mp3','m4a','ogg']:
    target=d+'/sample.'+extension;subprocess.run(['ffmpeg','-v','error','-y','-i',source,target],check=True)
    with open(target,'rb') as f:result=song_audio.validate(base64.b64encode(f.read()).decode())
    self.assertGreater(result[3],0)
