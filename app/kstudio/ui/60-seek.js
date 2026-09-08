/* ---------- seeking along the timeline ---------- */
$("tlwrap").addEventListener("pointerdown", e => {
  // While marking, the timeline is for marking: a press on an existing mark
  // takes it off, a press anywhere else starts a new one.
  if (marking){
    const t = tOf(e.offsetX), at = markAt(t);
    if (at >= 0){
      marks.splice(at, 1);
      marksToField();
      touched();
      toast(T.markGone);
      drawWave();
      return;
    }
    markFrom = t; markTo = t;
    return;
  }
  // Empty timeline space means seeking. What lies on it does not: a line block
  // and a word chip are dragged, not seeked. Without this rule, grabbing a word
  // first seeked the song and the stage jumped to another line under your hand.
  if (e.target.closest(".blk") || e.target.closest(".wrd")) return;
  seek(tOf(e.offsetX));
});
/* ---------- marking the stretches that hold no words ----------
   A vocalise is voice: nothing measurable tells it from a sung line. The
   timeline is where a person can see it — a loud stretch with no lines under
   it — so that is where it should be possible to say so, with the mouse,
   instead of reading seconds off and typing them into a field. */
let marks = [], marking = false, markFrom = null, markTo = null;

// A stretch the program heard is “taken” once a mark of ours covers it.
function markedAlready(q){
  return marks.some(([a, b]) => a <= q.start + 0.2 && b >= q.end - 0.2);
}
// Taking them is an edit like any other: undoable, saved, and the waveform
// shows the result at once.
function takeQuiet(list){
  const fresh = list.filter(x => !markedAlready(x));
  if (!fresh.length) return toast(T.quietNothingNew);
  snap("");
  let n = 0;
  fresh.forEach(x => { if (addMark(x.start, x.end)) n++; });
  if (!n){ past.pop(); refreshUndo(); return toast(T.quietNothingNew); }
  touched();
  drawWave();
  drawSummary(lastData);
  toast(T.quietAdded(n));
}

function marksFromField(){
  marks = ($("edNoText").value || "").split(/[;,]/).map(part => {
    const m = part.trim().match(/^([\d:.,]+)\s*[-–—]\s*([\d:.,]+)$/);
    if (!m) return null;
    const sec = v => v.split(":").reduce((a, x) => a * 60 + parseFloat(x.replace(",", ".")), 0);
    const a = sec(m[1]), b = sec(m[2]);
    return (isFinite(a) && isFinite(b) && b > a) ? [a, b] : null;
  }).filter(Boolean).sort((x, y) => x[0] - y[0]);
}
// “0:42.5” — a tenth of a second is as fine as anyone can hear a boundary, and
// finer than that turns the field into a wall of digits.
function markTime(t){
  const m = Math.floor(Math.max(0, t) / 60), r = Math.max(0, t) - m * 60;
  return m + ":" + (r < 10 ? "0" : "") + r.toFixed(1);
}
function marksToField(){
  $("edNoText").value = marks.map(([a, b]) => markTime(a) + "-" + markTime(b)).join(", ");
}
function addMark(a, b){
  if (b - a < 0.3) return false;                 // a click, not a stretch
  marks.push([Math.max(0, a), Math.min(dur, b)]);
  marks.sort((x, y) => x[0] - y[0]);
  // touching marks are one mark: two halves of the same solo help nobody
  for (let i = marks.length - 1; i > 0; i--)
    if (marks[i][0] <= marks[i - 1][1] + 0.05){
      marks[i - 1][1] = Math.max(marks[i - 1][1], marks[i][1]);
      marks.splice(i, 1);
    }
  marksToField();
  return true;
}
function markAt(t){
  return marks.findIndex(([a, b]) => t >= a && t <= b);
}
function setMarking(on){
  marking = on;
  $("btnMark").classList.toggle("on", on);
  document.body.classList.toggle("marking", on);
  markFrom = markTo = null;
  toast(on ? T.markOn : T.markOff);
  drawWave();
}
$("btnMark").addEventListener("click", () => setMarking(!marking));

