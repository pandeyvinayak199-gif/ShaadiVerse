import json,struct,urllib.request,urllib.error
from unittest.mock import patch
from test_workflows import WorkflowCase
class PhoneApp(WorkflowCase):
 def test_manifest_icons_and_content_type(self):
  with urllib.request.urlopen(self.url+'/manifest.webmanifest') as r:
   self.assertIn('application/manifest+json',r.headers['Content-Type']);manifest=json.load(r)
  self.assertEqual(manifest['name'],'ShaadiVerse');self.assertEqual(manifest['display'],'standalone');self.assertEqual(manifest['scope'],'/')
  self.assertTrue(any(i['purpose']=='maskable' for i in manifest['icons']))
  for icon in manifest['icons']:
   with urllib.request.urlopen(self.url+icon['src']) as r:data=r.read();self.assertIn('image/png',r.headers['Content-Type'])
   self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n');w,h=struct.unpack('>II',data[16:24]);self.assertEqual(icon['sizes'],f'{w}x{h}')
 def test_public_brand_assets_do_not_bypass_demo_access(self):
  with patch.dict('os.environ',{'DEMO_ACCESS_PASSWORD':'fixture-password'}):
   with urllib.request.urlopen(self.url+'/manifest.webmanifest') as r:self.assertEqual(r.status,200)
   with urllib.request.urlopen(self.url+'/icons/apple-touch-icon.png') as r:self.assertEqual(r.status,200)
   for route in ['/','/api/state']:
    with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(self.url+route)
    self.assertEqual(caught.exception.code,401)
