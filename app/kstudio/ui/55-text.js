/* ---------- editing the text itself ---------- */
// A typo in the source txt used to need a full rebuild — which threw away all
// the hand tuning. Here a line is fixed in place: its time stays, and the words
// are laid out inside it again.
function syllables(word){
  const m = word.toLowerCase().match(/[аеёиоуыэюяaeiouy]/g);
  return Math.max(1, m ? m.length : 1);        // syllables are counted by vowels
}
// The word as sung, stripped of everything that is not sung: dots on a scream,
// commas, case. Two words that match here are the same word.
function normTok(w){ return w.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ""); }
function retext(i, text){
  const parts = text.trim().split(/\s+/).filter(Boolean);
  const ln = lines[i];
  if (!parts.length || parts.join(" ") === ln.text) return false;
  ln.text = parts.join(" ");
  // Editing the text can turn a line into backing vocals and back.
  ln.backing = /^\(.*\)$/.test(ln.text.trim());
  // Dots added to a long scream, one word fixed in the middle: where the words
  // are the same words, their times are THEIR times — laying the whole line
  // out anew threw away exactly the rhythm the person had already set. Only
  // the changed stretch is laid out, in the gap the change occupies.
  const old = ln.words;
  const oldN = old.map(w => normTok(w.w)), newN = parts.map(normTok);
  let pre = 0;
  while (pre < old.length && pre < parts.length
         && oldN[pre] && oldN[pre] === newN[pre]) pre++;
  let suf = 0;
  while (suf < old.length - pre && suf < parts.length - pre
         && oldN[old.length - 1 - suf]
         && oldN[old.length - 1 - suf] === newN[parts.length - 1 - suf]) suf++;
  const words = [];
  for (let k = 0; k < pre; k++)
    words.push({w: parts[k], t: old[k].t, d: old[k].d, s: syllables(parts[k])});
  const mid = parts.slice(pre, parts.length - suf);
  if (mid.length){
    const gapStart = pre ? old[pre - 1].t + old[pre - 1].d : ln.start;
    const gapEnd = suf ? old[old.length - suf].t : ln.end;
    const lo = Math.min(gapStart, gapEnd);
    const hi = Math.max(gapEnd, lo + MIN_W * mid.length);
    const syl = mid.reduce((a, w) => a + syllables(w), 0) || 1;
    let acc = 0;
    mid.forEach(w => {
      const t0 = lo + (hi - lo) * acc / syl;
      acc += syllables(w);
      const t1 = lo + (hi - lo) * acc / syl;
      words.push({w, t: t0, d: Math.max(t1 - t0, MIN_W), s: syllables(w)});
    });
  }
  for (let k = old.length - suf; k < old.length; k++){
    const w = parts[parts.length - (old.length - k)];
    words.push({w, t: old[k].t, d: old[k].d, s: syllables(w)});
  }
  ln.words = words;
  ln.start = words[0].t;
  ln.end = Math.max(words[words.length - 1].t + (words[words.length - 1].d || 0),
                    ln.start + 0.2);
  return true;
}
// A missing or a stray line is as much a mistake in the text as a typo, and
// rebuilding the whole song over it makes no more sense.
function addLine(){
  if (sel < 0) return toast(T.addAfter);
  const cur = lines[sel];
  const next = lines[sel + 1];
  // A new line takes the gap up to the next one, but no more than two seconds:
  // there is no point filling a long pause after a solo. The gap can even be
  // negative — neighbouring lines may already overlap — and then a short piece
  // is taken; the “Check” panel will point at the overlap anyway.
  const start = cur.end;
  const room = next ? next.start - start : Infinity;
  const end = start + Math.max(0.4, Math.min(2, room));
  // `section` is a heading that STARTS at this line. An inserted line must not
  // carry one, or “[Chorus]” would appear in the song twice.
  const ln = {text: T.newLineText, start, end: Math.max(end, start + 0.4),
              section: null, backing: false, words: []};
  ln.words = ln.text.split(" ").map(w => ({w, t: start, d: 0, s: syllables(w)}));
  spread(ln);
  snap("");
  lines.splice(sel + 1, 0, ln);
  buildLines(); makeBlocks(); selectLine(sel + 1, false); touched();
  editText(sel);                       // let the real text be typed straight away
}
/* ---------- splitting a line, and joining two ----------
   The most ordinary correction there is: a long line sung in two breaths, or
   two short ones that are really one phrase. Neither needs a model — the words
   and their times are already known, only the grouping changes. Before this,
   it meant editing the file on disk and timing the whole song again. */
