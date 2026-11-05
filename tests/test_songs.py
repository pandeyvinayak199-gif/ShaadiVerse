import server
from test_workflows import WorkflowCase
class SpotifySongs(WorkflowCase):
 def demo(self,role='Super Organiser',cookie=None):return self.req('auth/demo',{'role':role},cookie)[2]
 def test_organiser_link_canonicalisation_and_edit(self):
  cookie=self.demo();track='3n3Ppam7vgaVa1iaRUc9Lp'
  status,data,_=self.req('save',{'kind':'songs','item':{'name':'Test song','artist':'Test artist','owner':'Family','spotifyUrl':'https://open.spotify.com/intl-en/track/'+track+'?si=tracking'}},cookie);self.assertEqual(status,200,data)
  song=self.req('state',cookie=cookie)[1]['songs'][0];self.assertEqual(song['spotifyUrl'],'https://open.spotify.com/track/'+track);self.assertEqual(song['artist'],'Test artist')
  song['spotifyUrl']='';self.assertEqual(self.req('save',{'kind':'songs','item':song},cookie)[0],200);self.assertEqual(self.req('state',cookie=cookie)[1]['songs'][0]['spotifyUrl'],'')
 def test_spotify_uri_and_short_link(self):
  self.assertEqual(server.spotify_link('spotify:track:3n3Ppam7vgaVa1iaRUc9Lp'),'https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp')
  self.assertEqual(server.spotify_link('https://spotify.link/Abc123?si=tracking'),'https://spotify.link/Abc123')
 def test_rejects_unsafe_and_unrelated_urls(self):
  cookie=self.demo()
  for value in ['javascript:alert(1)','https://evil.example/track/3n3Ppam7vgaVa1iaRUc9Lp','https://open.spotify.com.evil.example/track/3n3Ppam7vgaVa1iaRUc9Lp','https://user:pass@open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp','http://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp','https://open.spotify.com/track/not-a-track']:
   self.assertEqual(self.req('save',{'kind':'songs','item':{'name':'Bad link','spotifyUrl':value}},cookie)[0],400,value)
  self.assertEqual(self.req('state',cookie=cookie)[1]['songs'],[])
 def test_guest_requests_keep_link_and_are_private(self):
  owner=self.account();self.event(owner);self.guest(owner,'9777777700');self.guest(owner,'9777777701')
  guest=self.account('9777777700');other=self.account('9777777701')
  payload={'name':'Guest song','artist':'Artist','spotifyUrl':'https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp','owner':'Pretend organiser','status':'Approved'}
  self.assertEqual(self.req('song',payload,guest)[0],201)
  own=self.req('state',cookie=guest)[1]['songs'];self.assertEqual(len(own),1);self.assertEqual(own[0]['status'],'Pending');self.assertEqual(own[0]['owner'],'Event owner');self.assertEqual(own[0]['spotifyUrl'],payload['spotifyUrl'])
  self.assertEqual(self.req('state',cookie=other)[1]['songs'],[]);self.assertEqual(len(self.req('state',cookie=owner)[1]['songs']),1)
 def test_legacy_song_without_link_remains_available(self):
  cookie=self.demo();state=self.req('state',cookie=cookie)[1]
  with server.conn(True) as c:server.insert(c,'songs',{'name':'Old favourite','owner':'Family'},state['event'][0]['id'])
  self.assertEqual(self.req('state',cookie=cookie)[1]['songs'][0]['name'],'Old favourite')
