# Only this disposable test process mocks Supabase; the deployed app uses real HTTPS verification.
import argparse,os,sys,tempfile
from pathlib import Path
parser=argparse.ArgumentParser(description='Disposable local Google sign-in browser fixture. Never deploy this script.')
parser.add_argument('--allow-mocked-auth',action='store_true',required=True)
parser.parse_args()
workspace=tempfile.TemporaryDirectory(prefix='shaadi-google-browser-')
os.environ.update(APP_MODE='user',AUTH_PROVIDER='google',SUPABASE_URL='https://example.supabase.co',SUPABASE_PUBLISHABLE_KEY='fixture-public-key',PUBLIC_BASE_URL='http://127.0.0.1:3016',COOKIE_SECURE='0',DATABASE_URL='',DATABASE_PATH=workspace.name+'/app.sqlite3')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server,google_auth
identities={'owner':('owner@example.com','11111111-1111-4111-8111-111111111111'),'guest':('guest@example.com','22222222-2222-4222-8222-222222222222'),'planner':('planner@example.com','33333333-3333-4333-8333-333333333333')}
def provider(url,key,body=None,token=None):
 if not url.startswith('https://example.supabase.co/auth/v1/'):raise AssertionError('Unexpected network destination')
 if body:
  assert len(body['code_verifier'])>=43
  return {'access_token':body['auth_code']}
 address,subject=identities[token]
 return {'id':subject,'email':address,'email_confirmed_at':'2026-01-01','identities':[{'provider':'google','identity_data':{'email_verified':True}}],'user_metadata':{'full_name':token.title()+' User'}}
google_auth.request=provider
server.initialize();server.ThreadingHTTPServer(('127.0.0.1',3016),server.Handler).serve_forever()
