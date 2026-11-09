"""Private, event-scoped mashup files; byte storage supports SQLite and PostgreSQL."""
import base64,io,json,math,os,re,time
import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
MAX_BYTES=20*1024*1024
class AudioError(Exception):
 def __init__(self,status,message):self.status=status;super().__init__(message)
def quota(name,default):return max(1,min(4096,int(os.environ.get(name,str(default)))))*1024*1024
def validate(encoded):
 if not isinstance(encoded,str) or len(encoded)>4*((MAX_BYTES+2)//3):raise AudioError(413,'Choose an audio file up to 20 MB.')
 try:raw=base64.b64decode(encoded,validate=True)
 except (ValueError,TypeError):raise AudioError(400,'The audio file could not be read.') from None
 if not raw or len(raw)>MAX_BYTES:raise AudioError(413,'Choose a non-empty audio file up to 20 MB.')
 try:
  parsed=mutagen.File(io.BytesIO(raw))
  types={MP3:('audio/mpeg','mp3'),WAVE:('audio/wav','wav'),MP4:('audio/mp4','m4a'),OggVorbis:('audio/ogg','ogg'),OggOpus:('audio/ogg','ogg')}
  if type(parsed) not in types:raise ValueError()
  duration=float(parsed.info.length)
  if not math.isfinite(duration) or not 0<duration<=1800:raise ValueError()
  mime,extension=types[type(parsed)]
 except Exception:raise AudioError(400,'Use a valid MP3, WAV, M4A or OGG audio file, up to 30 minutes long.') from None
 return raw,mime,extension,duration

def song(c,s,song_id):
 if not s or not s.get('event_id'):raise AudioError(401,'Please sign in to your wedding.')
 role=s['role']
 if role not in ['Super Organiser','Co-Organiser','Guest']:raise AudioError(403,'Song uploads are available to guests and authorised organisers.')
 if role=='Co-Organiser' and not (s.get('demo_role') or 'songs' in s.get('permissions',[])):raise AudioError(403,'Ask your organiser for song permissions.')
 row=c.execute("SELECT data FROM records WHERE id=? AND kind='songs' AND event_id=?",(song_id,s['event_id'])).fetchone()
 if not row:raise AudioError(404,'Song not found in this wedding.')
 item=json.loads(row['data'])
 if role=='Guest' and item.get('requestedBy')!=s['phone']:raise AudioError(403,'You can access audio only for your own song requests.')
 return item

def metadata(c,event_id):
 return {r['song_id']:{'filename':r['filename'],'bytes':r['size'],'duration':r['duration'],'mime':r['mime'],'url':'/api/song-audio/'+str(r['song_id'])} for r in c.execute('SELECT song_id,filename,size,duration,mime FROM song_audio WHERE event_id=?',(event_id,))}

def upload(db,s,body):
 with db() as c:song(c,s,body.get('songId'))
 if body.get('consent') is not True:raise AudioError(400,'Confirm that you can share this audio with your wedding organisers.')
 filename=body.get('filename')
 if not isinstance(filename,str) or not filename.strip() or len(filename)>140 or re.search(r'[\x00-\x1f]',filename):raise AudioError(400,'Choose a file with a valid name (up to 140 characters).')
 filename=filename.replace('\\','/').split('/')[-1]
 raw,mime,extension,duration=validate(body.get('data'))
 with db(True) as c:
  if os.environ.get('DATABASE_URL'):c.execute('SELECT pg_advisory_xact_lock(823917824)')
  song(c,s,body.get('songId'))
  old=c.execute('SELECT size FROM song_audio WHERE song_id=?',(body['songId'],)).fetchone();previous=old['size'] if old else 0
  event_size=c.execute('SELECT coalesce(sum(size),0) AS total FROM song_audio WHERE event_id=?',(s['event_id'],)).fetchone()['total']
  total=c.execute('SELECT coalesce(sum(size),0) AS total FROM song_audio').fetchone()['total']
  if event_size-previous+len(raw)>quota('SONG_AUDIO_EVENT_MB',75) or total-previous+len(raw)>quota('SONG_AUDIO_TOTAL_MB',150):raise AudioError(413,'Audio storage is full. Ask your organiser to remove older mashups or increase storage.')
  c.execute('INSERT INTO song_audio(song_id,event_id,filename,mime,extension,size,duration,content,updated) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(song_id) DO UPDATE SET filename=excluded.filename,mime=excluded.mime,extension=excluded.extension,size=excluded.size,duration=excluded.duration,content=excluded.content,updated=excluded.updated',(body['songId'],s['event_id'],filename,mime,extension,len(raw),duration,raw,time.time()))
 return {'ok':True}

def remove(db,s,song_id):
 with db(True) as c:
  song(c,s,song_id);c.execute('DELETE FROM song_audio WHERE song_id=? AND event_id=?',(song_id,s['event_id']))
 return {'ok':True}

def download(db,s,song_id):
 with db() as c:
  song(c,s,song_id);row=c.execute('SELECT * FROM song_audio WHERE song_id=? AND event_id=?',(song_id,s['event_id'])).fetchone()
  if not row:raise AudioError(404,'This song has no uploaded audio.')
  return dict(row)
