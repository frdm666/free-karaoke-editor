/* ================= dropping files into the window ================= */
const AUDIO_RE = /\.(mp3|wav|flac|m4a|ogg|opus|aac|wma|mp4)$/i;
const TEXT_RE  = /\.(txt|lrc)$/i;
let dragDepth = 0;

function hasFiles(e){
  const t = e.dataTransfer;
  return t && Array.from(t.types || []).includes("Files");
}
window.addEventListener("dragenter", e => {
  if (!hasFiles(e)) return;
  e.preventDefault(); dragDepth++;
  $("dropHint").classList.remove("hide");
});
window.addEventListener("dragover", e => { if (hasFiles(e)) e.preventDefault(); });
window.addEventListener("dragleave", e => {
  if (!hasFiles(e)) return;
  if (--dragDepth <= 0){ dragDepth = 0; $("dropHint").classList.add("hide"); }
});
window.addEventListener("drop", async e => {
  if (!hasFiles(e)) return;
  e.preventDefault(); dragDepth = 0; $("dropHint").classList.add("hide");
  const files = Array.from(e.dataTransfer.files || []);
  if (!files.length) return;

  // A packed song opens itself: drop the .karaoke.zip anywhere in the window
  // and it goes back among the songs, no button hunted for.
  const pack = files.find(f => /\.zip$/i.test(f.name));
  if (pack){
    toast(T.taking(pack.name));
    try{
      const up = await upload(pack);
      await unpackSong(up.path);
    }catch(err){ toast(T.dropFail + err.message); }
    return;
  }

  const audio = files.find(f => AUDIO_RE.test(f.name));
  const text  = files.find(f => TEXT_RE.test(f.name));
  if (!audio && !text)
    return toast(T.dropUnknown);

  // The browser never gives the path of a dropped file, only its contents.
  // So the bytes are sent to the studio, which puts them next to the projects.
  screen("scrNew");
  try{
    if (audio){ toast(T.taking(audio.name));
      lastSong = null;                              // dropped by hand, not fetched
      $("grpCover").classList.add("hide");
      $("chkCover").checked = false;
      $("inAudio").value = (await upload(audio)).path;
      if (!$("inTitle").value.trim()) $("inTitle").value = fileStem(audio.name); }
    if (text){ $("inLyrics").value = (await upload(text)).path; }
    toast(audio && text ? T.filesOk
                        : T.filesHalf);
    askReport();
  }catch(err){ toast(T.dropFail + err.message); }
});

async function upload(file){
  const r = await fetch("/api/upload?name=" + encodeURIComponent(file.name),
                        {method:"POST", body:file});
  const j = await r.json().catch(()=>({error: T.badReply}));
  if (j.error) throw new Error(j.error);
  return j;
}

/* ================= a link instead of a file =================
   The sound is taken out of the link by yt-dlp, and once it is here the words
   are looked for by the name of the song. Both can fail, and neither failure
   is a dead end: the file picker and the box for pasting the text are right
   there. */
let lastSong = null;

let nameTyped = false;          // the name was typed, not merely offered
for (const id of ["inTitle", "inArtist"])
  $(id).addEventListener("input", () => { nameTyped = true; });

// “D:\\Music\\Lorna Shore - Forevermore.mp3” → “Lorna Shore - Forevermore”.
function fileStem(path){
  const name = String(path || "").split(/[\\/]/).pop() || "";
  return name.replace(/\.[a-z0-9]{1,5}$/i, "").trim();
}

