/* Account, multi-event, gate and live-provider workflows. */
let bootstrap={},csrfToken='',cameraStream=null,scanFrame=null;
const oldRender=render,oldSettings=settings,oldPassport=passport;
api=async function(path,body){
 const response=await fetch('/api/'+path,{method:body?'POST':'GET',credentials:'same-origin',headers:{'Content-Type':'application/json',...(csrfToken?{'X-CSRF-Token':csrfToken}:{})},...(body?{body:JSON.stringify(body)}:{})});
 let data;try{data=await response.json()}catch{throw Error('The server returned an unexpected response. Please retry.')}
 if(!response.ok){let e=Error(data.error||'The request failed.');e.status=response.status;throw e}
 if(data.csrf)csrfToken=data.csrf;return data;
};
refresh=async function({throwOnError=false}={}){
 try{
  state=await api('state');
  const role=state.user.role;
  if(!state.event.length){accountHome();return state}
  const pages={Guest:['Passport','Timeline','Celebrations'],Vendor:['Vendors','Timeline'],'Hotel Partner':['Travel & stay','Timeline'],'Finance Team':['Expenses','Timeline']};
  if(pages[role]&&!pages[role].includes(page))page=pages[role][0];
  if(role==='Super Organiser'&&['Passport'].includes(page))page='Overview';
  render();return state;
 }catch(e){if(throwOnError)throw e;if(e.status===401)login();else if(!navigator.onLine)offlineGate();else toast(e.message)}
};
login=function(){
 const demos=bootstrap.demoMode?`<div class="welcome-note">Explore with sample data. Demo sign-in never sends SMS or payments.</div><button class="primary" onclick="demo('Super Organiser')">Explore Rahul & Priya’s wedding →</button><div class="divider">TRY ANOTHER DEMO ROLE</div><div class="role-grid">${['Co-Organiser','Finance Team','Vendor','Guest','Hotel Partner'].map(r=>`<button onclick="demo('${r}')">${r}</button>`).join('')}</div><div class="divider">OR CREATE YOUR OWN CELEBRATION</div>`:'';
 $('#app').innerHTML=`<div class="login"><section class="login-art"><div class="brand" style="color:#fff1dc"><em>❋</em> ShaadiVerse</div><h1>Big celebrations.<br>Little details.<br>All together.</h1><p>Your people, your plans, and every beautiful moment in between. A little less chaos. A lot more magic.</p></section><section class="login-panel"><div class="login-box"><div class="eyebrow">Let the celebrations begin</div><h1>Your people.<br>Your happy place.</h1><p class="subtitle">Sign in with your phone to create an event or join your family.</p>${demos}<form id="account-login">${field('Your name','name','text','')}${field('Indian mobile number','phone','tel','')}<button class="primary">${bootstrap.demoMode?'Get sandbox code':'Send verification code'}</button></form>${!bootstrap.demoMode&&!bootstrap.smsReady?'<p class="welcome-note">Phone sign-in is waiting for the organiser to connect the SMS service.</p>':''}<p style="margin-top:20px;text-align:center"><button class="text-link" onclick="joinEvent()">Have an event code? Request to join →</button></p></div></section></div>`;
 $('#account-login').onsubmit=async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));try{
  let result=await api('auth/otp',{phone:data.phone});
  modal('A little code. Your own happy place.',`<p class="welcome-note">${result.sandboxCode?'Sandbox code: '+esc(result.sandboxCode)+'. No SMS was sent.':esc(result.message)}</p><form>${field('6-digit verification code','code','text','')}${formFooter('Verify & continue')}</form>`);
  $('#modal form').actionHandler=async b=>{await api('auth/verify',{...data,...b});$('#modal').close();page='Overview';await refresh()};
 }catch(e){toast(e.message)}};
 const invited=new URLSearchParams(location.search).get('event');if(invited)setTimeout(()=>invitationPreview(invited),0);
};
render=function(){
 if(!state.event?.length)return accountHome();
 for(const k of ['guests','vendors','tasks','hotels','transport','catering','joins','entries','songs','photos','gifts','members','expenses','team','messages'])state[k]??=[];
 oldRender();
 const e=state.event[0],switcher=$('.event-switch');
 switcher.setAttribute('role','button');switcher.tabIndex=0;switcher.setAttribute('aria-label','Switch or create event');switcher.onclick=eventSwitcher;switcher.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();eventSwitcher()}};
 switcher.querySelector('.avatar').textContent=e.name.split(/[&\s]+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('');switcher.querySelector(':scope > div > div').textContent=new Date(e.date+'T12:00:00').toLocaleDateString('en-IN',{month:'short',year:'numeric'}).toUpperCase();
 $('.footer span:last-child').textContent=state.mode==='sandbox'?'SANDBOX · SAMPLE DATA':'YOUR CELEBRATION';
 if(state.user.role==='Co-Organiser'&&!bootstrap.demoMode){
  const needed={Guests:'guests',Vendors:'vendors',Tasks:'tasks','Travel & stay':'hotels',Catering:'catering','Gifts & shagun':'gifts',Settings:'joins'};
  document.querySelectorAll('.sidebar .nav').forEach(n=>{let label=n.querySelectorAll('span')[1]?.textContent;if(needed[label]&&!state.user.permissions.includes(needed[label]))n.remove()});
 }
 if(['Super Organiser','Co-Organiser'].includes(state.user.role)&&(bootstrap.demoMode||state.user.role==='Super Organiser'||state.user.permissions.includes('entries'))){
  localStorage.setItem('shaadi-gate',JSON.stringify({eventId:e.id,name:e.name,scope:state.scope}));
 }
 if(new URLSearchParams(location.search).get('pass')&&['Super Organiser','Co-Organiser'].includes(state.user.role)){setTimeout(()=>scanner(new URLSearchParams(location.search).get('pass')),0);history.replaceState(null,'',location.pathname)}
};
function accountHome(){
 $('#app').innerHTML=`<div class="account-shell"><div class="brand"><em>❋</em> ShaadiVerse</div><div class="page-heading" style="margin-top:45px"><div><div class="eyebrow">WELCOME, ${esc(state.user.name)}</div><h1>A new chapter starts here.</h1><p class="subtitle">Create your celebration, or step into one you’re already part of.</p></div><button class="secondary" onclick="logout()">Sign out</button></div><div class="tiles"><section class="card tile"><div class="icon-large">✧</div><h2>Make it your own</h2><p>A wedding, a milestone, a reason to bring your people together.</p>${button('＋ Create an event','createEventForm()')}</section>${(state.events||[]).map(e=>`<section class="card tile"><div class="eyebrow">${esc(e.date)}</div><h2>${esc(e.name)}</h2><p>${esc(e.venue)}</p>${button('Open celebration',`selectEvent(${e.id})`)}</section>`).join('')}<section class="card tile"><h2>Joining the family?</h2><p>Use the event code your organiser shared. They’ll approve your request before you enter.</p>${button('Request to join','joinEvent()',true)}</section></div></div>`;
}
function eventSwitcher(){
 modal('Your celebrations',`<div class="event-options">${(state.events||[]).map(e=>`<button class="event-option" onclick="selectEvent(${e.id})"><span class="avatar">${initials(e.name)}</span><span><strong>${esc(e.name)}</strong><small>${esc(e.date)} · ${esc(e.venue)}</small></span><span>→</span></button>`).join('')}</div><div class="form-actions">${button('＋ Create a celebration','createEventForm()')}</div>`);
}
async function selectEvent(id){await api('events/select',{eventId:id});$('#modal').close();page='Overview';await refresh()}
function createEventForm(){
 if(state.user?.demo&&state.user.role!=='Super Organiser'){toast('Switch to the organiser role to create a sample event.');return}
 modal('Let’s make a little magic.',`<form>${field('Name of your event','name','text','')}${field('Date','date','date','')}${field('Venue','venue','text','')}${field('Overall budget (₹)','budget','number','0')}${field('Theme','theme','','Royal Rajasthani',['Royal Rajasthani','Pastel Beach','Boho Garden','Modern Minimal','Classic Gold'])}<p class="subtitle">${state.user?.demo?'This creates another fictional event in your private demo workspace. All demo features are available without payment.':'Start free with up to 50 guests, RSVP and your timeline.'}</p>${formFooter('Create my celebration')}</form>`);
 $('#modal form').actionHandler=async b=>{await api('events/create',b);$('#modal').close();page='Overview';await refresh();confetti();toast('Your celebration is ready. Let’s bring your people together!')};
}
joinEvent=function(code=''){
 modal('Find your celebration',`<p class="subtitle">Your organiser approves access. Phone verification is required before entering.</p><form>${field('Event code','code','text',code)}${field('Your name','name','text',state.user?.name||'')}${field('Mobile number','phone','tel',state.user?.phone||'')}${formFooter('Request to join')}</form>`);
 $('#modal form').actionHandler=async b=>{const d=await api('join',b);$('#modal').close();toast(d.message)};
};
async function invitationPreview(code){
 try{const e=await api('invitation?code='+encodeURIComponent(code));modal('You’re invited! ♡',`<div class="invitation-preview"><div class="eyebrow">WITH ALL OUR LOVE</div><h1>${esc(e.name)}</h1><p>${esc(e.date)} · ${esc(e.venue)}</p><p class="subtitle">Your place in the celebration begins with a request and a verified phone number.</p>${button('Request to join',`joinEvent(${JSON.stringify(e.code).replaceAll('"','&quot;')})`)}</div>`)}catch(e){toast(e.message)}
}
invite=function(){
 const e=state.event[0],url=location.origin+'/?event='+encodeURIComponent(e.code),message=`You’re invited to ${e.name}! ${e.date} · ${e.venue}. Join us: ${url}`;
 modal('Good news deserves to be shared.',`<p class="subtitle">Share a real invitation link. Your event’s private details stay protected.</p><div class="welcome-note">${esc(url)}</div><div class="quick-actions"><button class="secondary" id="copy-invitation">Copy invitation</button><a class="primary" target="_blank" rel="noopener" href="https://wa.me/?text=${encodeURIComponent(message)}">Share on WhatsApp ↗</a></div><p class="subtitle" style="margin-top:20px">Event code: ${esc(e.code)}. Guests still need verified phone access or organiser approval.</p>`);$('#copy-invitation').onclick=()=>copyText(message);
};
approveJoin=async function(id){await api('joins/approve',{id});await refresh();toast('Approved. Your guest can now verify their phone and sign in.')};
regenerate=async function(){await api('save',{kind:'event',item:state.event[0],regenerateCode:true});await refresh();toast('A fresh invitation code is ready. Old invitation links no longer work.')};
settings=function(){
 const e=state.event[0],owner=state.user.role==='Super Organiser';
 return heading('Make this celebration yours.','Your people, permissions and connected services.',owner?button('Edit celebration','editEvent()'):'')+`<div class="tiles"><section class="card tile"><h2>Event invitations</h2><p>Event code: <strong>${esc(e.code)}</strong></p>${button('Share invitation','invite()',true)}${owner?button('Regenerate code','regenerate()',true):''}</section><section class="card tile"><h2>Pending requests</h2>${state.joins.filter(j=>j.status==='Pending').map(j=>`<p>${esc(j.name)} · ${esc(j.phone)}</p>${button('Approve',`approveJoin(${j.id})`,true)}`).join('')||'<p>No pending requests. The guest list is feeling peaceful.</p>'}</section>${owner?`<section class="card tile"><h2>Your trusted team</h2><p>Give each person just the access they need. Finance is capped at five members.</p>${button('＋ Add team member','teamForm()',true)}${state.team.map(m=>`<div class="team-row"><strong>${esc(m.phone)}</strong><span>${esc(m.role)}${m.revoked?' · Revoked':''}</span>${m.phone!==state.user.phone&&!m.revoked?`<button class="text-link revoke-member" data-phone="${esc(m.phone)}" onclick="revokeMember(this.dataset.phone)">Revoke access</button>`:''}</div>`).join('')}</section>`:''}<section class="card tile"><h2>Connected services</h2>${[['Phone OTP','sms'],['WhatsApp Business','whatsapp'],['Razorpay checkout','payments']].map(([label,key])=>`<div class="budget-values"><span>${label}</span><span class="badge ${state.services[key]?'green':''}">${state.services[key]?'Configured':'Setup needed'}</span></div>`).join('')}<p>${bootstrap.demoMode?'Demo mode is enabled. Live payments and WhatsApp dispatch are disabled.':'Only verified accounts may enter your events. Credentials are configured securely in hosting settings.'}</p></section><section class="card tile"><h2>Guest access</h2><p>Revoking a guest blocks event access immediately and replaces their entry-pass token.</p>${state.guests.map(g=>`<div class="team-row"><strong>${esc(g.name)}</strong>${owner?`<button class="text-link" data-phone="${esc(g.phone)}" onclick="revokeMember(this.dataset.phone)">Revoke guest access</button>`:''}</div>`).join('')}</section>${owner?`<section class="card tile"><h2>Invitation delivery</h2><p>Only guests who explicitly opt in can receive WhatsApp templates.</p>${button('Select invitations','broadcast()',true)}${state.messages.some(m=>m.status==='Pending')?button('Send queued invitations','dispatchInvitations()'):''}${state.messages.map(m=>`<p>#${m.id} · ${esc(m.status)}${m.error?' · '+esc(m.error):''}</p>`).join('')}</section>`:''}</div>`;
};
function teamForm(){
 const options=['Finance Team','Co-Organiser','Vendor','Hotel Partner'];
 modal('Good people. Just the right access.',`<form>${field('Name','name')}${field('Phone number','phone','tel')}${field('Role','role','','Finance Team',options)}<label>Linked vendor or hotel<select name="entityId"><option value="">Not needed for finance / co-organiser</option>${state.vendors.map(v=>`<option value="${v.id}">Vendor · ${esc(v.name)}</option>`).join('')}${state.hotels.map(h=>`<option value="${h.id}">Hotel · ${esc(h.name)}</option>`).join('')}</select></label><fieldset><legend>Co-organiser permissions</legend><div class="permission-grid">${['guests','timeline','tasks','vendors','hotels','transport','catering','announcements','songs','gifts','polls','joins','entries'].map(k=>`<label><span><input type="checkbox" name="permission" value="${k}"> ${k}</span></label>`).join('')}</div></fieldset>${formFooter('Grant event access')}</form>`);
 $('#modal form').actionHandler=async b=>{let f=$('#modal form'),permissions=[...f.querySelectorAll('[name=permission]:checked')].map(x=>x.value);await save('members',{name:b.name,phone:b.phone,role:b.role,entityId:b.entityId?Number(b.entityId):null,permissions});$('#modal').close();toast('Access granted. They must verify their own phone to sign in.')};
}
async function revokeMember(phone){
 modal('Revoke event access?',`<p class="subtitle">This blocks this member’s event access and invalidates any existing guest pass. Other events stay unchanged.</p><div class="form-actions"><button class="secondary" onclick="document.querySelector('dialog').close()">Cancel</button><button class="primary" id="confirm-revoke">Revoke access</button></div>`);
 $('#confirm-revoke').onclick=async()=>{await api('members/revoke',{phone});$('#modal').close();await refresh();toast('Access revoked.')};
}
passport=function(){
 const e=state.event[0],g=state.guests[0];
 return heading('Your wedding passport.','Your invitation, your outfits, your very own place in the celebration.')+`<section class="hero"><div class="hero-art"></div><div class="hero-copy"><div class="eyebrow">YOU’RE PART OF OUR STORY</div><h2>${esc(e.name)} ♡</h2><p>${esc(e.date)} · ${esc(e.venue)}</p><p>Welcome, ${esc(g?.name||state.user.name)}</p></div></section><div class="tiles"><section class="card tile"><h2>Save you a seat?</h2><p>Your RSVP: <strong>${esc(g?.status||'Not registered')}</strong></p><form id="rsvp-form"><label><span><input type="checkbox" name="consent" required> I agree to use of my details for event coordination.</span></label><label><span><input type="checkbox" name="whatsappConsent" ${g?.whatsappConsent?'checked':''}> I’d like invitations and RSVP updates on WhatsApp. Optional.</span></label><label>Plus-ones <input type="number" name="plusOnes" min="0" max="${g?.plusOnes||0}" value="${g?.attendingPlusOnes||0}"></label><div class="quick-actions">${['Confirmed','Maybe','Declined'].map(s=>`<button type="submit" name="status" value="${s}">${s==='Confirmed'?'Yes, with bells on!':s}</button>`).join('')}</div></form></section><section class="card tile"><h2>Dress for the memories</h2>${state.timeline.map(t=>`<p><strong>${esc(t.name)}</strong><br>${esc(t.dress)} · ${esc(t.date)}</p>`).join('')}</section><section class="card tile"><h2>Your personal entry pass</h2><p>A signed pass, just for you. Keep it private; it can only be checked in once.</p>${g&&['Confirmed','Checked In'].includes(g.status)?button('Show my QR pass',`showPass(${g.id})`):'<p>Confirm your RSVP to receive your pass.</p>'}${button('Share a travel update','guestTravel()',true)}<p>Current milestone: ${esc(g?.travel||'Not updated')}</p></section></div>`;
};
// The existing view installs an RSVP handler; replace it after its deferred setup.
const originalView=view;
view=function(){const html=originalView();if(page==='Passport')setTimeout(()=>{const f=$('#rsvp-form');if(!f)return;f.onsubmit=async ev=>{ev.preventDefault();try{const d=new FormData(f);await api('rsvp',{status:ev.submitter.value,plusOnes:Number(d.get('plusOnes')),consent:d.has('consent'),whatsappConsent:d.has('whatsappConsent')});await refresh();if(ev.submitter.value==='Confirmed')confetti();toast('Your RSVP is saved. Let the countdown begin!')}catch(e){toast(e.message)}}},0);return html};
async function showPass(id){
 const pass=await api('pass?guestId='+id);
 modal('Your place in the celebration.',`<div class="pass-card"><h2>${esc(pass.name)}</h2><div id="pass-image"></div><p>Plus-ones confirmed: ${pass.plusOnes}</p><p class="subtitle">Show this QR at the gate. Don’t share your personal pass.</p><button class="secondary" id="download-pass">Download pass</button></div>`);
 // Trusted SVG is generated on the server by the pinned QR library, not user input.
 const image=document.createElement('img');const url=URL.createObjectURL(new Blob([pass.qrSvg],{type:'image/svg+xml'}));image.src=url;image.alt='Personal entry QR code for '+pass.name;image.width=260;image.height=260;$('#pass-image').append(image);
 $('#download-pass').onclick=()=>{const a=document.createElement('a');a.href=url;a.download='shaadi-entry-pass.svg';a.click()};$('#modal').addEventListener('close',()=>URL.revokeObjectURL(url),{once:true});
}
function gateQueue(){try{return JSON.parse(localStorage.getItem('shaadi-entry-queue')||'[]')}catch{return []}}
function saveQueue(items){localStorage.setItem('shaadi-entry-queue',JSON.stringify(items));}
function queueScope(){try{return JSON.parse(localStorage.getItem('shaadi-gate')||'null')}catch{return null}}
scanner=function(initial=''){
 modal('A warm welcome starts here.',`<p class="subtitle">Scan a signed pass or paste its code. Offline scans are pending until the server confirms them.</p><video id="gate-camera" playsinline muted hidden></video><canvas id="gate-canvas" hidden></canvas><div class="quick-actions" style="margin:15px 0"><button class="secondary" id="start-camera">Use camera</button><button class="secondary" onclick="syncGateQueue()">Sync pending scans (${gateQueue().filter(x=>x.scope===(state.scope||queueScope()?.scope)).length})</button></div><form>${field('QR pass contents','token','text',initial)}${field('Plus-ones arriving now','plusOnes','number','0')}${formFooter('Check entry')}</form><div id="scan-result" aria-live="polite"></div>`);
 $('#modal form').actionHandler=checkGate;
 $('#start-camera').onclick=startCamera;
 $('#modal').addEventListener('close',stopCamera,{once:true});
};
function stopCamera(){if(cameraStream)cameraStream.getTracks().forEach(t=>t.stop());cameraStream=null;if(scanFrame)cancelAnimationFrame(scanFrame);scanFrame=null;}
async function startCamera(){
 try{
  if(!navigator.mediaDevices?.getUserMedia)throw Error('Camera unavailable. Use HTTPS and allow camera access, or paste the pass contents.');
  cameraStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});const video=$('#gate-camera');video.hidden=false;video.srcObject=cameraStream;await video.play();
  const canvas=$('#gate-canvas'),ctx=canvas.getContext('2d',{willReadFrequently:true});
  const scan=()=>{
   if(!cameraStream||!$('#gate-camera'))return;
   if(video.readyState>=2){canvas.width=video.videoWidth;canvas.height=video.videoHeight;ctx.drawImage(video,0,0);const pixels=ctx.getImageData(0,0,canvas.width,canvas.height);const code=jsQR(pixels.data,pixels.width,pixels.height);
    if(code){$('#modal input[name=token]').value=code.data;stopCamera();video.hidden=true;toast('Pass captured. Confirm plus-ones, then check entry.');return}}
   scanFrame=requestAnimationFrame(scan);
  };scan();
 }catch(e){stopCamera();toast(e.message)}
}
async function checkGate(data){
 const scope=state.scope||queueScope()?.scope,request={token:data.token,plusOnes:Number(data.plusOnes),requestId:crypto.randomUUID()};
 try{if(!navigator.onLine)throw TypeError('Offline');const result=await api('checkin',request);$('#scan-result').innerHTML=`<div class="gate-result allowed">✓ Welcome, ${esc(result.name)}!<small>Entry confirmed by the server.</small></div>`;$('#modal input[name=token]').value='';}
 catch(e){if(e instanceof TypeError){if(!scope)return toast('Sign in online before using the offline gate queue.');let q=gateQueue();if(q.length>=100)return toast('Sync your pending scans before adding more.');if(q.some(x=>x.scope===scope&&x.token===request.token)){ $('#scan-result').innerHTML='<div class="gate-result denied">Already pending on this device. Wait for sync.</div>';return}q.push({...request,scope,queuedAt:Date.now()});saveQueue(q);$('#scan-result').innerHTML='<div class="gate-result pending">Pending verification<small>Offline scan saved. This is not an entry approval. Duplicates across devices are checked when synced.</small></div>';}
 else $('#scan-result').innerHTML=`<div class="gate-result denied">✕ ${esc(e.message)}</div>`;}
}
async function syncGateQueue(){
 if(!navigator.onLine)return toast('Reconnect to the internet to verify pending scans.');
 if(!state.scope){await refresh();if(!state.scope)return toast('Sign in to the event before syncing.');}
 let queue=gateQueue(),pending=queue.filter(x=>x.scope===state.scope),results=[];
 for(const item of pending){try{const r=await api('checkin',item);results.push('✓ '+r.name);queue=queue.filter(x=>x.requestId!==item.requestId)}catch(e){if(e.status&&e.status!==401&&e.status!==403){results.push('✕ '+e.message);queue=queue.filter(x=>x.requestId!==item.requestId)}else{toast(e.message);break}}saveQueue(queue);}
 if($('#scan-result'))$('#scan-result').innerHTML=`<div class="sync-results">${results.map(r=>`<p>${esc(r)}</p>`).join('')||'<p>No pending scans for this event.</p>'}</div>`;
 toast(results.length+' pending scans processed. Review each result.');
}
function offlineGate(){
 const gate=queueScope();if(!gate)return toast('You’re offline. Reconnect to sign in.');
 $('#app').innerHTML=`<div class="account-shell"><div class="brand"><em>❋</em> ShaadiVerse</div><h1 style="margin-top:45px">The gate, on the go.</h1><h2>${esc(gate.name)}</h2><p class="welcome-note">Offline mode. Scans are queued for verification; entry is not approved until you reconnect.</p>${button('Queue a QR scan','scanner()')}${button('Reconnect & sign in','location.reload()',true)}</div>`;
}
broadcast=function(){
 const demo=bootstrap.demoMode;
 modal('Send a little celebration.',`<p class="welcome-note">${demo?'Sandbox preview. No messages will be sent.':'Uses your approved WhatsApp invitation template. Only opted-in guests can be selected.'}</p><form><div class="recipient-list">${state.guests.filter(g=>g.whatsappConsent||demo).map(g=>`<label><span><input type="checkbox" name="guest" value="${g.id}"> ${esc(g.name)}</span></label>`).join('')||'<p class="subtitle">No opted-in guests yet. Guests can opt in when they RSVP.</p>'}</div>${formFooter(demo?'Preview sandbox invitation':'Queue selected invitations')}</form>`);
 $('#modal form').actionHandler=async()=>{const ids=[...$('#modal').querySelectorAll('[name=guest]:checked')].map(x=>Number(x.value));const d=await api('whatsapp',{guestIds:ids});$('#modal').close();toast(d.message);await refresh()};
};
async function dispatchInvitations(){
 modal('Send queued invitations?',`<p class="subtitle">This sends up to 20 pending invitations through your WhatsApp Business account. Provider messaging charges may apply.</p><div class="form-actions"><button class="secondary" onclick="document.querySelector('dialog').close()">Cancel</button><button class="primary" id="send-confirmed">Send invitations</button></div>`);
 $('#send-confirmed').onclick=async()=>{const r=await api('messages/dispatch',{});$('#modal').close();toast(r.message);await refresh()};
}
pricing=function(){
 const e=state.event[0];modal('Make room for every moment.',`<div class="plan-card"><div class="eyebrow">YOUR CURRENT PLAN · ${esc(e.plan)}</div><h2>Free</h2><p>One event · 50 guests · RSVP · Timeline · Invitations</p></div><div class="plan-card"><h2>Event Pass</h2><p class="plan-price">₹2,999 <small>one-time per event</small></p><p>Unlimited guests · Expense tracker · Vendor management · QR entry</p>${state.user.role==='Super Organiser'?button(e.plan==='Event Pass'?'Already on Event Pass':bootstrap.demoMode?'Payments disabled in demo':'Upgrade with Razorpay',e.plan==='Event Pass'||bootstrap.demoMode?"toast('Your demo plan is ready to explore.')":"checkout('Event Pass')"):'<p>Only your organiser can purchase an event plan.</p>'}</div><p class="subtitle">Planner Pro subscriptions are coming later. Guests always retain access to their event information.</p>${button('View payment receipt','paymentReceipt()',true)}`);
};
async function checkout(plan){
 if(!state.services.payments)return toast('Razorpay is not connected. Ask your organiser to finish secure payment setup.');
 const order=await api('payments/order',{plan});
 if(!window.Razorpay)await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://checkout.razorpay.com/v1/checkout.js';script.onload=resolve;script.onerror=()=>reject(Error('Unable to load secure checkout. Please retry.'));document.head.append(script)});
 const widget=new Razorpay({key:order.keyId,order_id:order.orderId,amount:order.amount,currency:order.currency,name:order.name,description:order.plan,prefill:{name:state.user.name,contact:'+91'+state.user.phone},theme:{color:'#7e3846'},handler:async result=>{try{await api('payments/verify',result);$('#modal').close();await refresh();confetti();toast('Payment verified. Your Event Pass is active!')}catch(e){toast(e.message+' Your plan will activate when a matching captured payment is verified.')}}});widget.open();
}
async function paymentReceipt(){const r=await api('invoice');modal('Your payment receipt.',`<p>Receipt: ${esc(r.receipt.id)}</p><p>Payment: ${esc(r.receipt.payment_id)}</p><p>${esc(r.receipt.plan)} · ${money(r.receipt.amount/100)}</p><p>${new Date(r.receipt.created*1000).toLocaleString()}</p><p class="subtitle">${esc(r.note)}</p>${button('Print receipt','window.print()',true)}`)}
logout=async function(){await api('auth/logout',{});csrfToken='';state={};stopCamera();localStorage.removeItem('shaadi-gate');saveQueue([]);login()};
async function boot(){
 try{bootstrap=await api('bootstrap');await refresh();if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});}catch(e){if(!navigator.onLine)offlineGate();else toast('Unable to connect. Please refresh the page.')}
}
