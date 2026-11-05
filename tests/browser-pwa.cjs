const {chromium,devices}=require('playwright');
const fs=require('fs'),os=require('os'),path=require('path');
(async()=>{
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'shaadiverse-pwa-'));
 const context=await chromium.launchPersistentContext(profile,{headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox'],viewport:{width:390,height:844},reducedMotion:'reduce'}),browser=context.browser(),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));const base=process.env.APP_URL||'http://127.0.0.1:3006';
 await page.goto(base);await page.getByRole('heading',{name:'A front-row seat to the celebration.'}).waitFor();
 await page.evaluate(()=>navigator.serviceWorker.ready);await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
 const cdp=await context.newCDPSession(page),manifest=await cdp.send('Page.getAppManifest');if(manifest.errors.length)throw Error(JSON.stringify(manifest.errors));
 const data=JSON.parse(manifest.data);if(data.name!=='ShaadiVerse'||data.display!=='standalone')throw Error('Wrong app identity');
 const eligibility=await cdp.send('Page.getInstallabilityErrors');console.log('Chromium installability:',JSON.stringify(eligibility.installabilityErrors));if(eligibility.installabilityErrors.length)throw Error('Browser reports installability errors');
 await page.evaluate(()=>{installPrompt=null;mountInstallButton()});await page.locator('.install-entry').click();await page.getByRole('heading',{name:'On Android'}).waitFor();await page.locator('#modal .modal-head button').click();
 await page.evaluate(()=>{
  const event=new Event('beforeinstallprompt',{cancelable:true});window.installPromptCalls=0;event.prompt=async()=>{window.installPromptCalls++};event.userChoice=Promise.resolve({outcome:'accepted'});window.dispatchEvent(event);
 });await page.locator('.install-entry').click();if(await page.evaluate(()=>window.installPromptCalls)!==1)throw Error('Native prompt not triggered');
 await page.evaluate(()=>window.dispatchEvent(new Event('appinstalled')));await page.getByRole('button',{name:'Explore Rahul & Priya’s wedding'}).click();await page.getByRole('heading',{name:'A beautiful celebration awaits.'}).waitFor();if(await page.locator('.install-entry').count())throw Error('Install entry returned after installation');
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Phone overflow');
 const cacheApi=await page.evaluate(async()=>{for(const key of await caches.keys()){for(const request of await(await caches.open(key)).keys()){if(new URL(request.url).pathname.startsWith('/api/'))return true}}return false});if(cacheApi)throw Error('Private API responses cached');
 await context.setOffline(true);await page.reload();try{await page.getByRole('heading',{name:'The gate, on the go.'}).waitFor({timeout:8000})}catch(e){console.log('Offline diagnostic:',JSON.stringify(await page.evaluate(async()=>({online:navigator.onLine,body:document.body.innerText.slice(0,800),boot:typeof boot,offlineGate:typeof offlineGate,gatePresent:!!localStorage.getItem('shaadi-gate'),scripts:[...document.scripts].map(s=>s.src),cache:[...await caches.keys()]}))));console.log('Page errors:',errors);throw e}await context.setOffline(false);
 const apple=await browser.newContext({...devices['iPhone 13'],reducedMotion:'reduce'}),iphone=await apple.newPage();iphone.on('pageerror',e=>errors.push(e.message));await iphone.goto(base);await iphone.getByRole('heading',{name:'A front-row seat to the celebration.'}).waitFor();await iphone.locator('.install-entry').click();await iphone.getByRole('heading',{name:'On your iPhone or iPad'}).waitFor();await iphone.screenshot({path:'/tmp/shaadiverse-iphone-install.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));console.log('PASS: valid installable manifest, icons, service worker, Android/native install flow, iPhone instructions, phone layout, offline launch, private API cache exclusion. OS home-screen installation itself requires a real device.');await browser.close();fs.rmSync(profile,{recursive:true,force:true});
})().catch(e=>{console.error(e);process.exit(1)});
