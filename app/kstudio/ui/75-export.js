/* ================= export ================= */
// A real instrumental from the artist beats any separated one. The timing is
// already tuned by hand — there is no need to redo it, only the audio changes.
$("btnTrack").addEventListener("click", () => openBrowser("track"));
async function replaceTrack(path){
  await flush();
  const j = await api(`/api/project/${encodeURIComponent(pid)}/track`,
                      {path, track: "instrumental", shift: true});
  watchJob(j.job, T.replTrack, async r => {
    await openProject(pid);            // re-read: both the audio and the times changed
    const parts = [T.replDone];
    if (Math.abs(r.offset) >= 0.05)
      parts.push(T.offsetDiff((r.offset > 0 ? "+" : "") + r.offset.toFixed(2)));
    if (Math.abs(r.shifted) >= 0.05) parts.push(T.shiftedToo);
    if (Math.abs(r.lengthDiff) > 1)
      parts.push(T.lengthDiff((r.lengthDiff > 0 ? "+" : "") + r.lengthDiff));
    toast(parts.join(" · "));
  });
}

// The way the text is split into lines is usually fixed after the first build,
// once it is clear how it sings. That is no reason to redo everything: the
// tracks are already in the project, only the timing is recomputed.
async function realign(lyricsPath){
  await flush();
  try{
    const j = await api(`/api/project/${encodeURIComponent(pid)}/realign`,
      {align: caps.whisper ? "auto" : "energy", lang: langOf(),
       lyrics: lyricsPath || "", noText: ($("edNoText").value || "").trim()});
    watchJob(j.job, lyricsPath ? T.realignNew : T.realignSame,
      r => {
        openProject(pid);
        toast(r && r.was && r.lines !== r.was
              ? T.realignStats(r.was, r.lines)
              : T.realignDone);
      });
  }catch(e){ toast(e.message); }
}
let checkOff = [];
function fillNoText(d){
  checkOff = (d && d.checkOff) ? d.checkOff.slice() : [];
  const el = $("edNoText");
  if (el) el.value = (d && d.noText) || "";
  if ($("chkKeepMarks"))
    $("chkKeepMarks").checked = !d || d.keepMarks !== false;
  marksFromField();
  if (marking) setMarking(false);
}
// Typed by hand, dragged with the mouse — one and the same thing underneath.
$("edNoText").addEventListener("change", () => { marksFromField(); touched(); drawWave(); });
$("chkKeepMarks").addEventListener("change", touched);
function langOf(){
  // Re-timing has no picker of its own, and the language of a song belongs to
  // the song, not to the window: read it off the text again.
  return "auto";
}
// The minimap answers to the mouse: a press jumps, a drag scrubs.
(() => {
  const c = $("mmap");
  if (!c) return;
  let down = false;
  const at = e => {
    const r = c.getBoundingClientRect();
    return clamp((e.clientX - r.left) / r.width, 0, 1) * dur;
  };
  c.addEventListener("pointerdown", e => { down = true;
    if (c.setPointerCapture) try{ c.setPointerCapture(e.pointerId); }catch(err){}
    seek(at(e)); });
  c.addEventListener("pointermove", e => { if (down) seek(at(e)); });
  c.addEventListener("pointerup", () => { down = false; });
})();

$("edTitle").addEventListener("click", editName);
$("edTitle").addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " "){ e.preventDefault(); editName(); }
});
$("btnLyrics").addEventListener("click", () => {
  if (!confirm(T.askLyrics)) return;
  openBrowser("lyrics2");
});
$("btnRealign").addEventListener("click", async () => {
  // A common case: the same file, simply edited. It is re-read from disk —
  // nothing has to be picked again. The model is named in the question: it
  // used to change to another one without a word.
  const m = (data && data.model) ? T.withModel(data.model) : "";
  if (!confirm(T.askRealign + m)) return;
  realign("");
});

// The finished file sits next to the original song and is not easy to find
// without a hint. Show the path and open the folder with one press.
let madeFile = "";
function showMade(path){
  madeFile = path || "";
  $("madePath").textContent = madeFile;
  $("madeRow").classList.toggle("hide", !madeFile);
}
$("btnReveal").addEventListener("click", async () => {
  if (!madeFile) return;
  await reveal(madeFile);
});
$("btnMadeHide").addEventListener("click", () => showMade(""));

