// The timeline under the hand, in a real browser. A press on empty timeline
// while the song stands still moves the playhead to the press — and nothing
// else moves. It used to be the other way round: the window always kept the
// playhead a third of the way across, so a press LEFT of it sent the whole
// track sliding RIGHT until the pressed point lay under the playhead, and
// the eye read it as a jump the wrong way. The window follows only while
// the song plays, or when the playhead has left it.
import puppeteer from 'puppeteer';

const API = process.env.KARAOKE_API;
let fail = 0;
const ok = (n, c, e='') => { console.log((c?'  ✓ ':'  ✗ ')+n+(e?' — '+e:'')); if(!c) fail++; };
const sleep = ms => new Promise(r=>setTimeout(r,ms));

const b = await puppeteer.launch({headless:'new', args:['--no-sandbox','--disable-dev-shm-usage']});
const p = await b.newPage();
const errs = []; p.on('pageerror', e => errs.push(String(e)));
p.on('dialog', d => d.dismiss());
await p.setViewport({width:1366, height:900});
await p.goto(API+'/', {waitUntil:'networkidle0'});
await sleep(700);
await p.waitForSelector('.card', {timeout:20000});
await p.click('.card');
await p.waitForSelector('#scrEdit:not(.hide)', {timeout:20000});
await sleep(700);

// Everything is judged by what a person can see: the clock, the playhead
// element, and where the line blocks stand on the screen.
const clock = async () => (await p.$eval('#tCur', e => e.textContent))
  .split(':').reduce((m, x) => m * 60 + parseFloat(x), 0);
const phead = () => p.$eval('#phead', e => parseFloat(e.style.left));
const blocks = () => p.$$eval('.blk', es => es.map(e => Math.round(e.getBoundingClientRect().left)));
const box = await p.$eval('#tlwrap', e => {
  const r = e.getBoundingClientRect();
  return {x: r.left, y: r.top, w: r.width, h: r.height};
});
const zoom = await p.$eval('#zoomNote', e => parseFloat(e.textContent));
ok('the window shows a known stretch of seconds', zoom > 0, String(zoom));

// Stand somewhere in the middle of the song, the way a person does — by
// picking a line from the list.
await p.evaluate(() => document.querySelectorAll('#scroll .ln')[2].click());
await sleep(600);
let t0 = await clock();
for (let i = 0; i < 6 && t0 < 0.4 * zoom; i++){
  await p.keyboard.press('ArrowRight'); await sleep(150); t0 = await clock();
}
ok('the playhead stands well inside the window', t0 >= 0.4 * zoom, t0.toFixed(2));
const x0 = await phead(), before = await blocks();
ok('and it is on the screen', x0 >= 0 && x0 <= box.w, `${x0.toFixed(0)} of ${box.w.toFixed(0)}`);

console.log('--- a press left of the playhead ---');
const fx = 0.15;
await p.mouse.click(box.x + box.w * fx, box.y + 6);
await sleep(400);
const t1 = await clock(), x1 = await phead(), after = await blocks();
// the press meant "this many seconds left of the playhead": pixels over the
// window's seconds-per-pixel
const meant = t0 - (x0 / box.w - fx) * zoom;
ok('the song moved back by what the press meant',
   Math.abs(t1 - meant) < 0.35, `${t0.toFixed(2)} → ${t1.toFixed(2)}, meant ${meant.toFixed(2)}`);
ok('the playhead now stands where the press was',
   Math.abs(x1 - box.w * fx) < box.w * 0.02, `${x1.toFixed(0)} vs ${(box.w * fx).toFixed(0)}`);
ok('and the line blocks did not move under the hand',
   before.length === after.length && before.every((v, i) => Math.abs(v - after[i]) <= 1),
   `${before.slice(0, 3)} → ${after.slice(0, 3)}`);

console.log('\n--- zooming in keeps the playhead where it is on the screen ---');
await p.click('#btnZoomIn');
await sleep(300);
const t2 = await clock(), x2 = await phead();
ok('the song did not move', Math.abs(t2 - t1) < 0.05, `${t1.toFixed(2)} → ${t2.toFixed(2)}`);
ok('the playhead kept its place on the screen', Math.abs(x2 - x1) < 3,
   `${x1.toFixed(0)} → ${x2.toFixed(0)}`);
await p.click('#btnZoomOut');
await sleep(300);

console.log('\n--- the window lets go when the playhead leaves it ---');
await p.mouse.click(box.x + box.w * 0.04, box.y + 6);
await sleep(300);
const near = await phead(), tn = await clock();
ok('a press near the left edge is honoured', near < box.w * 0.07, near.toFixed(0));
// where the window begins now, read off the screen; then walk the playhead
// out of its right edge five seconds at a time
const winStart = tn - near / box.w * zoom;
let t3 = tn, x3 = near;
for (let i = 0; i < 8 && t3 <= winStart + zoom; i++){
  await p.keyboard.press('ArrowRight'); await sleep(250);
  t3 = await clock(); x3 = await phead();
}
ok("the playhead walked past the window's edge", t3 > winStart + zoom, `${t3.toFixed(2)} > ${(winStart + zoom).toFixed(2)}`);
ok('and the window followed: the playhead is on the screen, not past it',
   x3 >= 0 && x3 <= box.w * 0.9, `${x3.toFixed(0)} of ${box.w.toFixed(0)}`);

ok('no errors in the page', errs.length === 0, errs.join(' | ').slice(0, 200));
await b.close();
console.log(fail ? `\n${fail} FAILED` : '\nAll checks passed');
process.exit(fail ? 1 : 0);
