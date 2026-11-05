"""Capability-scoped shared photo albums. Image bytes use the existing private database."""
import base64, binascii, hashlib, hmac, io, json, math, os, re, secrets, tempfile, threading, time, warnings, zipfile
from http.cookies import SimpleCookie
from urllib.parse import urlencode
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
import qrcode, qrcode.image.svg
register_heif_opener()
Image.MAX_IMAGE_PIXELS=16_000_000
PROCESS_IMAGE=threading.BoundedSemaphore(1)
MAX_INPUT=15*1024*1024

class AlbumError(Exception):
    def __init__(self,status,message):self.status=status;super().__init__(message)
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def name_value(value):
    if not isinstance(value,str) or not 1<=len(value.strip())<=80 or any(ord(c)<32 for c in value):raise AlbumError(400,'Enter your name (1–80 characters).')
    return value.strip()
def quota(name,default):return max(1,min(4096,int(os.environ.get(name,str(default)))))*1024*1024
def prepare_image(encoded):
    if not isinstance(encoded,str) or len(encoded)>((MAX_INPUT+2)//3)*4:raise AlbumError(413,'Each photo must be 15 MB or smaller. Choose a smaller image.')
    try:raw=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):raise AlbumError(400,'The photo upload was incomplete. Please retry.') from None
    if not raw or len(raw)>MAX_INPUT:raise AlbumError(413,'Each photo must be 15 MB or smaller.')
    if not PROCESS_IMAGE.acquire(timeout=20):raise AlbumError(503,'Another photo is being processed. Please retry this photo.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as check:
                if check.format not in ['JPEG','PNG','WEBP','HEIF','HEIC']:raise AlbumError(400,'Choose a JPEG, PNG, WebP or HEIC photo.')
                check.verify()
            with Image.open(io.BytesIO(raw)) as image:
                if image.format in ['HEIF','HEIC'] and image.width*image.height>24_000_000:raise AlbumError(413,'This HEIC original is very large. Export a smaller JPEG and try again.')
                image.draft('RGB',(2560,2560))
                image=ImageOps.exif_transpose(image)
                image.thumbnail((2560,2560),Image.Resampling.LANCZOS)
                if image.mode in ['RGBA','LA'] or 'transparency' in image.info:
                    rgba=image.convert('RGBA');clean=Image.new('RGB',rgba.size,'white');clean.paste(rgba,mask=rgba.getchannel('A'))
                else:clean=image.convert('RGB')
                # New pixel-only images strip EXIF/GPS, comments and other original metadata.
                pixels=Image.new('RGB',clean.size);pixels.paste(clean);width,height=pixels.size
                output=io.BytesIO();pixels.save(output,'JPEG',quality=88,optimize=True)
                pixels.thumbnail((480,480),Image.Resampling.LANCZOS);thumb=io.BytesIO();pixels.save(thumb,'JPEG',quality=78,optimize=True)
                return output.getvalue(),thumb.getvalue(),width,height
    except AlbumError:raise
    except (Image.DecompressionBombError,Image.DecompressionBombWarning):raise AlbumError(413,'This photo has very large dimensions. Export a smaller version and retry.') from None
    except (UnidentifiedImageError,OSError,ValueError):raise AlbumError(400,'This file is not a readable photo. Try a JPEG, PNG, WebP or HEIC image.') from None
    finally:PROCESS_IMAGE.release()

class Albums:
    def __init__(self,db,session,headers,identity,base_url):
        self.db=db;self.session=session;self.headers=headers;self.identity=identity;self.base_url=base_url.rstrip('/')
    def _manager(self,album):
        s=self.session
        return bool(s and s['event_id']==album['event_id'] and (s['role']=='Super Organiser' or (s['role']=='Co-Organiser' and (s['demo_role'] or 'photos' in s['permissions']))))
    def _album(self,c,album_id):
        album=c.execute('SELECT * FROM memory_albums WHERE id=?',(album_id,)).fetchone()
        if not album:raise AlbumError(404,'This Memories album was not found.')
        return dict(album)
    def _token_album(self,c,token):
        if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise AlbumError(404,'This album link is invalid or has been replaced.')
        album=c.execute('SELECT * FROM memory_albums WHERE share_token=?',(token,)).fetchone()
        if not album:raise AlbumError(404,'This album link is invalid or has been replaced.')
        return dict(album)
    def _visitor(self,c,album):
        try:token=SimpleCookie(self.headers.get('Cookie',''))['memories_'+album['id']].value
        except (KeyError,AttributeError):return None
        row=c.execute('SELECT * FROM memory_visitors WHERE album_id=? AND token_hash=? AND expires>?',(album['id'],digest(token),time.time())).fetchone()
        return dict(row) if row else None
    def _actor(self,c,album,write=False):
        visitor=self._visitor(c,album);manager=self._manager(album) or bool(visitor and visitor['is_host'])
        if not album['enabled'] and not manager:raise AlbumError(410,'Sharing for this album is paused by the organiser.')
        if visitor:actor={**visitor,'manager':manager,'memory_cookie':True}
        elif manager:actor={'id':'account:'+self.session['phone'],'name':self.session['name'],'csrf':self.session['csrf'],'manager':True,'memory_cookie':False}
        else:raise AlbumError(401,'Open the shared QR link and enter your name to access this album.')
        if write:
            provided=self.headers.get('X-Memories-CSRF' if actor['memory_cookie'] else 'X-CSRF-Token','')
            app_ok=self._manager(album) and hmac.compare_digest(self.headers.get('X-CSRF-Token',''),self.session['csrf'])
            if not app_ok and not hmac.compare_digest(provided,actor['csrf']):raise AlbumError(403,'Refresh the album before trying again.')
        return actor
    def _rate(self,c,key,maximum):
        key='memories:'+key;now=time.time();r=c.execute('SELECT * FROM limits WHERE bucket=?',(key,)).fetchone()
        if r and r['reset']>now and r['count']>=maximum:raise AlbumError(429,'Please wait before trying again. You can continue uploading later.')
        count=r['count']+1 if r and r['reset']>now else 1;reset=r['reset'] if r and r['reset']>now else now+3600
        c.execute('INSERT INTO limits VALUES(?,?,?) ON CONFLICT(bucket) DO UPDATE SET count=excluded.count,reset=excluded.reset',(key,count,reset))
    def _info(self,c,album):
        event=c.execute("SELECT data FROM records WHERE kind='event' AND event_id=?",(album['event_id'],)).fetchone()
        if not event:raise AlbumError(404,'The event for this album is unavailable.')
        event=json.loads(event['data']);total=c.execute('SELECT count(*) AS n,coalesce(sum(bytes),0) AS used FROM memory_photos WHERE album_id=?',(album['id'],)).fetchone()
        return {'id':album['id'],'name':event['name'],'date':event['date'],'enabled':bool(album['enabled']),'uploadsOpen':bool(album['uploads_open']),'photoCount':total['n'],'usedBytes':total['used'],'quotaBytes':quota('MEMORIES_ALBUM_MB',150),'maxFileBytes':MAX_INPUT}
    def access(self,body):
        with self.db() as c:
            album=self._token_album(c,body.get('token'))
            if not album['enabled'] and not self._manager(album):raise AlbumError(410,'The organiser has paused sharing for this album.')
            v=self._visitor(c,album)
            return {'album':self._info(c,album),'joined':bool(v),'name':v['name'] if v else '', 'csrf':v['csrf'] if v else ''}
    def _new_visitor(self,c,album,name,is_host=False):
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);vid=secrets.token_hex(16)
        c.execute('DELETE FROM memory_visitors WHERE expires<?',(time.time(),))
        c.execute('INSERT INTO memory_visitors VALUES(?,?,?,?,?,?,?)',(vid,album['id'],digest(token),name,csrf,int(is_host),time.time()+7*86400))
        secure='; Secure' if os.environ.get('COOKIE_SECURE','0')=='1' else ''
        cookie=f'memories_{album["id"]}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800'+secure
        return {'album':self._info(c,album),'name':name,'csrf':csrf,'manager':is_host or self._manager(album)},cookie
    def join(self,body):
        if body.get('consent') is not True:raise AlbumError(400,'Agree to sharing photos with people who have this album link.')
        name=name_value(body.get('name'))
        with self.db(True) as c:
            album=self._token_album(c,body.get('token'))
            if not album['enabled'] and not self._manager(album):raise AlbumError(410,'The organiser has paused sharing for this album.')
            self._rate(c,'join:'+self.identity,300)
            return self._new_visitor(c,album,name)
    def host(self,body):
        with self.db(True) as c:
            self._rate(c,'host:'+self.identity,20)
            album=self._album(c,body.get('albumId'))
            if not isinstance(body.get('key'),str) or not hmac.compare_digest(album['host_token'],body['key']):raise AlbumError(403,'The private host link is invalid.')
            data,cookie=self._new_visitor(c,album,'Organiser',True)
            data['shareToken']=album['share_token'];return data,cookie
    def member(self):
        s=self.session
        if not s or s['role'] not in ['Super Organiser','Co-Organiser','Guest'] or not s['event_id']:raise AlbumError(403,'Please open your event to see its shared album.')
        with self.db() as c:
            a=c.execute('SELECT * FROM memory_albums WHERE event_id=?',(s['event_id'],)).fetchone()
            if not a:return {'album':None,'canManage':s['role']=='Super Organiser' or (s['role']=='Co-Organiser' and (s['demo_role'] or 'photos' in s['permissions']))}
            a=dict(a);data={'album':self._info(c,a),'canManage':self._manager(a),'shareUrl':self.base_url+'/memories#'+a['share_token']}
            if self._manager(a):data.update(self._host_info(c,a))
            return data
    def _host_info(self,c,album):
        url=self.base_url+'/memories#'+album['share_token'];image=io.BytesIO();qrcode.make(url,image_factory=qrcode.image.svg.SvgPathImage,box_size=6,border=4).save(image)
        data={'album':self._info(c,album),'shareUrl':url,'qrSvg':image.getvalue().decode()}
        visitor=self._visitor(c,album)
        creator=self.session and self.session['role']=='Super Organiser' and self.session['event_id']==album['event_id']
        if creator or (visitor and visitor['is_host']):data['hostUrl']=self.base_url+'/memories#host='+album['id']+'.'+album['host_token']
        return data
    def manage(self,body):
        with self.db(True) as c:
            if body.get('albumId'):
                album=self._album(c,body['albumId']);actor=self._actor(c,album,True)
                if not actor['manager']:raise AlbumError(403,'Only the organiser can manage this album.')
            else:
                s=self.session
                if not s or not s['event_id'] or not (s['role']=='Super Organiser' or (s['role']=='Co-Organiser' and (s['demo_role'] or 'photos' in s['permissions']))):raise AlbumError(403,'Only the organiser can create a shared album.')
                if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']):raise AlbumError(403,'Refresh your event before trying again.')
                c.execute('INSERT INTO memory_albums(id,event_id,share_token,host_token,created) VALUES(?,?,?,?,?) ON CONFLICT(event_id) DO NOTHING',(secrets.token_hex(16),s['event_id'],secrets.token_urlsafe(32),secrets.token_urlsafe(32),time.time()))
                album=dict(c.execute('SELECT * FROM memory_albums WHERE event_id=?',(s['event_id'],)).fetchone())
            action=body.get('action','create')
            if action=='host-rotate':
                visitor=self._visitor(c,album)
                creator=self.session and self.session['role']=='Super Organiser' and self.session['event_id']==album['event_id']
                if not creator and not (visitor and visitor['is_host']):raise AlbumError(403,'Only the event creator or private host can replace host access.')
                c.execute('UPDATE memory_albums SET host_token=? WHERE id=?',(secrets.token_urlsafe(32),album['id']))
                c.execute('DELETE FROM memory_visitors WHERE album_id=? AND is_host=1 AND id<>?',(album['id'],visitor['id'] if visitor and visitor['is_host'] else ''))
            elif action=='rotate':
                c.execute('UPDATE memory_albums SET share_token=? WHERE id=?',(secrets.token_urlsafe(32),album['id']))
                c.execute('DELETE FROM memory_visitors WHERE album_id=? AND is_host=0',(album['id'],))
            elif action in ['sharing','uploads']:
                if not isinstance(body.get('enabled'),bool):raise AlbumError(400,'Choose whether this setting is enabled.')
                column='enabled' if action=='sharing' else 'uploads_open';c.execute('UPDATE memory_albums SET '+column+'=? WHERE id=?',(int(body['enabled']),album['id']))
            elif action!='create':raise AlbumError(400,'Unknown album action.')
            album=self._album(c,album['id']);return self._host_info(c,album)
    def listing(self,album_id,before=None):
        with self.db() as c:
            album=self._album(c,album_id);actor=self._actor(c,album)
            params=[album_id];where='album_id=?'
            if before:
                try:
                    stamp,pid=before.split(':',1);stamp=float(stamp)
                    if not math.isfinite(stamp) or not re.fullmatch('[a-f0-9]{32}',pid):raise ValueError()
                except (ValueError,TypeError):raise AlbumError(400,'Invalid gallery page.')
                where+=' AND (created<? OR (created=? AND id<?))';params.extend([stamp,stamp,pid])
            photos=[dict(r) for r in c.execute('SELECT id,visitor_id,uploader,width,height,created FROM memory_photos WHERE '+where+' ORDER BY created DESC,id DESC LIMIT 31',params)]
            more=len(photos)>30;photos=photos[:30];next_page=(str(photos[-1]['created'])+':'+photos[-1]['id']) if more else None
            for p in photos:
                p['canDelete']=actor['manager'] or p['visitor_id']==actor['id'];p.pop('visitor_id',None)
                base='/api/memories/image/'+p['id']+'?'+urlencode({'album':album_id})
                p.update(url=base,thumbnail=base+'&thumb=1',download=base+'&download=1')
            return {'album':self._info(c,album),'photos':photos,'next':next_page,'name':actor['name'],'csrf':actor['csrf'],'manager':actor['manager']}
    def upload(self,body):
        album_id=body.get('albumId');request_id=body.get('requestId')
        if not isinstance(request_id,str) or not re.fullmatch('[A-Za-z0-9_-]{8,80}',request_id):raise AlbumError(400,'Invalid upload request. Please retry.')
        with self.db() as c:
            album=self._album(c,album_id);actor=self._actor(c,album,True)
            if not album['uploads_open']:raise AlbumError(403,'The organiser has paused uploads. You can still save photos.')
            old=c.execute('SELECT id FROM memory_photos WHERE album_id=? AND visitor_id=? AND request_id=?',(album_id,actor['id'],request_id)).fetchone()
            if old:return {'ok':True,'id':old['id'],'replayed':True}
        image,thumb,width,height=prepare_image(body.get('data'))
        with self.db(True) as c:
            # Serialize quotas/checks with PostgreSQL as well as SQLite BEGIN IMMEDIATE.
            if os.environ.get('DATABASE_URL'):c.execute('SELECT pg_advisory_xact_lock(823917823)')
            album=self._album(c,album_id);actor=self._actor(c,album,True)
            if not album['uploads_open']:raise AlbumError(403,'Uploads were paused. This photo was not saved.')
            old=c.execute('SELECT id FROM memory_photos WHERE album_id=? AND visitor_id=? AND request_id=?',(album_id,actor['id'],request_id)).fetchone()
            if old:return {'ok':True,'id':old['id'],'replayed':True}
            self._rate(c,'upload:'+self.identity,1000)
            size=len(image)+len(thumb);used=c.execute('SELECT coalesce(sum(bytes),0) AS used FROM memory_photos WHERE album_id=?',(album_id,)).fetchone()['used']
            total=c.execute('SELECT coalesce(sum(bytes),0) AS used FROM memory_photos').fetchone()['used']
            if used+size>quota('MEMORIES_ALBUM_MB',150) or total+size>quota('MEMORIES_TOTAL_MB',300):raise AlbumError(413,'The photo storage allowance is full. Ask the organiser to free space or increase the storage allowance.')
            pid=secrets.token_hex(16);c.execute('INSERT INTO memory_photos VALUES(?,?,?,?,?,?,?,?,?,?,?)',(pid,album_id,actor['id'],actor['name'],image,thumb,size,width,height,time.time(),request_id))
            return {'ok':True,'id':pid,'bytes':size}
    def remove(self,body):
        with self.db(True) as c:
            album=self._album(c,body.get('albumId'));actor=self._actor(c,album,True)
            p=c.execute('SELECT visitor_id FROM memory_photos WHERE id=? AND album_id=?',(body.get('photoId'),album['id'])).fetchone()
            if not p:raise AlbumError(404,'Photo not found.')
            if not actor['manager'] and p['visitor_id']!=actor['id']:raise AlbumError(403,'You can remove only your own uploads.')
            c.execute('DELETE FROM memory_photos WHERE id=? AND album_id=?',(body['photoId'],album['id']))
        return {'ok':True}
    def image(self,album_id,pid,thumbnail=False):
        with self.db() as c:
            album=self._album(c,album_id);self._actor(c,album)
            column='thumbnail' if thumbnail else 'image'
            r=c.execute('SELECT '+column+' AS content FROM memory_photos WHERE id=? AND album_id=?',(pid,album_id)).fetchone()
            if not r:raise AlbumError(404,'Photo not found.')
            return bytes(r['content'])
    def download(self,album_id,ids):
        if not isinstance(ids,list) or not 1<=len(ids)<=50 or any(not re.fullmatch('[a-f0-9]{32}',i) for i in ids):raise AlbumError(400,'Select between 1 and 50 photos per download.')
        ids=list(dict.fromkeys(ids));output=tempfile.SpooledTemporaryFile(max_size=5*1024*1024)
        try:
            with self.db() as c:
                album=self._album(c,album_id);self._actor(c,album)
                total=0
                with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
                    for pid in ids:
                        r=c.execute('SELECT image FROM memory_photos WHERE id=? AND album_id=?',(pid,album_id)).fetchone()
                        if not r:raise AlbumError(404,'A selected photo is no longer available.')
                        content=bytes(r['image']);total+=len(content)
                        if total>50*1024*1024:raise AlbumError(413,'Select fewer photos for this download (maximum 50 MB per ZIP).')
                        archive.writestr('ShaadiVerse-'+pid+'.jpg',content)
            output.seek(0);return output
        except BaseException:output.close();raise
