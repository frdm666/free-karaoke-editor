/* ================= file browser ================= */
let pickTarget = null;
document.querySelectorAll("[data-pick]").forEach(b =>
  b.addEventListener("click", () => openBrowser(b.dataset.pick)));
$("brCancel").addEventListener("click", () => $("browser").classList.add("hide"));
$("brUp").addEventListener("click", () => showDir($("brBody").dataset.parent));

// The browser opens where it was left, not at the top: hunting for the same
// file across the whole drive every time is a chore. Audio and lyrics folders
// are remembered separately — they really do tend to differ.
const DIR_KEY = "karaoke.dir.";
function dirKind(kind){ return (kind === "lyrics" || kind === "lyrics2") ? "text" : "audio"; }
function rememberDir(kind, path){
  try { localStorage.setItem(DIR_KEY + dirKind(kind), path || ""); } catch(e){}
}
function startDir(kind){
  // 1) where we were last time with a file of this kind
  try {
    const saved = localStorage.getItem(DIR_KEY + dirKind(kind));
    if (saved) return saved;
  } catch(e){}
  // 2) next to whatever is already chosen in this window
  const field = kind === "lyrics" ? $("inLyrics").value : $("inAudio").value;
  if (field) return field;
  // 3) next to the sources of the open song — the sensible one in the editor
  if (data){
    const src = dirKind(kind) === "text" ? data.source_lyrics : data.source_audio;
    if (src) return src;
  }
  return "";
}
async function unpackSong(path){
  try{
    const r = await api("/api/unpack", {path});
    toast(T.unpacked);
    await loadList();
    if (r.id) openProject(r.id);
  }catch(e){ toast(e.message); }
}
async function openBrowser(kind){
  pickTarget = kind;
  $("browser").classList.remove("hide");
  $("brTitle").textContent = kind === "track" ? T.pickTrack
    : kind === "lyrics2" ? T.pickLyrics
    : kind === "pack" ? T.openPack
    : kind === "cover" ? T.pickCover
    : kind === "backdrop" ? T.pickBackdrop : T.pickFile;
  await showDir(startDir(kind));
}
// Looking the words up worked only while building; picking “another text”
// for a finished song sent a person back to files alone. The same search now
// stands above the file list — and a record that knows its times is taken
// with them, as pegs.
async function foundRows(box){
  const name = songName || (data && data.title) || "";
  if (!name) return;
  let got;
  try{
    got = await api("/api/lyrics/find",
      {track: name, artist: songArtist || (data && data.artist) || "",
       duration: dur || 0});
  }catch(e){ return; }                  // no library — the files are still here
  (got.found || []).slice(0, 3).forEach(f => {
    const r = document.createElement("div");
    r.className = "row found2";
    const timed = !!(f.timed && f.textTimed);
    r.innerHTML = '<span class="ic">🔎</span><span class="nm"></span>' +
      '<span class="sz"></span>';
    r.querySelector(".nm").textContent =
      (f.artist ? f.artist + " — " : "") + f.title +
      (timed ? " · " + T.lyricsHasTimes : "");
    r.querySelector(".sz").textContent = T.countLines(f.lines);
    r.addEventListener("click", async () => {
      $("browser").classList.add("hide");
      try{
        const saved = await api("/api/lyrics/save",
          {text: (timed ? f.textTimed : f.text) || "", name});
        realign(saved.path);
      }catch(e){ toast(e.message); }
    });
    box.appendChild(r);
  });
}

async function showDir(path){
  // “track” means audio, “lyrics2” means text, “pack” is a packed song
  const kind = pickTarget === "pack" ? "pack"
    : (pickTarget === "cover" || pickTarget === "backdrop") ? "image"
    : (pickTarget === "lyrics" || pickTarget === "lyrics2") ? "text" : "audio";
  const d = await api("/api/browse?kind="+kind+"&path="+encodeURIComponent(path||""));
  $("brPath").value = d.path;
  rememberDir(pickTarget, d.path);       // this is where we come back next time
  const body = $("brBody");
  body.dataset.parent = d.parent;
  body.innerHTML = "";
  if (pickTarget === "lyrics2") await foundRows(body);
  if (pickTarget === "cover") urlRow(body, T.coverUrlPh, takeCover);
  if (pickTarget === "backdrop") urlRow(body, T.backdropUrlPh, takeBackdrop);
  (d.drives||[]).forEach(dr => body.appendChild(row("💽", dr, () => showDir(dr))));
  d.dirs.forEach(x => body.appendChild(row("📁", x.name, () => showDir(x.path))));
  d.files.forEach(x => body.appendChild(row("🎵", x.name, () => {
    $("browser").classList.add("hide");
    if (pickTarget === "pack"){ unpackSong(x.path); return; }
    if (pickTarget === "cover"){ takeCover(x.path); return; }
    if (pickTarget === "backdrop"){ takeBackdrop(x.path); return; }
    if (pickTarget === "track"){ replaceTrack(x.path); return; }
    if (pickTarget === "lyrics2"){ realign(x.path); return; }
    if (pickTarget !== "lyrics"){
      lastSong = null;                              // not the song from the link
      $("grpCover").classList.add("hide");          // and its cover goes with it
      $("chkCover").checked = false;
    }
    $(pickTarget === "lyrics" ? "inLyrics" : "inAudio").value = x.path;
    if (pickTarget !== "lyrics" && !$("inTitle").value.trim())
      $("inTitle").value = fileStem(x.path);
    askReport();
  }, (x.size/1024/1024).toFixed(1)+T.mb)));
  if (!d.dirs.length && !d.files.length)
    body.innerHTML = '<div class="row muted">' + esc(T.noFiles) + '</div>';
}
function row(ic, name, fn, size){
  const e = document.createElement("div");
  e.className = "row";
  e.innerHTML = `<span class="ic">${ic}</span><span class="nm"></span>` +
                (size ? `<span class="sz">${size}</span>` : "");
  e.querySelector(".nm").textContent = name;
  e.addEventListener("click", fn);
  return e;
}

