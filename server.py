"""Shaadi Sync: event-scoped application API with durable authentication."""
import base64, hashlib, hmac, io, ipaddress, json, math, os, re, secrets, time
from datetime import date
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
import storage, providers
from seed import demo_records

DB=os.environ.get('DATABASE_PATH','shaadi.sqlite3')
SESSION_TTL=86400
ROLES=['Super Organiser','Co-Organiser','Finance Team','Vendor','Guest','Hotel Partner']
ALLOWED=['guests','timeline','vendors','tasks','hotels','transport','catering','announcements','songs','photos','gifts','polls']
CATALOG={'Event Pass':299900}  # INR paise, controlled by the server

def demo_mode():return os.environ.get('DEMO_MODE','0')=='1'
def conn(write=False):return storage.connect(DB,write)
def rows(kind,event_id=1,c=None):
    if c is None:
        with conn() as db:return rows(kind,event_id,db)
    return [dict(json.loads(r['data']),id=r['id']) for r in c.execute('SELECT id,data FROM records WHERE kind=? AND event_id=? ORDER BY id',(kind,event_id))]
def insert(c,kind,data,event_id):
    return c.execute('INSERT INTO records(kind,data,event_id) VALUES(?,?,?) RETURNING id',(kind,json.dumps(data,allow_nan=False),event_id)).fetchone()['id']
def update(c,kind,data,event_id):
    c.execute('UPDATE records SET data=? WHERE id=? AND kind=? AND event_id=?',(json.dumps(data,allow_nan=False),data['id'],kind,event_id))
def audit(c,s,action):c.execute('INSERT INTO audit(actor,action,created,event_id) VALUES(?,?,?,?)',(s['name'],action,time.time(),s['event_id']))
def secret(c):
    r=c.execute("SELECT value FROM settings WHERE name='signing_key'").fetchone()
    return r['value'].encode()
def initialize():
    storage.migrate(DB)
    with conn(True) as c:
        c.execute('INSERT INTO settings(name,value) VALUES(?,?) ON CONFLICT(name) DO NOTHING',('signing_key',secrets.token_hex(32)))
        for event in c.execute("SELECT id,data,event_id FROM records WHERE kind='event'").fetchall():
            code=json.loads(event['data']).get('code')
            if code:c.execute('INSERT INTO event_codes VALUES(?,?) ON CONFLICT(code) DO NOTHING',(code,event['event_id']))
        if demo_mode() and not c.execute('SELECT id FROM records LIMIT 1').fetchone():
            for kind,items in demo_records().items():
                for item in items:
                    record_id=insert(c,kind,item,1)
                    if kind=='event':c.execute('INSERT INTO event_codes VALUES(?,?)',(item['code'],1))
def hash_token(t):return hashlib.sha256(t.encode()).hexdigest()
def phone_number(raw):
    p=re.sub(r'[\s()-]','',str(raw))
    if p.startswith('+91'):p=p[3:]
    if not re.fullmatch(r'[6-9][0-9]{9}',p):raise ValueError('Enter a valid Indian mobile number (+91 or 10 digits).')
    return p
def text(value,limit=150):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Enter a valid value (maximum '+str(limit)+' characters).')
    return value.strip()
def amount(value):
    if isinstance(value,bool):raise ValueError('Invalid amount')
    n=float(value)
    if not math.isfinite(n) or n<0 or n>1e10:raise ValueError('Invalid amount')
    return n
def limit(c,bucket,maximum,window):
    now=time.time();r=c.execute('SELECT * FROM limits WHERE bucket=?',(bucket,)).fetchone()
    if r and r['reset']>now and r['count']>=maximum:raise HTTPError(429,'Too many attempts. Please try again later.')
    count=r['count']+1 if r and r['reset']>now else 1
    reset=r['reset'] if r and r['reset']>now else now+window
    c.execute('INSERT INTO limits(bucket,count,reset) VALUES(?,?,?) ON CONFLICT(bucket) DO UPDATE SET count=excluded.count,reset=excluded.reset',(bucket,count,reset))
def session_for(handler):
    try:token=SimpleCookie(handler.headers.get('Cookie',''))['session'].value
    except (KeyError,AttributeError):return None
    with conn() as c:
        r=c.execute('SELECT * FROM sessions WHERE token_hash=? AND expires>?',(hash_token(token),time.time())).fetchone()
        if not r or (not demo_mode() and r['auth_mode']!='verified'):return None
        s=dict(r);s['role']='Account';s['permissions']=[]
        if s['demo_role'] and demo_mode():s['role']=s['demo_role'];s['entity_id']=None
        elif s['event_id']:
            m=c.execute('SELECT * FROM memberships WHERE event_id=? AND phone=? AND revoked=0',(s['event_id'],s['phone'])).fetchone()
            if m:s.update(role=m['role'],entity_id=m['entity_id'],permissions=json.loads(m['permissions']))
            else:s['event_id']=None
        return s
class HTTPError(Exception):
    def __init__(self,status,message):self.status=status;super().__init__(message)