// A frame of the clip, drawn on the spot. Before this the only way to see
// whether a line sits where it should was to render the whole file.
// While the frame is open it follows the song: a seek redraws it where the
// playhead now stands, and the arrows step through without touching the song.
let stillT = 0, stillTimer = 0;
function stillFollow(){
  if ($("stillBox").classList.contains("hide")) return;
  clearTimeout(stillTimer);
  stillTimer = setTimeout(() => showStill(mediaTime(), false), 350);
}
async function showStill(at, opening){
  const box = $("stillBox"), img = $("stillImg");
  box.classList.remove("hide");
  stillT = opening ? 0 : Math.max(0, at);
  $("stillAt").textContent = opening ? T.stillOpeningAt : T.stillAt(fmt(at));
  // Asked for in the song's own time: the clip runs ahead of it by the length
  // of the opening, and how long that is, only the drawing knows.
  const url = `/api/project/${encodeURIComponent(pid)}/still?at=`
    + Math.max(0, at) + (opening ? "&opening=1" : "") + "&_=" + Date.now();
  try{
    const r = await fetch(url);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
    img.src = URL.createObjectURL(await r.blob());
  }catch(e){
    box.classList.add("hide");
    toast(T.stillFailed + e.message);
  }
}
// A song in one file: the folder it lives in does not travel between two
// computers, and a zip of it does.
$("btnPack").addEventListener("click", async () => {
  $("expMenu").classList.add("hide");
  await flush();                        // pack what is on the screen, not what was
  toast(T.packing);
  try{
    const r = await api(`/api/project/${encodeURIComponent(pid)}/pack`, {});
    showMade(r.path);
    toast(T.packed);
  }catch(e){ toast(e.message); }
});
$("btnUnpack").addEventListener("click", () => openBrowser("pack"));

