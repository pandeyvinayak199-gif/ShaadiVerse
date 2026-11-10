// Isolated regression fixtures only; requires APP_MODE=test and DEMO_MODE=1.
async function switchSampleRole(page,role){
 await page.evaluate(async role=>{await api('auth/demo',{role});page=role==='Guest'?'Passport':role==='Finance Team'?'Expenses':role==='Vendor'?'Vendors':role==='Hotel Partner'?'Travel & stay':'Overview';await refresh({throwOnError:true});localStorage.setItem('shaadi-guide-v1:'+state.scope+':disabled','yes');document.querySelector('#welcome-tip')?.remove()},role);
}
async function startSample(page){await page.locator('.login-box').waitFor();await switchSampleRole(page,'Super Organiser')}
module.exports={startSample,switchSampleRole};
