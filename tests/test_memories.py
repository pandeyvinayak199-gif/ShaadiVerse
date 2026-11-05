import base64,io,json,urllib.request,urllib.error,zipfile
from urllib.parse import urlparse
from unittest.mock import patch
from PIL import Image
from test_workflows import WorkflowCase
import server

def photo_bytes(fmt='JPEG'):
 output=io.BytesIO();image=Image.new('RGB',(120,90),'#bc9872');exif=Image.Exif();exif[315]='test metadata'
 image.save(output,fmt,**({'exif':exif} if fmt=='JPEG' else {}));return output.getvalue()
class SharedMemories(WorkflowCase):
 def owner(self):return self.req('auth/demo',{'role':'Super Organiser'})[2]
 def album(self,owner):
  status,data,_=self.req('memories/manage',{'action':'create'},owner);self.assertEqual(status,200,data);return data
 def visitor(self,album,name='Alice'):
  token=urlparse(album['shareUrl']).fragment;status,data,cookie=self.req('memories/join',{'token':token,'name':name,'consent':True});self.assertEqual(status,200,data);return cookie,data['csrf']
 def upload(self,album,cookie,csrf,key='request1234',raw=None):
  return self.req('memories/upload',{'albumId':album['album']['id'],'requestId':key,'data':base64.b64encode(raw or photo_bytes()).decode(),'uploader':'Spoofed name'},cookie,{'X-Memories-CSRF':csrf})
 def binary(self,path,cookie=None):
  request=urllib.request.Request(self.url+path,headers={'Cookie':cookie} if cookie else {})
  try:
   with urllib.request.urlopen(request) as r:return r.status,r.read(),dict(r.headers)
  except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
 def test_scan_name_upload_and_other_visitor_download(self):
  owner=self.owner();album=self.album(owner);token=urlparse(album['shareUrl']).fragment
  public=self.req('memories/access',{'token':token})[1];self.assertFalse(public['joined']);self.assertNotIn('hostUrl',public);self.assertNotIn('budget',str(public))
  a,csrf=self.visitor(album);status,uploaded,_=self.upload(album,a,csrf);self.assertEqual(status,201,uploaded)
  b,bs=self.visitor(album,'Bob');status,data,_=self.req('memories/album?album='+album['album']['id'],cookie=b);self.assertEqual(status,200);self.assertEqual(data['photos'][0]['uploader'],'Alice')
  self.assertFalse(data['photos'][0]['canDelete']);code,raw,headers=self.binary(data['photos'][0]['download'],b);self.assertEqual(code,200);self.assertIn('attachment',headers['Content-Disposition'])
  with Image.open(io.BytesIO(raw)) as image:self.assertEqual(image.format,'JPEG');self.assertEqual(len(image.getexif()),0)
  self.assertEqual(self.req('state',cookie=b)[0],401)
  self.assertEqual(self.upload(album,b,bs,'bobupload')[0],201)
  self.assertEqual(self.req('memories/album?album='+album['album']['id'],cookie=a)[1]['album']['photoCount'],2)
 def test_consent_csrf_and_input_validation(self):
  album=self.album(self.owner());token=urlparse(album['shareUrl']).fragment
  self.assertEqual(self.req('memories/join',{'token':token,'name':'Alice','consent':False})[0],400)
  a,csrf=self.visitor(album);self.assertEqual(self.upload(album,a,'wrong-csrf')[0],403)
  self.assertEqual(self.upload(album,a,csrf,raw=b'<svg><script>alert(1)</script></svg>')[0],400)
  self.assertEqual(self.req('memories/upload',{'albumId':album['album']['id'],'requestId':'badphoto123','data':'not-base64'},a,{'X-Memories-CSRF':csrf})[0],400)
  self.assertEqual(self.req('memories/album?album='+album['album']['id'],cookie=a)[1]['album']['photoCount'],0)
 def test_rotation_pause_and_host_recovery_preserve_photos(self):
  owner=self.owner();album=self.album(owner);a,csrf=self.visitor(album);self.assertEqual(self.upload(album,a,csrf)[0],201);aid=album['album']['id']
  self.assertEqual(self.req('memories/manage',{'albumId':aid,'action':'uploads','enabled':False},owner)[0],200);self.assertEqual(self.upload(album,a,csrf,'another123')[0],403)
  status,new,_=self.req('memories/manage',{'albumId':aid,'action':'rotate'},owner);self.assertEqual(status,200);self.assertEqual(new['album']['photoCount'],1)
  self.assertEqual(self.req('memories/access',{'token':urlparse(album['shareUrl']).fragment})[0],404);self.assertEqual(self.req('memories/album?album='+aid,cookie=a)[0],401)
  host_id,host_key=urlparse(album['hostUrl']).fragment.removeprefix('host=').split('.')
  status,h,hcookie=self.req('memories/host',{'albumId':host_id,'key':host_key});self.assertEqual(status,200);self.assertTrue(h['manager'])
  self.assertEqual(self.req('memories/manage',{'albumId':aid,'action':'sharing','enabled':False},hcookie,{'X-Memories-CSRF':h['csrf']})[0],200)
  self.assertEqual(self.req('memories/access',{'token':urlparse(new['shareUrl']).fragment})[0],410)
  self.assertEqual(self.req('memories/album?album='+aid,cookie=hcookie)[1]['album']['photoCount'],1)
 def test_event_isolation_and_no_visitor_management(self):
  one=self.album(self.owner());two=self.album(self.owner());a,csrf=self.visitor(one);b,bcsrf=self.visitor(two,'Bob');pid=self.upload(one,a,csrf)[1]['id']
  self.assertEqual(self.req('memories/album?album='+two['album']['id'],cookie=a)[0],401)
  self.assertEqual(self.binary('/api/memories/image/'+pid+'?album='+two['album']['id'],b)[0],404)
  self.assertEqual(self.req('memories/manage',{'albumId':one['album']['id'],'action':'rotate'},a,{'X-Memories-CSRF':csrf})[0],403)
  self.assertEqual(self.req('memories/host',{'albumId':one['album']['id'],'key':'wrong'})[0],403)
 def test_delete_rights_idempotency_and_zip(self):
  owner=self.owner();album=self.album(owner);a,csrf=self.visitor(album);b,bcsrf=self.visitor(album,'Bob')
  pid=self.upload(album,a,csrf)[1]['id'];again=self.upload(album,a,csrf);self.assertEqual(again[1]['id'],pid);self.assertTrue(again[1]['replayed'])
  bid=self.upload(album,b,bcsrf,'bobphoto123')[1]['id'];aid=album['album']['id']
  code,data,headers=self.binary('/api/memories/download?album='+aid+'&ids='+pid+','+bid,b);self.assertEqual(code,200);self.assertIn('application/zip',headers['Content-Type'])
  with zipfile.ZipFile(io.BytesIO(data)) as z:self.assertEqual(len(z.namelist()),2);self.assertTrue(all('/' not in n and n.endswith('.jpg') for n in z.namelist()))
  self.assertEqual(self.req('memories/remove',{'albumId':aid,'photoId':pid},b,{'X-Memories-CSRF':bcsrf})[0],403)
  self.assertEqual(self.req('memories/remove',{'albumId':aid,'photoId':bid},b,{'X-Memories-CSRF':bcsrf})[0],200)
  self.assertEqual(self.req('memories/remove',{'albumId':aid,'photoId':pid},owner)[0],200)
  self.assertEqual(self.req('memories/album?album='+aid,cookie=a)[1]['album']['photoCount'],0)
 def test_images_persist_after_initialize_and_storage_quota(self):
  owner=self.owner();album=self.album(owner);a,csrf=self.visitor(album);self.assertEqual(self.upload(album,a,csrf)[0],201);server.initialize()
  self.assertEqual(self.req('memories/album?album='+album['album']['id'],cookie=a)[1]['album']['photoCount'],1)
  with patch('memories.quota',return_value=1):self.assertEqual(self.upload(album,a,csrf,'overquota123')[0],413)
  self.assertEqual(self.req('memories/album?album='+album['album']['id'],cookie=a)[1]['album']['photoCount'],1)
 def test_large_gallery_paginates_without_a_per_person_photo_cap(self):
  import secrets
  owner=self.owner();album=self.album(owner);a,csrf=self.visitor(album);aid=album['album']['id'];raw=photo_bytes()
  with server.conn(True) as c:
   visitor=c.execute('SELECT id FROM memory_visitors WHERE album_id=?',(aid,)).fetchone()['id']
   for i in range(35):c.execute('INSERT INTO memory_photos VALUES(?,?,?,?,?,?,?,?,?,?,?)',(secrets.token_hex(16),aid,visitor,'Alice',raw,raw,len(raw)*2,120,90,float(i+1),'batch-'+str(i)))
  first=self.req('memories/album?album='+aid,cookie=a)[1];self.assertEqual(len(first['photos']),30);self.assertIsNotNone(first['next'])
  second=self.req('memories/album?album='+aid+'&before='+first['next'],cookie=a)[1];self.assertEqual(len(second['photos']),5);self.assertIsNone(second['next'])
  self.assertEqual(len({p['id'] for p in first['photos']+second['photos']}),35)
 def test_private_demo_password_does_not_block_qr_album(self):
  album=self.album(self.owner())
  with patch.dict('os.environ',{'DEMO_ACCESS_PASSWORD':'fixture-private-password'}):
   self.assertEqual(self.binary('/memories')[0],200);self.assertEqual(self.binary('/memory-client.js')[0],200);self.assertEqual(self.binary('/memory-style.css')[0],200);self.assertEqual(self.binary('/')[0],401)
   self.assertEqual(self.req('memories/access',{'token':urlparse(album['shareUrl']).fragment})[0],200)
 def test_guest_member_receives_no_private_host_link(self):
  owner=self.owner();album=self.album(owner);guest=self.req('auth/demo',{'role':'Guest'},owner)[2]
  status,data,_=self.req('memories/member',cookie=guest);self.assertEqual(status,200);self.assertFalse(data['canManage']);self.assertNotIn('hostUrl',data);self.assertEqual(data['shareUrl'],album['shareUrl'])
  vendor=self.req('auth/demo',{'role':'Vendor'},guest)[2];self.assertEqual(self.req('memories/member',cookie=vendor)[0],403)
 def test_large_photo_is_resized_for_sharing(self):
  album=self.album(self.owner());a,csrf=self.visitor(album);image=Image.new('RGB',(3000,2000),'#aabbcc');output=io.BytesIO();image.save(output,'JPEG')
  self.assertEqual(self.upload(album,a,csrf,raw=output.getvalue())[0],201)
  photo=self.req('memories/album?album='+album['album']['id'],cookie=a)[1]['photos'][0];self.assertEqual(photo['width'],2560);self.assertLessEqual(photo['height'],2560)
 def test_coorganiser_gets_controls_but_not_permanent_host_secret(self):
  owner=self.account();self.event(owner);album=self.album(owner);aid=album['album']['id']
  self.assertEqual(self.req('save',{'kind':'members','item':{'name':'Planner','phone':'9666666611','role':'Co-Organiser','permissions':['photos']}},owner)[0],200)
  co=self.account('9666666611');status,data,_=self.req('memories/member',cookie=co);self.assertEqual(status,200);self.assertTrue(data['canManage']);self.assertNotIn('hostUrl',data)
  status,data,_=self.req('memories/manage',{'albumId':aid,'action':'create'},co);self.assertEqual(status,200);self.assertNotIn('hostUrl',data)
  self.assertEqual(self.req('memories/manage',{'albumId':aid,'action':'host-rotate'},co)[0],403)
 def test_private_host_link_can_be_revoked_without_touching_guest_photos(self):
  owner=self.owner();album=self.album(owner);aid=album['album']['id'];oldkey=urlparse(album['hostUrl']).fragment.split('.')[1]
  status,data,cookie=self.req('memories/host',{'albumId':aid,'key':oldkey});self.assertEqual(status,200)
  status,new,_=self.req('memories/manage',{'albumId':aid,'action':'host-rotate'},owner);self.assertEqual(status,200);self.assertEqual(new['shareUrl'],album['shareUrl'])
  self.assertEqual(self.req('memories/host',{'albumId':aid,'key':oldkey})[0],403)
  self.assertEqual(self.req('memories/album?album='+aid,cookie=cookie)[0],401)
 def test_iphone_heic_is_decoded(self):
  album=self.album(self.owner());a,csrf=self.visitor(album);status,data,_=self.upload(album,a,csrf,raw=photo_bytes('HEIF'));self.assertEqual(status,201,data)
 def test_signed_in_guest_uploads_without_qr_join(self):
  owner=self.account();eid=self.event(owner);album=self.album(owner)
  self.guest(owner)
  guest=self.account('9777777700','Wedding guest')
  self.assertEqual(self.req('events/select',{'eventId':eid},guest)[0],200)
  status,data,_=self.upload(album,guest,'','guest-account-1');self.assertEqual(status,201,data)
  listing=self.req('memories/album?album='+album['album']['id'],cookie=guest)[1]
  self.assertEqual(listing['photos'][0]['uploader'],'Wedding guest');self.assertFalse(listing['manager']);self.assertTrue(listing['photos'][0]['canDelete'])
  self.assertEqual(self.req('memories/manage',{'albumId':album['album']['id'],'action':'uploads','enabled':False},guest)[0],403)
  self.assertEqual(self.req('memories/upload',{'albumId':album['album']['id'],'requestId':'bad-csrf-123','data':base64.b64encode(photo_bytes()).decode()},guest,{'X-CSRF-Token':'wrong'})[0],403)
  other=self.account('9888888801');self.event(other)
  self.assertEqual(self.upload(album,other,'','other-event-123')[0],401)
  self.req('memories/manage',{'albumId':album['album']['id'],'action':'uploads','enabled':False},owner)
  self.assertEqual(self.upload(album,guest,'','paused-guest-123')[0],403)
