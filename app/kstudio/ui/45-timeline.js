/* ================= the timeline ================= */
let zoom = 15;                  // how many seconds are visible
function pps(){ return $("tlwrap").clientWidth / zoom; }   // pixels per second
function viewStart(){ return clamp(mediaTime() - zoom*0.35, 0, Math.max(dur-zoom,0)); }
function xOf(t){ return (t - viewStart()) * pps(); }
function tOf(x){ return viewStart() + x / pps(); }

// Painting the waveform is the priciest thing this window does, and it used
// to happen sixty times a second whether anything moved or not — a paused
// editor warmed the room. It now runs only when the picture would differ:
// every place that changes the data marks it dirty, and the clock tick
// repaints on the mark or once the view itself has moved a pixel.
let waveDirty = true, waveSig = "";
function drawWave(){ waveDirty = true; }
// The whole song in one strip: the marks, the kept lines, the quiet
// stretches, and the window that is on screen right now. Click or drag to
// jump — on a long song the wheel is a hike, and this is a step.
function paintMap(){
  // Decoration must never take the editor down with it: a canvas without
  // some method (a test stand's stub, an odd browser) skips the strip.
  try{ paintMapInner(); }catch(e){}
}
function paintMapInner(){
  const c = $("mmap");
  if (!c || !dur) return;
  const w = c.clientWidth, h = c.clientHeight;
  if (!w) return;
  const pw = Math.round(w * devicePixelRatio), ph = Math.round(h * devicePixelRatio);
  if (c.width !== pw || c.height !== ph){ c.width = pw; c.height = ph; }
  const g = c.getContext("2d");
  if (g.setTransform) g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  else g.scale(devicePixelRatio, devicePixelRatio);
  g.clearRect(0, 0, w, h);
  const X = t => t / dur * w;
  // quiet stretches: a shade dimmer than the strip itself
  g.fillStyle = "rgba(0,0,0,.35)";
  (quiet || []).forEach(q => g.fillRect(X(q.start), 0, X(q.end) - X(q.start), h));
  // “no words here” marks, in the warning colour
  g.fillStyle = "rgba(255,204,77,.28)";
  marks.forEach(([a, b]) => g.fillRect(X(a), 0, X(b) - X(a), h));
  // the lines: thin ticks along the base; kept ones taller and in their hue
  lines.forEach(ln => {
    const x = X(ln.start), wd = Math.max(1, X(ln.end) - x);
    if (ln.keep){
      g.fillStyle = ln.keepSoft ? "rgba(126,224,138,.5)" : "rgba(126,224,138,.8)";
      g.fillRect(x, 2, wd, h - 4);
    } else {
      g.fillStyle = ln.voice === 2 ? colors[1] : colors[0];
      g.globalAlpha = 0.55;
      g.fillRect(x, h - 6, wd, 4);
      g.globalAlpha = 1;
    }
  });
  // the window now on screen
  const v0 = viewStart(), v1 = v0 + zoom;
  g.strokeStyle = "rgba(255,255,255,.65)";
  g.lineWidth = 1;
  g.strokeRect(X(v0) + 0.5, 0.5, Math.max(2, X(v1) - X(v0)) - 1, h - 1);
  // the playhead
  g.fillStyle = colors[0];
  g.fillRect(X(mediaTime()) - 0.5, 0, 1.5, h);
}

