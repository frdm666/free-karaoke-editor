// Everything a person set up in the Studio must reach the finished file: the
// second voice, the kept original, the highlight and theme colours, line edits.
const { JSDOM } = await import('jsdom');
import fs from 'fs';
import path from 'path';
import os from 'os';

const API = process.env.KARAOKE_API;
const html = await (await fetch(API + "/")).text();
const js   = await (await fetch(API + "/ui.js")).text();
const sleep = ms => new Promise(r=>setTimeout(r,ms));
let fail=0; const ok=(n,c,e='')=>{console.log((c?'  ✓ ':'  ✗ ')+n+(e?' — '+e:'')); if(!c)fail++;};

const dom = new JSDOM(html, { runScripts:"dangerously", pretendToBeVisual:true,
  url: API + "/",
  beforeParse(w){
    w.__errs=[]; w.onerror=m=>w.__errs.push(String(m)); w.confirm=()=>true;
    w.fetch = (...a) => fetch(typeof a[0]==="string" && a[0].startsWith("/")
        ? API + a[0] : a[0], a[1]);
    w.__now=0;
    w.AudioContext = class { constructor(){ this.state="running"; this.destination={}; }
      get currentTime(){ return w.__now; }
      createGain(){ return {gain:{value:1, setTargetAtTime(v){this.value=v;}}, connect(){}}; }
      createBufferSource(){ return {connect(){},start(){},stop(){},onended:null}; }
      decodeAudioData(){ return Promise.resolve({duration:26.04}); } resume(){} };
    w.HTMLCanvasElement.prototype.getContext = () => ({
      scale(){}, clearRect(){}, fillRect(){}, beginPath(){}, moveTo(){}, lineTo(){},
      stroke(){}, set fillStyle(v){}, set strokeStyle(v){}, set lineWidth(v){} });
    w.Element.prototype.getBoundingClientRect = () =>
      ({left:0,top:0,width:900,height:96,right:900,bottom:96,x:0,y:0});
    w.Element.prototype.setPointerCapture = function(){};
    Object.defineProperty(w.HTMLElement.prototype,'clientWidth',{get(){return 900;}});
    Object.defineProperty(w.HTMLElement.prototype,'clientHeight',{get(){return 400;}});
  }});
const w = dom.window, doc = w.document, $ = id => doc.getElementById(id);
w.eval(js);
await sleep(900);

const PID = (await (await fetch(API+"/api/state")).json()).projects[0].id;
const proj = async () => (await (await fetch(API+"/api/project/"+encodeURIComponent(PID))).json());
const before = await proj();
doc.querySelectorAll('.card')[0].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(1400);

console.log('--- setting the song up in the window ---');
doc.querySelectorAll('#scroll .ln')[1].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(120);
$("btnVoice").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));   // the second voice
await sleep(100);
doc.querySelectorAll('#scroll .ln')[2].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(120);
$("btnKeep").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));    // the original sings
await sleep(100);
$("col2").value = "#ee2288"; $("col2").dispatchEvent(new w.Event('input',{bubbles:true}));
$("colBg").value = "#101018"; $("colBg").dispatchEvent(new w.Event('input',{bubbles:true}));
$("colTx").value = "#f0f0ff"; $("colTx").dispatchEvent(new w.Event('input',{bubbles:true}));
await sleep(1000);                       // wait for the autosave

const saved = await proj();
ok('the second voice was saved', saved.lines[1].voice === 2, 'voice=' + saved.lines[1].voice);
ok('the kept original was saved', saved.lines[2].keep === true);
ok('the colours were saved', saved.colors && saved.colors[1] === '#ee2288', JSON.stringify(saved.colors));
ok('the look was saved', saved.theme && saved.theme[0] === '#101018', JSON.stringify(saved.theme));

console.log('\n--- building a standalone HTML the same way the button does ---');
const job = await (await fetch(API+"/api/project/"+encodeURIComponent(PID)+"/export",
  {method:'POST', headers:{'Content-Type':'application/json'},
   body: JSON.stringify({kind:'html'})})).json();
