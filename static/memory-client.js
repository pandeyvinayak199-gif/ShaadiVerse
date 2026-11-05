const root=document.querySelector('#memory-app'),viewer=document.querySelector('#photo-viewer');
const m={token:'',album:null,csrf:'',photos:[],next:null,name:'',manager:false,hostInfo:null,selected:new Set(),uploading:false,failed:[],loadedPages:0};
const safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function notify(message){const el=document.querySelector('#album-message');el.textContent=message;el.style.display='block';clearTimeout(window.messageTimer);window.messageTimer=setTimeout(()=>el.style.display='none',4500)}
async function call(path,body){
 const response=await fetch('/api/memories/'+path,{method:body?'POST':'GET',credentials:'same-origin',headers:{'Content-Type':'application/json',...(m.csrf?{'X-Memories-CSRF':m.csrf}:{})},...(body?{body:JSON.stringify(body)}:{})});
 let data;try{data=await response.json()}catch{throw Error('The server could not complete this request. Please retry.')}
 if(!response.ok){const error=Error(data.error||'Unable to open this album.');error.status=response.status;throw error}return data;
}
function unavailable(message){root.innerHTML=`<section class="join-card"><span class="bloom">❋</span><h1>A little pause in the memories.</h1><p class="notice error">${safe(message)}</p><p class="subtle">Ask the organiser for the current QR or album link. Your event’s guest list and finances are never available through this album.</p><button onclick="location.reload()">Try again</button></section>`}
async function start(){
 let fragment;try{fragment=decodeURIComponent(location.hash.slice(1))}catch{return unavailable('This album link is invalid. Ask the organiser for the current QR.');}
 if(!fragment)return unavailable('Scan the event’s Memories QR or open the shared album link to begin.');
 try{
  if(fragment.startsWith('host=')){
   const pair=fragment.slice(5).split('.');if(pair.length!==2)throw Error('This private host link is invalid.');
   const data=await call('host',{albumId:pair[0],key:pair[1]});m.album=data.album;m.name=data.name;m.csrf=data.csrf;m.token=data.shareToken;await openGallery();
  }else{
   m.token=fragment;const data=await call('access',{token:m.token});m.album=data.album;
   if(data.joined){m.name=data.name;m.csrf=data.csrf;await openGallery()}else joinForm();
  }
 }catch(e){unavailable(e instanceof TypeError?'You’re offline. Reconnect to open the shared photo album.':e.message)}
}
function joinForm(){
 root.innerHTML=`<section class="join-card"><span class="bloom">❋</span><div class="eyebrow">YOU WERE THERE. SHARE THE MAGIC.</div><h1>${safe(m.album.name)}</h1><p class="subtle">${safe(m.album.date)} · ${m.album.photoCount} photos shared</p><p>All those little moments, in one happy place.</p><div class="notice">Anyone with this album’s QR or link can view, upload and download its photos. Your name will appear beside your uploads; names are self-entered, not verified identities.</div><form class="join-form" id="join-form"><label>Your name<input name="name" maxlength="80" autocomplete="name" required placeholder="What should we call you?"></label><label class="consent"><input type="checkbox" name="consent" required><span>I agree to share my name and photos with people who have this album link. I’ll upload only photos I have permission to share.</span></label><button class="primary">Enter the Memories album →</button><p id="join-error" class="subtle" role="alert"></p></form><p class="subtle">No app install, event account or phone OTP required.</p></section>`;
 document.querySelector('#join-form').onsubmit=async event=>{event.preventDefault();const form=event.target,button=form.querySelector('button');button.disabled=true;try{const fields=new FormData(form),data=await call('join',{token:m.token,name:fields.get('name'),consent:fields.has('consent')});m.name=data.name;m.csrf=data.csrf;await openGallery()}catch(e){document.querySelector('#join-error').textContent=e.message;button.disabled=false}};
}
function usageText(album){return 'JPEG, PNG, WebP and HEIC · up to 15 MB per submitted file · '+(album.usedBytes/1024/1024).toFixed(1)+' of '+Math.round(album.quotaBytes/1024/1024)+' MB album allowance used. No fixed per-person photo count; storage and fair-use limits apply.'}
function renderAlbum(){
 const a=m.album;
 root.innerHTML=`<section class="hero"><div class="eyebrow">A LITTLE SCAN. A LOT OF MEMORIES.</div><div class="hero-top"><div><h1>${safe(a.name)}</h1><p class="subtle">${safe(a.date)} · Sharing as <strong>${safe(m.name)}</strong></p></div><div class="actions"><button id="refresh-album">↻ Refresh album</button><button id="copy-album">Copy shared album link</button><button id="browse-photos">Browse photos ↓</button></div></div><p class="subtle">Everyone here can share photos and save their favourites. Keep the link within your celebration.</p></section>${m.manager?'<section id="host-controls" class="owner-panel"><p class="subtle">Loading organiser controls…</p></section>':''}<section class="upload-box"><h2>Every camera has a different story.</h2><p class="subtle">Choose multiple pictures at once, and add more whenever you like. Photos are optimised to 2560 px for sharing and location metadata is removed; keep your originals.</p>${a.uploadsOpen?`<div class="upload-row"><label>Choose photos<input id="photo-files" type="file" multiple accept="image/jpeg,image/png,image/webp,image/heic,image/heif"></label><button class="primary" id="upload-photos">Upload selected photos</button></div>`:'<p class="notice">The organiser has paused uploads. You can still save photos from the gallery.</p>'}<p class="subtle" id="album-usage">${usageText(a)}</p><div id="upload-status" class="upload-status" role="status" aria-live="polite"></div><button id="retry-uploads" hidden>Retry unsaved photos</button></section><div class="gallery-bar"><h2 id="photo-count">${a.photoCount} ${a.photoCount===1?'photo':'photos'} shared</h2><div class="actions"><span class="selection-counter" id="selection-count"></span><button id="download-selected" disabled>Save selected as ZIP</button></div></div><section class="photo-grid" id="photo-grid"></section><div class="more"><button id="load-more" hidden>More memories ↓</button></div><footer class="memory-footer">Made for every perspective. ♡ ShaadiVerse<br>This shared album gives access to photos only, never guest lists or event finances.</footer>`;
 document.querySelector('#refresh-album').onclick=()=>refreshGallery().catch(e=>notify(e.message));
 document.querySelector('#copy-album').onclick=()=>copySharedLink();
 document.querySelector('#browse-photos').onclick=()=>document.querySelector('#photo-grid').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
 document.querySelector('#upload-photos')?.addEventListener('click',()=>{const files=[...document.querySelector('#photo-files').files];if(!files.length)return notify('Choose at least one photo first.');uploadJobs(files.map(file=>({file,requestId:crypto.randomUUID()})))});
 document.querySelector('#retry-uploads').onclick=()=>uploadJobs([...m.failed]);
 document.querySelector('#download-selected').onclick=()=>{if(m.selected.size>50)return notify('Select up to 50 photos per ZIP. You can download more in another batch.');downloadLink('/api/memories/download?album='+m.album.id+'&ids='+[...m.selected].join(','),'ShaadiVerse-memories.zip')};
 document.querySelector('#load-more').onclick=()=>refreshGallery(true).catch(e=>notify(e.message));renderPhotos();if(m.manager)loadHostControls();
}
async function openGallery(){const data=await call('album?album='+m.album.id);applyGallery(data,false);renderAlbum()}
function applyGallery(data,append){m.album=data.album;m.csrf=data.csrf;m.name=data.name;m.manager=data.manager;m.next=data.next;m.photos=append?[...new Map([...m.photos,...data.photos].map(p=>[p.id,p])).values()]:data.photos;m.loadedPages=append?m.loadedPages+1:1;}
async function refreshGallery(append=false){
 const oldUploads=m.album.uploadsOpen,oldEnabled=m.album.enabled,previous=m.photos.map(p=>p.id+':'+p.canDelete).join(',');const before=append&&m.next?'&before='+encodeURIComponent(m.next):'';let data;try{data=await call('album?album='+m.album.id+before)}catch(e){if([401,403,410].includes(e.status)){m.closed=true;unavailable(e.message)}throw e}applyGallery(data,append);if((oldUploads!==m.album.uploadsOpen||oldEnabled!==m.album.enabled)&&!m.uploading)renderAlbum();else if(append||previous!==m.photos.map(p=>p.id+':'+p.canDelete).join(','))renderPhotos();const count=document.querySelector('#photo-count');if(count)count.textContent=m.album.photoCount+' '+(m.album.photoCount===1?'photo':'photos')+' shared';const usage=document.querySelector('#album-usage');if(usage)usage.textContent=usageText(m.album);
}
function renderPhotos(){
 const grid=document.querySelector('#photo-grid');if(!grid)return;
 grid.innerHTML=m.photos.map(photo=>`<article class="photo-card"><button class="photo-open" data-open="${photo.id}" aria-label="View photo shared by ${safe(photo.uploader)}"><img src="${safe(photo.thumbnail)}" alt="Shared photo by ${safe(photo.uploader)}" loading="lazy" decoding="async"></button><div class="photo-meta"><strong>${safe(photo.uploader)}</strong><small>${new Date(photo.created*1000).toLocaleString()}</small><div class="photo-actions"><label class="select-photo"><input type="checkbox" data-select="${photo.id}" ${m.selected.has(photo.id)?'checked':''}> Select</label><a class="button" href="${safe(photo.download)}" download>Save photo ↓</a></div></div></article>`).join('')||'<div class="empty"><span>▧</span>No photos yet. Be the first to share a little magic.</div>';
 grid.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>viewPhoto(b.dataset.open));grid.querySelectorAll('[data-select]').forEach(input=>input.onchange=()=>{if(input.checked)m.selected.add(input.dataset.select);else m.selected.delete(input.dataset.select);updateSelection()});
 document.querySelector('#load-more').hidden=!m.next;updateSelection();
}
function updateSelection(){document.querySelector('#selection-count').textContent=m.selected.size?m.selected.size+' selected':'';document.querySelector('#download-selected').disabled=!m.selected.size}
function viewPhoto(id){
 const photo=m.photos.find(p=>p.id===id);if(!photo)return;
 viewer.innerHTML=`<div class="viewer-head"><h3>Shared by ${safe(photo.uploader)}</h3><button id="close-photo" aria-label="Close photo">✕</button></div><img class="viewer-image" src="${safe(photo.url)}" alt="Photo shared by ${safe(photo.uploader)}"><div class="viewer-bottom"><a class="button primary" href="${safe(photo.download)}" download>Save this photo ↓</a>${photo.canDelete?'<button id="remove-photo">Remove photo</button>':''}</div><p class="subtle">Your browser may save downloads to Files / Downloads. On iPhone, long-press the opened photo to save it to Photos.</p>`;viewer.showModal();document.querySelector('#close-photo').onclick=()=>viewer.close();document.querySelector('#remove-photo')?.addEventListener('click',async()=>{if(!confirm('Remove this photo from the shared album? This cannot be undone.'))return;try{await call('remove',{albumId:m.album.id,photoId:id});m.selected.delete(id);viewer.close();await refreshGallery();notify('Photo removed.')}catch(e){notify(e.message)}});
}
function downloadLink(url,name){const a=document.createElement('a');a.href=url;a.download=name;a.click()}
async function optimisedFile(file){
 try{
  const url=URL.createObjectURL(file);try{
   const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url});
   const scale=Math.min(1,2560/image.naturalWidth,2560/image.naturalHeight),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.naturalWidth*scale));canvas.height=Math.max(1,Math.round(image.naturalHeight*scale));const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);
   const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.9));if(blob)return blob;
  }finally{URL.revokeObjectURL(url)}
 }catch{}
 return file; // HEIC can be decoded by the server if this browser cannot preview it.
}
async function asBase64(blob){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=()=>reject(Error('This photo could not be read.'));r.readAsDataURL(blob)})}
async function uploadJobs(jobs){
 if(m.uploading||!jobs.length)return;m.uploading=true;const button=document.querySelector('#upload-photos'),input=document.querySelector('#photo-files'),retry=document.querySelector('#retry-uploads'),status=document.querySelector('#upload-status');if(button)button.disabled=true;if(input)input.disabled=true;retry.hidden=true;
 const failedIds=new Set(jobs.map(j=>j.requestId));m.failed=m.failed.filter(j=>!failedIds.has(j.requestId));let saved=0,processed=0;const outcomes=[];
 try{
  for(let index=0;index<jobs.length;index++){
   const job=jobs[index];status.textContent=`Uploading ${index+1} of ${jobs.length}: ${job.file.name}…`;
   try{
    const blob=await optimisedFile(job.file);if(blob.size>m.album.maxFileBytes)throw Error('This photo is too large. Choose a smaller version.');
    const payload={albumId:m.album.id,data:await asBase64(blob),requestId:job.requestId};
    for(let attempt=0;;attempt++){try{await call('upload',payload);break}catch(e){if(e.status!==503||attempt>=2)throw e;await new Promise(resolve=>setTimeout(resolve,500*(attempt+1)+Math.random()*500))}}saved++;outcomes.push({name:job.file.name,ok:true});
   }catch(e){m.failed.push(job);outcomes.push({name:job.file.name,error:e.message});if(e.status===401||e.status===403||e.status===410||(e.status===413&&e.message.includes('allowance'))){m.failed.push(...jobs.slice(index+1));break}}
   processed++;
  }
  status.innerHTML=`<strong>Saved ${saved} of ${jobs.length} selected photos.</strong>${saved!==jobs.length?'<p>Unsaved photos are kept in this page’s retry queue. Keep the page open if you want to retry.</p>':''}<ul>${outcomes.map(o=>`<li class="${o.ok?'saved':'failed'}">${safe(o.name)} · ${o.ok?'Saved':safe(o.error)}</li>`).join('')}</ul>`;
  try{await refreshGallery()}catch(e){notify('Some photos may have saved. Reconnect and refresh to confirm.');}
 }finally{m.uploading=false;if(button)button.disabled=false;if(input){input.disabled=false;input.value=''}retry.hidden=!m.failed.length;retry.textContent='Retry '+m.failed.length+' unsaved '+(m.failed.length===1?'photo':'photos')}
}
async function copySharedLink(){const url=m.hostInfo?.shareUrl||location.origin+'/memories#'+m.token;try{await navigator.clipboard.writeText(url);notify('Shared album link copied.')}catch{notify('Copy the original QR link shared by your organiser.')}}
async function loadHostControls(){
 try{
  const data=await call('manage',{albumId:m.album.id,action:'create'});m.hostInfo=data;const target=document.querySelector('#host-controls');if(!target)return;
  target.innerHTML=`<details><summary>Organiser controls</summary><p class="subtle">You can manage shared access and remove photos. Keep the private host link separate from the guest QR.</p><div class="actions"><button data-action="uploads">${data.album.uploadsOpen?'Pause uploads':'Resume uploads'}</button><button data-action="sharing">${data.album.enabled?'Pause shared access':'Resume shared access'}</button><button data-action="rotate">Replace shared link</button>${data.hostUrl?'<button id="copy-host">Copy private host link</button>':''}</div><p class="notice">${data.album.enabled?'Shared access is open.':'Shared access is paused. Only the organiser can see this view.'} Your private host link grants organiser control. Never print it or share it with guests.</p></details>`;
  target.querySelectorAll('[data-action]').forEach(b=>b.onclick=async()=>{const action=b.dataset.action;if(action==='rotate'&&!confirm('Replace the shared QR/link? Existing guest sessions will stop working; photos and the private host link stay unchanged.'))return;try{const next=await call('manage',{albumId:m.album.id,action,enabled:action==='uploads'?!m.album.uploadsOpen:!m.album.enabled});m.album=next.album;m.hostInfo=next;await openGallery();notify(action==='rotate'?'New shared link ready. Copy and share the updated link.':'Album settings updated.')}catch(e){notify(e.message)}});
  if(document.querySelector('#copy-host'))document.querySelector('#copy-host').onclick=async()=>{try{await navigator.clipboard.writeText(data.hostUrl);notify('Private host link copied. Keep it secret.')}catch{notify('Use the private host link provided in your event’s Memories screen.')}};
 }catch(e){const target=document.querySelector('#host-controls');if(target)target.textContent=e.message}
}
window.addEventListener('unhandledrejection',event=>{notify(event.reason?.message||'Please retry.');event.preventDefault()});
window.addEventListener('beforeunload',event=>{if(m.uploading){event.preventDefault();event.returnValue=''}});
setInterval(()=>{if(m.album&&!m.closed&&!document.hidden&&!m.uploading&&!viewer.open&&!m.selected.size&&m.loadedPages===1)refreshGallery().catch(()=>{})},20000);
start();