function paintWave(){
  const c=$("wave"), w=$("tlwrap").clientWidth, h=$("tlwrap").clientHeight;
  // Reallocating the canvas buffer on every repaint fed the garbage
  // collector for nothing: the size only changes when the window does.
  const pw = Math.round(w*devicePixelRatio), ph = Math.round(h*devicePixelRatio);
  if (c.width !== pw || c.height !== ph){ c.width = pw; c.height = ph; }
  const g=c.getContext("2d");
  // setTransform resets the scale absolutely; the test stands' canvas stub
  // knows only scale, where nothing accumulates anyway
  if (g.setTransform) g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  else g.scale(devicePixelRatio, devicePixelRatio);
  g.clearRect(0,0,w,h);

  // Stretches without singing — intro, interlude, solo. They are shaded: no
  // line belongs there, and the eye catches it at once.
  const kq = pps(), vq = viewStart();
  quiet.forEach(q => {
    const x = (q.start - vq) * kq, wd = (q.end - q.start) * kq;
    if (x + wd < 0 || x > w) return;
    g.fillStyle = "rgba(255,255,255,.05)";
    g.fillRect(x, 0, wd, h);
    g.fillStyle = "rgba(139,147,176,.85)";
    g.font = "10px system-ui, sans-serif";
    if (wd > 74) g.fillText(T.waveQuiet, x + 6, 12);
  });

  // The beat grid, under everything a person put there: bars carry a line
  // through the whole height, beats a shorter one, sixteenths only a tick —
  // and only while there is room enough for them to be told apart.
  if (grid.on){
    const st = gridStep();
    if (st > 0 && st * kq > 3){
      const first = Math.floor((vq - grid.beat0) / st) - 1;
      const beats = grid.sub || 1;
      for (let n = first; ; n++){
        const t = grid.beat0 + n * st;
        const x = (t - vq) * kq;
        if (x > w) break;
        if (x < 0) continue;
        // which of the four beats of a bar this is, and whether it is a beat
        // at all rather than a subdivision between two
        const idx = Math.round((t - grid.beat0) / st);
        const onBeat = idx % beats === 0;
        const onBar = idx % (beats * 4) === 0;
        g.fillStyle = onBar ? "rgba(255,204,77,.30)"
                    : onBeat ? "rgba(255,255,255,.16)"
                             : "rgba(255,255,255,.07)";
        g.fillRect(Math.round(x), onBar ? 0 : (onBeat ? 0 : h * 0.62),
                   onBar ? 2 : 1, onBar ? h : (onBeat ? h : h * 0.38));
      }
    }
  }

  // The marks a person made, and the one being dragged right now.
  const all = marks.concat(markFrom !== null && markTo !== null
                           ? [[Math.min(markFrom, markTo), Math.max(markFrom, markTo)]] : []);
  all.forEach(([a, b], i) => {
    const x = (a - vq) * kq, wd = (b - a) * kq;
    if (x + wd < 0 || x > w) return;
    g.fillStyle = i < marks.length ? "rgba(255,204,77,.16)" : "rgba(255,204,77,.28)";
    g.fillRect(x, 0, wd, h);
    g.fillStyle = "rgba(255,204,77,.55)";
    g.fillRect(x, 0, 1.5, h);
    g.fillRect(x + wd - 1.5, 0, 1.5, h);
    if (wd > 60){
      g.fillStyle = "rgba(255,204,77,.9)";
      g.font = "10px system-ui, sans-serif";
      g.fillText(T.waveNoText, x + 6, h - 6);
    }
  });

  if (!envelope.length) return;
  const v0=viewStart(), mid=40;
  g.fillStyle="rgba(120,150,190,.42)";
  for (let x=0; x<w; x++){
    const t=v0 + x/w*zoom, i=Math.floor(t/envHop);
    if (i<0 || i>=envelope.length) continue;
    const a=Math.min(envelope[i]*1.7,1)*34;
    g.fillRect(x, mid-a, 1, a*2);
  }
  g.strokeStyle="rgba(255,204,77,.35)"; g.lineWidth=1;
  onsets.forEach(t => { const x=xOf(t); if (x>=0&&x<=w){
    g.beginPath(); g.moveTo(x+.5,4); g.lineTo(x+.5,76); g.stroke(); } });

  // The words of every line, always in sight: a thin band along the bottom of
  // the wave, one box per word, neighbouring lines in alternating shades — so
  // the whole layout can be watched without selecting anything. The selected
  // line's own lane below stays the place to grab and drag.
  const wy = h - 11, wh = 7;
  if (kq < 8) return;          // words this small are noise, and the costliest kind
  lines.forEach((ln, li) => {
    if (!ln.words || ln.end == null || ln.start == null) return;
    if (ln.end < vq || ln.start > vq + zoom) return;
    g.fillStyle = li % 2 ? "rgba(255,204,77,.30)" : "rgba(150,175,215,.38)";
    ln.words.forEach(word => {
      const x = (word.t - vq) * kq, wd = Math.max((word.d || 0) * kq, 1.5);
      if (x + wd < 0 || x > w) return;
      g.fillRect(x, wy, Math.max(wd - 1, 1), wh);
    });
  });
}
/* The blocks are created once and live in a container that is simply shifted.
   Rebuilding them every frame means 60 DOM rebuilds a second, which visibly
   slows the window down on a song of sixty lines. */