// A line next to a hole reaches across it: the aligner had to end it somewhere.
// The marks already say where the emptiness is — so cut the spans back to them,
// without timing anything again.
$("btnClip").addEventListener("click", () => {
  if (!marks.length) return toast(T.clipNoMarks);
  snap("");
  let n = 0;
  lines.forEach(ln => {
    let a = ln.start, b = ln.end;
    marks.forEach(([lo, hi]) => {
      if (b <= lo || a >= hi) return;          // nowhere near this hole
      if (a >= lo && b <= hi) return;          // wholly inside: moving it is another matter
      if (a < lo && b <= hi) b = lo;
      else if (a >= lo && a < hi && b > hi) a = hi;
      else if (a < lo && hi < b){ if (lo - a >= b - hi) b = lo; else a = hi; }
    });
    if (Math.abs(a - ln.start) < 0.01 && Math.abs(b - ln.end) < 0.01) return;
    if (b - a < 0.2) return;                   // nothing usable would be left
    ln.start = a; ln.end = b; spread(ln); n++;
  });
  // …and the lines that sit wholly inside a hole: trimming cannot help them,
  // they have to leave it. They are pushed to the singing that follows, at a
  // sung pace, pressed against the line that comes after them — the same
  // reasoning the timing itself uses.
  let moved = 0;
  const inHole = ln => marks.find(([lo, hi]) => ln.start >= lo - 0.25 && ln.end <= hi + 0.25);
  for (let i = 0; i < lines.length; i++){
    const hole = inHole(lines[i]);
    if (!hole) continue;
    let j = i;
    while (j + 1 < lines.length && inHole(lines[j + 1])) j++;
    const run = lines.slice(i, j + 1);
    const nextStart = j + 1 < lines.length ? lines[j + 1].start
                                           : (dur || data.duration || 0);
    const prevEnd = i > 0 ? lines[i - 1].end : 0;
    // after the hole if there is room there, otherwise before it
    let lo = Math.max(hole[1], prevEnd), hi = nextStart;
    if (hi - lo < 0.5){ lo = prevEnd; hi = Math.min(hole[0], nextStart); }
    const syl = run.reduce((a, ln) => a + ln.words.reduce((b, w) => b + (w.s || 1), 0), 0) || 1;
    const need = run.reduce((a, ln) => a + ln.words.length, 0) * MIN_W;
    if (hi - lo < 0.25){
      // no room between the neighbours at all: right against the hole then,
      // cramped on purpose — better a tight line in the right place than
      // words over the stretch that was marked
      lo = hole[1];
      hi = lo + Math.max(0.3, 0.12 * run.reduce((a, ln) => a + ln.words.length, 0));
    }
    const span = Math.min(hi - lo, Math.max(syl * 0.45, need));
    let base = hi - span, acc = 0;
    run.forEach(ln => {
      const own = ln.words.reduce((b, w) => b + (w.s || 1), 0) || 1;
      ln.start = base + span * acc / syl;
      acc += own;
      ln.end = Math.max(base + span * acc / syl - 0.05, ln.start + 0.2);
      spread(ln);
      moved++;
    });
    i = j;
  }
  if (!n && !moved){ past.pop(); return toast(T.clipNothing); }
  curLine = -2; layoutBlocks(); touched(); refreshUndo();
  toast(moved ? T.clipMoved(n, moved) : T.clipDone(n));
});

$("tlwrap").addEventListener("pointermove", e => {
  if (!marking || markFrom === null) return;
  markTo = tOf(e.offsetX);
  drawWave();
});
window.addEventListener("pointerup", () => {
  if (!marking || markFrom === null) return;
  const a = Math.min(markFrom, markTo === null ? markFrom : markTo);
  const b = Math.max(markFrom, markTo === null ? markFrom : markTo);
  markFrom = markTo = null;
  if (addMark(a, b)){ toast(T.markAdded(markTime(a), markTime(b))); touched(); }
  drawWave();
});

/* ---------- the beat grid ----------
   A song at one tempo is a ruler: every line begins on a beat, and placing
   them by eye against a waveform is doing arithmetic with a magnifying glass.
   Four beats to a bar, sixteenths when the zoom is close enough for them to
   mean anything, and the lines snap to it while it is on. Nothing here guesses
   at the music: the tempo is typed, or tapped in, and the first beat is put
   where the playhead stands. */
