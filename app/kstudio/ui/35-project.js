/* ================= the project and its timing ================= */
let pid=null, data=null, lines=[], envelope=[], envHop=0.02, onsets=[];
let sel=-1, curLine=-1, curDuo=-1, loopSel=false, saveT=0;

async function openProject(id){
  pid = id;
  data = await api("/api/project/"+encodeURIComponent(id));
  lines = data.lines;
  envelope = decodeEnv(data.envelope);
  quiet = data.quiet || [];
  envHop = (data.envelope||{}).hop || 0.02;
  onsets = findOnsets();
  figureDoubt();
  sel = -1; curLine = -2; waOffset = 0; playing = false;
  songName = data.title || "";
  songArtist = data.artist || "";
  showName();
  fillNoText(data);
  $("hint").textContent = T.hotkeys;
  showMade("");
  refreshCover();
  refreshBackdrop();
  const gsav = data.grid || {};
  grid = {on: !!gsav.on, bpm: clamp(+gsav.bpm || 120, 20, 300),
          beat0: +gsav.beat0 || 0, sub: gsav.sub === 4 ? 4 : 1,
          pulse: !!gsav.pulse};
  showGrid();
  $("chkDotsLong").checked = !!data.dotsLong;
  $("chkMelody").checked = !!data.melody;
  $("chkHolds").checked = data.holds !== false;
  showCut();
  colors = (Array.isArray(data.colors) && data.colors.length === 2)
    ? data.colors.slice() : ["#4de1ff", "#ff8ad1"];
  theme = (Array.isArray(data.theme) && data.theme.length === 2)
    ? data.theme.slice() : ["#0a0b14", "#e8ebf5"];
  applyColors();
  screen("scrEdit");
  buildLines();
  makeBlocks();
  centerLine(0);                    // text in sight at once, not at the bottom edge
  showProblems(data.problems);
  await loadAudio(id, data.tracks);
  lastData = data;
  $("zoomNote").textContent = zoomText();
  drawSummary(data);            // the length is known only after the audio loads
  $("tDur").textContent = fmt(dur);
  drawWave();
  requestAnimationFrame(tick);
}
function decodeEnv(env){
  if (!env || !env.data) return [];
  const bin = atob(env.data), out = new Float32Array(bin.length);
  for (let i=0;i<bin.length;i++) out[i] = bin.charCodeAt(i)/255;
  return out;
}
function findOnsets(){
  if (!envelope.length) return [];
  const sorted = Array.from(envelope).sort((a,b)=>a-b);
  const floor = sorted[Math.floor(sorted.length*0.15)];
  const peak  = sorted[Math.floor(sorted.length*0.98)];
  const rng = Math.max(peak-floor, 1e-6);
  const on = floor + 0.20*rng, off = floor + 0.11*rng;
  const res=[]; let active=false, start=0;
  for (let i=0;i<envelope.length;i++){
    if (!active && envelope[i] >= on){ active=true; start=i;
      while (start>0 && i-start < 10 && envelope[start-1] > off*0.7) start--;
    } else if (active && envelope[i] < off){
      active=false;
      if ((i-start)*envHop >= 0.18) res.push(start*envHop);
    }
  }
  return res;
}

/* ---------- the lyrics ---------- */
let quiet = [];                 // stretches where nobody sings for a while
const lineEls=[];
function buildLines(){
  const box=$("scroll"); box.innerHTML=""; lineEls.length=0;
  lines.forEach((ln,i) => {
    const el=document.createElement("div");
    el.className = "ln" + (ln.backing ? " back" : "") + (ln.voice === 2 ? " v2" : "")
      + (ln.keep ? " keep" : "");
    ln.words.forEach((w,j) => {
      // a syllable reads on to the word before it — the mark that split it
      // is a timing device, never a letter
      const after = ln.words[j+1];
      const txt = w.w + (after && !after.g ? " " : "");
      const sp=document.createElement("span"); sp.className="w";
      const hl=document.createElement("span"); hl.className="hl"; hl.textContent=txt;
      sp.appendChild(hl); sp.appendChild(document.createTextNode(txt));
      el.appendChild(sp);
    });
    el.addEventListener("click", e => {
      if (skipClick){ skipClick = false; return; }   // that was the end of a drag
      selectLine(i, !e.shiftKey && !e.ctrlKey && !e.metaKey,
        e.shiftKey ? "range" : (e.ctrlKey || e.metaKey) ? "add" : "");
    });
    el.addEventListener("dblclick", () => editText(i));
    box.appendChild(el);
    // the “original sings” tag is not a word, there is nothing to highlight
    lineEls.push({el, hls:[...el.children].filter(e=>e.className==="w")
                                          .map(s=>s.firstChild)});
    if (ln.keep) markKeep(i);
  });
}
/* Several lines can be selected: moving a chunk to the second voice or deleting
   a stray repeat as a batch is ordinary work, and doing it one by one is slow.
   When `marked` is empty we work with the single line `sel`. */
