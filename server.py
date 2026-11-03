import json, sqlite3, secrets, os, time, hashlib, base64, hmac
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote
from http.cookies import SimpleCookie
from pathlib import Path
DB=os.environ.get('DATABASE_PATH','shaadi.sqlite3')
SESSIONS={}; OTPS={}
SESSION_TTL=86400
ROLES=['Super Organiser','Co-Organiser','Finance Team','Vendor','Guest','Hotel Partner']
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def initialize():
 with conn() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, kind TEXT, data TEXT); CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, created REAL);')
  if c.execute('SELECT count(*) FROM records').fetchone()[0]: return
  seeds={
   'event':[dict(name='Rahul & Priya',code='RAHUL-PRIYA-2026',date='2026-12-12',venue='The Leela Palace, Jaipur',budget=2500000,plan='Event Pass',theme='Royal Rajasthani',hashtag='#RaPriKiShaadi',approvalThreshold=100000)],
   'guests':[dict(name=n,phone=f'90000000{i:02}',side=s,family=f,status=st,diet=d,plusOnes=1,events=['Wedding','Sangeet'],travel=t,consent=False) for i,(n,s,f,st,d,t) in enumerate([
    ('Ananya Sharma','Bride','Sharma family','Confirmed','Veg','Reached hotel'),('Vikram Malhotra','Groom','Malhotra family','Confirmed','Non-veg','Landed'),('Meera Kapoor','Bride','Kapoor family','Invited','Jain','Not updated'),('Arjun Singh','Groom','Singh family','Checked In','Veg','Reached hotel'),('Neha & Rohan Gupta','Both','Gupta family','Confirmed','Veg','On the way'),('Ishaan Mehta','Groom','Mehta family','Maybe','Vegan','Not updated'),('Kavita Sharma','Bride','Sharma family','Confirmed','Jain','Left home'),('Dev Patel','Both','Patel family','Declined','Veg','Not updated'),('Riya Agarwal','Bride','Agarwal family','Invited','Veg','Not updated'),('Aditya Verma','Groom','Verma family','Arrived','Non-veg','Reached hotel'),('Sunita Malhotra','Groom','Malhotra family','Confirmed','Veg','Left home'),('Pooja Sethi','Bride','Sethi family','To Be Invited','Vegan','Not updated')])],
   'timeline':[dict(name=n,date=d,time=t,venue=v,dress=dr,color=co) for n,d,t,v,dr,co in [('Mehendi','2026-12-10','15:00','Palace Gardens','Florals & sunshine','green'),('Haldi','2026-12-11','10:00','Poolside Courtyard','A little yellow magic','yellow'),('Sangeet','2026-12-11','19:00','Sheesh Mahal','Bring the sparkle','purple'),('Wedding','2026-12-12','18:30','Royal Courtyard','Royal Indian elegance','red'),('Reception','2026-12-13','19:30','Grand Ballroom','Black tie & beautiful','blue')]],
   'vendors':[dict(name=n,category=ca,contact='9876543210',quote=q,paid=p,status=st,arrival='16:00',deliverables='Final walkthrough · Team briefing · Setup') for n,ca,q,p,st in [('Saffron Stories','Catering',650000,300000,'Booked'),('The Marigold Co.','Decor',480000,240000,'In Progress'),('Frames of Forever','Photography',280000,140000,'Booked'),('DJ Aakash','Music',85000,40000,'Booked')]],
   'expenses':[dict(name=n,category=ca,amount=a,paid=p,due='2026-12-05',status='Approved',mode='UPI') for n,ca,a,p in [('Palace venue booking','Venue',800000,400000),('Wedding feast','Catering',650000,300000),('Floral wonderland','Decor',480000,240000),('Every little memory','Photography',280000,140000)]],
   'tasks':[dict(name=n,owner=o,due='2026-12-01',status=s) for n,o,s in [('Finalise the sangeet playlist','Priya','In Progress'),('Confirm airport pickups','Rahul','To Do'),('Send the last round of invites','Ananya','To Do'),('Approve floral mood board','Priya','Done')]],
   'hotels':[dict(name='The Leela Palace',rooms=30,assigned=18,address='Delhi-Jaipur Highway, Jaipur',checkin='14:00')],
   'transport':[dict(name='Airport → The Leela',time='14:30',vehicle='RJ14 AB 2026',driver='Rajesh · 98765 43210')],
   'catering':[dict(name='Wedding dinner',booked=450,event='Wedding'),dict(name='Sangeet dinner',booked=380,event='Sangeet')],
   'announcements':[dict(name='A little celebration, a lot of love',message='Your people. Your plans. One beautiful celebration. Let’s make every moment count.',created=time.time())],
   'polls':[dict(name='Who will rule the dance floor?',options={'Team Bride':28,'Team Groom':22})],
   'gifts':[], 'songs':[], 'joins':[], 'entries':[], 'photos':[], 'members':[], 'support':[]}
  for kind,rows in seeds.items():
   for row in rows:c.execute('INSERT INTO records(kind,data) VALUES(?,?)',(kind,json.dumps(row)))
