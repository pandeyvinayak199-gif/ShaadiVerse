const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.APP_URL||'http://127.0.0.1:3009');await page.getByRole('button',{name:'Explore Rahul & Priya’s wedding'}).click();await page.getByRole('heading',{name:'A beautiful celebration awaits.'}).waitFor();
 for(const width of [320,360,390,760,1024,1440]){
  await page.setViewportSize({width,height:844});
  await page.evaluate(()=>{state.event[0].hashtag='#RahulAndPriyaCelebrateTheirBeautifulWeddingWithAllTheirFamilyAndFriends';render()});
  const badge=await page.locator('.hero-badge').boundingBox(),timer=await page.locator('#countdown').boundingBox();
  if(badge.y<timer.y+timer.height)throw Error('Hashtag overlap at '+width);
  if(badge.x<0||badge.x+badge.width>width+1)throw Error('Hashtag overflow at '+width);
 }
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>nav('Expenses'));const before=await page.evaluate(()=>state.event[0].budget);
 await page.getByRole('button',{name:'＋ Add budget',exact:true}).click();await page.locator('#modal input[name=amount]').fill('123.45');await page.locator('#modal button[type=submit]').click();await page.waitForFunction(b=>state.event[0].budget===b+123.45,before);
 await page.getByRole('button',{name:'− Remove amount',exact:true}).click();await page.locator('#modal input[name=amount]').fill('23.45');await page.locator('#modal button[type=submit]').click();await page.waitForFunction(b=>state.event[0].budget===b+100,before);
 await page.getByRole('button',{name:'Clear budget',exact:true}).click();await page.locator('#modal button[type=button]').last().click();if(await page.evaluate(()=>state.event[0].budget)!==before+100)throw Error('Cancel changed budget');
 const expenses=await page.evaluate(()=>state.expenses.length);await page.getByRole('button',{name:'Clear budget',exact:true}).click();await page.getByRole('button',{name:'Yes, clear budget'}).click();await page.waitForFunction(()=>state.event[0].budget===0);
 if(await page.evaluate(()=>state.expenses.length)!==expenses)throw Error('Expenses removed');await page.reload();await page.getByRole('heading',{name:'A beautiful celebration awaits.'}).waitFor();if(await page.evaluate(()=>state.event[0].budget)!==0)throw Error('Budget not persisted');if(await page.locator('main').innerText().then(s=>/NaN|Infinity/.test(s)))throw Error('Invalid zero budget display');await page.getByRole('button',{name:'＋ Add budget',exact:true}).waitFor();
 if(errors.length)throw Error(errors.join('\n'));console.log('PASS: six responsive widths, long hashtag, add/remove/clear/cancel, expenses preserved, persistence, zero budget display.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