def pass_token(c,event_id,g):
    nonce=g.get('passNonce')
    if not nonce:
        nonce=secrets.token_urlsafe(18);g['passNonce']=nonce;update(c,'guests',g,event_id)
    payload=f'SS1.{event_id}.{g["id"]}.{nonce}'
    sig=hmac.new(secret(c),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+sig

def identify_pass(c,event_id,token):
    token=str(token)
    if token.startswith(('https://','http://')):token=parse_qs(urlparse(token).query).get('pass',[''])[0]
    parts=token.split('.')
    if len(parts)!=5 or parts[0]!='SS1' or parts[1]!=str(event_id):raise HTTPError(400,'Pass does not belong to this event.')
    payload='.'.join(parts[:-1]);expected=hmac.new(secret(c),payload.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,parts[-1]):raise HTTPError(400,'Pass signature is invalid.')
    g=next((g for g in rows('guests',event_id,c) if str(g['id'])==parts[2]),None)
    if not g or g.get('passNonce')!=parts[3]:raise HTTPError(400,'This pass has been revoked or replaced.')
    return g

class Handler(SimpleHTTPRequestHandler):
    def client_identity(self):
        value=self.client_address[0]
        if os.environ.get('TRUST_PROXY','0')=='1':
            candidate=self.headers.get('X-Forwarded-For','').split(',')[-1].strip()
            try:value=str(ipaddress.ip_address(candidate))
            except ValueError:pass
        return hash_token(value)
    def setup(self):
        super().setup();self.connection.settimeout(25)
    def log_message(self,*a):pass
    def response(self,code,data,cookie=None):
        b=json.dumps(data,allow_nan=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(b)
    def require_access(self):
        password=os.environ.get('DEMO_ACCESS_PASSWORD','')
        if not password or urlparse(self.path).path in ['/api/health','/api/webhooks/razorpay','/api/webhooks/whatsapp']:return True
        try:
            scheme,encoded=self.headers.get('Authorization','').split(' ',1)
            user,pw=base64.b64decode(encoded,validate=True).decode().split(':',1)
            if scheme.lower()=='basic' and user=='demo' and hmac.compare_digest(pw.encode(),password.encode()):return True
        except (ValueError,UnicodeError):pass
        self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="Shaadi Sync private demo", charset="UTF-8"');self.end_headers();return False
    def do_GET(self):self.handle_api(False)
    def do_POST(self):self.handle_api(True)
    def handle_api(self,post):
        if not self.require_access():return
        try:
            parsed=urlparse(self.path);path=parsed.path;query=parse_qs(parsed.query);self.s=session_for(self)
            if post:
                length=int(self.headers.get('Content-Length','0'))
                if length<0 or length>1000000:raise HTTPError(413,'Request too large')
                raw=self.rfile.read(length)
                if path.startswith('/api/webhooks/'):
                    return self.response(200,self.webhook(path,raw))
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise HTTPError(415,'JSON content type required')
                origin=self.headers.get('Origin')
                allowed=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
                if origin and origin not in {allowed,'https://'+self.headers.get('Host',''),'http://'+self.headers.get('Host','')}:raise HTTPError(403,'Request origin is not allowed')
                body=json.loads(raw or b'{}')
                if not isinstance(body,dict):raise ValueError('JSON object required')
                if self.s and path not in ['/api/auth/otp','/api/auth/verify','/api/auth/demo']:
                    if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),self.s['csrf']):raise HTTPError(403,'Refresh the page before making this request.')
                return self.post(path,body)
            if path=='/api/health':return self.response(200,{'ok':True})
            if path=='/api/bootstrap':return self.response(200,{'demoMode':demo_mode(),'smsReady':providers.sms_ready(),'whatsappReady':providers.whatsapp_ready(),'paymentsReady':providers.payments_ready()})
            if path=='/api/webhooks/whatsapp':
                token=os.environ.get('WHATSAPP_VERIFY_TOKEN','')
                if not token or query.get('hub.mode')!=['subscribe'] or not hmac.compare_digest(query.get('hub.verify_token',[''])[0],token):raise HTTPError(403,'Invalid verification token')
                payload=query.get('hub.challenge',[''])[0].encode();self.send_response(200);self.end_headers();return self.wfile.write(payload)
            if path=='/api/invitation':
                code=query.get('code',[''])[0]
                with conn() as c:
                    found=next((dict(json.loads(r['data']),id=r['id']) for r in c.execute("SELECT * FROM records WHERE kind='event'") if json.loads(r['data']).get('code')==code),None)
                if not found:raise HTTPError(404,'Invitation not found')
                return self.response(200,{k:found[k] for k in ['id','name','date','venue','code']})
            if path=='/api/state':return self.response(200,self.state())
            if path=='/api/events':return self.response(200,{'events':self.events()})
            if path=='/api/audit':
                self.require_role('Super Organiser','Finance Team')
                with conn() as c:data=[dict(r) for r in c.execute('SELECT actor,action,created FROM audit WHERE event_id=? ORDER BY id DESC LIMIT 100',(self.s['event_id'],))]
                return self.response(200,{'audit':data})
            if path=='/api/pass':return self.response(200,self.entry_pass(query))
            if path=='/api/invoice':return self.response(200,self.invoice(query))
            if path.startswith('/api/'):raise HTTPError(404,'Not found')
            target=(Path(__file__).parent/'static'/('index.html' if path=='/' else unquote(path).lstrip('/'))).resolve()
            if not target.is_relative_to((Path(__file__).parent/'static').resolve()) or not target.is_file():raise HTTPError(404,'Not found')
            content=target.read_bytes();self.send_response(200);self.send_header('Content-Type',self.guess_type(str(target)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.end_headers();self.wfile.write(content)
        except HTTPError as e:self.response(e.status,{'error':str(e)})
        except providers.ProviderError as e:self.response(503,{'error':str(e)})
        except (ValueError,TypeError,KeyError,OverflowError):self.response(400,{'error':'Invalid request. Please check the submitted fields.'})
        except Exception:
            # No provider bodies, keys, cookies, OTPs, IDs or PII in logs.
            self.response(500,{'error':'The request could not be completed. Please retry.'})
    def require_role(self,*roles):
        if not self.s:raise HTTPError(401,'Please sign in')
        if not self.s['event_id'] or self.s['role'] not in roles:raise HTTPError(403,'You do not have access to this event or action.')
    def can_manage(self,kind):
        self.require_role('Super Organiser','Co-Organiser')
        if self.s['role']=='Co-Organiser' and kind not in self.s['permissions'] and not self.s['demo_role']:raise HTTPError(403,'Your organiser has not granted this permission.')
    def events(self):
        if not self.s:raise HTTPError(401,'Please sign in')
        with conn() as c:
            if self.s['demo_role']:items=[dict(json.loads(r['data']),id=r['id']) for r in c.execute("SELECT * FROM records WHERE kind='event' AND event_id=1")]
            else:items=[dict(json.loads(r['data']),id=r['id']) for r in c.execute("SELECT r.* FROM records r JOIN memberships m ON m.event_id=r.event_id WHERE r.kind='event' AND m.phone=? AND m.revoked=0",(self.s['phone'],))]
            return [{k:e.get(k) for k in ['id','name','date','venue','plan']} for e in items]
    def state(self):
        if not self.s:raise HTTPError(401,'Please sign in')
        s=self.s;eid=s['event_id'];role=s['role']
        user={k:s.get(k) for k in ['name','phone','role','event_id','permissions']};user['demo']=bool(s['demo_role'])
        data={'user':user,'events':self.events(),'csrf':s['csrf'],'mode':'sandbox' if demo_mode() else 'live','services':{'sms':providers.sms_ready(),'whatsapp':providers.whatsapp_ready(),'payments':providers.payments_ready()},'event':[],'scope':hash_token(str(eid)+':'+s['phone'])}
        if not eid:return data
        kinds=['event','timeline','announcements','polls']
        if role=='Super Organiser':kinds+=ALLOWED+['joins','entries','members','expenses']
        elif role=='Co-Organiser':kinds+=[k for k in ALLOWED+['joins','entries'] if s['demo_role'] or k in s['permissions']]
        elif role=='Finance Team':kinds+=['expenses']
        elif role=='Guest':kinds+=['transport']
        data.update({k:rows(k,eid) for k in set(kinds)})
        if not data['event']:raise HTTPError(404,'Event no longer exists')
        for p in data['polls']:p['hasVoted']=s['phone'] in p.get('voters',[]);p.pop('voters',None)
        if role=='Guest':
            gs=[g for g in rows('guests',eid) if g['phone']==s['phone']]
            data['guests']=gs
            invited=set(gs[0].get('events',[])) if gs else set()
            data['timeline']=[t for t in data['timeline'] if t['name'] in invited]
        if role=='Vendor':data['vendors']=[v for v in rows('vendors',eid) if v['id']==s.get('entity_id') or (s['demo_role'] and v==rows('vendors',eid)[0])]
        if role=='Hotel Partner':data['hotels']=[h for h in rows('hotels',eid) if h['id']==s.get('entity_id') or (s['demo_role'] and h==rows('hotels',eid)[0])]
        if role not in ['Super Organiser','Finance Team']:
            for e in data['event']:e.pop('budget',None);e.pop('approvalThreshold',None)
        for g in data.get('guests',[]):g.pop('passNonce',None)
        if role=='Super Organiser':
            with conn() as c:
                data['team']=[dict(r) for r in c.execute('SELECT phone,role,permissions,revoked FROM memberships WHERE event_id=?',(eid,))]
                data['messages']=[dict(r) for r in c.execute('SELECT id,guest_id,status,error,created FROM outbox WHERE event_id=? ORDER BY id DESC LIMIT 50',(eid,))]
        return data
    def login_session(self,phone,name,demo_role=None):
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
        with conn(True) as c:
            eid=1 if demo_role else None
            if not demo_role:
                c.execute('INSERT INTO users(phone,name,created) VALUES(?,?,?) ON CONFLICT(phone) DO NOTHING',(phone,name,time.time()))
                # Pre-registered guests gain access only after verified phone ownership.
                for r in c.execute("SELECT * FROM records WHERE kind='guests'").fetchall():
                    g=json.loads(r['data'])
                    if g.get('phone')==phone:
                        c.execute("INSERT INTO memberships(event_id,phone,role,entity_id,permissions) VALUES(?,?,?,?,?) ON CONFLICT(event_id,phone) DO NOTHING",(r['event_id'],phone,'Guest',r['id'],'[]'))
                m=c.execute('SELECT event_id FROM memberships WHERE phone=? AND revoked=0 ORDER BY event_id LIMIT 1',(phone,)).fetchone()
                if m:eid=m['event_id']
                c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?)',(hash_token(token),phone,name,eid,csrf,time.time()+SESSION_TTL,demo_role,'sandbox' if demo_mode() else 'verified'))
        secure='; Secure' if os.environ.get('COOKIE_SECURE','0')=='1' else ''
        return self.response(200,{'ok':True,'csrf':csrf},f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}'+secure)
    def post(self,path,b):
        if path=='/api/auth/demo':
            if not demo_mode():raise HTTPError(403,'Demo access is disabled.')
            role=b.get('role','Super Organiser')
            if role not in ROLES:raise ValueError('role')
            return self.login_session('9000000000','Ananya Sharma' if role=='Guest' else 'Priya Sharma',role)
        if path=='/api/auth/otp':
            phone=phone_number(b.get('phone'));now=time.time()
            if not demo_mode() and not providers.sms_ready():raise providers.ProviderError('SMS verification is not configured. Connect Twilio Verify to sign in.')
            with conn(True) as c:
                limit(c,'otp-phone:'+phone,5,3600)
                limit(c,'otp-ip:'+self.client_identity(),20,3600)
                old=c.execute('SELECT * FROM challenges WHERE phone=?',(phone,)).fetchone()
                if old and now-old['created']<30:raise HTTPError(429,'Wait 30 seconds before requesting another code.')
                code=f'{secrets.randbelow(1000000):06d}'
                mode='sandbox' if demo_mode() else 'twilio'
                digest=hmac.new(secret(c),code.encode(),hashlib.sha256).hexdigest() if mode=='sandbox' else ''
                c.execute('INSERT INTO challenges VALUES(?,?,?,?,?) ON CONFLICT(phone) DO UPDATE SET code_hash=excluded.code_hash,created=excluded.created,attempts=0,mode=excluded.mode',(phone,digest,now,0,mode))
            if mode=='twilio':providers.sms_send(phone)
            return self.response(200,{'sandboxCode':code,'message':'Sandbox only. No SMS sent.'} if mode=='sandbox' else {'message':'Verification code sent to your phone.'})
        if path=='/api/auth/verify':
            phone=phone_number(b.get('phone'));code=str(b.get('code',''))
            with conn(True) as c:
                o=c.execute('SELECT * FROM challenges WHERE phone=?',(phone,)).fetchone()
                if not o or time.time()-o['created']>300 or o['attempts']>=5:raise HTTPError(400,'Request a new verification code.')
                c.execute('UPDATE challenges SET attempts=attempts+1 WHERE phone=?',(phone,))
                valid=bool(re.fullmatch(r'[0-9]{6}',code))
                if o['mode']=='sandbox':valid=valid and demo_mode() and hmac.compare_digest(hmac.new(secret(c),code.encode(),hashlib.sha256).hexdigest(),o['code_hash'])
                else:valid=valid and providers.sms_check(phone,code)
                # Commit failed-attempt counters before reporting failure.
                if valid:c.execute('DELETE FROM challenges WHERE phone=?',(phone,))
            if not valid:raise HTTPError(400,'Incorrect verification code.')
            with conn() as c:u=c.execute('SELECT name FROM users WHERE phone=?',(phone,)).fetchone()
            return self.login_session(phone,u['name'] if u else text(b.get('name') or 'Wedding guest',80))
        if path=='/api/join':return self.join(b)
        if not self.s:raise HTTPError(401,'Please sign in')
        s=self.s;eid=s['event_id']
        if path=='/api/auth/logout':
            with conn(True) as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(s['token_hash'],))
            return self.response(200,{'ok':True},'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if path=='/api/events/create':return self.create_event(b)
        if path=='/api/events/select':
            event_id=int(b.get('eventId',0))
            if event_id not in [e['id'] for e in self.events()]:raise HTTPError(403,'You are not a member of this event.')
            with conn(True) as c:c.execute('UPDATE sessions SET event_id=? WHERE token_hash=?',(event_id,s['token_hash']))
            return self.response(200,{'ok':True})
        if path=='/api/members/revoke':return self.revoke(b)
        if path=='/api/joins/approve':return self.approve_join(b)
        if path=='/api/checkin':return self.checkin(b)
        if path=='/api/whatsapp':return self.queue_messages(b)
        if path=='/api/messages/dispatch':return self.dispatch_messages()
        if path=='/api/payments/order':return self.order(b)
        if path=='/api/payments/verify':return self.verify_payment(b)
        if path=='/api/rsvp' or path=='/api/guest-update':
            self.require_role('Guest')
            with conn(True) as c:
                g=next((g for g in rows('guests',eid,c) if g['phone']==s['phone']),None)
                if not g:raise HTTPError(404,'Guest not found')
                if not b.get('consent'):raise HTTPError(400,'Explicit consent is required.')
                if path=='/api/rsvp':
                    status=b.get('status');plus=int(b.get('plusOnes',0))
                    if status not in ['Confirmed','Declined','Maybe'] or not 0<=plus<=g.get('plusOnes',0):raise ValueError('Invalid RSVP')
                    g.update(status=status,attendingPlusOnes=plus,consent=True,whatsappConsent=bool(b.get('whatsappConsent')))
                    if status=='Confirmed':pass_token(c,eid,g)
                    else:g['passNonce']=secrets.token_urlsafe(18)
                else:
                    if b.get('travel') not in ['Not updated','Left home','Landed','On the way to hotel','Reached hotel']:raise ValueError('Travel milestone')
                    g.update(travel=b['travel'],consent=True)
                update(c,'guests',g,eid);audit(c,s,'Guest updated RSVP' if path=='/api/rsvp' else 'Guest shared a travel milestone')
            return self.response(200,{'ok':True})
        if path=='/api/song':
            self.require_role('Guest')
            with conn(True) as c:insert(c,'songs',{'name':text(b.get('name')),'owner':s['name'],'status':'Pending'},eid)
            return self.response(201,{'ok':True})
        if path=='/api/vote':
            self.require_role(*ROLES)
            with conn(True) as c:
                if os.environ.get('DATABASE_URL'):c.execute('SELECT id FROM records WHERE id=? FOR UPDATE',(b.get('id'),))
                poll=next((p for p in rows('polls',eid,c) if p['id']==b.get('id')),None)
                if not poll or b.get('option') not in poll['options']:raise ValueError('Poll option')
                if s['phone'] in poll.get('voters',[]):raise HTTPError(409,'You have already voted in this poll.')
                poll['options'][b['option']]+=1;poll.setdefault('voters',[]).append(s['phone']);update(c,'polls',poll,eid)
            return self.response(200,{'ok':True})
        if path=='/api/save':return self.save_record(b)
        raise HTTPError(404,'Not found')
    def create_event(self,b):
        if self.s['demo_role']:raise HTTPError(403,'Sign in with your phone account to create a personal event.')
        name=text(b.get('name'),80);day=text(b.get('date'));date.fromisoformat(day)
        code=re.sub('[^A-Z0-9]+','-',name.upper()).strip('-')[:35]+'-'+day[:4]+'-'+secrets.token_hex(4).upper()
        e={'name':name,'date':day,'venue':text(b.get('venue'),150),'code':code,'budget':amount(b.get('budget',0)),'approvalThreshold':100000,'theme':b.get('theme','Royal Rajasthani'),'hashtag':'#'+re.sub('[^a-zA-Z0-9]','',name),'plan':'Free'}
        with conn(True) as c:
            limit(c,'create-event:'+self.s['phone'],10,86400)
            eid=insert(c,'event',e,0);c.execute('INSERT INTO event_codes VALUES(?,?)',(code,eid));c.execute('UPDATE records SET event_id=? WHERE id=?',(eid,eid))
            c.execute('INSERT INTO memberships(event_id,phone,role,permissions) VALUES(?,?,?,?)',(eid,self.s['phone'],'Super Organiser','[]'))
            c.execute('UPDATE sessions SET event_id=? WHERE token_hash=?',(eid,self.s['token_hash']))
            insert(c,'timeline',{'name':'Wedding','date':day,'time':'18:30','venue':e['venue'],'dress':'Celebrate in your own style'},eid)
            audit(c,{**self.s,'event_id':eid},'Created event')
        return self.response(201,{'ok':True,'eventId':eid,'code':code})
    def join(self,b):
        phone=phone_number(b.get('phone'));name=text(b.get('name'),80);code=text(b.get('code'))
        with conn(True) as c:
            limit(c,'join-ip:'+self.client_identity(),20,3600)
            event=next((r for r in c.execute("SELECT * FROM records WHERE kind='event'") if json.loads(r['data']).get('code')==code),None)
            if not event:raise HTTPError(404,'Event code not found')
            eid=event['event_id'];existing=next((j for j in rows('joins',eid,c) if j.get('phone')==phone and j.get('status')=='Pending'),None)
            if not existing:insert(c,'joins',{'name':name,'phone':phone,'status':'Pending'},eid)
        return self.response(201,{'ok':True,'message':'Request sent. Your organiser must approve it; phone verification is still required to sign in.'})
    def approve_join(self,b):
        self.can_manage('joins');eid=self.s['event_id']
        with conn(True) as c:
            if os.environ.get('DATABASE_URL'):c.execute("SELECT id FROM records WHERE kind='event' AND event_id=? FOR UPDATE",(eid,))
            j=next((j for j in rows('joins',eid,c) if j['id']==b.get('id') and j['status']=='Pending'),None)
            if not j:raise HTTPError(404,'Pending request not found')
            g=next((g for g in rows('guests',eid,c) if g['phone']==j['phone']),None)
            if not g:
                self.guest_capacity(c)
                gid=insert(c,'guests',{'name':j['name'],'phone':j['phone'],'family':'Approved guests','side':'Both','status':'Invited','diet':'Veg','plusOnes':0,'events':['Wedding'],'travel':'Not updated','whatsappConsent':False},eid)
            else:gid=g['id']
            j['status']='Approved';update(c,'joins',j,eid)
            c.execute("INSERT INTO memberships(event_id,phone,role,entity_id,permissions) VALUES(?,?,?,?,?) ON CONFLICT(event_id,phone) DO UPDATE SET revoked=0,role=excluded.role,entity_id=excluded.entity_id",(eid,j['phone'],'Guest',gid,'[]'))
            audit(c,self.s,'Approved guest join request')
        return self.response(200,{'ok':True})
    def guest_capacity(self,c):
        e=rows('event',self.s['event_id'],c)[0]
        if e['plan']=='Free' and len(rows('guests',self.s['event_id'],c))>=50:raise HTTPError(402,'Free events support 50 guests. Upgrade to Event Pass to add more.')
    def revoke(self,b):
        self.require_role('Super Organiser');phone=phone_number(b.get('phone'));eid=self.s['event_id']
        if phone==self.s['phone']:raise HTTPError(400,'You cannot revoke your own organiser access.')
        with conn(True) as c:
            c.execute("INSERT INTO memberships(event_id,phone,role,permissions,revoked) VALUES(?,?,?,?,1) ON CONFLICT(event_id,phone) DO UPDATE SET revoked=1",(eid,phone,'Guest','[]'))
            for g in rows('guests',eid,c):
                if g['phone']==phone:g['passNonce']=secrets.token_urlsafe(18);g['status']='Invited';update(c,'guests',g,eid)
            audit(c,self.s,'Revoked event member access')
        return self.response(200,{'ok':True})
    def save_record(self,b):
        kind=b.get('kind');item=b.get('item');s=self.s;eid=s['event_id']
        if not isinstance(item,dict):raise ValueError('item')
        if kind=='expenses':self.require_role('Super Organiser','Finance Team')
        elif kind in ['event','members']:self.require_role('Super Organiser')
        elif kind in ALLOWED:self.can_manage(kind)
        else:raise HTTPError(403,'This record type cannot be edited here.')
        if kind in ['expenses','vendors'] and rows('event',eid)[0]['plan']=='Free':raise HTTPError(402,'This feature needs an Event Pass. Guest event information remains available.')
        with conn(True) as c:
            if os.environ.get('DATABASE_URL'):c.execute("SELECT id FROM records WHERE kind='event' AND event_id=? FOR UPDATE",(eid,))
            old=next((r for r in rows(kind,eid,c) if r['id']==item.get('id')),None)
            if item.get('id') and not old:raise HTTPError(404,'Record not found in this event')
            data={**(old or {}),**item}
            if kind=='event':
                # Plan/code/ownership are controlled by dedicated endpoints, never client fields.
                data={**old,**{k:item[k] for k in ['name','date','venue','hashtag','budget','approvalThreshold','theme'] if k in item}}
                date.fromisoformat(data['date']);data['budget']=amount(data['budget']);data['approvalThreshold']=amount(data['approvalThreshold']);text(data['name'],80)
                if b.get('regenerateCode'):
                    data['code']=re.sub('[^A-Z0-9]+','-',data['name'].upper())[:35]+'-'+secrets.token_hex(4).upper()
                    c.execute('DELETE FROM event_codes WHERE event_id=?',(eid,));c.execute('INSERT INTO event_codes VALUES(?,?)',(data['code'],eid))
            elif kind=='guests':
                data['name']=text(data.get('name'),80);data['phone']=phone_number(data.get('phone'));data['plusOnes']=int(data.get('plusOnes',0))
                if not 0<=data['plusOnes']<=20:raise ValueError('plusOnes')
                if data.get('status') not in ['To Be Invited','Invited','Confirmed','Declined','Maybe','Arrived','Checked In']:raise ValueError('status')
                if data.get('status')=='Checked In' and (not old or old.get('status')!='Checked In'):raise HTTPError(400,'Use the gate scanner to check in a guest.')
                if any(g['phone']==data['phone'] and g['id']!=item.get('id') for g in rows('guests',eid,c)):raise HTTPError(409,'This phone number is already on the guest list.')
                if not old:self.guest_capacity(c)
                if old and data['phone']!=old['phone']:raise HTTPError(400,'Revoke the old guest and create a new invitation to change phone ownership.')
                data['passNonce']=(old or {}).get('passNonce',secrets.token_urlsafe(18));data['whatsappConsent']=(old or {}).get('whatsappConsent',False)
                data.setdefault('events',['Wedding']);data.setdefault('family','Friends');data.setdefault('diet','Veg');data.setdefault('travel','Not updated')
            elif kind=='members':
                data['phone']=phone_number(data.get('phone'));data['name']=text(data.get('name'),80);role=data.get('role','Finance Team')
                if role not in ROLES or role in ['Super Organiser','Guest']:raise ValueError('Staff role')
                if data['phone']==s['phone']:raise HTTPError(400,'You cannot change your own organiser membership.')
                if role=='Finance Team':
                    count=c.execute("SELECT count(*) AS n FROM memberships WHERE event_id=? AND role='Finance Team' AND revoked=0 AND phone<>?",(eid,data['phone'])).fetchone()['n']
                    if count>=5:raise HTTPError(400,'Finance team is limited to 5 members.')
                entity=data.get('entityId')
                if role in ['Vendor','Hotel Partner']:
                    if not any(x['id']==entity for x in rows('vendors' if role=='Vendor' else 'hotels',eid,c)):raise ValueError('Select a vendor or hotel belonging to this event')
                permissions=data.get('permissions',[])
                if not isinstance(permissions,list) or any(p not in ALLOWED+['joins','entries'] for p in permissions):raise ValueError('permissions')
                c.execute('INSERT INTO memberships(event_id,phone,role,entity_id,permissions) VALUES(?,?,?,?,?) ON CONFLICT(event_id,phone) DO UPDATE SET role=excluded.role,entity_id=excluded.entity_id,permissions=excluded.permissions,revoked=0',(eid,data['phone'],role,entity,json.dumps(permissions)))
            elif kind=='expenses':
                for k in ['amount','paid']:data[k]=amount(data.get(k,0))
                if data['paid']>data['amount']:raise ValueError('Payment exceeds expense')
                data['status']='Needs Approval' if data['amount']>rows('event',eid,c)[0]['approvalThreshold'] and s['role']!='Super Organiser' else 'Approved'
            elif kind=='timeline':date.fromisoformat(data['date']);text(data['name']);text(data['venue'])
            if old:update(c,kind,data,eid)
            else:data['id']=insert(c,kind,data,eid)
            audit(c,s,'Saved '+str(kind)+' #'+str(data['id']))
        return self.response(200,{'ok':True,'id':data['id']})
    def entry_pass(self,q):
        self.require_role('Super Organiser','Co-Organiser','Guest');eid=self.s['event_id']
        with conn(True) as c:
            if rows('event',eid,c)[0]['plan']=='Free':raise HTTPError(402,'Ask your organiser to activate Event Pass for QR entry. Your invitation and RSVP remain available.')
            g=next((g for g in rows('guests',eid,c) if str(g['id'])==q.get('guestId',[''])[0]),None)
            if not g or (self.s['role']=='Guest' and g['phone']!=self.s['phone']):raise HTTPError(404,'Guest pass not found')
            if g['status'] not in ['Confirmed','Checked In']:raise HTTPError(400,'Confirm your RSVP to receive a pass.')
            token=pass_token(c,eid,g)
        import qrcode, qrcode.image.svg
        output=io.BytesIO();qrcode.make(token,image_factory=qrcode.image.svg.SvgPathImage,box_size=6,border=4).save(output)
        return {'token':token,'qrSvg':output.getvalue().decode(),'name':g['name'],'guestId':g['id'],'plusOnes':g.get('attendingPlusOnes',0)}
    def checkin(self,b):
        self.can_manage('entries');eid=self.s['event_id']
        with conn(True) as c:
            if os.environ.get('DATABASE_URL'):c.execute("SELECT id FROM records WHERE kind='event' AND event_id=? FOR UPDATE",(eid,))
            if rows('event',eid,c)[0]['plan']=='Free':raise HTTPError(402,'Activate Event Pass to use QR check-in.')
            if b.get('token'):g=identify_pass(c,eid,b['token'])
            elif self.s['demo_role']:g=next((g for g in rows('guests',eid,c) if str(g['id'])==str(b.get('guestId'))),None)
            else:raise HTTPError(400,'A valid signed QR pass is required.')
            if not g:raise HTTPError(404,'Pass not recognised')
            membership=c.execute('SELECT revoked FROM memberships WHERE event_id=? AND phone=?',(eid,g['phone'])).fetchone()
            if membership and membership['revoked']:raise HTTPError(403,'Access has been revoked.')
            request_id=text(b.get('requestId') or secrets.token_hex(16),80)
            previous=next((e for e in rows('entries',eid,c) if e.get('requestId')==request_id),None)
            if previous:
                if previous['guestId']!=g['id']:raise HTTPError(409,'Check-in request ID already used.')
                return self.response(200,{'ok':True,'name':g['name'],'replayed':True})
            if g['status']=='Checked In' or any(entry.get('guestId')==g['id'] for entry in rows('entries',eid,c)):raise HTTPError(409,'Duplicate scan — this guest is already checked in.')
            if g['status']!='Confirmed':raise HTTPError(400,'Guest must have a confirmed RSVP.')
            plus=int(b.get('plusOnes',0))
            if not 0<=plus<=g.get('attendingPlusOnes',0):raise HTTPError(400,'Plus-one count exceeds the RSVP allowance.')
            g['status']='Checked In';update(c,'guests',g,eid)
            insert(c,'entries',{'name':g['name'],'guestId':g['id'],'staff':self.s['name'],'created':time.time(),'plusOnes':plus,'requestId':request_id},eid);audit(c,self.s,'Gate entry #'+str(g['id']))
        return self.response(200,{'ok':True,'name':g['name']})
    def queue_messages(self,b):
        self.can_manage('guests');eid=self.s['event_id']
        if demo_mode():return self.response(200,{'mode':'sandbox','message':'Sandbox preview only. No WhatsApp messages were sent.'})
        if not providers.whatsapp_ready():raise providers.ProviderError('WhatsApp Business is not configured.')
        guest_ids=b.get('guestIds',[])
        if not isinstance(guest_ids,list) or not 1<=len(guest_ids)<=100:raise ValueError('Select between 1 and 100 guests')
        with conn(True) as c:
            eligible=[g for g in rows('guests',eid,c) if g['id'] in guest_ids and g.get('whatsappConsent')]
            if len(eligible)!=len(set(guest_ids)):raise HTTPError(400,'Every recipient must belong to this event and explicitly opt in to WhatsApp.')
            for g in eligible:
                pending=c.execute("SELECT id FROM outbox WHERE event_id=? AND guest_id=? AND status IN ('Pending','Sending')",(eid,g['id'])).fetchone()
                if not pending:c.execute('INSERT INTO outbox(event_id,guest_id,phone,status,created) VALUES(?,?,?,?,?)',(eid,g['id'],g['phone'],'Pending',time.time()))
            audit(c,self.s,'Queued opted-in WhatsApp invitations')
        return self.response(200,{'mode':'live','message':'Invitations queued. Review and send from the delivery panel.'})
    def dispatch_messages(self):
        self.can_manage('guests');eid=self.s['event_id']
        if demo_mode():raise HTTPError(400,'Live dispatch is disabled in demo mode.')
        if not providers.whatsapp_ready():raise providers.ProviderError('WhatsApp Business is not configured.')
        with conn(True) as c:
            limit(c,'whatsapp-dispatch:'+str(eid),5,3600)
            pending=[dict(r) for r in c.execute("SELECT * FROM outbox WHERE event_id=? AND status='Pending' ORDER BY id LIMIT 20",(eid,))]
            for m in pending:c.execute("UPDATE outbox SET status='Sending' WHERE id=?",(m['id'],))
        sent=0;e=rows('event',eid)[0]
        for m in pending:
            g=next((g for g in rows('guests',eid) if g['id']==m['guest_id']),None)
            try:
                if not g or not g.get('whatsappConsent'):raise providers.ProviderError('Recipient consent is no longer available.')
                result=providers.whatsapp_send(m['phone'],g['name'],e['name'],e['code']);mid=result['messages'][0]['id']
                with conn(True) as c:c.execute("UPDATE outbox SET status='Sent',provider_id=? WHERE id=?",(mid,m['id']))
                sent+=1
            except (providers.ProviderError,KeyError,IndexError):
                # Uncertain sends are not retried automatically: avoid duplicate external messages.
                with conn(True) as c:c.execute("UPDATE outbox SET status='Review required',error=? WHERE id=?",('Check provider logs before retrying.',m['id']))
        return self.response(200,{'message':f'{sent} invitations sent; review delivery status for the rest.'})
    def order(self,b):
        self.require_role('Super Organiser')
        if demo_mode():raise HTTPError(400,'Payments are disabled in demo mode.')
        plan=b.get('plan')
        if plan not in CATALOG:raise ValueError('Unknown plan')
        eid=self.s['event_id']
        if rows('event',eid)[0]['plan']==plan:raise HTTPError(409,'This event already has this plan.')
        with conn(True) as c:limit(c,'payment-order:'+self.s['phone'],10,3600)
        result=providers.payment_request('orders',{'amount':CATALOG[plan],'currency':'INR','receipt':'ss_'+secrets.token_hex(12),'notes':{'event_id':str(eid),'plan':plan},'payment_capture':1})
        if result.get('amount')!=CATALOG[plan] or result.get('currency')!='INR' or not re.fullmatch(r'order_[A-Za-z0-9]+',result.get('id','')):raise providers.ProviderError('Unexpected payment order response.')
        with conn(True) as c:c.execute('INSERT INTO purchases VALUES(?,?,?,?,?,?,?,?,?)',(result['id'],eid,self.s['phone'],plan,CATALOG[plan],'INR','Pending',None,time.time()))
        return self.response(200,{'orderId':result['id'],'keyId':os.environ['RAZORPAY_KEY_ID'],'amount':CATALOG[plan],'currency':'INR','name':'Shaadi Sync','plan':plan})
    def activate_payment(self,payment):
        with conn(True) as c:
            if os.environ.get('DATABASE_URL'):c.execute('SELECT id FROM purchases WHERE id=? FOR UPDATE',(payment.get('order_id'),))
            p=c.execute('SELECT * FROM purchases WHERE id=?',(payment.get('order_id'),)).fetchone()
            if not p or payment.get('status')!='captured' or payment.get('amount')!=p['amount'] or payment.get('currency')!=p['currency']:raise HTTPError(400,'Captured payment does not match this order.')
            if p['status']=='Paid':
                if p['payment_id']!=payment['id']:raise HTTPError(409,'This order has already been paid.')
                return
            if os.environ.get('DATABASE_URL'):c.execute("SELECT id FROM records WHERE kind='event' AND event_id=? FOR UPDATE",(p['event_id'],))
            event=rows('event',p['event_id'],c)[0];event['plan']=p['plan'];update(c,'event',event,p['event_id'])
            c.execute("UPDATE purchases SET status='Paid',payment_id=? WHERE id=?",(payment['id'],p['id']))
            audit(c,{'name':'Razorpay verified payment','event_id':p['event_id']},'Activated '+p['plan'])
    def verify_payment(self,b):
        self.require_role('Super Organiser')
        order_id=text(b.get('razorpay_order_id'));pid=text(b.get('razorpay_payment_id'));signature=text(b.get('razorpay_signature'))
        with conn() as c:p=c.execute('SELECT * FROM purchases WHERE id=? AND event_id=? AND phone=?',(order_id,self.s['event_id'],self.s['phone'])).fetchone()
        if not p:raise HTTPError(404,'Payment order not found')
        expected=hmac.new(os.environ.get('RAZORPAY_KEY_SECRET','').encode(),(order_id+'|'+pid).encode(),hashlib.sha256).hexdigest()
        if not os.environ.get('RAZORPAY_KEY_SECRET') or not hmac.compare_digest(expected,signature):raise HTTPError(400,'Payment signature is invalid.')
        if not re.fullmatch(r'pay_[A-Za-z0-9]+',pid):raise ValueError('payment id')
        payment=providers.payment_request('payments/'+pid)
        if payment.get('id')!=pid or payment.get('order_id')!=order_id:raise HTTPError(400,'Payment does not match the checkout order.')
        self.activate_payment(payment);return self.response(200,{'ok':True})
    def invoice(self,q):
        self.require_role('Super Organiser','Finance Team')
        with conn() as c:p=c.execute("SELECT * FROM purchases WHERE event_id=? AND status='Paid' ORDER BY created DESC LIMIT 1",(self.s['event_id'],)).fetchone()
        if not p:raise HTTPError(404,'No completed purchase for this event.')
        return {'receipt':dict(p),'note':'Payment receipt. A GST tax invoice requires configured seller GST registration and billing details.'}
    def webhook(self,path,raw):
        if path not in ['/api/webhooks/razorpay','/api/webhooks/whatsapp']:raise HTTPError(404,'Webhook not found')
        name='RAZORPAY_WEBHOOK_SECRET' if path.endswith('razorpay') else 'WHATSAPP_APP_SECRET'
        key=os.environ.get(name,'')
        sig=self.headers.get('X-Razorpay-Signature','') if path.endswith('razorpay') else self.headers.get('X-Hub-Signature-256','').removeprefix('sha256=')
        if not key or not hmac.compare_digest(hmac.new(key.encode(),raw,hashlib.sha256).hexdigest(),sig):raise HTTPError(403,'Invalid webhook signature')
        data=json.loads(raw)
        if path.endswith('razorpay'):
            if data.get('event')=='payment.captured':self.activate_payment(data['payload']['payment']['entity'])
            return {'ok':True}
        with conn(True) as c:
            for entry in data.get('entry',[]):
                for change in entry.get('changes',[]):
                    value=change.get('value',{})
                    for status in value.get('statuses',[]):
                        if status.get('status') in ['sent','delivered','read','failed']:
                            c.execute('UPDATE outbox SET status=? WHERE provider_id=?',(status['status'].title(),status.get('id')))
                    for m in value.get('messages',[]):
                        mid=m.get('id');context=m.get('context',{}).get('id')
                        if not mid or c.execute('SELECT id FROM webhook_events WHERE id=?',(mid,)).fetchone():continue
                        outbound=c.execute('SELECT * FROM outbox WHERE provider_id=?',(context,)).fetchone()
                        if not outbound or m.get('from')!='91'+outbound['phone']:continue
                        choice=m.get('button',{}).get('payload') or m.get('interactive',{}).get('button_reply',{}).get('id')
                        rsvp={'RSVP_YES':'Confirmed','RSVP_NO':'Declined','RSVP_MAYBE':'Maybe'}.get(choice)
                        if not rsvp:continue
                        g=next((g for g in rows('guests',outbound['event_id'],c) if g['id']==outbound['guest_id']),None)
                        membership=c.execute('SELECT revoked FROM memberships WHERE event_id=? AND phone=?',(outbound['event_id'],outbound['phone'])).fetchone()
                        if not g or (membership and membership['revoked']):continue
                        g['status']=rsvp
                        if rsvp=='Confirmed':pass_token(c,outbound['event_id'],g)
                        else:g['passNonce']=secrets.token_urlsafe(18)
                        update(c,'guests',g,outbound['event_id']);c.execute('INSERT INTO webhook_events VALUES(?,?)',(mid,time.time()))
        return {'ok':True}

if __name__=='__main__':
    os.umask(0o077)
    initialize()
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT',3000))),Handler).serve_forever()
