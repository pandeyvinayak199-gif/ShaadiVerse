const { chromium }=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.APP_URL||'http://127.0.0.1:3001';await page.goto(base);
 await page.getByRole('button',{name:'Explore Rahul & Priya’s wedding'}).click();await page.getByRole('heading',{name:'A beautiful celebration awaits.'}).waitFor();
 // Generate an actual pass and decode its SVG pixels using the vendored camera decoder.
 const qr=await page.evaluate(async()=>{
  const state=await api('state'),g=state.guests.find(g=>g.status==='Confirmed'),p=await api('pass?guestId='+g.id);
  const image=new Image(),url=URL.createObjectURL(new Blob([p.qrSvg],{type:'image/svg+xml'}));image.src=url;await image.decode();
  const canvas=document.createElement('canvas');canvas.width=900;canvas.height=900;const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,900,900);ctx.drawImage(image,0,0,900,900);const pixels=ctx.getImageData(0,0,900,900);const decoded=jsQR(pixels.data,900,900);URL.revokeObjectURL(url);return {matches:decoded?.data===p.token,token:p.token};
 });if(!qr.matches)throw Error('QR did not decode to its signed token');
 await page.evaluate(()=>nav('Guests'));await page.getByRole('button',{name:'▦ Gate check-in'}).click();await page.locator('#modal input[name=token]').fill(qr.token);
 await page.getByRole('button',{name:'Check entry',exact:true}).click();await page.getByText('Entry confirmed by the server.').waitFor();
 await page.locator('#modal input[name=token]').fill(qr.token);await page.getByRole('button',{name:'Check entry',exact:true}).click();await page.getByText(/Duplicate scan/).waitFor();await page.locator('#modal .modal-head button').click();
 // Offline requests remain pending and are visibly different from approval.
 const offline=await page.evaluate(async()=>{const s=await api('state'),g=s.guests.find(g=>g.status==='Confirmed');return (await api('pass?guestId='+g.id)).token});
 await page.evaluate(()=>scanner());await context.setOffline(true);await page.locator('#modal input[name=token]').fill(offline);await page.getByRole('button',{name:'Check entry',exact:true}).click();await page.getByText('Pending verification',{exact:false}).waitFor();
 await context.setOffline(false);await page.getByRole('button',{name:/Sync pending scans/}).click();await page.locator('.sync-results').getByText(/✓/).waitFor();await page.locator('#modal .modal-head button').click();
 await page.evaluate(()=>nav('Settings'));await page.getByRole('heading',{name:'Your trusted team'}).waitFor();await page.getByRole('button',{name:'＋ Add team member'}).click();await page.locator('#modal input[name=name]').fill('Finance Browser');await page.locator('#modal input[name=phone]').fill('9666666612');await page.getByRole('button',{name:'Grant event access'}).click();await page.getByText('9666666612',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');await page.screenshot({path:'/tmp/shaadi-settings-mobile.png',fullPage:true});
 await page.evaluate(()=>createEventForm());await page.locator('#modal input[name=name]').fill('Aarav & Diya');await page.locator('#modal input[name=date]').fill('2027-02-12');await page.locator('#modal input[name=venue]').fill('Jaipur Gardens');await page.getByRole('button',{name:'Create my celebration'}).click();await page.getByRole('heading',{name:'Aarav & Diya',exact:false}).waitFor();
 await page.evaluate(()=>invite());const invitation=await page.locator('#modal .welcome-note').textContent();if(!invitation.includes('/?event='))throw Error('Invitation link missing');await page.locator('#modal .modal-head button').click();
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:'/tmp/shaadi-personal-event.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));console.log('PASS: QR encode/decode, check-in and duplicate, offline pending/sync, team membership, mobile layout, sample event creation, invitation link; no JavaScript errors.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