// Lines the model barely heard, measured against this song and not against a
// number picked in advance: on a screamed vocal every word sits low, and what
// gives a bad line away is standing out from its neighbours.
let weakBelow = null;
function figureDoubt(){
  const got = lines.map(l => l.sure).filter(v => typeof v === "number").sort((a, b) => a - b);
  weakBelow = got.length >= 8 ? got[got.length >> 1] * 0.5 : null;
}
function doubtful(ln){
  return weakBelow !== null && typeof ln.sure === "number" && ln.sure < weakBelow;
}
const blockEls = [];
function makeBlocks(){
  const box = $("blocks");
  box.innerHTML = ""; blockEls.length = 0;
  lines.forEach((ln, i) => {
    const e = document.createElement("div");
    e.className = "blk" + (ln.voice === 2 ? " v2" : "") + (ln.keep ? " keep" : "")
                + (doubtful(ln) ? " doubt" : "") + (ln.lock ? " lock" : "");
    e.dataset.i = i;
    e.appendChild(document.createTextNode((i+1) + ". " + ln.text));
    // Grips on both sides: the right one moves the end of the line, the left
    // one the start. There used to be no left grip, so the start could not be
    // moved without moving the whole line.
    for (const side of ["left", "right"]){
      const grip = document.createElement("div");
      grip.className = "grip " + side;
      grip.dataset.grip = side;
      grip.title = side === "left" ? T.gripStart : T.gripEnd;
      e.appendChild(grip);
    }
    box.appendChild(e);
    blockEls.push(e);
  });
  updateLanes();
  layoutBlocks();
  paintMarks();          // the blocks are rebuilt — the marks have to come back
}
// The second lane is only needed when the song has a second voice: otherwise
// the timeline would be twice as tall for nothing.
function updateLanes(){
  const two = lines.some(l => l.voice === 2);
  const wrap = $("tlwrap");
  if (wrap.classList.contains("twolane") === two) return;
  wrap.classList.toggle("twolane", two);
  drawWave();                       // the canvas under the timeline changed height
}
function layoutBlock(i){
  const e = blockEls[i], ln = lines[i];
  if (!e) return;
  const k = pps();
  e.style.left = (ln.start * k) + "px";
  e.style.width = Math.max((ln.end - ln.start) * k, 14) + "px";
  e.classList.toggle("sel", i === sel);
  e.classList.toggle("bad", !!(window.__badLines && window.__badLines.has(i)));
}
function layoutBlocks(){
  for (let i = 0; i < blockEls.length; i++) layoutBlock(i);
  makeWords();
  showNextHint();
}
// An empty timeline window looks broken: not a single line in sight and no clue
// what is ahead. A hint at the edge says where things are going and how long.
function showNextHint(){
  const box = $("tlnext");
  if (!box) return;
  const w = $("tlwrap").clientWidth, a = viewStart(), b = a + zoom;
  const visible = lines.some(l => l.end > a && l.start < b);
  if (visible || !lines.length){ box.classList.add("hide"); return; }
  const t = mediaTime();
  const next = lines.find(l => l.start >= b);
  const back = !next;
  const target = next || lines.filter(l => l.end <= a).pop() || lines[0];
  const away = back ? t - target.end : target.start - t;
  box.classList.toggle("back", back);
  box.classList.remove("hide");
  box.innerHTML = (back ? T.backLast : "")
    + `<b>${esc(target.text.slice(0, 40))}</b> `
    + (back ? "" : "▶ ")
    + (away >= 60 ? fmt(away) : Math.max(0, Math.round(away)) + T.sec)
    + (back ? T.ago : "");
}

/* ---------- the words of the selected line ----------
   Singing inside a line is uneven: a pause, a stretched word, a patter. The
   syllable layout knows nothing of that, so every word can be moved on its own. */
