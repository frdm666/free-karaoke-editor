// Four things that used to take a person's own hands, against a running
// studio and a real browser: a found text that brings its times along, the
// quiet stretches turned into marks with one press, a frame of the clip
// without rendering a file, and a song packed to travel between computers.
import puppeteer from 'puppeteer';

const API = process.env.KARAOKE_API;
let fail = 0;
const ok = (n, c, e='') => { console.log((c?'  ✓ ':'  ✗ ')+n+(e?' — '+e:'')); if(!c) fail++; };
const sleep = ms => new Promise(r=>setTimeout(r,ms));
const post = async (path, body) => (await (await fetch(API + path, {method:'POST',
  headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})).json());
const get = async path => (await (await fetch(API + path)).json());

async function finish(jid, seconds = 180){
  for (let i = 0; i < seconds * 2; i++){
    const j = await get('/api/job?id=' + jid);
    if (j.done || j.error) return j;
    await sleep(500);
  }
  return {done:false, ok:false, log:['timed out']};
}

console.log('--- a found text brings its times along ---');
// The stub library answers with a synced record, as LRCLIB does.
const found = await post('/api/lyrics/find', {track: 'Stub Song', duration: 21});
const timedOne = (found.found || []).find(f => f.timed);
ok('a record with a timing is offered', !!timedOne,
   JSON.stringify((found.found || []).map(f => f.timed)));
