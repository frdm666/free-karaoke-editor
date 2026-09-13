// The second voice of a line and the highlight colours: they switch and reach the disk.
const { JSDOM } = await import('jsdom');
const API = process.env.KARAOKE_API;
const html = await (await fetch(API + "/")).text();
const js   = await (await fetch(API + "/ui.js")).text();

const dom = new JSDOM(html, { runScripts:"dangerously", pretendToBeVisual:true,
  url: API + "/",
  beforeParse(w){
    w.__errs=[]; w.onerror=m=>w.__errs.push(String(m));
    w.confirm = () => true;
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
const proj = async () => (await (await fetch(API+"/api/project/"+encodeURIComponent(PID))).json());
const click = id => $(id).dispatchEvent(new w.MouseEvent('click',{bubbles:true}));

doc.querySelectorAll('.card')[0].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(1200);

console.log('--- the second voice ---');
doc.querySelectorAll('#scroll .ln')[1].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(120);
ok('the button shows the voice of the selected line',
   /Голос 1/.test($("btnVoice").textContent), $("btnVoice").textContent);
click("btnVoice"); await sleep(120);
ok('the line became the second voice', /Голос 2/.test($("btnVoice").textContent),
   $("btnVoice").textContent);
ok('the second-voice class appeared on stage',
   doc.querySelectorAll('#scroll .ln')[1].classList.contains('v2'));
ok('and on the timeline too',
   doc.querySelectorAll('#blocks .blk')[1].classList.contains('v2'));

console.log('\n--- colours ---');
$("col2").value = "#ff5577";
$("col2").dispatchEvent(new w.Event('input',{bubbles:true}));
await sleep(120);
ok('the second colour was applied to the page',
   doc.documentElement.style.getPropertyValue('--accent-2').trim() === '#ff5577',
   doc.documentElement.style.getPropertyValue('--accent-2'));

console.log('\n--- the look ---');
$("colBg").value = "#101820";
$("colBg").dispatchEvent(new w.Event('input',{bubbles:true}));
await sleep(150);
ok('the stage took the background',
   doc.documentElement.style.getPropertyValue('--page-bg').trim() === '#101820',
   doc.documentElement.style.getPropertyValue('--page-bg'));
// …and the window around it did not: an orange page used to make an orange
// editor, timeline and all
ok('and the window kept its own',
   doc.documentElement.style.getPropertyValue('--bg').trim() === '',
   doc.documentElement.style.getPropertyValue('--bg'));
// a deliberately unreadable pair: dark letters on a dark background
$("colTx").value = "#151d26";
$("colTx").dispatchEvent(new w.Event('input',{bubbles:true}));
await sleep(150);
const tx = doc.documentElement.style.getPropertyValue('--page-text').trim();
ok('letters that blended into the background were lightened', tx !== '#151d26', tx);

console.log('\n--- all of it survives to the disk ---');
await sleep(900);                        // wait for the autosave
const d = await proj();
ok('the voice of the line was saved', d.lines[1].voice === 2, 'voice=' + d.lines[1].voice);
ok('the colours were saved', Array.isArray(d.colors) && d.colors[1] === '#ff5577',
   JSON.stringify(d.colors));
ok('the look was saved', Array.isArray(d.theme) && d.theme[0] === '#101820',
   JSON.stringify(d.theme));

console.log('\n--- a span the original sings ---');
ok('the button is there and switched off', !$("btnKeep").classList.contains('on'));
click("btnKeep"); await sleep(150);
ok('the line is marked', doc.querySelectorAll('#scroll .ln')[1].classList.contains('keep'));
ok('it shows on the timeline too',
   doc.querySelectorAll('#blocks .blk')[1].classList.contains('keep'));
ok('a mark appeared in the text',
   /поёт оригинал/.test(doc.querySelectorAll('#scroll .ln')[1].textContent),
   doc.querySelectorAll('#scroll .ln')[1].textContent.slice(-30));
await sleep(900);
ok('the mark was written to disk', (await proj()).lines[1].keep === true);
// The button walks a circle now: full voice → quiet, to sing along → off.
click("btnKeep"); await sleep(900);
const soft = (await proj()).lines[1];
ok('a second press holds the original back to a guide',
   soft.keep === true && soft.keepSoft === true, JSON.stringify(soft.keep) + '/' + JSON.stringify(soft.keepSoft));
click("btnKeep"); await sleep(900);
ok('and a third takes it off', !(await proj()).lines[1].keep);
ok('the mark left the text',
   !/поёт оригинал/.test(doc.querySelectorAll('#scroll .ln')[1].textContent));

console.log('\n--- back to the main voice ---');
click("btnVoice"); await sleep(900);
const d2 = await proj();
ok('the voice went back to the first', (d2.lines[1].voice || 1) === 1, 'voice=' + d2.lines[1].voice);
// put the colour back so the other suites are not disturbed
$("col2").value = "#ff8ad1";
$("col2").dispatchEvent(new w.Event('input',{bubbles:true}));
await sleep(900);

ok('no JS errors', w.__errs.length===0, w.__errs.slice(0,2).join(' | '));
console.log(fail ? '\nFAILED: '+fail : '\nAll checks passed');
process.exit(fail?1:0);
