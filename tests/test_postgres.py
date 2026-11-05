"""Optional tests create and drop ONLY their own random database on a disposable server."""
import concurrent.futures,json,os,secrets,threading,unittest
from unittest.mock import patch
from test_workflows import WorkflowCase
import server,storage
@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'),'Requires an explicitly supplied disposable PostgreSQL server')
class PostgreSQLRelease(WorkflowCase):
 def setUp(self):
  import psycopg
  from psycopg import sql
  from psycopg.conninfo import conninfo_to_dict,make_conninfo
  self.admin_url=os.environ['TEST_DATABASE_URL'];self.database='shaadi_test_'+secrets.token_hex(6)
  with psycopg.connect(self.admin_url,autocommit=True) as c:c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(self.database)))
  options=conninfo_to_dict(self.admin_url);options['dbname']=self.database;self.url_db=make_conninfo(**options)
  self.env=patch.dict(os.environ,{'DATABASE_URL':self.url_db,'DEMO_MODE':'1','ALLOW_SANDBOX_OTP':'0','DEMO_ACCESS_PASSWORD':''});self.env.start();self.csrf={};self.http=None
 def start(self):
  server.initialize();self.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.url='http://127.0.0.1:'+str(self.http.server_port);threading.Thread(target=self.http.serve_forever,daemon=True).start()
 def tearDown(self):
  import psycopg
  from psycopg import sql
  if self.http:self.http.shutdown();self.http.server_close()
  self.env.stop()
  with psycopg.connect(self.admin_url,autocommit=True) as c:c.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(self.database)))
 def demo(self):return self.req('auth/demo',{'role':'Super Organiser'})[2]
 def test_postgres_memories_photo_bytes_persist(self):
  import base64,urllib.request
  from test_memories import photo_bytes
  self.start();owner=self.demo();status,album,_=self.req('memories/manage',{'action':'create'},owner);self.assertEqual(status,200,album)
  token=album['shareUrl'].split('#')[1];status,visitor,cookie=self.req('memories/join',{'token':token,'name':'Postgres visitor','consent':True});self.assertEqual(status,200,visitor)
  payload={'albumId':album['album']['id'],'requestId':'postgres-photo','data':base64.b64encode(photo_bytes()).decode()}
  status,photo,_=self.req('memories/upload',payload,cookie,{'X-Memories-CSRF':visitor['csrf']});self.assertEqual(status,201,photo);server.initialize()
  listing=self.req('memories/album?album='+album['album']['id'],cookie=cookie)[1];self.assertEqual(listing['album']['photoCount'],1)
  req=urllib.request.Request(self.url+listing['photos'][0]['download'],headers={'Cookie':cookie})
  with urllib.request.urlopen(req) as result:self.assertTrue(result.read().startswith(b'\xff\xd8'))
 def test_postgres_memories_concurrent_quota(self):
  import base64
  from test_memories import photo_bytes
  import memories
  self.start();owner=self.demo();album=self.req('memories/manage',{'action':'create'},owner)[1];token=album['shareUrl'].split('#')[1]
  a=self.req('memories/join',{'token':token,'name':'A','consent':True});b=self.req('memories/join',{'token':token,'name':'B','consent':True})
  encoded=base64.b64encode(photo_bytes()).decode();image,thumbnail,_,_=memories.prepare_image(encoded);allowance=len(image)+len(thumbnail)+1
  def upload(item):
   _,visitor,cookie=item
   return self.req('memories/upload',{'albumId':album['album']['id'],'requestId':'quota-photo-test','data':encoded},cookie,{'X-Memories-CSRF':visitor['csrf']})[0]
  with patch('memories.quota',return_value=allowance),concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(upload,[a,b]))
  self.assertEqual(sorted(results),[201,413])
 def test_private_schema_and_rls(self):
  import psycopg
  with psycopg.connect(self.url_db,autocommit=True) as c:
   if not c.execute("SELECT 1 FROM pg_roles WHERE rolname='anon'").fetchone():c.execute('CREATE ROLE anon')
  self.start()
  with server.conn() as c:
   schemas=c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='shaadi_sync'").fetchall();self.assertEqual({r['table_name'] for r in schemas},set(storage.APP_TABLES))
   self.assertFalse(c.execute("SELECT has_schema_privilege('anon','shaadi_sync','USAGE') AS granted").fetchone()['granted'])
   self.assertEqual(c.execute("SELECT count(*) AS n FROM pg_class WHERE relnamespace='shaadi_sync'::regnamespace AND relkind='r' AND relrowsecurity").fetchone()['n'],len(storage.APP_TABLES))
 def test_postgres_demo_survey_and_restart(self):
  self.start();cookie=self.demo();data=self.req('state',cookie=cookie)[1];self.assertEqual(len(data['guests']),12)
  survey={'rating':5,'usefulness':4,'willingness':'Maybe','persona':'Investor','comments':'PostgreSQL validation','consent':True}
  self.assertEqual(self.req('feedback',survey,cookie)[0],200);server.initialize()
  self.assertEqual(self.req('state',cookie=cookie)[1]['event'][0]['id'],data['event'][0]['id'])
  with server.conn() as c:self.assertEqual(c.execute('SELECT count(*) AS n FROM feedback').fetchone()['n'],1)
 def test_postgres_concurrent_gate(self):
  self.start();cookie=self.demo();g=next(g for g in self.req('state',cookie=cookie)[1]['guests'] if g['status']=='Confirmed');token=self.req('pass?guestId='+str(g['id']),cookie=cookie)[1]['token']
  def scan(i):return self.req('checkin',{'token':token,'requestId':'pg-scan-'+str(i)},cookie)[0]
  with concurrent.futures.ThreadPoolExecutor(2) as p:results=list(p.map(scan,[1,2]))
  self.assertEqual(sorted(results),[200,409])
 def test_legacy_public_tables_move_without_touching_other_tables(self):
  import psycopg
  with psycopg.connect(self.url_db,autocommit=True) as c:
   c.execute('CREATE TABLE public.records(id BIGSERIAL PRIMARY KEY,kind TEXT,data TEXT,event_id INTEGER DEFAULT 1)')
   c.execute('CREATE TABLE public.settings(name TEXT PRIMARY KEY,value TEXT)')
   c.execute('CREATE TABLE public.sessions(token_hash TEXT PRIMARY KEY,phone TEXT,name TEXT,event_id INTEGER,csrf TEXT,expires DOUBLE PRECISION,demo_role TEXT)')
   c.execute("INSERT INTO public.settings VALUES('signing_key','fixture-preserved-secret')")
   c.execute('INSERT INTO public.records(kind,data) VALUES(%s,%s)',('event',json.dumps({'name':'Preserved wedding','code':'EXISTING-EVENT'})))
   c.execute('CREATE TABLE public.unrelated_project_data(id INTEGER)');c.execute('INSERT INTO public.unrelated_project_data VALUES(7)')
  self.start()
  with server.conn() as c:
   self.assertEqual(server.rows('event',1,c)[0]['name'],'Preserved wedding')
   self.assertIsNone(c.execute("SELECT to_regclass('public.records') AS t").fetchone()['t'])
   self.assertEqual(c.execute('SELECT id FROM public.unrelated_project_data').fetchone()['id'],7)
