"""Supabase Google OAuth with server-held PKCE and a browser-bound login attempt."""
import base64,hashlib,json,os,re,secrets,time,urllib.request,urllib.error,uuid
from http.cookies import SimpleCookie
from urllib.parse import urlparse,urlencode
class AuthError(Exception):
 def __init__(self,status,message):self.status=status;super().__init__(message)
def email(value):
 if not isinstance(value,str) or len(value)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ValueError('Enter a valid email address.')
 return value.strip().lower()
def configuration():
 url=os.environ.get('SUPABASE_URL','').rstrip('/');key=os.environ.get('SUPABASE_PUBLISHABLE_KEY') or os.environ.get('SUPABASE_ANON_KEY','');base=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
 project=urlparse(url);app=urlparse(base)
 if project.scheme!='https' or not re.fullmatch(r'[a-z0-9]+\.supabase\.co',project.netloc) or project.path or not key:raise AuthError(503,'Google sign-in is not configured yet.')
 if (app.scheme!='https' and not (app.scheme=='http' and app.hostname in ['localhost','127.0.0.1'])) or not app.netloc or app.username or app.password or app.path or app.query or app.fragment:raise AuthError(503,'The app sign-in address is not configured yet.')
 return url,key,base

def ready():
 try:configuration();return True
 except AuthError:return False

def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def cookie(value,secure=False,clear=False):return 'google_login='+value+'; HttpOnly; SameSite=Lax; Path=/; Max-Age='+('0' if clear else '600')+('; Secure' if secure else '')
def start(db):
 url,key,base=configuration();attempt=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48);challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
 with db(True) as c:
  c.execute('DELETE FROM oauth_attempts WHERE expires<?',(time.time(),));c.execute('INSERT INTO oauth_attempts VALUES(?,?,?)',(digest(attempt),verifier,time.time()+600))
 destination=url+'/auth/v1/authorize?'+urlencode({'provider':'google','prompt':'select_account','redirect_to':base+'/auth/callback','code_challenge':challenge,'code_challenge_method':'s256'})
 return destination,cookie(attempt,base.startswith('https://'))
def request(url,key,body=None,token=None):
 headers={'apikey':key,'Accept':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 payload=None
 if body is not None:headers['Content-Type']='application/json';payload=json.dumps(body).encode()
 try:
  with urllib.request.urlopen(urllib.request.Request(url,data=payload,headers=headers),timeout=10) as response:return json.load(response)
 except (urllib.error.URLError,ValueError):raise AuthError(503,'Google sign-in could not be verified. Please try again.') from None

def finish(db,headers,query):
 url,key,base=configuration()
 try:attempt=SimpleCookie(headers.get('Cookie',''))['google_login'].value
 except (KeyError,AttributeError):raise AuthError(400,'Your sign-in attempt expired. Please try again.')
 if not re.fullmatch(r'[A-Za-z0-9_-]{43}',attempt):raise AuthError(400,'Invalid sign-in attempt.')
 with db(True) as c:
  if os.environ.get('DATABASE_URL'):c.execute('SELECT id FROM oauth_attempts WHERE id=? FOR UPDATE',(digest(attempt),))
  row=c.execute('SELECT * FROM oauth_attempts WHERE id=?',(digest(attempt),)).fetchone();c.execute('DELETE FROM oauth_attempts WHERE id=?',(digest(attempt),))
 if not row or row['expires']<time.time():raise AuthError(400,'Your sign-in attempt expired. Please try again.')
 if query.get('error'):raise AuthError(400,'Google sign-in was cancelled or declined. Please try again.')
 code=query.get('code',[''])[0]
 if not isinstance(code,str) or not 1<=len(code)<=2048:raise AuthError(400,'The sign-in code is missing. Please try again.')
 result=request(url+'/auth/v1/token?grant_type=pkce',key,{'auth_code':code,'code_verifier':row['verifier']});token=result.get('access_token') if isinstance(result,dict) else None
 if not isinstance(token,str) or not token:raise AuthError(400,'The sign-in response could not be verified.')
 user=request(url+'/auth/v1/user',key,token=token)
 try:
  if not isinstance(user,dict):raise ValueError()
  subject=str(uuid.UUID(user['id']));address=email(user['email'])
  identities=user.get('identities',[])
  if not user.get('email_confirmed_at') or not (isinstance(identities,list) and any(isinstance(i,dict) and i.get('provider')=='google' and isinstance(i.get('identity_data'),dict) and i['identity_data'].get('email_verified') is True for i in identities)):raise ValueError()
 except (KeyError,ValueError,TypeError):raise AuthError(403,'A verified Google account is required.') from None
 name=user.get('user_metadata',{}).get('full_name') or user.get('user_metadata',{}).get('name') or address.split('@')[0]
 if not isinstance(name,str):name=address.split('@')[0]
 return {'subject':url+'|'+subject,'email':address,'name':name[:80]}

def resolve(c,identity):
 row=c.execute('SELECT account_id,email FROM auth_accounts WHERE subject=?',(identity['subject'],)).fetchone()
 if row:
  if row['email']!=identity['email']:raise AuthError(409,'Your Google email changed. Contact the organiser to update account access.')
  return row['account_id']
 if c.execute('SELECT account_id FROM auth_accounts WHERE email=?',(identity['email'],)).fetchone():raise AuthError(409,'This email is already linked to a different sign-in identity.')
 account='google:'+digest(identity['subject']);c.execute('INSERT INTO auth_accounts VALUES(?,?,?,?) ON CONFLICT DO NOTHING',(account,identity['subject'],identity['email'],time.time()))
 row=c.execute('SELECT account_id,email FROM auth_accounts WHERE subject=?',(identity['subject'],)).fetchone()
 if not row or row['email']!=identity['email']:raise AuthError(409,'This email is linked to another identity.')
 return row['account_id']

def access_key(c,address):
 row=c.execute('SELECT account_id FROM auth_accounts WHERE email=?',(address,)).fetchone();return row['account_id'] if row else 'email:'+address

def grant(c,account,address):
 # Pending team grants are made by the wedding owner, never by a login parameter.
 if os.environ.get('DATABASE_URL'):
  events={r['event_id'] for r in c.execute('SELECT event_id FROM memberships WHERE phone=?',('email:'+address,))}
  events.update(r['event_id'] for r in c.execute("SELECT event_id,data FROM records WHERE kind='guests'") if json.loads(r['data']).get('email','').lower()==address)
  for eid in sorted(events):c.execute("SELECT id FROM records WHERE kind='event' AND event_id=? FOR UPDATE",(eid,))
 pending=c.execute('SELECT * FROM memberships WHERE phone=?',('email:'+address,)).fetchall()
 for m in pending:
  c.execute('INSERT INTO memberships(event_id,phone,role,entity_id,permissions,revoked) VALUES(?,?,?,?,?,?) ON CONFLICT(event_id,phone) DO UPDATE SET revoked=1 WHERE excluded.revoked=1',(m['event_id'],account,m['role'],m['entity_id'],m['permissions'],m['revoked']))
  c.execute('DELETE FROM memberships WHERE event_id=? AND phone=?',(m['event_id'],'email:'+address))
 for row in c.execute("SELECT id,event_id,data FROM records WHERE kind='guests'").fetchall():
  guest=json.loads(row['data'])
  if guest.get('email','').lower()!=address:continue
  c.execute("INSERT INTO memberships(event_id,phone,role,entity_id,permissions) VALUES(?,?,?,?,?) ON CONFLICT(event_id,phone) DO NOTHING",(row['event_id'],account,'Guest',row['id'],'[]'))
