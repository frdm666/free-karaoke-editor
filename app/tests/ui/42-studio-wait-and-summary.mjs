// The countdown to the singing on an empty stage, and the summary after building.
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

// The sizes are in rem off html{font-size:clamp(16px…)} — jsdom does not compute them.
// Take the lower bound of the clamp, 16px: pass there and it passes on a big screen.
const cssPx = v => /rem$/.test(String(v)) ? parseFloat(v) * 16 : parseFloat(v || 0);
let fail=0; const ok=(n,c,e='')=>{console.log((c?'  ✓ ':'  ✗ ')+n+(e?' — '+e:'')); if(!c)fail++;};
const PID = (await (await fetch(API+"/api/state")).json()).projects[0].id;
const proj = await (await fetch(API+"/api/project/"+encodeURIComponent(PID))).json();
doc.querySelectorAll('.card')[0].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(1400);

console.log('--- the summary after building ---');
const sum = $("sum").textContent;
ok('the summary is not empty', $("sum").children.length >= 4, `${$("sum").children.length} cells`);
{
  const c = $("sum").querySelector(".c");
  const size = el => cssPx(w.getComputedStyle(el).fontSize);
  ok('the numbers in the summary are large', size(c.querySelector("b")) >= 16,
     w.getComputedStyle(c.querySelector("b")).fontSize);
  ok('the labels in the summary are no smaller than 12px', size(c.querySelector("span")) >= 12,
     w.getComputedStyle(c.querySelector("span")).fontSize);
}
const cells = [...$("sum").querySelectorAll('.c')].map(c => c.textContent);
ok('it carries the number of lines',
   cells.some(c => c.startsWith(String(proj.lines.length)) && /Строк/.test(c)),
   cells.join(" | "));
ok('and the length of the song', /Длина/.test(sum));
ok('and the places without singing', /Без пения/.test(sum));

console.log('\n--- the countdown while nobody sings ---');
const last = proj.lines[proj.lines.length - 1];
$("btnPlay").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(120);
w.__now = last.end + 0.4; await sleep(260);
ok('after the last line you can see how much is left',
   !$("wait").classList.contains('hide'), $("wait").textContent);
const n1 = $("waitNum").textContent, f1 = parseFloat($("waitFill").style.width);
ok('the countdown sits at the top of the stage, not amid the text',
   (w.getComputedStyle($("wait")).top || "") !== "50%",
   w.getComputedStyle($("wait")).top);
// Small type on a big screen cannot be read — we keep the sizes under control.
const px = (el, prop) => cssPx(w.getComputedStyle(el)[prop]);
ok('the number in the countdown is large', px($("waitNum"), "fontSize") >= 18,
   w.getComputedStyle($("waitNum")).fontSize);
ok('its caption is no smaller than 12px', px($("waitTtl"), "fontSize") >= 12,
   w.getComputedStyle($("waitTtl")).fontSize);
ok('the line we are waiting for is readable', px($("waitTxt"), "fontSize") >= 14,
   w.getComputedStyle($("waitTxt")).fontSize);
w.__now = last.end + 1.4; await sleep(260);
const n2 = $("waitNum").textContent, f2 = parseFloat($("waitFill").style.width);
ok('the countdown is running', n1 !== n2, `${n1} → ${n2}`);
ok('the bar is moving', f2 > f1, `${f1}% → ${f2}%`);

console.log('\n--- a short gap is not counted ---');
// in the test song the pauses between lines are fractions of a second
const gaps = [];
for (let i = 1; i < proj.lines.length; i++)
  gaps.push({at: proj.lines[i-1].end, gap: proj.lines[i].start - proj.lines[i-1].end});
const small = gaps.filter(g => g.gap > 0.2 && g.gap < 5).sort((a,b)=>a.gap-b.gap)[0];
ok('the song does have short pauses', !!small, JSON.stringify(gaps.map(g=>+g.gap.toFixed(2))));
w.__now = small.at + small.gap/2; await sleep(260);
ok(`a ${small.gap.toFixed(1)} s pause shows nothing`,
   $("wait").classList.contains('hide'), $("wait").textContent);
w.__now = proj.lines[1].start + 0.2; await sleep(260);
ok('and there is no countdown on the line itself', $("wait").classList.contains('hide'));

console.log('\n--- an empty stretch explains what lies ahead ---');
// Zoom the timeline in so that not a single line really falls into the window.
const ZOOMS = 5;
for (let i = 0; i < ZOOMS; i++)
  $("btnZoomIn").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