if (timedOne){
  ok('the words come without the stamps',
     !/^\s*\[\d+:/.test(timedOne.text || ''), (timedOne.text || '').slice(0, 24));
  const lines = (timedOne.textTimed || '').split('\n').filter(Boolean);
  const pegs = lines.filter(l => /^\s*\[\d+:\d/.test(l));
  ok('and the timed copy carries pegs', pegs.length > 0, pegs.slice(0, 2).join(' | '));
  ok('sparse ones, not a stamp on every line', pegs.length < lines.length,
     `${pegs.length} of ${lines.length}`);
}

// A song of our own to work on, with a stretch of silence in it.
const built = await finish((await post('/api/new', {
  audio: process.env.KARAOKE_SONG, lyrics: process.env.KARAOKE_TEXT,
  align: 'energy', separate: false, title: 'Packed Song', titleSet: true})).job);
ok('the song is built', built.ok, (built.log || []).slice(-1)[0]);
const pid = built.result;
ok('and it is called what was typed for it',
   (await get('/api/project/' + encodeURIComponent(pid))).title === 'Packed Song');

console.log('\n--- a frame of the clip, without rendering one ---');
const shot = await fetch(`${API}/api/project/${encodeURIComponent(pid)}/still?at=1`);
const png = Buffer.from(await shot.arrayBuffer());
ok('the frame comes back as a picture', shot.ok
   && png.slice(1, 4).toString() === 'PNG', shot.status + ' ' + png.slice(0, 8).toString('hex'));
ok('and it is a whole frame, not a thumbnail', png.length > 5000, png.length);
const card = await fetch(`${API}/api/project/${encodeURIComponent(pid)}/still?at=0&opening=1`);
const cardPng = Buffer.from(await card.arrayBuffer());
ok('the opening can be looked at too', card.ok && cardPng.length > 5000, cardPng.length);
ok('and it is not the same frame as the song',
   Buffer.compare(png, cardPng) !== 0);

console.log('\n--- the quiet stretches become marks with one press ---');
const b = await puppeteer.launch({headless:'new', args:['--no-sandbox','--disable-dev-shm-usage']});
const p = await b.newPage();
const errs = []; p.on('pageerror', e => errs.push(String(e)));
// One handler, two moods: the questions are dismissed except when a test
// step means to walk through one.
let dlgMode = 'dismiss';
p.on('dialog', d => dlgMode === 'accept' ? d.accept() : d.dismiss());
await p.setViewport({width:1366, height:900});
// The stand's song is short and holds no five-second silence of its own; what
// is under test is the offer and the press, not the hearing — that is measured
// on real audio elsewhere. So the song's record arrives in the window with the
// stretches the program would have heard, by the same road it always takes.
await p.evaluateOnNewDocument(id => {
  const real = window.fetch;
  window.fetch = async (url, opts) => {
    const r = await real(url, opts);
    if (typeof url === 'string' && url.endsWith('/api/project/' + id)){
      const data = await r.json();
      if (!(data.quiet || []).length)
        data.quiet = [{start: 3.0, end: 9.0}, {start: 14.0, end: 20.0}];
      return new Response(JSON.stringify(data), {status: 200,
        headers: {'Content-Type': 'application/json'}});
    }
    return r;
  };
}, encodeURIComponent(pid));
await p.goto(API + '/', {waitUntil:'networkidle0'});
await sleep(700);
await p.waitForSelector('.card', {timeout:20000});
await p.evaluate(id => {
  const card = [...document.querySelectorAll('.card')].find(c => c.dataset.id === id);
  (card || document.querySelector('.card')).click();
}, pid);
await p.waitForSelector('#scrEdit:not(.hide)', {timeout:20000});
await sleep(900);

// Start from no marks at all, whatever the song came with.
await p.$eval('#edNoText', e => { e.value = ''; e.dispatchEvent(new Event('change', {bubbles:true})); });
await sleep(200);
const chips = await p.$$('#sum .qchip i');
ok('the heard stretches offer to be marked', chips.length > 0, chips.length);
if (chips.length){
  await chips[0].click();
  await sleep(400);
  const field = await p.$eval('#edNoText', e => e.value.trim());
  ok('and one press writes the mark into the field', field.length > 0, field);
  ok('the chip then shows as taken',
     await p.$eval('#sum .qchip', e => e.classList.contains('taken')));
  const before = field;
  const all = await p.$('#sum .c.wide button');
  if (all){
    await all.click();
    await sleep(500);
    const after = await p.$eval('#edNoText', e => e.value.trim());
    ok('and “mark them all” takes the rest', after.length >= before.length, after);
  }
}

console.log('\n--- the keep button walks its circle: full, quiet, yours ---');
// One press leaves the line to the original, another holds the original back
// to a guide — to be sung along with — and a third gives the line back.
await p.click('#scroll .ln');
await sleep(300);
const keepState = async () => {
  await sleep(900);                     // the autosave walks to the disk
  const d = await get('/api/project/' + encodeURIComponent(pid));
  return {keep: !!d.lines[0].keep, soft: !!d.lines[0].keepSoft,
          btn: await p.$eval('#btnKeep', e => e.textContent)};
};
await p.click('#btnKeep');
let ks = await keepState();
ok('one press leaves the line to the original', ks.keep && !ks.soft,
   JSON.stringify(ks));
await p.click('#btnKeep');
ks = await keepState();
ok('a second holds it back to a guide', ks.keep && ks.soft, JSON.stringify(ks));
ok('and the button says so', /quiet|тихо/i.test(ks.btn), ks.btn);
await p.click('#btnKeep');
ks = await keepState();
ok('a third gives the line back', !ks.keep && !ks.soft, JSON.stringify(ks));

console.log('\n--- the timing leaves for UltraStar and the subtitles ---');
const usJob = await finish((await post(`/api/project/${encodeURIComponent(pid)}/export`,
  {kind: 'ultrastar'})).job);
ok('the UltraStar file is written', usJob.ok && usJob.result && !!usJob.result.path,
   (usJob.log || []).slice(-1)[0]);
if (usJob.ok && usJob.result.path){
  const fs = await import('fs');
  const us = fs.readFileSync(usJob.result.path, 'utf8');
  ok('with the song named in its header', us.includes('#TITLE:Packed Song'),
     us.split('\n')[0]);
  ok('its notes freestyle and its end marked',
     /\nF \d+ \d+ 0 /.test(us) && us.trim().endsWith('E'));
  fs.unlinkSync(usJob.result.path);
}
const assJob = await finish((await post(`/api/project/${encodeURIComponent(pid)}/export`,
  {kind: 'ass'})).job);
ok('the subtitles are written', assJob.ok && assJob.result && !!assJob.result.path,
   (assJob.log || []).slice(-1)[0]);
if (assJob.ok && assJob.result.path){
  const fs = await import('fs');
  const sub = fs.readFileSync(assJob.result.path, 'utf8');
  ok('with karaoke tags on the words', sub.includes('{\\k'), sub.slice(0, 60));
  ok('and the styles for both voices', sub.includes('Style: Voice1')
     && sub.includes('Style: Voice2'));
  fs.unlinkSync(assJob.result.path);
}

console.log('\n--- found texts stand in the other-lyrics picker ---');
// The search that worked only while building now answers in the editor too.
// Through the very button a person presses: the window's functions live in
// their own closure, and the test has no back door to them.
dlgMode = 'accept';
await p.click('#btnLyrics');
await sleep(1800);
dlgMode = 'dismiss';
const rowsSeen = await p.evaluate(() => {
  const rows = [...document.querySelectorAll('#brBody .row.found2 .nm')]
    .map(e => e.textContent);
  document.getElementById('browser').classList.add('hide');
  return rows;
});
ok('the found records are offered above the files', rowsSeen.length > 0,
   JSON.stringify(rowsSeen));
ok('and a timed one says so', rowsSeen.some(t => /разметк|timing/i.test(t)),
   JSON.stringify(rowsSeen));

console.log('\n--- the cover can be given, cut from a clip, and taken away ---');
// A song from a file on disk had nowhere to get a cover. Now any picture
// serves — and so does a clip: a frame is cut from a third of the way in.
const { execFileSync } = await import('child_process');
const os2 = await import('os');
const path2 = await import('path');
const fs2 = await import('fs');
const ctmp = fs2.mkdtempSync(path2.join(os2.tmpdir(), 'cover61_'));
const clip = path2.join(ctmp, 'clip.mp4');
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'lavfi',
  '-i', 'color=c=red:s=64x36:d=3', '-pix_fmt', 'yuv420p', clip]);