// The cover, changeable after the build: a song from a file had nowhere to
// get one, and a song from a link had no way to swap it.
function refreshCover(){
  const on = !!(data && data.cover && data.coverBg);
  $("btnCoverOff").classList.toggle("hide", !on);
  $("grpCoverDark").classList.toggle("hide", !on);
  showDark((data && data.coverDark != null) ? data.coverDark : 66);
}
// Darker reads better, lighter shows more of the picture — a matter of the
// cover at hand, so it is a knob, not a constant. Two ways in: the slider for
// the eye, the field for a number you already know; an exact percent could
// not be felt for on a narrow slider at all.
function showDark(v){
  const dark = Math.round(clamp(+v || 0, 0, 95));
  $("rCoverDark").value = dark;
  if (document.activeElement !== $("nCoverDark")) $("nCoverDark").value = dark;
  return dark;
}
function setDark(v){
  const dark = showDark(v);
  if (!data || data.coverDark === dark) return;
  data.coverDark = dark;
  touched();
  // The open frame follows, once the hand has settled.
  clearTimeout(stillTimer);
  stillTimer = setTimeout(() => {
    refreshStill();
  }, 400);
}
$("rCoverDark").addEventListener("input", () => setDark($("rCoverDark").value));
$("nCoverDark").addEventListener("input", () => setDark($("nCoverDark").value));
$("nCoverDark").addEventListener("keydown", e => {
  e.stopPropagation();                  // digits are digits, not hotkeys
  if (e.key === "Enter"){ e.preventDefault(); $("nCoverDark").blur(); }
});
// Leaving the field with nonsense in it shows what actually stands.
$("nCoverDark").addEventListener("blur", () => showDark(data && data.coverDark));
$("btnCover").addEventListener("click", () => openBrowser("cover"));
$("btnCoverOff").addEventListener("click", async () => {
  try{
    await api(`/api/project/${encodeURIComponent(pid)}/cover`, {remove: true});
    data.cover = null; data.coverBg = false;
    refreshCover(); toast(T.coverGone);
  }catch(e){ toast(e.message); }
});
// A cover or a clip can come by link too: a row above the files takes the
// address and hands it to whatever is being fetched.
function urlRow(box, placeholder, take){
  const r = document.createElement("div");
  r.className = "row urlrow";
  r.innerHTML = '<span class="ic">🔗</span>' +
    '<input class="nm" type="text">' +
    '<button class="words"></button>';
  const inp = r.querySelector("input");
  inp.placeholder = placeholder;
  const btn = r.querySelector("button");
  btn.textContent = T.coverUrlGo;
  const go = () => {
    const url = inp.value.trim();
    if (!/^https?:\/\//.test(url)) return toast(T.coverUrlBad);
    $("browser").classList.add("hide");
    take(null, url);
  };
  btn.addEventListener("click", go);
  inp.addEventListener("keydown", e => {
    e.stopPropagation();
    if (e.key === "Enter") go();
  });
  inp.addEventListener("click", e => e.stopPropagation());
  box.appendChild(r);
}

async function takeCover(path, url){
  try{
    const r = await api(`/api/project/${encodeURIComponent(pid)}/cover`,
      url ? {url} : {path});
    data.cover = "cover.jpg"; data.coverBg = true;
    refreshCover(); toast(T.coverSet);
    refreshStill();
  }catch(e){ toast(e.message); }
}

// A clip standing behind the lyrics, instead of a still. It is kept small on
// purpose — the render blurs it into a slow field of colour — so the link the
// song itself came from is a fair place to get one.
function refreshBackdrop(){
  $("btnClipBgOff").classList.toggle("hide", !(data && data.backdrop));
}
async function takeBackdrop(path, url){
  toast(T.backdropWait);
  try{
    await api(`/api/project/${encodeURIComponent(pid)}/backdrop`,
      url ? {url} : {path});
    data.backdrop = "backdrop.mp4";
    refreshBackdrop(); toast(T.backdropSet);
    refreshStill();
  }catch(e){ toast(e.message); }
}
$("btnClipBg").addEventListener("click", () => openBrowser("backdrop"));
$("btnClipBgOff").addEventListener("click", async () => {
  try{
    await api(`/api/project/${encodeURIComponent(pid)}/backdrop`, {off: true});
    data.backdrop = null;
    refreshBackdrop(); toast(T.backdropGone);
    refreshStill();
  }catch(e){ toast(e.message); }
});

$("btnStill").addEventListener("click", () => showStill(mediaTime(), false));
$("stillOpening").addEventListener("click", () => showStill(0, true));
$("stillHide").addEventListener("click", () => $("stillBox").classList.add("hide"));
$("stillPrev").addEventListener("click", () => showStill(Math.max(0, stillT - 2), false));
$("stillNext").addEventListener("click", () => showStill(Math.min(dur, stillT + 2), false));

// The other doors out: the singing games and the subtitle world. Behind one
// narrow button, because the header is a shelf, not a warehouse.
$("btnExportMore").addEventListener("click", e => {
  e.stopPropagation();
  $("expMenu").classList.toggle("hide");
});
document.addEventListener("click", () => $("expMenu").classList.add("hide"));
async function exportKind(kind, label){
  $("expMenu").classList.add("hide");
  await flush();
  const j = await api(`/api/project/${encodeURIComponent(pid)}/export`, {kind});
  watchJob(j.job, label, r => {
    screen("scrEdit"); showMade(r.path); toast(T.jobReady);
  });
}
$("btnExportUs").addEventListener("click", () => exportKind("ultrastar", T.jobUs));
$("btnExportAss").addEventListener("click", () => exportKind("ass", T.jobAss));

$("btnExportHtml").addEventListener("click", async () => {
  await flush();
  const j = await api(`/api/project/${encodeURIComponent(pid)}/export`, {kind:"html"});
  watchJob(j.job, T.jobHtml, r => {
    screen("scrEdit"); showMade(r.path); toast(T.jobReady);
  });
});
// The MP4 dialog: size, frames, quality and the opening — remembered
// between songs, because taste does not change per song.
$("btnExportMp4").addEventListener("click", () => {
  try{
    const saved = JSON.parse(localStorage.getItem("mp4opts") || "{}");
    if (saved.size) $("expSize").value = saved.size;
    if (saved.fps) $("expFps").value = saved.fps;
    if (saved.q) $("expQ").value = saved.q;
    if (saved.intro != null) $("expIntro").checked = !!saved.intro;
    // The key is not remembered between songs: it belongs to one throat and
    // one song, and a forgotten +3 would quietly retune the next one.
    $("expKey").value = "0";
  }catch(e){}
  $("expDlg").classList.remove("hide");
});
$("btnExpCancel").addEventListener("click", () => $("expDlg").classList.add("hide"));
$("expDlg").addEventListener("click", e => {
  if (e.target === $("expDlg")) $("expDlg").classList.add("hide");
});
$("btnExpGo").addEventListener("click", async () => {
  $("expDlg").classList.add("hide");
  const [w, h] = $("expSize").value.split("x").map(Number);
  const opts = {kind: "mp4", width: w, height: h,
                fps: +$("expFps").value, crf: +$("expQ").value,
                intro: $("expIntro").checked,
                semitones: +$("expKey").value || 0};
  try{
    localStorage.setItem("mp4opts", JSON.stringify({size: $("expSize").value,
      fps: $("expFps").value, q: $("expQ").value, intro: $("expIntro").checked}));
  }catch(e){}
  await flush();
  const j = await api(`/api/project/${encodeURIComponent(pid)}/export`, opts);
  watchJob(j.job, T.jobVideo, r => {
    screen("scrEdit"); showMade(r.path); toast(T.videoReady);
    // The video takes a while to draw, and then it has to be found. Open the
    // folder ourselves.
    reveal(r.path);
  });
});
async function reveal(path){
  if (!path) return;
  try { await api("/api/reveal", {path}); }
  catch(e){ toast(e.message); }
}

window.addEventListener("resize", () => { layoutBlocks(); drawWave(); drawBlocks(); });
loadList().catch(e => { document.body.innerHTML =
  '<div class="empty"><h2>' + esc(T.serverDown) + '</h2>' + esc(e.message) + '</div>'; });
})();