const marked = new Set();
// The selection anchor: Shift extends the range from it. Without one,
// Shift+arrow restarted the selection at the current line and it never grew.
let anchor = -1;
function targets(){
  return marked.size ? [...marked].sort((a, b) => a - b) : (sel >= 0 ? [sel] : []);
}
function paintMarks(){
  lineEls.forEach((L, k) => L.el.classList.toggle("mark", marked.has(k)));
  blockEls.forEach((e, k) => e.classList.toggle("mark", marked.has(k)));
}
/* Drag selection: press on a line, drag across its neighbours, they get picked.
   That is how lists work everywhere, and it is exactly what was missing: Shift
   and Ctrl have to be known, while press-and-drag does not. */
let picking = null, skipClick = false;
function lineIndexFromEvent(e){
  const el = e.target && e.target.closest ? e.target.closest(".ln") : null;
  if (!el) return -1;
  return lineEls.findIndex(L => L.el === el);
}
function pickRange(a, b){
  marked.clear();
  for (let k = Math.min(a, b); k <= Math.max(a, b); k++) marked.add(k);
  sel = b;
  lineEls.forEach((L, k) => L.el.classList.toggle("sel", k === sel));
  paintMarks();
  $("selNote").textContent = marked.size > 1
    ? T.linesPicked(marked.size) : T.lineNo(sel + 1, fmtMs(lines[sel].start));
  $("selNote").classList.toggle("many", marked.size > 1);
  layoutBlocks();
  refreshVoice(); refreshKeep(); refreshRhythm();
}
$("scroll").addEventListener("pointerdown", e => {
  // The “click after a drag” flag lives exactly until the next press: otherwise,
  // if no click followed the drag, it would swallow the next real one.
  skipClick = false;
  if (editingText >= 0 || e.button !== 0) return;
  const i = lineIndexFromEvent(e);
  if (i < 0) return;
  // Pointer capture is not taken immediately: while this is still an ordinary
  // click it must not retarget the click from the line to the stage, which
  // would break selecting a single line.
  picking = {from: i, last: i, moved: false, id: e.pointerId};
});
$("stage").addEventListener("pointermove", e => {
  if (!picking) return;
  // While dragging, look up the line under the cursor: the event target stays
  // the same once the stage has captured the pointer.
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const ln = el && el.closest ? el.closest(".ln") : null;
  const i = ln ? lineEls.findIndex(L => L.el === ln) : -1;
  if (i < 0 || i === picking.last) return;
  picking.last = i;
  if (!picking.moved){
    picking.moved = true;
    try { $("stage").setPointerCapture(picking.id); } catch (err) {}
  }
  document.body.classList.add("picking");
  anchor = picking.from;
  pickRange(picking.from, i);
});
window.addEventListener("pointerup", e => {
  if (!picking) return;
  const was = picking;
  picking = null;
  document.body.classList.remove("picking");
  if (was.moved){
    try { $("stage").releasePointerCapture(was.id); } catch (err) {}
    skipClick = true;                   // a click after a drag resets nothing
    return;
  }
  // The stage keeps scrolling under the cursor while the song plays: by the
  // time the browser assembles a click, the pressed line is no longer the one
  // under the pointer, and the click landed on a neighbour — or nowhere. The
  // press is what the person meant, so the press is what selects.
  skipClick = true;
  selectLine(was.from, !e.shiftKey && !e.ctrlKey && !e.metaKey,
    e.shiftKey ? "range" : (e.ctrlKey || e.metaKey) ? "add" : "");
});