const cSet = await post(`/api/project/${encodeURIComponent(pid)}/cover`, {path: clip});
ok('frames are cut out of the clip — a slideshow', cSet.ok === true
   && cSet.cover === true && cSet.frames >= 2, JSON.stringify(cSet));
let pd = await get('/api/project/' + encodeURIComponent(pid));
ok('and the song stands on it now', pd.cover === 'cover.jpg' && pd.coverBg === true,
   `${pd.cover} / ${pd.coverBg}`);
ok('with the set written down for the video',
   Array.isArray(pd.coverSet) && pd.coverSet.length >= 2,
   JSON.stringify(pd.coverSet || null));
const stillC = Buffer.from(await (await fetch(
  `${API}/api/project/${encodeURIComponent(pid)}/still?at=1`)).arrayBuffer());
ok('the preview frame changed with the backdrop',
   Buffer.compare(stillC, png) !== 0 && stillC.length > 5000, stillC.length);
// A cover can come by link too — the stand's own frame endpoint serves as
// the picture on the other end of one.
const byUrl = await post(`/api/project/${encodeURIComponent(pid)}/cover`,
  {url: `${API}/api/project/${encodeURIComponent(pid)}/still?at=2`});
ok('a cover arrives by link', byUrl.ok === true && byUrl.cover === true,
   JSON.stringify(byUrl));
// Two ways to set the darkness: the slider for the eye, the field for a
// number you already know. Both must agree, and both must reach the disk.
{
  await p.evaluate(() => {
    document.getElementById('grpCoverDark').classList.remove('hide');
  });
  await p.click('#nCoverDark', {clickCount: 3});
  await p.type('#nCoverDark', '83');
  await sleep(1200);
  const shown = await p.$eval('#rCoverDark', e => +e.value);
  ok('a typed percent moves the slider with it', shown === 83, shown);
  const saved = await get('/api/project/' + encodeURIComponent(pid));
  ok('and a typed percent reaches the disk', saved.coverDark === 83,
     saved.coverDark);
  // nonsense in the field must not stick
  await p.click('#nCoverDark', {clickCount: 3});
  await p.type('#nCoverDark', '999');
  await sleep(1200);
  const clamped = await p.$eval('#rCoverDark', e => +e.value);
  ok('an impossible percent is clamped, not obeyed', clamped === 95, clamped);
}

// The darkness knob is saved with the ordinary edits and clamped.
const pdNow = await get('/api/project/' + encodeURIComponent(pid));
await post(`/api/project/${encodeURIComponent(pid)}/timings`,
  {lines: pdNow.lines, coverDark: 40});
const pdDark = await get('/api/project/' + encodeURIComponent(pid));
ok('the backdrop darkness is remembered', pdDark.coverDark === 40, pdDark.coverDark);

const cOff = await post(`/api/project/${encodeURIComponent(pid)}/cover`, {remove: true});
ok('and it can be taken away', cOff.ok === true && cOff.cover === false,
   JSON.stringify(cOff));
pd = await get('/api/project/' + encodeURIComponent(pid));
ok('leaving the plain background', !pd.cover && !pd.coverBg && !pd.coverSet,
   `${pd.cover} / ${pd.coverBg} / ${pd.coverSet}`);
fs2.rmSync(ctmp, {recursive: true, force: true});

console.log('\n--- and the song travels in one file ---');
// a corrupt zip gets a calm sentence, not a stack trace
const badZip = await fetch(`${API}/api/unpack`, {method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({path: process.env.KARAOKE_SONG})});
ok('a non-zip is refused politely', badZip.status === 400, badZip.status);