function splitLine(){
  if (sel < 0) return toast(T.pickLineFirst);
  const ln = lines[sel];
  if (!ln.words || ln.words.length < 2) return toast(T.splitTooShort);
  // Where the singing pauses longest inside the line: that is where a person
  // draws breath, and where the line wants to be cut.
  let at = 1, widest = -1;
  for (let i = 1; i < ln.words.length; i++){
    const gap = ln.words[i].t - (ln.words[i - 1].t + (ln.words[i - 1].d || 0));
    if (gap > widest){ widest = gap; at = i; }
  }
  snap("");
  const tail = ln.words.slice(at), head = ln.words.slice(0, at);
  const cut = tail[0].t;
  const second = {
    text: tail.map(w => w.w).join(" "),
    start: cut, end: ln.end,
    section: null, backing: ln.backing, voice: ln.voice,
    keep: ln.keep, lock: ln.lock, words: tail,
  };
  ln.words = head;
  ln.text = head.map(w => w.w).join(" ");
  // Words can overlap slightly, so the last word of the first half may reach
  // past where the second half begins. A line must never end after the next
  // one starts — the highlight would jump back and forth.
  const headEnd = head[head.length - 1].t + (head[head.length - 1].d || 0);
  ln.end = Math.max(ln.start + 0.05, Math.min(headEnd, cut));
  lines.splice(sel + 1, 0, second);
  buildLines(); makeBlocks(); selectLine(sel + 1, false); touched();
  toast(T.lineSplit);
}
function joinLine(){
  if (sel < 0) return toast(T.pickLineFirst);
  if (sel + 1 >= lines.length) return toast(T.joinNoNext);
  const a = lines[sel], b = lines[sel + 1];
  if (b.section) return toast(T.joinAcrossSection);
  snap("");
  a.words = a.words.concat(b.words);
  a.text = (a.text + " " + b.text).replace(/\s+/g, " ").trim();
  a.end = b.end;
  a.keep = a.keep || b.keep;
  a.lock = a.lock || b.lock;
  lines.splice(sel + 1, 1);
  marked.clear();
  buildLines(); makeBlocks(); selectLine(sel, false); touched();
  toast(T.lineJoined);
}
$("btnSplit").addEventListener("click", splitLine);
$("btnJoin").addEventListener("click", joinLine);

function delLine(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  if (lines.length <= idx.length) return toast(T.delLast);
  const what = idx.length > 1 ? T.delAskMany(idx.length) : T.delAsk(lines[idx[0]].text);
  if (!confirm(what)) return;
  snap("");
  idx.slice().reverse().forEach(i => lines.splice(i, 1));
  const keep = clamp(idx[0], 0, lines.length - 1);
  marked.clear();
  buildLines(); makeBlocks(); selectLine(keep, false); touched();
  toast(idx.length > 1 ? T.linesDeleted(idx.length) : T.lineDeleted);
}
// Editing the text had to be guessed: a double click on a line is not what
// comes to mind while looking at the timeline. The button says it out loud.
$("btnText").addEventListener("click", () => {
  if (sel < 0) return toast(T.pickLineFirst);
  editText(sel);
});
$("btnAddLine").addEventListener("click", addLine);
$("btnDelLine").addEventListener("click", delLine);