let out = null;
for (let i = 0; i < 120; i++){
  const st = await (await fetch(API+"/api/job?id="+encodeURIComponent(job.job))).json();
  if (st.done){ out = st.result; break; }
  await sleep(500);
}
ok('the page build finished', !!out && !!out.path, JSON.stringify(out));
const page = fs.readFileSync(out.path, 'utf8');
const mark = '<script id="payload" type="application/json">';
const a = page.indexOf(mark) + mark.length, b = page.indexOf('</scr'+'ipt>', a);
const P = JSON.parse(page.slice(a,b).replace(/\\u003c/g,'<').replace(/\\u003e/g,'>')
                                    .replace(/\\u0026/g,'&'));

console.log('\n--- and all of it is inside the finished file ---');
ok('the highlight colours made it through', P.colors && P.colors[1] === '#ee2288', JSON.stringify(P.colors));
ok('the styling made it through', P.theme && P.theme.bg === '#101018', JSON.stringify(P.theme));
ok('the text colour is readable', P.theme && P.theme.text === '#f0f0ff', JSON.stringify(P.theme));
ok('the second voice made it through', P.data.lines[1].voice === 2, 'voice=' + P.data.lines[1].voice);
ok('the kept original made it through', P.data.lines[2].keep === true);
ok('the text of the lines was not harmed',
   P.data.lines.map(l=>l.text).join('|') === saved.lines.map(l=>l.text).join('|'));
ok('the timings match the window',
   P.data.lines.every((l,i) => Math.abs(l.start - saved.lines[i].start) < 0.002),
   P.data.lines[0].start + ' vs ' + saved.lines[0].start);
ok('the audio is embedded in the file', /data:audio\//.test(page));
ok('the page opens without the internet',
   !/https?:\/\/(?!127\.0\.0\.1)/.test(page.replace(/<!--[\s\S]*?-->/g,'')),
   (page.match(/https?:\/\/[^\s"']+/g)||[]).slice(0,2).join(' '));

console.log('\n--- and the finished page really shows it ---');
const dom2 = new JSDOM(page, { runScripts:'dangerously', pretendToBeVisual:true,
  url:'https://local.test/exported',
  beforeParse(w2){
    w2.__errs=[]; w2.onerror=m=>w2.__errs.push(String(m));
    class FA{ constructor(){this.paused=true;this.volume=1;this.duration=26;this._t=0;this._h={};
      setTimeout(()=>this._fire('loadedmetadata'),0);}
      get currentTime(){return this._t;} set currentTime(v){this._t=v;}
      addEventListener(n,f){(this._h[n]=this._h[n]||[]).push(f);} removeEventListener(){}
      _fire(n){(this._h[n]||[]).slice().forEach(f=>f());}
      play(){this.paused=false;return Promise.resolve();} pause(){this.paused=true;}}
    w2.Audio=FA;
  }});
await sleep(400);
const d2 = dom2.window.document;
const lns = [...d2.querySelectorAll('#scroll .ln')];
ok('the second-voice line is marked', lns[1].classList.contains('v2'));
ok('the line with the original is marked and labelled',
   lns[2].classList.contains('keep') && /поёт оригинал|original sings/.test(lns[2].textContent),
   lns[2].textContent.slice(-30));
const root2 = d2.documentElement.style;
ok('the second colour is applied', root2.getPropertyValue('--accent-2').trim() === '#ee2288',
   root2.getPropertyValue('--accent-2'));
// this is the finished page, and the page's look is the whole page's look
ok('the background is applied', root2.getPropertyValue('--bg').trim() === '#101018',
   root2.getPropertyValue('--bg'));
ok('the page has no JS errors', dom2.window.__errs.length === 0,
   dom2.window.__errs.slice(0,2).join(' | '));

// put the stand back the way it was
doc.querySelectorAll('#scroll .ln')[1].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(80); $("btnVoice").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
doc.querySelectorAll('#scroll .ln')[2].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(80); $("btnKeep").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
$("col2").value = "#ff8ad1"; $("col2").dispatchEvent(new w.Event('input',{bubbles:true}));
$("colBg").value = "#0a0b14"; $("colBg").dispatchEvent(new w.Event('input',{bubbles:true}));
$("colTx").value = "#e8ebf5"; $("colTx").dispatchEvent(new w.Event('input',{bubbles:true}));
await sleep(900);
try { fs.unlinkSync(out.path); } catch(e){}

ok('the window has no JS errors', w.__errs.length===0, w.__errs.slice(0,2).join(' | '));
console.log(fail ? '\nFAILED: '+fail : '\nAll checks passed');
process.exit(fail?1:0);
