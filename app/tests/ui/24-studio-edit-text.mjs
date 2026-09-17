// A typo in the lyrics: fixed by double-clicking the line, without rebuilding
// and without losing the timing.
const { JSDOM } = await import('jsdom');
const API = process.env.KARAOKE_API;
const html = await (await fetch(API + "/")).text();
const js   = await (await fetch(API + "/ui.js")).text();

const dom = new JSDOM(html, { runScripts:"dangerously", pretendToBeVisual:true,
  url: API + "/",
  beforeParse(w){
    w.__errs=[]; w.onerror=m=>w.__errs.push(String(m));
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
const sleep = ms => new Promise(r=>setTimeout(r,ms));
w.eval(js);
await sleep(900);

let fail=0; const ok=(n,c,e='')=>{console.log((c?'  ✓ ':'  ✗ ')+n+(e?' — '+e:'')); if(!c)fail++;};
const st = await (await fetch(API+"/api/state")).json();
const PID = st.projects[0].id;
const srv = async () => (await (await fetch(API+"/api/project/"+encodeURIComponent(PID))).json()).lines;

doc.querySelectorAll('.card')[0].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(1200);
ok('the editor opened', !$('scrEdit').classList.contains('hide'));

const before = await srv();
const I = 2;
const dbl = el => el.dispatchEvent(new w.MouseEvent('dblclick',{bubbles:true}));
const keyOn = (el,key) => el.dispatchEvent(new w.KeyboardEvent('keydown',
  {key, bubbles:true, cancelable:true}));

console.log('\n--- a double click opens the editor ---');
dbl(doc.querySelectorAll('#scroll .ln')[I]);
await sleep(80);
let inp = doc.querySelector('.lnedit');
ok('an input field appeared', !!inp);
ok('with the current text of the line', inp && inp.value === before[I].text,
   inp ? `«${inp.value}» / «${before[I].text}»` : '');

console.log('\n--- Enter saves ---');
const NEW = "исправленный текст этой строки";
inp.value = NEW;
keyOn(inp, 'Enter');
await sleep(900);
const after = await srv();
ok('the text on the server changed', after[I].text === NEW, after[I].text);
ok('the input field went away', !doc.querySelector('.lnedit'));
ok('the line on stage shows the new text',
   doc.querySelectorAll('#scroll .ln')[I].textContent.replace(/\s+/g,' ').trim()
     .includes('исправленный'),
   doc.querySelectorAll('#scroll .ln')[I].textContent.trim().slice(0,40));
ok('the label on the timeline updated',
   doc.querySelectorAll('.blk')[I].textContent.includes('исправленный'),
   doc.querySelectorAll('.blk')[I].textContent.slice(0,40));

console.log('\n--- the timing of the line survived ---');
ok('the line time is in place',
   Math.abs(after[I].start - before[I].start) < 1e-6 &&
   Math.abs(after[I].end - before[I].end) < 1e-6,
   `${before[I].start}–${before[I].end} → ${after[I].start}–${after[I].end}`);
ok('as many words as in the new text', after[I].words.length === NEW.split(' ').length,
   after[I].words.length + ' words');
const ws = after[I].words;
ok('the words are laid out inside the line in order',
   ws.every((x,k)=> k===0 || x.t >= ws[k-1].t - 1e-9) &&
   ws[0].t >= after[I].start - 1e-6 &&
   ws[ws.length-1].t + ws[ws.length-1].d <= after[I].end + 1e-6,
   `${ws[0].t.toFixed(2)} … ${(ws[ws.length-1].t+ws[ws.length-1].d).toFixed(2)}`);
ok('a long word got more time than a short one',
   (() => { const a = ws.find(x=>x.w==='исправленный'), b = ws.find(x=>x.w==='и');
            return !a || !b ? true : a.d > b.d; })());
ok('the neighbouring lines were not touched',
   after[I-1].text === before[I-1].text && after[I+1].text === before[I+1].text);

console.log('\n--- Escape cancels ---');
dbl(doc.querySelectorAll('#scroll .ln')[I]);
await sleep(80);
inp = doc.querySelector('.lnedit');
inp.value = "это не должно сохраниться";
keyOn(inp, 'Escape');
await sleep(700);
const after2 = await srv();
ok('the text stayed as it was', after2[I].text === NEW, after2[I].text);

console.log('\n--- an empty line is refused ---');
dbl(doc.querySelectorAll('#scroll .ln')[I]);
await sleep(80);
inp = doc.querySelector('.lnedit');
inp.value = "   ";
keyOn(inp, 'Enter');
await sleep(700);
const after3 = await srv();
ok('empty text did not wipe the line', after3[I].text === NEW, after3[I].text);
ok('the number of lines did not change', after3.length === before.length,
   `${before.length} → ${after3.length}`);

console.log('\n--- as many words as before: each keeps its own time ---');
// A line rewritten whole — signs put where the words are sung, or a misheard
// line typed out again — used to be spread evenly across its span, throwing
// away the very times the model had measured word by word.
const wasW = after[I].words.map(w => ({t: w.t, d: w.d}));
const SAME = wasW.map((_, k) => 'знак' + (k + 1)).join(' ');
dbl(doc.querySelectorAll('#scroll .ln')[I]);
await sleep(200);
inp = doc.querySelector('.lnedit');
inp.value = SAME;
keyOn(inp, 'Enter');
await sleep(900);
const swapped = await srv();
ok('the new text is there', swapped[I].text === SAME, swapped[I].text);
ok('and every word kept the time of the one it replaced',
   swapped[I].words.length === wasW.length &&
   swapped[I].words.every((w, k) => Math.abs(w.t - wasW[k].t) < 1e-6 &&
                                    Math.abs(w.d - wasW[k].d) < 1e-6),
   swapped[I].words.map(w => w.t.toFixed(2)).join(' ') + ' vs ' +
   wasW.map(w => w.t.toFixed(2)).join(' '));

console.log('\n--- editing can be found without knowing about the double click ---');
const click = id => $(id).dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
doc.querySelectorAll('#scroll .ln')[3].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(80);
ok('the “Line text” button exists and is labelled plainly',
   !!$('btnText') && /Текст/.test($('btnText').textContent), ($('btnText')||{}).textContent);
click('btnText'); await sleep(120);
ok('it opens the same input field', !!doc.querySelector('.lnedit'));
ok('and edits exactly the selected line',
   doc.querySelector('.lnedit').value === (await srv())[3].text,
   doc.querySelector('.lnedit').value);
doc.querySelector('.lnedit').dispatchEvent(new w.KeyboardEvent('keydown',
  {key:'Escape',bubbles:true,cancelable:true}));
await sleep(300);

console.log('\n--- and by double-clicking the block on the timeline ---');
doc.querySelectorAll('.blk')[4].dispatchEvent(new w.MouseEvent('dblclick',{bubbles:true}));
await sleep(150);
ok('a double click on a block opens the editor', !!doc.querySelector('.lnedit'));
ok("that block's line is the one edited",
   doc.querySelector('.lnedit').value === (await srv())[4].text,
   doc.querySelector('.lnedit').value);
doc.querySelector('.lnedit').dispatchEvent(new w.KeyboardEvent('keydown',
  {key:'Escape',bubbles:true,cancelable:true}));
await sleep(300);

// Cleaning up after ourselves: the project on the stand is shared, and the
// edits eat the slack inside the lines — the next run would fail for nothing.
console.log('\n--- putting the project back ---');
let __g = 0;
while (!$('btnUndo').disabled && __g++ < 100){
  $('btnUndo').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
  await sleep(90);
}
await sleep(900);
ok('the undo history is used up', $('btnUndo').disabled, 'steps ' + __g);

ok('no JS errors', w.__errs.length===0, w.__errs.slice(0,2).join(' | '));

console.log(fail ? '\nFAILED: '+fail : '\nAll checks passed');
process.exit(fail?1:0);