const wordEls = [];
function makeWords(){
  const box = $("words");
  if (!box) return;
  const ln = sel >= 0 ? lines[sel] : null;
  if (!ln){ box.innerHTML = ""; wordEls.length = 0; return; }
  if (wordEls.length !== ln.words.length || box.dataset.line !== String(sel)){
    box.innerHTML = ""; wordEls.length = 0;
    box.dataset.line = String(sel);
    ln.words.forEach((w, j) => {
      const e = document.createElement("div");
      e.className = "wrd"; e.dataset.j = j;
      e.title = T.wordHint(w.w);
      const t = document.createElement("span");
      t.className = "wtx"; t.textContent = w.w;
      e.appendChild(t);
      // A word has edges like a line: start on the left, end on the right.
      // Without them a word's length could not be set at all — it simply ran
      // to its neighbour.
      for (const side of ["left", "right"]){
        const g = document.createElement("div");
        g.className = "wgrip " + side;
        g.dataset.wgrip = side;
        g.title = side === "left" ? T.wordStart : T.wordEnd;
        e.appendChild(g);
      }
      box.appendChild(e); wordEls.push(e);
    });
  }
  layoutWords();
}
function layoutWords(){
  const ln = sel >= 0 ? lines[sel] : null;
  if (!ln) return;
  const k = pps();
  // Words overlap in time more often than not, and an article the aligner gave
  // no time of its own starts exactly where its neighbour does — drawn as they
  // are, such chips lie on top of each other and the small one cannot even be
  // grabbed. Each chip is given a sliver of its own and trimmed short of the
  // next one: the drawing steps aside, the times stay exactly as they are.
  let prevRight = -1e9;
  wordEls.forEach((e, j) => {
    const w = ln.words[j];
    if (!w) return;
    const left = Math.max(w.t * k, prevRight + 1);
    let width = Math.max(w.d * k, 12);
    const next = ln.words[j + 1];
    if (next){
      // Twelve pixels is the least a finger or a cursor can take hold of:
      // a sliver thinner than that is visible and still ungrabbable.
      const nextLeft = Math.max(next.t * k, left + 13);
      width = Math.max(12, Math.min(width, nextLeft - left - 1));
    }
    prevRight = left + width;
    e.style.left = left + "px";
    e.style.width = width + "px";
    // on a narrow word the label is unreadable anyway — show no stub
    e.classList.toggle("tiny", width < 26);
  });
}
// No word collapses to zero: the highlight would flash past it instantly.
const MIN_W = 0.06;

// Words are no longer glued end to end. A word's length used to mean “up to
// the next one”, so where a word ENDS could not be set at all — the neighbour
// had to be moved. Now each has its own start and length, and a gap between
// words is allowed: pauses inside a line are normal in a song.
function editWord(j, mode, t0, d0, dt){
  const ln = lines[sel], w = ln.words[j];
  const prev = ln.words[j-1], next = ln.words[j+1];

  // Neighbours GIVE WAY instead of holding a wall. Words in a line sit end to
  // end, and forbidding overlap locks every word between its own neighbours so
  // it cannot move at all — which is exactly what used to happen.
  // The bound is not the neighbour's edge but the edge of THE ONE AFTER IT: a
  // neighbour may shrink, but not vanish.
  // The outer words are bounded only by the song. Pinning them to the edges of
  // their own line is wrong: lines sit end to end, and the last word could not
  // be moved by even a millisecond. The line stretches after it, and if it runs
  // into the next one the “Check” panel says so — that is what it is for.
  const floor = prev ? prev.t + MIN_W : 0;
  const ceil  = next ? next.t + next.d - MIN_W
                     : Math.max(ln.end, dur || t0 + d0 + 10);

  if (mode === "left"){
    // move the start, the end stays put — that is how length is set
    const end = t0 + d0;
    w.t = clamp(t0 + dt, floor, end - MIN_W);
    w.d = end - w.t;
  } else if (mode === "right"){
    w.t = t0;
    w.d = clamp(d0 + dt, MIN_W, ceil - t0);
  } else {
    w.t = clamp(t0 + dt, floor, Math.max(floor, ceil - d0));
    w.d = d0;
  }

  // Once moved, push the neighbours back exactly as far as we ran into them.
  if (prev && prev.t + prev.d > w.t) prev.d = Math.max(MIN_W, w.t - prev.t);
  if (next && w.t + w.d > next.t){
    const nEnd = next.t + next.d;
    next.t = w.t + w.d;
    next.d = Math.max(MIN_W, nEnd - next.t);
  }
  // A word may go past the old bounds of its line — the line stretches after
  // it, or the last word would hit an invisible wall.
  ln.start = Math.min(ln.start, ln.words[0].t);
  const last = ln.words[ln.words.length - 1];
  ln.end = Math.max(ln.end, last.t + last.d);
  layoutWords(); layoutBlock(sel);
}
function drawBlocks(){                       // once a frame — one container shift
  $("tlscroll").style.transform = "translateX(" + (-viewStart() * pps()) + "px)";
  $("phead").style.left = xOf(mediaTime()) + "px";
  showNextHint();
}

