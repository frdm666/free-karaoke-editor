// The page's look, in a real browser: the colours a person picks for the
// finished page go on the stage that previews it — and nowhere else. They used
// to go on the whole window: an orange page made an orange editor, buttons,
// panels and timeline included, and the person could not tell the tool from
// the work.
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

// What a person sees: the computed colours of the window, the toolbar and
// the stage.
const look = () => p.evaluate(() => {
  const cs = el => getComputedStyle(el);
  return {
    body: cs(document.body).backgroundImage,
    button: cs(document.getElementById('btnFit')).color,
    panel: cs(document.querySelector('.side') || document.body).backgroundColor,
    stage: cs(document.getElementById('stage')).backgroundColor,
    line: cs(document.querySelector('#scroll .ln.cur') || document.querySelector('#scroll .ln')).color,
  };
});
const before = await look();
ok('the stage starts in the page\'s default look', /rgb\(10, 11, 20\)/.test(before.stage), before.stage);

console.log('--- an orange page ---');
await p.$eval('#colBg', e => { e.value = '#d4922b'; e.dispatchEvent(new Event('input', {bubbles:true})); });
await sleep(300);
const after = await look();
ok('the stage took the colour', /rgb\(212, 146, 43\)/.test(after.stage), after.stage);
ok('the window behind the panels did not', after.body === before.body, after.body.slice(0, 60));
ok('the buttons kept their colour', after.button === before.button, `${before.button} → ${after.button}`);
ok('the side panel kept its colour', after.panel === before.panel, `${before.panel} → ${after.panel}`);

console.log('\n--- the text colour follows the page too ---');
await p.$eval('#colTx', e => { e.value = '#1a1000'; e.dispatchEvent(new Event('input', {bubbles:true})); });
await sleep(300);
const dark = await look();
ok('the current line took a dark text on the orange', dark.line !== after.line, `${after.line} → ${dark.line}`);
ok('and the buttons are still what they were', dark.button === before.button, dark.button);

ok('no errors in the page', errs.length === 0, errs.join(' | ').slice(0, 200));
await b.close();
console.log(fail ? `\n${fail} FAILED` : '\nAll checks passed');
process.exit(fail ? 1 : 0);