let grid = {on: false, bpm: 120, beat0: 0, sub: 1, pulse: false};

function gridStep(){
  const bpm = clamp(+grid.bpm || 120, 20, 300);
  return 60 / bpm / (grid.sub || 1);
}
function nearestBeat(t){
  const st = gridStep();
  if (!(st > 0)) return null;
  return grid.beat0 + Math.round((t - grid.beat0) / st) * st;
}
function showGrid(){
  $("chkGrid").checked = !!grid.on;
  // the tempo and its settings appear with the grid and go away with it
  $("gridMore").classList.toggle("hide", !grid.on);
  $("chkSixteen").checked = grid.sub === 4;
  $("chkPulse").checked = !!grid.pulse;
  if (document.activeElement !== $("nBpm")) $("nBpm").value = grid.bpm;
}
function saveGrid(){
  if (!data) return;
  data.grid = {on: !!grid.on, bpm: +grid.bpm, beat0: +grid.beat0,
               sub: grid.sub, pulse: !!grid.pulse};
  touched();
  drawWave(); drawBlocks();
}
$("chkGrid").addEventListener("change", () => {
  grid.on = $("chkGrid").checked;
  showGrid();                 // the tempo and its settings come with it
  saveGrid();
});
$("chkSixteen").addEventListener("change", () => {
  grid.sub = $("chkSixteen").checked ? 4 : 1; saveGrid();
});
// The pulse is for the video, not for the window: a person can work with the
// grid on the timeline and want nothing of it in the clip, or the other way.
// Two countdowns over one pause say the same thing twice. The dots stand down
// on a wait the panel at the top is already counting — unless asked otherwise.
/* ---------- which piece of the song the singer is given ----------
   Two presses at the playhead say where it starts and where it stops. The
   recording itself is untouched: the cut is a setting, so tomorrow it can be
   moved or dropped without rebuilding anything. */
// The open frame follows any edit that changes how it will look. Written out
// at every such edit, it was ten copies of one thought.
function refreshStill(){
  if (!$("stillBox").classList.contains("hide")) showStill(stillT, false);
}
function showCut(){
  const t = data && data.trim;
  const on = !!(t && t.length === 2 && t[1] > t[0]);
  $("btnCutAll").classList.toggle("hide", !on);
  $("cutNote").textContent = on ? fmtMs(t[0]) + " – " + fmtMs(t[1]) : "";
}
function setCut(a, b){
  if (!data) return;
  const lo = Math.max(0, a), hi = Math.min(dur || 0, b);
  data.trim = (hi - lo > 1) ? [lo, hi] : null;
  showCut(); touched();
  refreshStill();
}
$("btnCutFrom").addEventListener("click", () => {
  const t = data && data.trim;
  setCut(mediaTime(), t && t[1] > mediaTime() ? t[1] : (dur || 0));
  toast(T.cutSet($("cutNote").textContent));
});
$("btnCutTo").addEventListener("click", () => {
  const t = data && data.trim;
  setCut(t && t[0] < mediaTime() ? t[0] : 0, mediaTime());
  toast(T.cutSet($("cutNote").textContent));
});
$("btnCutAll").addEventListener("click", () => {
  if (!data) return;
  data.trim = null; showCut(); touched();
  refreshStill();
  toast(T.cutGone);
});
// Three switches that only say how the video should look. Each was the same
// five lines with one word changed, which is three chances to get it wrong and
// three places to remember when a fourth is added.
[["chkHolds", "holds"], ["chkMelody", "melody"],
 ["chkDotsLong", "dotsLong"]].forEach(([id, key]) => {
  $(id).addEventListener("change", () => {
    if (!data) return;
    data[key] = $(id).checked;
    touched();
    refreshStill();
  });
});
$("chkPulse").addEventListener("change", () => {
  grid.pulse = $("chkPulse").checked;
  saveGrid();
  refreshStill();
});
$("nBpm").addEventListener("input", () => {
  grid.bpm = clamp(+$("nBpm").value || 120, 20, 300); saveGrid();
});
$("nBpm").addEventListener("keydown", e => {
  e.stopPropagation();                    // digits are digits, not hotkeys
  if (e.key === "Enter"){ e.preventDefault(); $("nBpm").blur(); }
});
$("btnBeatOne").addEventListener("click", () => {
  grid.beat0 = mediaTime();
  if (!grid.on){ grid.on = true; showGrid(); }
  saveGrid();
  toast(T.beatOneSet(fmtMs(grid.beat0)));
});
// Tapping is how a person knows a tempo without being told it: four taps or
// more, and the spacing between them is the answer. Taps more than three
// seconds apart start a new count — that is somebody coming back to it later,
// not a very slow song.
let taps = [];
$("btnTapTempo").addEventListener("click", () => {
  const now = performance.now() / 1000;
  if (taps.length && now - taps[taps.length - 1] > 3) taps = [];
  taps.push(now);
  if (taps.length < 4){ toast(T.tapMore(4 - taps.length)); return; }
  taps = taps.slice(-8);
  const span = taps[taps.length - 1] - taps[0];
  const bpm = clamp(60 * (taps.length - 1) / span, 20, 300);
  grid.bpm = Math.round(bpm * 10) / 10;
  grid.beat0 = mediaTime();
  grid.on = true;
  showGrid(); saveGrid();
  toast(T.tapDone(grid.bpm));
});