function selectLine(i, jump, mode){
  const prev = sel, was = sel;
  sel = clamp(i, 0, lines.length-1);
  if (mode === "add"){                       // Ctrl — add or remove one
    if (!marked.size && was >= 0) marked.add(was);
    if (marked.has(sel) && marked.size > 1) marked.delete(sel); else marked.add(sel);
    anchor = sel;
  } else if (mode === "range"){              // Shift — the whole run from the anchor
    const from = anchor >= 0 ? anchor : (was < 0 ? sel : was);
    marked.clear();
    for (let k = Math.min(from, sel); k <= Math.max(from, sel); k++) marked.add(k);
    anchor = from;
  } else {
    marked.clear();
    anchor = sel;
  }
  lineEls.forEach((L,k)=>L.el.classList.toggle("sel", k===sel));
  paintMarks();
  $("selNote").textContent = marked.size > 1
    ? T.linesPicked(marked.size)
    : T.lineNo(sel+1, fmtMs(lines[sel].start));
  $("selNote").classList.toggle("many", marked.size > 1);
  if (jump) seek(Math.max(0, lines[sel].start - 0.7));
  if (prev >= 0) layoutBlock(prev);
  layoutBlock(sel);
  makeWords();                       // the word row always belongs to the selected line
  refreshVoice(); refreshKeep(); refreshRhythm();
}
// Scrolling the lyrics by hand. The only way used to be ↑ ↓ one line at a
// time — you never get back to the start of a long song like that.
let freeScroll = 0, scrollY = 0;
function stageScroll(dy){
  const box = $("scroll"), stage = $("stage");
  const max = Math.max(0, box.scrollHeight - stage.clientHeight);
  scrollY = clamp(scrollY + dy, 0, max);
  box.style.transition = "none";
  box.style.transform = `translateY(${-scrollY}px)`;
  freeScroll = Date.now();            // let go of auto-centring for a while
}
$("stage").addEventListener("wheel", e => {
  e.preventDefault();
  stageScroll(e.deltaY * (e.deltaMode === 1 ? 24 : 1));
}, {passive:false});

function centerLine(i){
  // While a person scrolls, do not yank the text out from under them.
  if (Date.now() - freeScroll < 2500) return;
  $("scroll").style.transition = "";
  // Before a line is chosen, show the first one: the text padding is set in
  // fractions of the WINDOW while the stage is shorter, so without centring the
  // text ends up at the bottom edge or past it.
  if (i < 0) i = 0;
  if (!lineEls[i]) return;
  const el=lineEls[i].el;
  scrollY = el.offsetTop + el.offsetHeight/2 - $("stage").clientHeight/2;
  $("scroll").style.transform = `translateY(${-scrollY}px)`;
}

/* ---------- saving ---------- */
/* ---------- undo ----------
   Edits go to disk by themselves, so there is no “close without saving” here,
   and undo is the only protection from a wrong move. We keep snapshots of the
   lines: there are few of them, and this way no inverse action has to be
   written for every kind of edit. */
const past = [];
let lastSnap = {what: "", at: 0};
function snap(what){
  // A run of identical small steps (holding [ or ]) is one undo step, or it
  // would take fifty presses to get back to where things were.
  const now = Date.now();
  if (what && what === lastSnap.what && now - lastSnap.at < 900){
    lastSnap.at = now;
    return;
  }
  lastSnap = {what: what || "", at: now};
  past.push(JSON.stringify(lines));
  if (past.length > 120) past.shift();
  refreshUndo();
}
function undo(){
  if (!past.length){ refreshUndo(); return toast(T.nothingToUndo); }
  lines = JSON.parse(past.pop());
  lastSnap = {what: "", at: 0};
  buildLines(); makeBlocks();
  selectLine(clamp(sel, 0, lines.length - 1), false);
  curLine = -2;
  refreshUndo(); touched();
  toast(T.undone);
}
function refreshUndo(){ $("btnUndo").disabled = past.length === 0; }

