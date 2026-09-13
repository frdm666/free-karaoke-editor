// The Frame button in a real browser: a press opens the frame, another press
// closes it, and the button shows which it is. It used to open only — the
// way out was the cross in the frame's corner, and a person who pressed the
// button again to put the frame away got nothing for it.
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

const shown = () => p.$eval('#stillBox', e => !e.classList.contains('hide'));
const lit = () => p.$eval('#btnStill', e => e.classList.contains('on'));

ok('the frame starts put away', !(await shown()));
ok('and the button is not lit', !(await lit()));

console.log('--- one press opens ---');
await p.click('#btnStill');
await sleep(300);
ok('the frame is shown', await shown());
ok('the button is lit while it is', await lit());
// the picture itself may take a moment; the box must not go away on its own
await sleep(2500);
ok('and it stays', await shown());
ok('the picture arrived', await p.$eval('#stillImg', e => e.src.startsWith('blob:')),
   await p.$eval('#stillImg', e => e.src.slice(0, 20)));

console.log('\n--- the next press closes ---');
await p.click('#btnStill');
await sleep(300);
ok('the frame is put away by the same button', !(await shown()));
ok('and the button is not lit', !(await lit()));

console.log('\n--- the cross still works ---');
await p.click('#btnStill');
await sleep(300);
ok('opened again', await shown());
await p.click('#stillHide');
await sleep(200);
ok('closed by the cross', !(await shown()));
ok('with the button unlit', !(await lit()));

ok('no errors in the page', errs.length === 0, errs.join(' | ').slice(0, 200));
await b.close();
console.log(fail ? `\n${fail} FAILED` : '\nAll checks passed');
process.exit(fail ? 1 : 0);