const packed = await post(`/api/project/${encodeURIComponent(pid)}/pack`, {});
ok('the song packs', !!packed.path && /\.karaoke\.zip$/.test(packed.path || ''), packed.path);
const backIn = await post('/api/unpack', {path: packed.path});
ok('and unpacks back into the list', !!backIn.id, JSON.stringify(backIn));
if (backIn.id){
  const twin = await get('/api/project/' + encodeURIComponent(backIn.id));
  ok('as the same song it was', twin.title === 'Packed Song', twin.title);
  ok('with its lines in place', (twin.lines || []).length > 0, (twin.lines || []).length);
  await post(`/api/project/${encodeURIComponent(backIn.id)}/delete`, {});
}

console.log('\n--- the beat grid ---');
// A song at one tempo is a ruler. The grid has to survive a save and a
// reopening, and the drawing has to cope with it — a canvas that throws takes
// the whole editor down with it.
{
  await p.evaluate(() => {
    document.getElementById('chkGrid').click();
    const b = document.getElementById('nBpm');
    b.value = '174'; b.dispatchEvent(new Event('input', {bubbles: true}));
  });
  await sleep(300);
  await p.click('#btnBeatOne');
  await sleep(1200);
  const rec = await get('/api/project/' + encodeURIComponent(pid));
  ok('the grid is saved with the song',
     rec.grid && rec.grid.on === true && Math.abs(rec.grid.bpm - 174) < 0.01,
     JSON.stringify(rec.grid));
  await p.evaluate(() => {
    document.getElementById('chkSixteen').click();
  });
  await sleep(900);
  const rec2 = await get('/api/project/' + encodeURIComponent(pid));
  ok('and sixteenths are remembered too', rec2.grid && rec2.grid.sub === 4,
     JSON.stringify(rec2.grid));
  // zoom right in: the floor used to be four seconds, and the magnet reached
  // far enough at four seconds that there was nothing to be done about it
  const deep = await p.evaluate(() => {
    for (let i = 0; i < 12; i++) document.getElementById('btnZoomIn').click();
    return document.getElementById('zoomNote').textContent;
  });
  ok('the timeline zooms in past a second', /^0\.\d/.test(deep.trim()), deep);
}

console.log('\n--- a clip can stand behind the lyrics ---');
// The backdrop is a real file here, made on the spot: the endpoint is the
// only place that turns any clip into the small one a song carries around.
{
  const fsx = await import('fs');
  const os = await import('os');
  const pathx = await import('path');
  const { execFileSync } = await import('child_process');
  const clip = pathx.join(os.tmpdir(), 'karaoke-back-' + process.pid + '.mp4');
  let made = true;
  try{
    execFileSync('ffmpeg', ['-y', '-v', 'error', '-f', 'lavfi', '-i',
      'color=c=0x203040:s=320x180:d=3', '-r', '8', clip]);
  }catch(e){ made = false; }
  ok('a clip to stand behind is made', made);
  if (made){
    const set = await post(`/api/project/${encodeURIComponent(pid)}/backdrop`,
                           {path: clip});
    ok('the studio takes it', set.ok === true && set.backdrop === true,
       JSON.stringify(set));
    const rec = await get('/api/project/' + encodeURIComponent(pid));
    ok('and the song remembers it', rec.backdrop === 'backdrop.mp4', rec.backdrop);
    // the frame preview must draw with it and not fall over
    const shot = await fetch(API + `/api/project/${encodeURIComponent(pid)}/still?at=2`);
    ok('a frame still draws with the clip behind', shot.ok, shot.status);
    const off = await post(`/api/project/${encodeURIComponent(pid)}/backdrop`,
                           {off: true});
    ok('and it can be taken away again',
       off.ok === true && off.backdrop === false, JSON.stringify(off));
    const rec2 = await get('/api/project/' + encodeURIComponent(pid));
    ok('the song forgets it too', !rec2.backdrop, rec2.backdrop);
    try{ fsx.unlinkSync(clip); }catch(e){}
  }
  const bad = await post(`/api/project/${encodeURIComponent(pid)}/backdrop`,
                         {path: '/nowhere/at/all.mp4'});
  ok('a path to nothing is refused, not swallowed', !!bad.error, JSON.stringify(bad));
}

ok('nothing in the window went wrong', errs.length === 0, errs.slice(0, 2).join(' | '));
await b.close();
await post(`/api/project/${encodeURIComponent(pid)}/delete`, {});
const fs = await import('fs');
if (packed.path) try{ fs.unlinkSync(packed.path); }catch(e){}
console.log(fail ? '\nFAILED: ' + fail : '\nAll checks passed');
process.exit(fail ? 1 : 0);