function resetLink(){
  $("inLink").value = "";
  $("inTitle").value = "";
  $("inArtist").value = "";
  nameTyped = false;
  $("grpCover").classList.add("hide");
  $("chkCover").checked = false;
  $("lyricsFound").innerHTML = "";
  $("lyricsFound").classList.add("hide");
  $("pasteBox").classList.add("hide");
  $("taLyrics").value = "";
  $("pasteCount").textContent = "";
  $("lyricsNote").textContent = "";
  lastSong = null;
  // Without yt-dlp the link cannot be taken, and saying so beforehand is
  // better than letting a person paste one and wait for the refusal.
  note("linkNote", caps.fetch === false ? (caps.fetchHelp || "") : "", true);
}
function note(id, msg, warn){
  const e = $(id);
  e.textContent = msg || "";
  e.classList.toggle("warnish", !!warn && !!msg);
}
// A job that fell over carries its own “error”, and that is not the request
// failing — reading it through api() would throw on the very answer that has
// to be shown. So the job is read as it is.
async function jobState(jid){
  const r = await fetch("/api/job?id=" + encodeURIComponent(jid),
                        {headers: {"X-Karaoke-Lang": LANG}});
  return await r.json().catch(() => ({error: T.badReply, done: true}));
}
// The job screen takes the whole window; a download belongs where it was
// started, next to the field with the link.
function followJob(jid, onLine){
  return new Promise((resolve, reject) => {
    const tick = async () => {
      let j;
      try { j = await jobState(jid); }
      catch(e){ return setTimeout(tick, 900); }   // the server will be back
      const log = j.log || [];
      if (log.length && onLine) onLine(log[log.length - 1]);
      if (!j.done && !j.error) return setTimeout(tick, 600);
      if (j.done && j.ok) resolve(j.result);
      else reject(new Error(j.error || T.jobFail));
    };
    tick();
  });
}
async function takeLink(){
  const url = $("inLink").value.trim();
  if (!url) return note("linkNote", T.linkNeedUrl, true);
  const btn = $("btnFetch");
  btn.disabled = true;
  note("linkNote", T.linkWorking);
  let trace = "";
  try{
    const j = await api("/api/fetch", {url});
    const got = await followJob(j.job, line => {
      // The whole error goes to a file, and the log says which one. Worth
      // keeping: when the reason is a fault of ours, that file is the answer.
      if (/last-error\.txt/.test(line)) trace = line;
      note("linkNote", line);
    });
    lastSong = got;
    if (!$("inTitle").value.trim()) $("inTitle").value = got.track || got.title || "";
    if (!$("inArtist").value.trim()) $("inArtist").value = got.artist || "";
    $("grpCover").classList.toggle("hide", !got.cover);
    $("chkCover").checked = !!got.cover;
    $("inAudio").value = got.path;
    note("linkNote", T.linkGot(got.name));
    askReport();
    findLyrics(got);
  }catch(e){
    // The job already says “It did not download”; the word “Error” in front of
    // the downloader's own sentence only doubles it.
    note("linkNote", T.linkFail(String(e.message).replace(/^(Error|Ошибка):\s*/, ""))
                     + (trace ? " · " + trace : ""), true);
  }finally{
    btn.disabled = false;
  }
}
$("btnFetch").addEventListener("click", takeLink);
$("inLink").addEventListener("keydown", e => { if (e.key === "Enter") takeLink(); });

