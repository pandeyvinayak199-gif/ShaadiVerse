"""Personal guest invitations. A name-only link is a private, single-account claim link."""
import io,json,re,time,base64
from datetime import datetime,timezone
import qrcode,qrcode.image.svg
class InviteError(Exception):
 def __init__(self,status,message):self.status=status;super().__init__(message)
def qr(value):
 out=io.BytesIO();qrcode.make(value,image_factory=qrcode.image.svg.SvgPathImage,box_size=6,border=4).save(out);return out.getvalue().decode()
def png(value):
 out=io.BytesIO();qrcode.make(value).save(out,format='PNG');return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()
def clock(value):
 try:return datetime.strptime(value,'%H:%M').strftime('%I:%M %p').lstrip('0')
 except (ValueError,TypeError):return value or 'Time to be announced'
def get(c,token):
 if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise InviteError(404,'This invitation is not available.')
 row=c.execute('SELECT * FROM guest_invitations WHERE token=?',(token,)).fetchone()
 if not row or row['revoked'] or row['expires']<time.time():raise InviteError(410,'This invitation has expired or been replaced. Ask your organiser for a new link.')
 guest=c.execute("SELECT data FROM records WHERE id=? AND kind='guests' AND event_id=?",(row['guest_id'],row['event_id'])).fetchone();event=c.execute("SELECT data FROM records WHERE kind='event' AND event_id=?",(row['event_id'],)).fetchone()
 if not guest or not event:raise InviteError(404,'This wedding invitation is no longer available.')
 return dict(row),dict(json.loads(guest['data']),id=row['guest_id']),json.loads(event['data'])
def preview(c,token):
 row,g,e=get(c,token)
 return {'guestName':g['name'],'weddingName':e['name'],'date':e['date'],'venue':e.get('venue',''),'requiresInvitedEmail':bool(g.get('email')),'claimed':bool(row['claimed_by'])}
def date_label(value):
 try:return datetime.strptime(value,'%Y-%m-%d').strftime('%d %B %Y').lstrip('0')
 except (ValueError,TypeError):return value
def message(c,row,g,e,url):
 functions=[json.loads(r['data']) for r in c.execute("SELECT data FROM records WHERE kind='timeline' AND event_id=? ORDER BY id",(row['event_id'],))]
 functions.sort(key=lambda t:(t.get('date',''),t.get('time','')))
 lines=[f"Dear {g['name']},",'',f"You are warmly invited to {e['name']}!",f"Wedding date: {date_label(e['date'])}"]
 if e.get('venue'):lines.append('Venue: '+e['venue'])
 if functions:
  lines+=['','Join us for:']
  lines += [f"• {t['name']} — {date_label(t['date'])}, {clock(t.get('time'))}"+(f" · {t['venue']}" if t.get('venue') else '') for t in functions]
 lines+=['',f"Please RSVP here: {url}",'Tap Guest login, continue with Google, and choose the functions you will attend. You can add your family, diets, travel and stay details within your invitation allowance.',f"Plus-ones allowed: {g.get('plusOnes',0)}.",'Your personal wedding entry QR pass is ready in your guest portal after you confirm your RSVP.']
 if g.get('email'):lines.append('Use the Google email your organiser invited.')
 lines+=['Please keep this personal invitation private.','We look forward to celebrating with you!']
 return '\n'.join(lines)
