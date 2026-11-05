/* Release 1.0: investor demonstration and consent-based concept pilot. */
const featureLogin=login,featureRender=render,featureSettings=settings;
login=function(){
 if(!bootstrap.demoMode)return featureLogin();
 $('#app').innerHTML=`<div class="login investor-login"><section class="login-art"><div class="brand" style="color:#fff1dc"><em>❋</em> ShaadiVerse</div><div class="eyebrow" style="color:#e7c78d;margin-top:48px">LESS CHAOS. MORE CELEBRATION.</div><h1 style="margin-top:18px">Big celebrations.<br>Beautifully<br>in sync.</h1><p>One joyful home for your people, plans, and every little detail. Built for weddings. Made for togetherness.</p><div class="demo-trust"><span>♧ Guests & RSVP</span><span>▦ Personal entry passes</span><span>♡ Every family detail</span></div></section><section class="login-panel"><div class="login-box"><div class="eyebrow">INVESTOR & PILOT EDITION · 1.0</div><h1>A front-row seat<br>to the celebration.</h1><p class="subtitle">Step inside Rahul & Priya’s wedding. Your sample workspace is private to this browser session.</p><div class="welcome-note">Interactive demonstration · No messages sent · No payments charged. Use fictional details during the pilot.</div><button class="primary" onclick="demo('Super Organiser')">Explore Rahul & Priya’s wedding →</button><button class="secondary" style="width:100%;margin-top:12px" id="start-walkthrough" onclick="startPresentation()">✧ Take the five-minute walkthrough</button><p id="walkthrough-status" class="subtitle" role="status" aria-live="polite" hidden></p><div class="divider">SEE IT THROUGH THEIR EYES</div><div class="role-grid">${['Guest','Co-Organiser','Finance Team','Vendor','Hotel Partner'].map(r=>`<button onclick="demo('${r}')">${r}</button>`).join('')}</div><p class="subtitle" style="margin-top:24px">Try the experience, then share your thoughts in the pilot survey. Responses are research feedback, not customer traction.</p>${bootstrap.sandboxOtpAvailable?'<details style="margin-top:20px"><summary>Private developer phone sandbox</summary><button class="text-link" onclick="featureLogin()">Open developer sign-in</button></details>':''}</div></section></div>`;
};
render=function(){
 featureRender();
 if(!state.event?.length)return;
 const sidebar=$('.sidebar .side-footer');
 if(sidebar){
  const panel=document.createElement('div');panel.className='pilot-actions';
  panel.innerHTML=`<button class="secondary" onclick="feedbackForm()">♡ Share pilot feedback</button>${state.user.demo?'<button class="text-link" onclick="demoRoles()">Switch demo role</button>':''}${state.user.role==='Super Organiser'?'<button class="text-link" onclick="connections()">Connections · Set up later</button>':''}`;
  sidebar.prepend(panel);
 }
 if(state.user.demo){
  const content=$('.content'),banner=document.createElement('div');banner.className='demo-strip';banner.innerHTML=`<span><strong>DEMONSTRATION</strong> Fictional wedding · Your own sample workspace</span><div><button onclick="demoRoles()">Switch role</button><button onclick="beginTour()">Walkthrough</button><button onclick="feedbackForm()">Pilot survey</button>${state.user.role==='Super Organiser'?'<button onclick="resetDemoPrompt()">Start fresh</button>':''}</div>`;content.prepend(banner);
 }
 if(state.user.role==='Super Organiser'){
  const header=$('.page-heading');if(header){const presentation=document.createElement('button');presentation.className='presentation-toggle';presentation.textContent=document.body.classList.contains('presenting')?'Exit presentation':'▣ Present';presentation.title='Toggle presentation layout';presentation.onclick=()=>{document.body.classList.toggle('presenting');render()};header.append(presentation)}
 }
};
settings=function(){return featureSettings()+`<section class="card tile release-connections"><div class="eyebrow">READY WHEN YOU ARE</div><h2>Connect services later.</h2><p>Your investor demo and pilot survey work without SMS, WhatsApp or payments. Each service has a setup checklist for when you’re ready.</p>${button('Open connection checklist','connections()')}<button class="secondary" onclick="feedbackForm()">Share pilot feedback</button></section>`};
function demoRoles(){
 modal('One celebration. Every perspective.',`<p class="subtitle">Switch roles inside the same isolated sample workspace. Guests never receive finance data or other guests’ room information.</p><div class="role-grid" style="margin-top:20px">${['Super Organiser','Co-Organiser','Finance Team','Vendor','Guest','Hotel Partner'].map(r=>`<button onclick="switchDemoRole('${r}')">${r}</button>`).join('')}</div>`);
}
async function switchDemoRole(role){$('#modal').close();await demo(role)}
function resetDemoPrompt(){
 modal('A fresh start to the festivities?',`<p class="subtitle">Start a new sample wedding for your next presentation. Your previous pilot survey response is retained. Shared photos remain at their original album links; save your private Memories host link before starting fresh. Other visitors’ workspaces and real events are unaffected.</p><div class="form-actions"><button class="secondary" onclick="document.querySelector('dialog').close()">Keep exploring</button><button class="primary" id="fresh-demo">Start fresh demo</button></div>`);
 $('#fresh-demo').onclick=async()=>{await api('demo/reset',{});$('#modal').close();page='Overview';saveQueue([]);await refresh();toast('Fresh sample wedding ready. Let the celebrations begin!')};
}
async function connections(){
 const data=await api('integrations');
 modal('Connections · Ready when you are',`<div class="connection-list"><div class="welcome-note">Storage: ${esc(data.storage.provider)} · ${esc(data.storage.status)}. No credentials are entered or displayed in this app.</div>${data.services.map(s=>`<section class="connection-item"><div class="connection-title"><h3>${esc(s.name)}</h3><span class="badge ${s.configured?'green':''}">${s.configured?'Configuration present':'Connect later'}</span></div><p>${esc(s.steps)}</p><details><summary>Hosting setting names</summary><ul>${s.settings.map(n=>`<li><code>${esc(n)}</code></li>`).join('')}</ul></details><a class="text-link" href="${esc(s.url)}" target="_blank" rel="noopener">Open provider dashboard ↗</a></section>`).join('')}</div>`);
}
function feedbackForm(){
 modal('Help shape a happier celebration.',`<p class="subtitle">A short concept-pilot survey. We don’t collect your contact details here. Please avoid names, phone numbers, or private event information in comments.</p><form id="pilot-feedback">${field('Your perspective','persona','','Family organiser',['Family organiser','Wedding planner','Guest','Vendor','Investor','Other'])}${field('How easy was the app to use? (1 = difficult, 5 = easy)','rating','','5',['1','2','3','4','5'])}${field('How useful would this be for your celebration? (1–5)','usefulness','','5',['1','2','3','4','5'])}${field('Would you consider using it?','willingness','','Maybe',['Yes','Maybe','No'])}<label>What stood out? What confused you? (optional)<textarea name="comments" rows="3" maxlength="2000"></textarea></label><label><span><input name="consent" type="checkbox" required> I agree that my answers may be stored and analysed for this product pilot. I won’t include personal information.</span></label>${formFooter('Submit pilot feedback')}</form>`);
 $('#modal form').actionHandler=async b=>{const d=await api('feedback',{...b,rating:Number(b.rating),usefulness:Number(b.usefulness),consent:b.consent==='on'});$('#modal').close();modal('Your thoughts mean a lot. ♡',`<div class="survey-thanks"><span>❋</span><h2>Thank you for being part of the story.</h2><p class="subtitle">${esc(d.message)}</p><button class="primary" onclick="document.querySelector('dialog').close()">Back to the celebration</button></div>`)};
}
const TOUR=[
 {page:'Overview',title:'One home for the whole celebration.',body:'Start with the wedding countdown, RSVP headcount, timeline, tasks and spending. The numbers come from this fictional sample wedding, not real users or revenue.'},
 {page:'Guests',title:'Every name, every little detail.',body:'Search and edit sample guests, track RSVP and dietary needs, or import a fictional guest CSV. Confirmed guests receive a signed QR pass.'},
 {page:'Timeline',title:'A celebration that stays in sync.',body:'See each function, venue, time and dress code. Guest accounts only receive the sub-events they are invited to.'},
 {page:'Expenses',title:'A little clarity for every rupee.',body:'Explore paid versus outstanding expenses and approval status. The server restricts financial data to organisers and authorised finance members.'},
 {page:'Settings',title:'The right access. At the right time.',body:'Review join requests, team permissions and delivery status. Open Connections to see how Supabase, SMS, WhatsApp and payments can be configured later.'},
 {page:'Overview',title:'The guest experience is part of the story.',body:'Use “Switch demo role” to explore the private guest passport and QR pass. Camera scans can be queued offline; entry is only approved after server verification.'}
];
let tourIndex=0;
let walkthroughStarting=false;
async function startPresentation(){
 if(walkthroughStarting)return;
 walkthroughStarting=true;
 const button=document.querySelector('#start-walkthrough'),status=document.querySelector('#walkthrough-status');
 if(button){button.disabled=true;button.textContent='Preparing your walkthrough…';button.setAttribute('aria-busy','true')}
 if(status){status.hidden=false;status.textContent='Opening your private sample wedding. A sleeping service may take a moment to wake up.'}
 try{await demo('Super Organiser');await beginTour()}
 catch(e){
  if(status?.isConnected){status.hidden=false;status.setAttribute('role','alert');status.textContent='The walkthrough could not open: '+e.message+' Please try again.'}
  else toast('The walkthrough could not open: '+e.message);
 }finally{walkthroughStarting=false;if(button?.isConnected){button.disabled=false;button.removeAttribute('aria-busy');button.textContent='✧ Take the five-minute walkthrough'}}
}
async function beginTour(){
 if(!state.user?.demo||!state.event?.length){await startPresentation();return}
 if(state.user.role!=='Super Organiser')await demo('Super Organiser');
 tourIndex=0;tourStep();
}
function tourStep(){
 const step=TOUR[tourIndex];if(!step)return;nav(step.page);
 modal(step.title,`<div class="tour-progress">${TOUR.map((_,i)=>`<i class="${i<=tourIndex?'active':''}"></i>`).join('')}</div><p class="subtitle">${esc(step.body)}</p><div class="form-actions"><button class="secondary" onclick="document.querySelector('dialog').close()">Explore this screen</button>${tourIndex?'<button class="secondary" onclick="tourIndex--;tourStep()">Back</button>':''}<button class="primary" onclick="${tourIndex===TOUR.length-1?'finishTour()':'tourIndex++;tourStep()'}">${tourIndex===TOUR.length-1?'Finish & share feedback':'Next moment →'}</button></div>`);
}
function finishTour(){$('#modal').close();feedbackForm()}
demo=async function(role){await api('auth/demo',{role});page=role==='Guest'?'Passport':role==='Finance Team'?'Expenses':role==='Vendor'?'Vendors':role==='Hotel Partner'?'Travel & stay':'Overview';await refresh({throwOnError:true});if(!state.user?.demo||!state.event?.length)throw Error('The sample wedding did not load. Please reload the page.')};
boot();
