/* ---------- dragging the blocks ---------- */
let drag=null, wdrag=null, diveAt=null;
$("blocks").addEventListener("dblclick", e => {
  const blk = e.target.closest(".blk"); if (!blk) return;
  editText(+blk.dataset.i);          // edit the text where the line is seen
});
// The edge stops at the outermost word: beyond that the line can only be
// squeezed whole, and there is no way to guess that without being told.
let saidLimit = 0;
function hitLimit(){
  if (Date.now() - saidLimit < 4000) return;
  saidLimit = Date.now();
  toast(T.edgeLimit);
}
$("blocks").addEventListener("pointerdown", e => {
  const blk = e.target.closest(".blk"); if (!blk) return;
  const i = +blk.dataset.i;
  // Overlapping blocks stack, and the top one used to swallow every press:
  // the line underneath could not be reached at all. The press keeps its old
  // meaning — select and maybe drag — and a SECOND press on the same spot,
  // released without moving, dives to the line underneath (see pointerup).
  diveAt = (!e.shiftKey && !e.ctrlKey && !e.metaKey && i === sel)
    ? {x: e.clientX, t: viewStart() + (e.clientX -
         $("tlwrap").getBoundingClientRect().left) / pps()}
    : null;
  selectLine(i, false, e.shiftKey ? "range" : (e.ctrlKey || e.metaKey) ? "add" : "");
  if (marked.size > 1) return;               // a batch is selected, not dragged
  snap("");                       // a snapshot before the edit, while data is whole
  drag = {i, x0:e.clientX, start:lines[i].start, end:lines[i].end,
          words: lines[i].words.map(w=>w.t),
          durs: lines[i].words.map(w=>w.d),      // keep hand-tuned word lengths
          grip: e.target.dataset.grip || "",
          // Alt squeezes the whole line into the new span instead of stretching
          // the outermost word alone: for a line that grabbed a minute and a
          // half, moving one word is no use at all.
          all: e.altKey};
  $("tlwrap").classList.add("drag");
  e.preventDefault();
});
// A word is dragged the same way as a line, but only it is changed.
$("words").addEventListener("pointerdown", e => {
  const el = e.target.closest(".wrd"); if (!el || sel < 0) return;
  const j = +el.dataset.j, w = lines[sel].words[j];
  snap("");
  wdrag = {j, x0:e.clientX, t0:w.t, d0:w.d,
           mode: e.target.dataset.wgrip || "move"};
  el.classList.add("on");
  $("tlwrap").classList.add("drag");
  e.preventDefault();
});
window.addEventListener("pointermove", e => {
  if (wdrag){
    const dt = (e.clientX - wdrag.x0) / $("tlwrap").clientWidth * zoom;
    editWord(wdrag.j, wdrag.mode, wdrag.t0, wdrag.d0, dt);
    const w = lines[sel].words[wdrag.j];
    $("selNote").textContent = wdrag.mode === "move"
      ? T.wordAt(w.w, fmtMs(w.t))
      : T.wordSpan(w.w, fmtMs(w.t), fmtMs(w.t + w.d), w.d.toFixed(2));
    return;
  }
  if (!drag) return;
  const dt = (e.clientX - drag.x0) / $("tlwrap").clientWidth * zoom;
  // Hold Alt to place a line exactly where the hand puts it: the magnet that
  // pulls to the start of a phrase is a help until the moment it is not, and
  // then there was no way to overrule it.
  const free = e.altKey;
  const ln = lines[drag.i];
  if (drag.grip && drag.all){
    // The whole line into the new span: every word moves, in proportion to its
    // syllables. This is what narrowing a line that swallowed an interlude
    // actually means.
    if (drag.grip === "right")
      ln.end = Math.max(drag.start + 0.3, drag.end + dt);
    else
      ln.start = clamp(drag.start + dt, 0, drag.end - 0.3);
    spread(ln);
  } else if (drag.grip === "right"){
    // Dragging the right edge stretches the LAST word; the rest stay exactly
    // where they were. This used to recompute the whole line, changing timing
    // that had been tuned by hand for no reason at all.
    const last = ln.words.length - 1;
    const floor = last >= 0 ? drag.words[last] + MIN_W : drag.start + 0.2;
    ln.end = Math.max(floor, drag.end + dt);
    if (last >= 0) ln.words[last].d = ln.end - ln.words[last].t;
    if (ln.end <= floor + 0.001) hitLimit();
  } else if (drag.grip === "left"){
    // The left edge does the same to the FIRST word: the line end is untouched.
    const w0 = ln.words[0];
    const ceil = w0 ? (drag.words[0] + drag.durs[0]) - MIN_W : drag.end - 0.2;
    let ns = clamp(drag.start + dt, 0, ceil);
    if (ns >= ceil - 0.001) hitLimit();
    const snap2 = free ? null : (grid.on ? nearestBeat(ns) : nearestOnset(ns));
    if (snap2 !== null && Math.abs(snap2 - ns) < zoom*0.012) ns = clamp(snap2, 0, ceil);
    ln.start = ns;
    if (w0){ w0.t = ns; w0.d = (drag.words[0] + drag.durs[0]) - ns; }
  } else {
    let ns = Math.max(0, drag.start + dt);
    // With the grid on, the beat is what a line belongs to; without it, the
    // start of a phrase in the sound.
    const snap = free ? null : (grid.on ? nearestBeat(ns) : nearestOnset(ns));
    if (snap !== null && Math.abs(snap-ns) < zoom*0.012) ns = snap;
    const d = ns - drag.start;
    ln.start = ns; ln.end = drag.end + d;
    ln.words.forEach((w,k) => w.t = drag.words[k] + d);
  }
  layoutBlock(drag.i); layoutWords();
  $("selNote").textContent = drag.grip === "right"
    ? T.lineEndAt(drag.i+1, fmtMs(ln.end))
    : T.lineAt(drag.i+1, fmtMs(ln.start));
});
window.addEventListener("pointerup", e => {
  if (wdrag){
    wdrag = null;
    wordEls.forEach(e => e.classList.remove("on"));
    $("tlwrap").classList.remove("drag"); curLine=-2; touched();
    return;
  }
  // A still second click on an already-selected block dives to the line
  // beneath it: overlapping lines can all be reached now, not only the top.
  if (diveAt && Math.abs(e.clientX - diveAt.x) < 3){
    const pile = [];
    for (let k = 0; k < lines.length; k++)
      if (lines[k].start <= diveAt.t && diveAt.t <= lines[k].end) pile.push(k);
    if (pile.length > 1){
      const at = pile.indexOf(sel);
      const next = pile[(at >= 0 ? at + 1 : 0) % pile.length];
      diveAt = null;
      if (drag){ drag = null; $("tlwrap").classList.remove("drag"); past.pop(); refreshUndo(); }
      selectLine(next, false);
      toast(T.lineDove(next + 1));
      return;
    }
  }
  diveAt = null;
  if (!drag) return;
  drag = null; $("tlwrap").classList.remove("drag"); curLine=-2; touched();
});
function nearestOnset(t){
  if (!onsets.length) return null;
  let best=null, bd=1e9;
  for (const o of onsets){ const d=Math.abs(o-t); if (d<bd){ bd=d; best=o; } }
  return best;
}