def rows(kind):
 with conn() as c:return [dict(json.loads(r['data']),id=r['id']) for r in c.execute('SELECT * FROM records WHERE kind=?',(kind,))]
def get_session(h):
 try:
  cookie=SimpleCookie(h.headers.get('Cookie',''));session=SESSIONS.get(cookie['session'].value)
  if session and time.time()-session.get('created',0)<SESSION_TTL:return session
  return None
 except:return None
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def response(self,code,data,cookie=None):
  b=json.dumps(data).encode(); self.send_response(code); self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff');
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(b)
 def require_access(self):
  password=os.environ.get('DEMO_ACCESS_PASSWORD','')
  if not password or urlparse(self.path).path=='/api/health':return True
  try:
   scheme,encoded=self.headers.get('Authorization','').split(' ',1)
   credentials=base64.b64decode(encoded,validate=True).decode()
   username,supplied=credentials.split(':',1)
   if scheme.lower()=='basic' and username=='demo' and hmac.compare_digest(supplied.encode(),password.encode()):return True
  except (ValueError,UnicodeError):pass
  self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="Shaadi Sync private demo", charset="UTF-8"');self.send_header('Cache-Control','no-store');self.end_headers();return False
 def do_GET(self):
  if not self.require_access():return
  path=urlparse(self.path).path
  if path=='/api/health':return self.response(200,{'ok':True,'mode':'sandbox'})
  if path=='/api/audit':
   s=get_session(self)
   if not s or s['role'] not in ['Super Organiser','Finance Team']:return self.response(403,{'error':'Finance access required'})
   with conn() as c:data=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]
   return self.response(200,{'audit':data})
  if path=='/api/state':
   s=get_session(self)
   if not s:return self.response(401,{'error':'Please sign in'})
   role=s['role']; kinds=['event','timeline','announcements','polls']
   if role in ['Super Organiser','Co-Organiser']:kinds+=['guests','vendors','tasks','hotels','transport','catering','joins','entries','songs','photos','gifts','members']
   if role in ['Super Organiser','Finance Team']:kinds+=['expenses']
   if role=='Guest':kinds+=['transport']
   data={k:rows(k) for k in kinds}
   for poll in data.get('polls',[]):
    poll['hasVoted']=s['phone'] in poll.get('voters',[]);poll.pop('voters',None)
   if role=='Guest':
    data['guests']=[g for g in rows('guests') if g['phone']==s['phone']]
    invited=set(data['guests'][0].get('events',[])) if data['guests'] else set()
    data['timeline']=[t for t in data['timeline'] if t['name'] in invited]
   if role=='Vendor':data['vendors']=[v for v in rows('vendors') if v['id']==s.get('vendorId')]
   if role=='Hotel Partner':data['hotels']=[h for h in rows('hotels') if h['id']==s.get('hotelId')]
   if role not in ['Super Organiser','Finance Team']:
    for e in data['event']:e.pop('budget',None);e.pop('approvalThreshold',None)
   return self.response(200,dict(data,user=s,mode='sandbox'))
  if path.startswith('/api/'):return self.response(404,{'error':'Not found'})
  target=(Path('static') / ('index.html' if path=='/' else unquote(path).lstrip('/'))).resolve()
  if not target.is_relative_to(Path('static').resolve()) or not target.is_file():return self.response(404,{'error':'Not found'})
  content=target.read_bytes();self.send_response(200);self.send_header('Content-Type',self.guess_type(str(target)));self.send_header('Content-Length',str(len(content)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(content)
 def do_POST(self):
  if not self.require_access():return
  try:
   length=int(self.headers.get('Content-Length',0))
   if length>1000000:return self.response(413,{'error':'Request too large'})
   body=json.loads(self.rfile.read(length) or b'{}');path=urlparse(self.path).path;s=get_session(self)
   if path=='/api/auth/otp':
    phone=str(body.get('phone',''))
    if not phone.isdigit() or len(phone)!=10:return self.response(400,{'error':'Enter a 10-digit phone number'})
    now=time.time();old=OTPS.get(phone)
    if old and now-old['created']<30:return self.response(429,{'error':'Please wait 30 seconds before retrying'})
    code=f'{secrets.randbelow(1000000):06d}';OTPS[phone]={'hash':hashlib.sha256(code.encode()).hexdigest(),'created':now,'attempts':0}
    return self.response(200,{'sandboxCode':code,'message':'Sandbox OTP only. No SMS was sent.'})
   if path=='/api/auth/verify':
    phone=str(body.get('phone',''));o=OTPS.get(phone)
    if not o or time.time()-o['created']>300 or o['attempts']>=5:return self.response(400,{'error':'Request a new code'})
    o['attempts']+=1
    if hashlib.sha256(str(body.get('code','')).encode()).hexdigest()!=o['hash']:return self.response(400,{'error':'Incorrect code'})
    del OTPS[phone]
    guest=next((g for g in rows('guests') if g['phone']==phone),None)
    if not guest:return self.response(403,{'error':'Your number must be registered or approved by an organiser'})
    user={'name':guest['name'],'phone':phone,'role':'Guest'}
   elif path=='/api/auth/demo':
    role=body.get('role','Super Organiser')
    if os.environ.get('DEMO_MODE','1')!='1':return self.response(403,{'error':'Demo access is disabled'})
    if role not in ROLES:return self.response(400,{'error':'Invalid role'})
    user={'name':'Priya Sharma' if role!='Guest' else 'Ananya Sharma','phone':'9000000000','role':role,'vendorId':rows('vendors')[0]['id'],'hotelId':rows('hotels')[0]['id']}
   else:user=None
   if user:
    user['created']=time.time();token=secrets.token_urlsafe(32);SESSIONS[token]=user;return self.response(200,{'ok':True},f'session={token}; HttpOnly; SameSite=Strict; Path=/')
   if path=='/api/auth/logout':
    try:SESSIONS.pop(SimpleCookie(self.headers.get('Cookie',''))['session'].value,None)
    except KeyError:pass
    return self.response(200,{'ok':True},'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
   if path=='/api/join':
    if body.get('code')!=rows('event')[0]['code']:return self.response(404,{'error':'Event code not found'})
    phone=str(body.get('phone',''))
    if not phone.isdigit() or len(phone)!=10 or not body.get('name'):return self.response(400,{'error':'Name and 10-digit phone required'})
    self.insert('joins',{'name':body['name'],'phone':phone,'status':'Pending'})
    return self.response(201,{'ok':True,'message':'Request sent. An organiser must approve your access.'})
   if not s:return self.response(401,{'error':'Please sign in'})
   role=s['role'];organiser=role=='Super Organiser';co=role=='Co-Organiser'
   if path=='/api/guest-update':
    if role!='Guest':return self.response(403,{'error':'Guest access required'})
    g=next((g for g in rows('guests') if g['phone']==s['phone']),None)
    if not g:return self.response(404,{'error':'Guest not found'})
    if not body.get('consent'):return self.response(400,{'error':'Travel sharing requires explicit consent'})
    if body.get('travel') not in ['Not updated','Left home','Landed','On the way to hotel','Reached hotel']:return self.response(400,{'error':'Invalid travel milestone'})
    g.update(travel=body['travel'],consent=True);self.update('guests',g);return self.response(200,{'ok':True})
   if path=='/api/song':
    if role!='Guest':return self.response(403,{'error':'Guest access required'})
    if not str(body.get('name','')).strip():raise ValueError('Song name is required')
    self.insert('songs',{'name':str(body['name'])[:150],'owner':s['name'],'status':'Pending'});return self.response(201,{'ok':True})
   if path=='/api/vote':
    poll=next((p for p in rows('polls') if p['id']==body.get('id')),None)
    if not poll or body.get('option') not in poll['options']:raise ValueError('Invalid poll option')
    if s['phone'] in poll.get('voters',[]):return self.response(409,{'error':'You have already voted in this poll'})
    poll['options'][body['option']]+=1;poll.setdefault('voters',[]).append(s['phone']);self.update('polls',poll);return self.response(200,{'ok':True})
   if path=='/api/rsvp':
    if role!='Guest':return self.response(403,{'error':'Guest access required'})
    g=next((g for g in rows('guests') if g['phone']==s['phone']),None)
    if not g:return self.response(404,{'error':'Guest not found'})
    if not body.get('consent'):return self.response(400,{'error':'Consent is required to record your RSVP'})
    status=body.get('status');plus=int(body.get('plusOnes',0))
    if status not in ['Confirmed','Declined','Maybe'] or plus>g['plusOnes'] or plus<0:return self.response(400,{'error':'Invalid RSVP or plus-one limit'})
    g.update(status=status,attendingPlusOnes=plus,consent=bool(body.get('consent')));self.update('guests',g)
    return self.response(200,{'ok':True})
   if path=='/api/checkin':
    if not (organiser or co):return self.response(403,{'error':'Organiser access required'})
    g=next((g for g in rows('guests') if str(g['id'])==str(body.get('guestId'))),None)
    if not g:return self.response(404,{'error':'Pass not recognised'})
    if g['status']=='Checked In':return self.response(409,{'error':'Duplicate scan — this guest is already checked in'})
    if g['status']!='Confirmed':return self.response(400,{'error':'Guest must have a confirmed RSVP'})
    g['status']='Checked In';self.update('guests',g);self.insert('entries',{'name':g['name'],'staff':s['name'],'created':time.time()})
    return self.response(200,{'ok':True,'name':g['name']})
   if path=='/api/whatsapp':
    if not (organiser or co):return self.response(403,{'error':'Organiser access required'})
    return self.response(200,{'mode':'sandbox','message':'Message preview queued in sandbox. No WhatsApp messages were sent.'})
   if path=='/api/save':
    kind=body.get('kind');item=body.get('item',{});allowed=['guests','timeline','vendors','tasks','hotels','transport','catering','announcements','joins','songs','photos','gifts','polls']
    if kind=='expenses':permit=role in ['Super Organiser','Finance Team']
    elif kind in ['event','members']:permit=organiser
    else:permit=(organiser or co) and kind in allowed
    if not permit:return self.response(403,{'error':'You do not have permission for this action'})
    if kind=='members' and item.get('role')=='Finance Team' and len([x for x in rows('members') if x.get('role')=='Finance Team' and x['id']!=item.get('id')])>=5:return self.response(400,{'error':'Finance team is limited to 5 members'})
    if kind=='expenses':
     for key in ['amount','paid']:
      item[key]=float(item.get(key,0))
      if item[key]<0:raise ValueError('Amounts must be positive')
     item['status']='Needs Approval' if item['amount']>rows('event')[0]['approvalThreshold'] and not organiser else 'Approved'
    if kind=='event':
     if not organiser:return self.response(403,{'error':'Organiser access required'})
     if not item.get('name') or not item.get('date'):raise ValueError('Event name and date are required')
    if kind=='guests' and not item.get('name'):raise ValueError('Guest name is required')
    if item.get('id'):
     old=next((r for r in rows(kind) if r['id']==item['id']),None)
     if not old:return self.response(404,{'error':'Record not found'})
     old.update(item);item=old;self.update(kind,item)
    else:self.insert(kind,item)
    with conn() as c:c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(s['name'],f'Saved {kind}',time.time()))
    return self.response(200,{'ok':True})
   return self.response(404,{'error':'Not found'})
  except (ValueError,KeyError,TypeError) as e:return self.response(400,{'error':str(e)})
 def insert(self,kind,data):
  with conn() as c:c.execute('INSERT INTO records(kind,data) VALUES(?,?)',(kind,json.dumps(data)))
 def update(self,kind,data):
  with conn() as c:c.execute('UPDATE records SET data=? WHERE id=? AND kind=?',(json.dumps(data),data['id'],kind))
if __name__=='__main__':
 initialize();ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT',3000))),Handler).serve_forever()
