import fs from 'fs';
import path from 'path';
import { chromium } from 'playwright';

const authPath = process.env.SUNO_AUTH || path.join(process.env.HOME, '.config/suno-cli/auth.json');
const out = process.argv[2] || '/root/.openclaw/workspace/suno-automato-cli/suno-library/suno-logged-in-state.png';
const data = JSON.parse(fs.readFileSync(authPath, 'utf8'));
function findCookie(obj) {
  const vals=[];
  function walk(x){
    if(!x) return;
    if(typeof x==='string') vals.push(x);
    else if(Array.isArray(x)) x.forEach(walk);
    else if(typeof x==='object') Object.values(x).forEach(walk);
  }
  walk(obj);
  return vals.find(s => s.includes('__client') || s.includes('__session') || s.length > 500) || '';
}
const cookieRaw = data.cookie || data.client_cookie || data.__client || data.session_cookie || findCookie(data);
const cookies=[];
if (cookieRaw.includes('=')) {
  for (const part of cookieRaw.split(';')) {
    const i=part.indexOf('=');
    if(i<0) continue;
    const name=part.slice(0,i).trim(); const value=part.slice(i+1).trim();
    if(!name || !value) continue;
    cookies.push({name,value,domain: name.startsWith('__Host-') ? 'auth.suno.com' : '.suno.com', path:'/', secure:true, sameSite:'Lax'});
    if(name==='__client') cookies.push({name,value,domain:'auth.suno.com',path:'/',secure:true,sameSite:'Lax'});
  }
} else if (cookieRaw) {
  cookies.push({name:'__client',value:cookieRaw,domain:'auth.suno.com',path:'/',secure:true,sameSite:'Lax'});
}
const browser = await chromium.launch({headless:true, args:['--no-sandbox','--disable-dev-shm-usage']});
const context = await browser.newContext({viewport:{width:1400,height:1000}});
if (cookies.length) await context.addCookies(cookies);
const page = await context.newPage();
await page.goto('https://suno.com/create', {waitUntil:'domcontentloaded', timeout:45000});
await page.waitForTimeout(6000);
await page.screenshot({path:out, fullPage:false});
const text=(await page.locator('body').innerText().catch(()=>''));
fs.writeFileSync(out.replace(/\.png$/,'.txt'), 'url='+page.url()+'\nCOOKIES_ADDED='+cookies.map(c=>c.name).join(',')+'\n'+text.slice(0,1500));
await browser.close();
console.log(JSON.stringify({ok:true,out, text:out.replace(/\.png$/,'.txt'), cookiesAdded:cookies.map(c=>c.name)}));
