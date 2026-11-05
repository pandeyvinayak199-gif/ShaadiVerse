/* Native browser installation when supported; honest platform guidance otherwise. */
let installPrompt=null,installedThisSession=false;
const isInstalled=()=>installedThisSession||window.matchMedia('(display-mode: standalone)').matches||window.navigator.standalone===true;
const isApplePhone=()=>/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;mountInstallButton()});
window.addEventListener('appinstalled',()=>{installedThisSession=true;installPrompt=null;document.querySelectorAll('.install-entry').forEach(b=>b.remove());toast('ShaadiVerse is on your home screen. Let the celebrations begin!')});
function mountInstallButton(){
 document.querySelectorAll('.install-entry').forEach(b=>{if(isInstalled())b.remove();else b.textContent=installPrompt?'↓ Install ShaadiVerse':'↓ Get ShaadiVerse on your phone'});
 if(isInstalled()||document.querySelector('.install-entry'))return;
 const target=document.querySelector('.login-box')||document.querySelector('.sidebar .side-footer')||document.querySelector('.account-shell');
 if(!target)return;
 const button=document.createElement('button');button.className='secondary install-entry';button.type='button';button.textContent=installPrompt?'↓ Install ShaadiVerse':'↓ Get ShaadiVerse on your phone';button.onclick=installShaadiVerse;target.append(button);
}
async function installShaadiVerse(){
 if(isInstalled())return toast('You’re already using the installed ShaadiVerse app.');
 if(installPrompt){
  const prompt=installPrompt;installPrompt=null;
  try{await prompt.prompt();const result=await prompt.userChoice;if(result.outcome!=='accepted')showPhoneInstallGuide();}
  catch{showPhoneInstallGuide()}
  mountInstallButton();return;
 }
 showPhoneInstallGuide();
}
function showPhoneInstallGuide(){
 const apple=isApplePhone();
 modal('ShaadiVerse, on your home screen.',`<div class="phone-install"><img src="/icons/apple-touch-icon.png" width="76" height="76" alt="ShaadiVerse app icon"><p class="subtitle">Open your celebration straight from your phone, in its own app window.</p>${apple?`<h3>On your iPhone or iPad</h3><ol><li>Open this app’s HTTPS link in <strong>Safari</strong>.</li><li>Tap <strong>Share</strong> (the square with an upward arrow).</li><li>Choose <strong>Add to Home Screen</strong>. Keep <strong>Open as Web App</strong> enabled if shown.</li><li>Tap <strong>Add</strong>, then open <strong>ShaadiVerse</strong> from your home screen.</li></ol>`:`<h3>On Android</h3><ol><li>Open this app’s HTTPS link in <strong>Chrome</strong>.</li><li>Tap the <strong>⋮ menu</strong> in the top-right corner.</li><li>Choose <strong>Install app</strong> or <strong>Add to Home screen → Install</strong>.</li><li>Open <strong>ShaadiVerse</strong> from your home screen.</li></ol><details><summary>Using an iPhone instead?</summary><p>Open the link in Safari, tap Share, then Add to Home Screen and Add.</p></details>`}<p class="welcome-note">Use Safari or Chrome directly, rather than an in-app WhatsApp/Instagram browser. You may be asked for the existing demo password again. Internet is needed for sign-in, saved updates and feedback; offline gate scans remain pending until synced.</p><div class="form-actions"><button class="primary" onclick="document.querySelector('dialog').close()">Got it</button></div></div>`);
}
const installObserver=new MutationObserver(mountInstallButton);
installObserver.observe(document.getElementById('app'),{childList:true});
window.matchMedia('(display-mode: standalone)').addEventListener?.('change',mountInstallButton);
mountInstallButton();
