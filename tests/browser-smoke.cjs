// Optional: npm-installed Playwright and system Chromium are required.
const { chromium } = require('playwright');
(async () => {
 const browser = await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',args:['--no-sandbox']});
 const page = await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.APP_URL || 'http://127.0.0.1:3000');
 await page.getByRole('button',{name:'Explore Rahul & Priya’s wedding'}).click();
 await page.getByRole('heading',{name:'A beautiful celebration awaits.'}).waitFor();
 for (const [nav,title] of [['Guests','Your favourite people, all in one place.'],['Timeline','Every moment has its moment.'],['Vendors','The magic makers.'],['Expenses','Big dreams. Thoughtful budgets.'],['Travel & stay','A warm welcome, before the wedding.'],['Catering','Love, laughter & a second helping.'],['Tasks','A little teamwork. A lot of magic.'],['Celebrations','A little extra shaadi magic.'],['Gifts & shagun','Little gestures. Lasting gratitude.'],['Settings','Make this celebration yours.']]) {
  await page.locator('.sidebar .nav').filter({hasText:nav}).click();
  await page.getByRole('heading',{name:title,exact:true}).waitFor();
 }
 await page.getByRole('button',{name:'Edit celebration',exact:true}).click();
 await page.locator('input[name=name]').fill('Rahul & Priya');
 await page.getByRole('button',{name:'Save changes',exact:true}).click();
 await page.locator('.sidebar .nav').filter({hasText:'Overview'}).click();
 await page.screenshot({path:'/tmp/shaadi-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile page overflows');
 await page.screenshot({path:'/tmp/shaadi-mobile.png',fullPage:true});
 await page.getByRole('button',{name:'Open navigation'}).click();
 await page.locator('.sidebar .nav').filter({hasText:'Switch role'}).click();
 await page.getByRole('button',{name:'Guest',exact:true}).click();
 await page.getByRole('heading',{name:'Your wedding passport.'}).waitFor();
 await page.getByRole('button',{name:'Share a travel update'}).click();
 await page.locator('#modal input[name=consent]').check();
 await page.getByRole('button',{name:'Share update',exact:true}).click();
 await page.getByText('Current milestone: Left home',{exact:true}).waitFor();
 if(errors.length)throw Error(errors.join('\n'));
 console.log('PASS: 11 organiser screens, event settings, guest travel consent, desktop and mobile, no JavaScript errors.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
