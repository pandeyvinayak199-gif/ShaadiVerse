const {chromium}=require('playwright');
const {startSample,switchSampleRole}=require('./browser-fixtures.cjs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']}),page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.APP_URL||'http://127.0.0.1:3017');await startSample(page);
 for(const role of ['Super Organiser','Co-Organiser']){
  if(role==='Co-Organiser')await switchSampleRole(page,role);
  await page.evaluate(()=>nav('Guests'));
  for(const width of [320,390,760,1024,1440]){
   await page.setViewportSize({width,height:844});const button=page.getByRole('button',{name:'＋ Add guest',exact:true});await button.scrollIntoViewIfNeeded();const box=await button.boundingBox();if(!box||box.x<0||box.x+box.width>width+1||box.height<44)throw Error('Guest button clipped or too small: '+role+' '+width);
   const styles=await button.evaluate(b=>{const c=getComputedStyle(b);return {background:c.backgroundColor,color:c.color,expected:getComputedStyle(document.documentElement).getPropertyValue('--wine').trim()}});if(styles.background===styles.color||styles.background==='rgb(255, 255, 255)')throw Error('Guest button is white on white');await page.evaluate(()=>document.body.classList.add('dark'));if(await button.evaluate(b=>getComputedStyle(b).backgroundColor)!==styles.background)throw Error('Dark mode hides the primary guest action');await page.evaluate(()=>document.body.classList.remove('dark'));
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw Error('Guest page overflow at '+width);
  }
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'＋ Add guest',exact:true}).click();await page.locator('#modal [name=name]').fill(role+' guest');await page.locator('#modal [name=email]').fill((role==='Super Organiser'?'owner-added':'planner-added')+'@example.com');await page.getByRole('button',{name:'Add to the celebration',exact:true}).click();await page.getByRole('cell',{name:new RegExp(role+' guest')}).waitFor();
  await page.evaluate(()=>nav('Vendors'));await page.getByRole('button',{name:'＋ Add vendor',exact:true}).click();if(await page.locator('#modal [name=arrival]').count())throw Error('Vendor arrival field still exists');await page.locator('#modal [name=name]').fill(role+' vendor');await page.locator('#modal [name=category]').fill('Music');await page.locator('#modal [name=contact]').fill('9888877777');await page.locator('#modal [name=quote]').fill('10000');await page.locator('#modal [name=paid]').fill('0');await page.locator('#modal [name=deliverables]').fill('Music arrangements');await page.getByRole('button',{name:'Save & celebrate',exact:true}).click();await page.getByRole('heading',{name:role+' vendor',exact:true,level:2}).waitFor();if(await page.locator('.content').getByText(/Arrival:/).count())throw Error('Vendor cards still show arrival');
 }
 await page.reload();await page.waitForFunction(()=>state.user?.role==='Co-Organiser');await page.evaluate(()=>nav('Vendors'));await page.getByRole('heading',{name:'Co-Organiser vendor',exact:true,level:2}).waitFor();if(errors.length)throw Error(errors.join('\n'));
 console.log('PASS: visible contrasting Add guest action at five widths in both organiser roles; guest creation; vendor creation without arrival; vendor cards and reload persistence.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