/* ---------- countdown to the singing ---------- */
// While nobody sings the stage is empty and it is impossible to tell whether
// the song is running. A moving countdown means everything else moves too.
function idxAt(t){
  let idx = -1;
  for (let i=0;i<lines.length;i++){ if (lines[i].start <= t) idx = i; else break; }
  return (idx >= 0 && t < lines[idx].end) ? idx : -1;
}
let waitFrom = 0;
function showWait(t, cur){
  const box = $("wait");
  // A short gap between lines needs no countdown: it is obvious anyway, and a
  // label flashing for half a second only gets in the way.
  // Ten seconds, not five: a gap shorter than that is a breath between lines,
  // and counting it down draws the eye away from the singing for nothing.
  const MIN_GAP = 10.0;
  if (cur >= 0){ box.classList.add("hide"); return; }
  // Seconds, not milliseconds: this is “how long to wait”, not timing.
  const left = s => s >= 60 ? fmt(s) : Math.ceil(s) + T.sec;
  // the wait is until the singer's own next line — a backing na-na-na in the
  // middle of the gap is not what the countdown is for
  const next = lines.find(l => l.start > t && !l.backing);
  if (!next){                              // the song is over
    if (dur - t < 3){ box.classList.add("hide"); return; }
    box.classList.remove("hide");
    $("waitTtl").textContent = T.theEnd;
    $("waitNum").textContent = left(Math.max(0, dur - t));
    $("waitTxt").textContent = T.tillEnd;
    $("waitFill").style.width = dur ? (100 * t / dur).toFixed(1) + "%" : "0";
    return;
  }
  const prev = lines.filter(l => l.end <= t).pop();
  const from = prev ? prev.end : 0;
  const span = Math.max(next.start - from, 0.001);
  if (span < MIN_GAP){ box.classList.add("hide"); return; }
  box.classList.remove("hide");
  $("waitTtl").textContent = prev ? T.interlude : T.intro;
  $("waitNum").textContent = left(next.start - t);
  $("waitTxt").textContent = T.till + shortLine(next.text, 32) + T.quote;
  $("waitFill").style.width = (100 * clamp((t - from) / span, 0, 1)).toFixed(1) + "%";
  waitFrom = from;
}

/* ---------- two voices and their colours ---------- */
// Vocals sometimes overlap: a lead and a backing part, a clean voice and a
// scream. A line can be given the second voice — it is painted in the second
// colour both here and on the finished page.
let colors = ["#4de1ff", "#ff8ad1"];
let theme = ["#0a0b14", "#e8ebf5"];      // background and text colour

/* Readability. A person picks the colours, but letters that blend into the
   background are not a style, they are a broken page. The hue is kept, the
   lightness is moved. */
function rgbOf(c){
  c = String(c || "").trim().replace("#", "");
  if (c.length === 3) c = c.split("").map(x => x + x).join("");
  if (!/^[0-9a-f]{6}$/i.test(c)) return null;
  return [0,2,4].map(i => parseInt(c.slice(i,i+2), 16));
}
function lum(rgb){
  const f = v => (v/=255) <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
  return 0.2126*f(rgb[0]) + 0.7152*f(rgb[1]) + 0.0722*f(rgb[2]);
}
function contrast(a, b){
  const ra = rgbOf(a), rb = rgbOf(b);
  if (!ra || !rb) return 21;
  const la = lum(ra), lb = lum(rb);
  return (Math.max(la,lb)+0.05) / (Math.min(la,lb)+0.05);
}
function hex(rgb){ return "#" + rgb.map(v => clamp(Math.round(v),0,255)
                                              .toString(16).padStart(2,"0")).join(""); }
function readable(bg, text, need){
  need = need || 4.5;
  if (contrast(bg, text) >= need) return {color: text, fixed: false};
  const up = lum(rgbOf(bg) || [0,0,0]) < 0.5;
  let c = rgbOf(text) || [128,128,128];
  for (let i = 0; i < 64; i++){
    c = c.map(v => up ? Math.min(255, v + (255-v)*0.08 + 2) : Math.max(0, v - v*0.08 - 2));
    if (contrast(bg, hex(c)) >= need) return {color: hex(c), fixed: true};
  }
  return {color: up ? "#ffffff" : "#000000", fixed: true};
}
function applyColors(){
  const root = document.documentElement.style;
  root.setProperty("--accent", colors[0]);
  root.setProperty("--accent-2", colors[1]);
  $("col1").value = colors[0]; $("col2").value = colors[1];
  root.setProperty("--bg", theme[0]);
  root.setProperty("--bg2", theme[0]);
  root.setProperty("--text", theme[1]);
  const t = rgbOf(theme[1]), b = rgbOf(theme[0]);
  if (t && b) root.setProperty("--dim", hex(t.map((v,i) => v*0.55 + b[i]*0.45)));
  $("colBg").value = theme[0]; $("colTx").value = theme[1];
  document.querySelectorAll(".sw").forEach(b => {
    b.style.background = $(b.dataset.for).value;
  });
}