let editingText = -1;
function editText(i){
  if (editingText >= 0) return;
  if (i < 0 || !lines[i]) return;
  selectLine(i, false);
  centerLine(i);                   // the line may be off-stage — bring it into view
  editingText = i;
  const el = lineEls[i].el, ln = lines[i];
  const inp = document.createElement("input");
  inp.className = "lnedit"; inp.value = ln.text;
  inp.setAttribute("aria-label", T.lineTextAria(i+1));
  el.replaceChildren(inp);
  inp.focus(); inp.select();

  const finish = (save) => {
    if (editingText < 0) return;
    editingText = -1;
    if (save) snap("");
    const changed = save && retext(i, inp.value);
    // nothing changed, so there must be no undo step, or the button would stay
    // lit over an empty history and do nothing when pressed
    if (save && !changed){ past.pop(); refreshUndo(); }
    buildLines();                       // rebuild the stage: the word count changed
    makeBlocks();                       // and the label on the timeline too
    selectLine(i, false);
    if (changed){ touched(); toast(T.lineTextFixed); }
  };
  inp.addEventListener("keydown", e => {
    e.stopPropagation();                // or Enter and Space would hit the hotkeys
    if (e.key === "Enter"){ e.preventDefault(); finish(true); }
    if (e.key === "Escape"){ e.preventDefault(); finish(false); }
  });
  inp.addEventListener("blur", () => finish(true));
  inp.addEventListener("click", e => e.stopPropagation());
  inp.addEventListener("dblclick", e => e.stopPropagation());
}

let songName = "", songArtist = "", namingNow = false;

function showName(){
  $("edTitle").textContent = songName + (songArtist ? " — " + songArtist : "");
}

// The name is not only a label in the window: it stands in the corner of the
// video, on its opening card, on the page, and it names the exported files.
// Taken from a file name or a lyrics header it is often wrong, and there was
// no way to say otherwise.
function editName(){
  if (namingNow) return;
  namingNow = true;
  const h = $("edTitle"), was = h.textContent;
  const box = document.createElement("span");
  box.className = "nameEdit";
  const t = document.createElement("input");
  t.className = "t"; t.value = songName; t.placeholder = T.namePlaceTitle;
  t.setAttribute("aria-label", T.namePlaceTitle);
  const dash = document.createElement("span");
  dash.textContent = "—";
  const a = document.createElement("input");
  a.className = "a"; a.value = songArtist; a.placeholder = T.namePlaceArtist;
  a.setAttribute("aria-label", T.namePlaceArtist);
  box.append(t, dash, a);
  h.replaceChildren(box);
  t.focus(); t.select();

  const finish = (save) => {
    if (!namingNow) return;
    namingNow = false;
    const nt = t.value.trim(), na = a.value.trim();
    const changed = save && (nt !== songName || na !== songArtist);
    if (changed){ songName = nt; songArtist = na; }
    h.replaceChildren();
    showName();
    if (!songName && !songArtist) h.textContent = was;   // nothing to show
    if (changed){ touched(); toast(T.nameFixed); }
  };
  for (const inp of [t, a]){
    inp.addEventListener("keydown", e => {
      e.stopPropagation();              // Enter and Space belong to the stage
      if (e.key === "Enter"){ e.preventDefault(); finish(true); }
      if (e.key === "Escape"){ e.preventDefault(); finish(false); }
    });
    inp.addEventListener("blur", () => {
      // Moving between the two fields is not leaving the name.
      setTimeout(() => { if (![t, a].includes(document.activeElement)) finish(true); }, 0);
    });
  }
}

function spread(ln){
  const total = ln.words.reduce((s,w)=>s+(w.s||1),0)||1;
  // The span used to be forced up to 0.15 s here — and on a narrow line the
  // words were laid out WIDER than the line itself, spilling out of the block.
  // No invented lengths: if a line is too short for its words, the line grows.
  const need = ln.words.length * MIN_W;
  if (ln.end - ln.start < need) ln.end = ln.start + need;
  const span = ln.end - ln.start;
  let acc=0;
  ln.words.forEach(w => { w.t = ln.start + span*acc/total; acc += (w.s||1);
    w.d = ln.start + span*acc/total - w.t; });
}