// Half a second across the window is close enough to place a word by eye. The
// floor used to be four seconds, and at four seconds the magnet still reaches
// a couple of frames either side — so the one thing a person could do about it,
// zoom in further, was the one thing they could not do.
function setZoom(z){ zoom=clamp(z,0.5,120);
  $("zoomNote").textContent=zoomText(); layoutBlocks(); drawWave(); drawBlocks(); }
function zoomText(){
  return (zoom < 2 ? zoom.toFixed(1) : String(Math.round(zoom))) + T.sec;
}
$("btnZoomIn").addEventListener("click", ()=>setZoom(zoom/1.6));
// A line is a couple of seconds long and the view is fifteen: to see the words
// apart one had to zoom in by hand every time. This does it in one press.
$("btnFit").addEventListener("click", () => {
  if (sel < 0) return toast(T.pickLineFirst);
  const ln = lines[sel];
  const span = Math.max(ln.end - ln.start, 0.4);
  setZoom(clamp(span * 1.6, 4, 120));
  seek(Math.max(0, ln.start - span * 0.15));
});
$("btnZoomOut").addEventListener("click", ()=>setZoom(zoom*1.6));

/* ---------- tidy everything up ---------- */
$("btnSnap").addEventListener("click", () => {
  if (!onsets.length) return toast(T.noVocalWave);
  let n=0;
  snap("");
  lines.forEach(ln => {
    const o = nearestOnset(ln.start);
    if (o === null || Math.abs(o-ln.start) > 0.7) return;
    const d = o - ln.start;
    if (Math.abs(d) < 0.01) return;
    ln.start += d; ln.end += d; ln.words.forEach(w=>w.t += d); n++;
  });
  if (!n) past.pop();               // nothing moved — nothing to undo
  curLine=-2; layoutBlocks(); touched(); refreshUndo();
  toast(n ? T.movedN(n) : T.allInPlace);
});

/* ---------- looping a line ---------- */
function restToo(){ return $("chkRest").checked; }
function putHere(){
  if (sel < 0) return toast(T.pickLineFirst);
  const d = mediaTime() - lines[sel].start;
  snap("");
  const last = restToo() ? lines.length - 1 : sel;
  for (let k = sel; k <= last; k++){
    lines[k].start += d; lines[k].end += d;
    lines[k].words.forEach(w => w.t += d);
  }
  curLine = -2; layoutBlocks(); touched();
  $("selNote").textContent = T.lineNo(sel+1, fmtMs(lines[sel].start));
  toast(restToo() ? T.lineSetRest(sel+1) : T.lineSet(sel+1));
}
$("btnHere").addEventListener("click", putHere);

$("btnLoop").addEventListener("click", () => {
  if (sel < 0) return toast(T.pickLineFirst);
  loopSel = !loopSel;
  $("btnLoop").classList.toggle("on", loopSel);
  if (loopSel){ seek(Math.max(0, lines[sel].start-0.6)); play(); }
});

