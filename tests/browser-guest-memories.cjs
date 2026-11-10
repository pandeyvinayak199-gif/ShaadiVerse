const {startSample,switchSampleRole}=require('./browser-fixtures.cjs');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']}),page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.APP_URL||'http://127.0.0.1:3010');await startSample(page);await page.getByRole('heading',{name:'Your wedding, coming together.'}).waitFor();await page.evaluate(()=>nav('Memories'));await page.getByRole('button',{name:'Create our Memories album'}).click();await page.getByRole('button',{name:'Download QR',exact:true}).waitFor();
 await switchSampleRole(page,'Guest');await page.getByRole('heading',{name:'Your wedding passport.'}).waitFor();await page.evaluate(()=>nav('Memories'));await page.getByRole('button',{name:'＋ Add photos',exact:true}).click();
 const bytes=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=32;c.getContext('2d').fillRect(0,0,32,32);return c.toDataURL('image/png').split(',')[1]});
 await page.locator('#member-photo-files').setInputFiles(['family.png','dance.png'].map(name=>({name,mimeType:'image/png',buffer:Buffer.from(bytes,'base64')})));await page.locator('#modal input[name=consent]').check();await page.getByRole('button',{name:'Upload selected photos',exact:true}).click();await page.getByText('Saved 2 of 2 selected photos.',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Close',exact:true}).last().click();await page.getByRole('heading',{name:'2 memories, and counting.'}).waitFor();
 const listing=await page.evaluate(()=>api('memories/album?album='+memoryPanelData.album.id));if(listing.photos.length!==2||listing.manager||listing.photos.some(p=>p.uploader!==listing.name))throw Error('Guest upload identity or permissions incorrect');
 if(await page.getByRole('button',{name:'Pause uploads',exact:true}).count())throw Error('Guest sees organiser controls');if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
 await page.reload();await page.getByRole('heading',{name:'Your wedding passport.'}).waitFor();await page.evaluate(()=>nav('Memories'));await page.getByRole('heading',{name:'2 memories, and counting.'}).waitFor();
 if(errors.length)throw Error(errors.join('\n'));console.log('PASS: signed-in guest multi-photo upload directly from Memories, verified identity, no organiser controls, phone layout and persistence.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