// the widest gap between lines
let hole = {gap: 0};
for (let i = 1; i < proj.lines.length; i++){
  const g = proj.lines[i].start - proj.lines[i-1].end;
  if (g > hole.gap) hole = {gap: g, at: proj.lines[i-1].end + g/2, next: proj.lines[i]};
}
w.__now = hole.at; await sleep(300);

w.__now = last.end + 2.5; await sleep(300);
ok('after the song the hint looks back', $("tlnext").classList.contains('back'),
   $("tlnext").textContent);

w.__now = proj.lines[0].start + 0.2; await sleep(300);
ok('while a line is on screen there is no hint', $("tlnext").classList.contains('hide'),
   $("tlnext").textContent);
console.log('\n--- a long interlude: both the countdown and the hint ---');
// The test song has no long pauses — we make one ourselves with the same mouse
// events a person would use to move a line. Ctrl+Z puts it all back afterwards.
const pd = (t,x) => { const e = new w.MouseEvent(t,{bubbles:true,cancelable:true,clientX:x});
                      Object.defineProperty(e,'pointerId',{value:1}); return e; };
$("btnPlay").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));   // stop
for (let i = 0; i < ZOOMS; i++)                 // back to the normal zoom
  $("btnZoomOut").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(200);
const LAST = proj.lines.length - 1;
const blk = doc.querySelectorAll('#blocks .blk')[LAST];
// The push has to clear the ten seconds below which a gap is a breath and
// gets no countdown. It used to be 360 px, on the belief that five zoom-ins
// and five zoom-outs come back to where they started — they did not, because
// zooming in hit its floor and the way back overshot, so the same 360 px were
// silently worth sixteen seconds instead of six.
blk.dispatchEvent(pd('pointerdown', 200));
w.dispatchEvent(pd('pointermove', 1100));      // +900 px at 60 px/s = +15 s
w.dispatchEvent(pd('pointerup', 1100));
await sleep(1000);                              // wait for the autosave
const now = (await (await fetch(API+"/api/project/"+encodeURIComponent(PID))).json()).lines[LAST];
ok('the last line was pushed away — a long interlude appeared',
   now.start > proj.lines[LAST].start + 3,
   `${proj.lines[LAST].start.toFixed(2)} → ${now.start.toFixed(2)}`);

const mid = proj.lines[LAST - 1].end + (now.start - proj.lines[LAST - 1].end) / 2;
$("btnPlay").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(120);
w.__now = mid; await sleep(300);
ok('in a long interlude there is a countdown', !$("wait").classList.contains('hide'),
   $("wait").textContent);
ok('the line that comes next is named',
   $("waitTxt").textContent.includes(now.text.slice(0, 12)), $("waitTxt").textContent);
// At the normal zoom the neighbouring lines fall into the window — no hint needed.
ok('while lines are visible there is no hint on the timeline',
   $("tlnext").classList.contains('hide'), $("tlnext").textContent);
for (let i = 0; i < ZOOMS; i++)                 // zoom in: the window sits inside the interlude
  $("btnZoomIn").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(300);
ok('in an empty window the hint shows the line ahead',
   !$("tlnext").classList.contains('hide') &&
   !$("tlnext").classList.contains('back') &&
   $("tlnext").textContent.includes(now.text.slice(0, 12)),
   $("tlnext").textContent);
for (let i = 0; i < ZOOMS; i++)
  $("btnZoomOut").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(200);

$("btnPlay").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
$("btnUndo").dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await sleep(1000);
const back2 = (await (await fetch(API+"/api/project/"+encodeURIComponent(PID))).json()).lines[LAST];
ok('the stand was put back to its original state',
   Math.abs(back2.start - proj.lines[LAST].start) < 0.01,
   `${back2.start} vs ${proj.lines[LAST].start}`);

console.log('\n--- the colour pairs are labelled ---');
const picks = [...doc.querySelectorAll('.pick')];
ok('there are two pairs', picks.length === 2, String(picks.length));
ok('each has its own label', picks.every(p => p.querySelector('b') &&
   p.querySelector('b').textContent.trim().length > 2),
   picks.map(p => p.querySelector('b') && p.querySelector('b').textContent).join(" | "));
// The swatches are the program's own buttons now: the system's colour panel
// stayed open however you pressed the page, so it was replaced.
{
  const sws = [...doc.querySelectorAll('.pick .sw')];
  ok('the swatches are labelled individually',
     sws.length === 4 && sws.every(b => (b.title || '').length > 2),
     sws.map(b => b.title).join(' | '));
}

ok('no JS errors', w.__errs.length===0, w.__errs.slice(0,2).join(' | '));
console.log(fail ? '\nFAILED: '+fail : '\nAll checks passed');
process.exit(fail?1:0);