/* ---------- choosing a colour ----------
   The system's colour panel is the system's window: pressing anywhere on the
   page leaves it standing, and it covers the very song it is meant to dress.
   So the swatches open a popover of our own — a row of ready colours and a
   field for a code — and the wheel stays one press away for those who want it. */
const SWATCHES = [
  "#4de1ff", "#7ee08a", "#ffcc4d", "#ff8ad1", "#ff7a7a", "#b98cff", "#9ad0ff", "#ffffff",
  "#1fb6d6", "#3fa85a", "#d19b1f", "#d1568f", "#c14b4b", "#7d55c7", "#5a7fa8", "#c8ccd8",
  "#0a0b14", "#141830", "#1d2436", "#2b2f45", "#3a3f58", "#5d6480", "#8b93b0", "#e8ebf5",
];
let swFor = null;
function closeSw(){ $("swPop").classList.add("hide"); swFor = null; }
function openSw(btn){
  const id = btn.dataset.for;
  swFor = id;
  const pop = $("swPop"), grid = $("swGrid");
  grid.replaceChildren();
  SWATCHES.forEach(c => {
    const b = document.createElement("button");
    b.style.background = c;
    b.title = c;
    b.addEventListener("click", () => setSw(c));
    grid.appendChild(b);
  });
  $("swHex").value = $(id).value;
  pop.classList.remove("hide");
  // under the swatch, and never off the edge of the window
  const r = btn.getBoundingClientRect(), pr = pop.getBoundingClientRect();
  pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pr.width - 8)) + "px";
  pop.style.top = Math.max(8, r.top - pr.height - 8) + "px";
}
function setSw(value){
  if (!swFor || !/^#[0-9a-f]{6}$/i.test(value)) return;
  const inp = $(swFor);
  inp.value = value;
  inp.dispatchEvent(new Event("input", {bubbles: true}));
  $("swHex").value = value;
  document.querySelectorAll(".sw").forEach(b => {
    b.style.background = $(b.dataset.for).value;
  });
}
document.querySelectorAll(".sw").forEach(b => {
  // the press must not reach the page, or the popover would close itself
  // before the click that opens it ever landed
  b.addEventListener("pointerdown", e => e.stopPropagation());
  b.addEventListener("click", e => {
    e.stopPropagation();
    if (swFor === b.dataset.for) return closeSw();
    openSw(b);
  });
});
$("swHex").addEventListener("input", () => setSw($("swHex").value.trim()));
$("swHex").addEventListener("keydown", e => {
  e.stopPropagation();
  if (e.key === "Enter" || e.key === "Escape") closeSw();
});
$("swPop").addEventListener("click", e => e.stopPropagation());
$("swPop").addEventListener("pointerdown", e => e.stopPropagation());
$("swMore").addEventListener("click", () => {
  const id = swFor;
  closeSw();
  if (id) $(id).click();          // the system wheel, for those who want it
});
// A press anywhere outside — on the page, on another swatch, on the song —
// puts the popover away.
document.addEventListener("pointerdown", () => { if (swFor) closeSw(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSw(); });
function pickTheme(i, val){
  if (theme[i] === val) return;
  theme[i] = val;
  const r = readable(theme[0], theme[1]);
  theme[1] = r.color;
  applyColors(); touched();
  if (r.fixed) toast(T.colorFixed);
}
$("colBg").addEventListener("input", e => pickTheme(0, e.target.value));
$("colTx").addEventListener("input", e => pickTheme(1, e.target.value));
function pickColor(i, val){
  if (colors[i] === val) return;
  colors[i] = val; applyColors(); touched();
}
$("col1").addEventListener("input", e => pickColor(0, e.target.value));
$("col2").addEventListener("input", e => pickColor(1, e.target.value));

// A line named in passing is cut at a word, never inside one: “…before w”
// says nothing and reads as a fault. The ellipsis admits there is more.
function shortLine(text, most){
  const s = String(text || "").split(/\s+/).filter(Boolean).join(" ");
  if (s.length <= most) return s;
  const cut = s.slice(0, most);
  const sp = cut.lastIndexOf(" ");
  return (sp >= most / 2 ? cut.slice(0, sp) : cut).replace(/[\s,.;:—-]+$/, "") + "…";
}

function voiceOf(ln){ return (ln && ln.voice === 2) ? 2 : 1; }
function refreshVoice(){
  $("btnVoice").textContent = sel < 0 ? T.voiceNone : T.voiceBtn(voiceOf(lines[sel]));
  $("btnVoice").classList.toggle("on", sel >= 0 && voiceOf(lines[sel]) === 2);
}
function toggleVoice(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  const to = voiceOf(lines[idx[0]]) === 2 ? 1 : 2;
  idx.forEach(i => {
    lines[i].voice = to;
    lineEls[i].el.classList.toggle("v2", to === 2);
    if (blockEls[i]) blockEls[i].classList.toggle("v2", to === 2);
  });
  updateLanes();
  refreshVoice(); touched();
  toast(idx.length > 1 ? T.voiceManyOn(to, idx.length)
                       : (to === 2 ? T.voice2On : T.voice1On));
}
$("btnVoice").addEventListener("click", toggleVoice);

// Sometimes a piece is not meant to be sung: backing vocals, speech, a moment
// that matters to the story. Such a line is marked, and in the finished karaoke
// the original is heard there again.
function refreshKeep(){
  const ln = sel >= 0 ? lines[sel] : null;
  const on = !!(ln && ln.keep);
  $("btnKeep").classList.toggle("on", on);
  $("btnKeep").textContent = !on ? T.keep
    : (ln.keepSoft ? T.keepSoftYes : T.keepYes);
}
function toggleKeep(){
  // Three states in a circle: not kept → the original at full voice (not
  // yours to sing) → the original held back to a guide (sing along with it)
  // → not kept. One button, because the choice is one choice.
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  const head = lines[idx[0]];
  const to = !head.keep ? {keep: true, keepSoft: false}
    : !head.keepSoft ? {keep: true, keepSoft: true}
    : {keep: false, keepSoft: false};
  idx.forEach(i => {
    lines[i].keep = to.keep;
    lines[i].keepSoft = to.keepSoft;
    lineEls[i].el.classList.toggle("keep", to.keep);
    markKeep(i);
    if (blockEls[i]) blockEls[i].classList.toggle("keep", to.keep);
  });
  refreshKeep(); touched();
  toast(idx.length > 1 ? T.keepManyMsg(to, idx.length)
    : to.keepSoft ? T.keepSoftMsg : (to.keep ? T.keepOnMsg : T.keepOffMsg));
}
// A tag right in the text: one glance says this line is not yours to sing.
function markKeep(i){
  const el = lineEls[i] && lineEls[i].el;
  if (!el) return;
  const old = el.querySelector(".kp");
  if (old) old.remove();
  if (!lines[i].keep) return;
  const kp = document.createElement("i");
  kp.className = "kp";
  kp.textContent = lines[i].keepSoft ? T.sungTogether : T.sungByOriginal;
  el.appendChild(kp);
}
$("btnKeep").addEventListener("click", toggleKeep);

/* ---------- a line put right by hand ----------
   Re-timing used to throw away every hand-made correction along with the rest.
   A lock says “leave this one alone”: the model gets no vote on it. */
function toggleLock(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  const to = !lines[idx[0]].lock;
  idx.forEach(i => {
    lines[i].lock = to;
    if (blockEls[i]) blockEls[i].classList.toggle("lock", to);
  });
  touched();
  toast(to ? T.lockedN(idx.length) : T.unlockedN(idx.length));
}
$("btnLock").addEventListener("click", toggleLock);

/* ---------- re-laying the words inside a line ----------
   The line's edges are right — set by hand, perhaps locked — and the words
   inside are a mess: an article under its neighbour, lengths from a bad pass.
   Re-spread them by syllables within the line's own span. The lock is no
   obstacle: it guards against the model, not against the person. */
$("btnEven").addEventListener("click", () => {
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  idx.forEach(i => spread(lines[i]));
  layoutBlocks(); layoutWords(); touched();
  toast(T.evenDone(idx.length));
});

/* ---------- timing a few lines again ----------
   The timing is wrong in one place and right everywhere else; redoing all of
   it costs minutes and throws away the corrections made by hand. */
$("btnRealignPart").addEventListener("click", async () => {
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  const a = Math.min(...idx), b = Math.max(...idx);
  if (!confirm(T.realignPartAsk(a + 1, b + 1))) return;
  await flush();
  try{
    const j = await api("/api/project/" + encodeURIComponent(pid) + "/realign-part",
      {from: a, to: b, align: caps.whisper ? "auto" : "energy", lang: langOf(),
       noText: ($("edNoText").value || "").trim()});
    watchJob(j.job, T.realignPart, r => {
      openProject(pid);
      toast(T.realignPartDone((r && r.lines) || 0));
    });
  }catch(e){ toast(e.message); }
});

/* ---------- copying a line and its rhythm ----------
   A chorus is sung the same way every time, and timing it again from scratch is
   wasted work. A line that is already right can be copied whole (Ctrl+D), or
   only its word layout can be taken and applied to the same line elsewhere. */
let clip = null;                  // {text, words:[{w, dt, d}]}
function sameText(i){
  return !!(clip && lines[i] &&
            clip.items.some(c => c.text.trim() === lines[i].text.trim()));
}
function copyRhythm(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  // Copy everything selected: the words, the layout, the voice, the marks and
  // the gaps between lines. Later either the rhythm alone or the lines
  // themselves can be pasted — one of them or the whole batch.
  const base = lines[idx[0]].start;
  clip = {
    span: lines[idx[idx.length - 1]].end - base,
    items: idx.map(i => {
      const ln = lines[i];
      return {text: ln.text, voice: voiceOf(ln), keep: !!ln.keep,
              backing: !!ln.backing, at: ln.start - base, len: ln.end - ln.start,
              words: ln.words.map(w => ({w: w.w, s: w.s, dt: w.t - ln.start, d: w.d}))};
    }),
  };
  refreshRhythm();
  toast(idx.length > 1 ? T.copiedLines(idx.length)
                       : T.copiedLine(shortLine(lines[idx[0]].text, 30)));
}
// Put a copy into a line: text, words and marks from the copy, place from the target.
function putLine(ln, item, start){
  ln.text = item.text;
  ln.voice = item.voice;
  ln.keep = item.keep;
  ln.backing = item.backing;
  ln.section = ln.section || null;
  ln.start = start;
  ln.end = start + Math.max(item.len, MIN_W * item.words.length);
  ln.words = item.words.map(c => ({w: c.w, s: c.s, t: start + c.dt, d: c.d}));
  const last = ln.words[ln.words.length - 1];
  if (last) ln.end = Math.max(ln.end, last.t + last.d);
}
function pasteLine(){
  if (!clip) return toast(T.rhythmNone);
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  // “Paste” means “add”, not “overwrite”: the copies go in after the selection
  // and nothing that already exists disappears.
  const after = idx[idx.length - 1];
  const cur = lines[after], next = lines[after + 1];
  const start = cur.end;
  const span = Math.max(clip.span, 0.4);
  const room = next ? Math.max(next.start - start, 0.4) : Infinity;
  const k = Math.min(1, room / span);
  snap("");
  const made = clip.items.map(item => {
    const ln = {text: "", words: [], section: null};
    putLine(ln, {...item, len: item.len * k,
                 words: item.words.map(w => ({...w, dt: w.dt * k,
                                              d: Math.max(w.d * k, MIN_W)}))},
            start + item.at * k);
    return ln;
  });
  lines.splice(after + 1, 0, ...made);
  marked.clear();
  buildLines(); makeBlocks(); updateLanes();
  selectLine(after + 1, false); curLine = -2; touched();
  toast(made.length > 1 ? T.linesPasted(made.length) : T.linePasted);
}
function applyRhythm(i, item){
  const ln = lines[i];
  if (ln.words.length !== item.words.length) return false;
  item.words.forEach((c, j) => { ln.words[j].t = ln.start + c.dt; ln.words[j].d = c.d; });
  const last = ln.words[ln.words.length - 1];
  ln.end = Math.max(ln.end, last.t + last.d);
  return true;
}
function pasteRhythm(){
  if (!clip) return toast(T.rhythmNone);
  if (sel < 0) return toast(T.pickLineFirst);
  // One line — or every later line with the same text, if the box is ticked.
  const idx = marked.size ? targets()
            : restToo() ? lines.map((l, i) => i).filter(i => i >= sel && sameText(i))
            : [sel];
  const list = idx.length ? idx : [sel];
  const one = clip.items.length === 1;
  const src = k => one ? clip.items[0] : clip.items[k % clip.items.length];
  const bad = list.filter((i, k) => lines[i].words.length !== src(k).words.length);
  if (bad.length === list.length)
    return toast(T.rhythmMismatch(src(0).words.length, lines[sel].words.length));
  snap("");
  let done = 0;
  list.forEach((i, k) => { if (applyRhythm(i, src(k))) done++; });
  layoutBlocks(); makeWords(); curLine = -2; touched();
  toast(done > 1 ? T.rhythmPastedN(done) : T.rhythmPasted);
}
// A whole copy of a line — when a repeat is missing from the text and the
// timing of the original is already good.
function duplicateLine(){
  if (sel < 0) return toast(T.pickLineFirst);
  const cur = lines[sel], next = lines[sel + 1];
  const span = Math.max(cur.end - cur.start, MIN_W * cur.words.length, 0.4);
  const start = cur.end;
  // The copy goes right after the original. If there is less room before the
  // next line than the line takes, the copy is squeezed — otherwise it would
  // run into its neighbour at once.
  const room = next ? Math.max(next.start - start, MIN_W * cur.words.length) : Infinity;
  const k = Math.min(1, room / span);
  const copy = {
    text: cur.text, section: null, backing: cur.backing,
    voice: cur.voice, keep: cur.keep, start, end: start + span * k,
    words: cur.words.map(w => ({w: w.w, s: w.s,
                                t: start + (w.t - cur.start) * k,
                                d: Math.max(w.d * k, MIN_W)})),
  };
  const last = copy.words[copy.words.length - 1];
  if (last) copy.end = Math.max(copy.end, last.t + last.d);
  snap("");
  lines.splice(sel + 1, 0, copy);
  buildLines(); makeBlocks(); selectLine(sel + 1, false); touched();
  toast(T.lineCopied);
}
function refreshRhythm(){
  const n = clip ? lines.filter((l, i) => sameText(i)).length : 0;
  $("btnPaste").disabled = !clip;
  $("btnPasteLine").disabled = !clip;
  $("btnPaste").textContent = T.pasteRhythm(n);
  $("btnPaste").classList.toggle("on", !!clip && sel >= 0 && sameText(sel));
}
$("btnRhythm").addEventListener("click", copyRhythm);
$("btnPaste").addEventListener("click", pasteRhythm);
$("btnPasteLine").addEventListener("click", pasteLine);
$("btnUndo").addEventListener("click", undo);

// The save state is always visible instead of flashing for a second: one has
// to know whether an edit is on disk without guessing.
let dirty = false, saving = null;
function saveState(kind, text){
  const n = $("savedNote");
  n.className = "saved on " + kind;
  n.textContent = text;
}
async function saveNow(){
  if (!dirty) return;
  dirty = false;
  saveState("busy", T.saving);
  try{
    const r = await api(`/api/project/${encodeURIComponent(pid)}/timings`,
      {lines, colors, theme,
       noText: ($("edNoText").value || "").trim(),
       keepMarks: $("chkKeepMarks") ? $("chkKeepMarks").checked : true,
       checkOff, title: songName, artist: songArtist,
       coverDark: (data && data.coverDark != null) ? data.coverDark : undefined,
       grid: (data && data.grid) ? data.grid : undefined,
       dotsLong: (data && data.dotsLong !== undefined)
                 ? !!data.dotsLong : undefined,
       melody: (data && data.melody !== undefined) ? !!data.melody : undefined,
       holds: (data && data.holds !== undefined) ? !!data.holds : undefined,
       trim: (data && data.trim !== undefined) ? data.trim : undefined});
    showProblems(r.problems);
    saveState("ok", T.savedOk);
  }catch(e){
    dirty = true;                       // not saved — the edit is still ours
    saveState("bad", T.saveBad);
    toast(T.saveErr(e.message));
    clearTimeout(saveT); saveT = setTimeout(() => { saving = saveNow(); }, 3000);
  }
}
function touched(){
  dirty = true;
  saveState("busy", T.unsaved);
  clearTimeout(saveT);
  saveT = setTimeout(() => { saving = saveNow(); }, 350);
}
// Before exporting, wait for the edit to reach the disk: the server builds the
// file from what it has, and without this the page could carry the old timing.
async function flush(){
  clearTimeout(saveT);
  if (dirty) saving = saveNow();
  await saving;
}