async function findLyrics(song){
  const box = $("lyricsFound");
  box.innerHTML = ""; box.classList.add("hide");
  if ($("inLyrics").value.trim()) return;      // a text is already chosen
  note("lyricsNote", T.lyricsSearching);
  try{
    const r = await api("/api/lyrics/find", {track: song.track || song.title,
      artist: song.artist || "", duration: song.duration || 0});
    const found = r.found || [];
    if (!found.length) return note("lyricsNote", T.lyricsNone(r.source));
    note("lyricsNote", T.lyricsFoundN(found.length, r.source));
    found.forEach(f => box.appendChild(foundRow(f)));
    box.classList.remove("hide");
  }catch(e){
    note("lyricsNote", T.lyricsNone(caps.lyricsSource || "") + " " + e.message);
  }
}
function foundRow(f){
  const e = document.createElement("div");
  e.className = "one";
  e.innerHTML = '<div class="t"><b></b><span></span><div class="first"></div></div>' +
                '<button></button>';
  e.querySelector("b").textContent = f.artist ? f.artist + " — " + f.title : f.title;
  e.querySelector("span").textContent =
    [T.countLines(f.lines), f.duration ? fmt(f.duration) : "", f.source]
      .filter(Boolean).join(" · ");
  e.querySelector(".first").textContent = (f.text || "").split("\n")[0] || "";
  // A record that knows when its lines are sung is worth more than one that
  // only knows the words: those times become pegs, and the model no longer
  // has to guess the places — which is the one thing it gets badly wrong.
  const timed = !!(f.timed && f.textTimed);
  const btn = e.querySelector("button");
  btn.textContent = timed ? T.lyricsUseTimed : T.lyricsUse;
  if (timed) btn.classList.add("pri");
  btn.addEventListener("click", () => takeFound(f, timed));
  if (timed){
    e.querySelector("span").textContent += " · " + T.lyricsHasTimes;
    const words = document.createElement("button");
    words.className = "words";
    words.textContent = T.lyricsWordsOnly;
    words.addEventListener("click", () => takeFound(f, false));
    e.appendChild(words);
  }
  return e;
}
// Taking a found text puts it in the box AND straight into the field: it works
// with one press, and it is still there to be read and corrected.
async function takeFound(f, withTimes){
  const timed = !!(withTimes && f.textTimed);
  $("taLyrics").value = (timed ? f.textTimed : f.text) || "";
  $("pasteBox").classList.remove("hide");
  countPasted();
  note("lyricsNote", timed ? T.lyricsTookTimed : T.lyricsTook);
  await useTyped(true);
}
$("btnPasteText").addEventListener("click", () => {
  const box = $("pasteBox");
  box.classList.toggle("hide");
  if (!box.classList.contains("hide")){ $("taLyrics").focus(); countPasted(); }
});
$("btnPasteHide").addEventListener("click", () => $("pasteBox").classList.add("hide"));
$("taLyrics").addEventListener("input", countPasted);
function countPasted(){
  const n = $("taLyrics").value.split("\n").filter(x => x.trim()).length;
  $("pasteCount").textContent = n ? T.countLines(n) : "";
}
// A one-line field cannot hold lyrics: the line breaks are lost on the way in
// and the whole song arrives as one long run. So a paste that is plainly the
// words themselves is taken to the box below, where the lines stay lines.
function looksLikeText(s){
  return /[\r\n\u2028\u2029]/.test(s) || (s.length > 200 && /\s/.test(s));
}
$("inLyrics").addEventListener("paste", e => {
  const raw = (e.clipboardData || window.clipboardData || {}).getData
    ? (e.clipboardData || window.clipboardData).getData("text") : "";
  if (!looksLikeText(raw)) return;                  // a path: let it through
  e.preventDefault();
  $("taLyrics").value = raw.replace(/\r\n?/g, "\n").replace(/[\u2028\u2029]/g, "\n").trim();
  $("pasteBox").classList.remove("hide");
  countPasted();
  note("lyricsNote", T.pastedIntoBox);
  useTyped(true);
});
// And a link pasted into the field for a file belongs one row down.
$("inAudio").addEventListener("paste", e => {
  const raw = (e.clipboardData || window.clipboardData || {}).getData
    ? (e.clipboardData || window.clipboardData).getData("text").trim() : "";
  if (!/^https?:\/\//i.test(raw)) return;
  e.preventDefault();
  $("inLink").value = raw;
  note("linkNote", T.linkMoved);
  $("inLink").focus();
});
$("btnUseText").addEventListener("click", () => useTyped(false));
async function useTyped(quiet){
  const text = $("taLyrics").value.trim();
  if (!text) return note("lyricsNote", T.pasteEmpty, true);
  try{
    const name = lastSong ? (lastSong.track || lastSong.title || "lyrics") : "lyrics";
    const r = await api("/api/lyrics/save", {text, name});
    $("inLyrics").value = r.path;
    if (!quiet) note("lyricsNote", T.textSaved);
    askReport();
  }catch(e){ note("lyricsNote", e.message, true); }
}

