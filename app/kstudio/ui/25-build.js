/* ================= building a song ================= */
$("btnBuild").addEventListener("click", async () => {
  const audio = $("inAudio").value.trim(), lyrics = $("inLyrics").value.trim();
  if (!audio || !lyrics) return toast(T.pickBoth);
  try{
    const j = await api("/api/new", {audio, lyrics, align: $("selAlign").value,
      model: $("selModel").value, lang: $("selLang").value,
      separate: $("chkSep").checked, noText: $("inNoText").value.trim(),
      separator: $("chkFine").checked ? "htdemucs_ft" : "htdemucs",
      // What the song is called. A link fills the fields in; a file from disk
      // leaves them for the person, because the name that survives every file
      // system is not the name anybody wants to read on a video.
      title: $("inTitle").value.trim(),
      artist: $("inArtist").value.trim(),
      // Whether the name was typed or merely offered: a name of one's own
      // outranks the “title:” inside a lyrics file, an offered one does not.
      titleSet: nameTyped,
      cover: (lastSong && lastSong.cover) || "",
      coverBg: !!(lastSong && lastSong.cover && $("chkCover").checked)});
    watchJob(j.job, T.jobBuild, id => openProject(id));
  }catch(e){ toast(e.message); }
});

function watchJob(jid, title, onDone){
  $("jobTitle").textContent = title;
  $("jobLog").textContent = "";
  $("btnJobBack").classList.add("hide");
  screen("scrJob");
  const tick = async () => {
    let j;
    // A failed job used to leave this screen spinning with no way back: its
    // “error” came through api() as a thrown request, and the tick stopped.
    try { j = await jobState(jid); } catch(e){ return setTimeout(tick, 900); }
    $("jobLog").textContent = (j.log||[]).join("\n");
    $("jobLog").scrollTop = 1e9;
    if (!j.done && !j.error) return setTimeout(tick, 600);
    if (j.done && j.ok) onDone(j.result);
    else {
      $("jobTitle").textContent = T.jobFail;
      $("btnJobBack").classList.remove("hide");
    }
  };
  tick();
}
$("btnJobBack").addEventListener("click", loadList);
$("btnBack").addEventListener("click", async () => {
  stop(); await flush();            // leave only once the edit is written
  loadList();
});
// The tab was closed right after an edit — get it onto disk in time.
window.addEventListener("beforeunload", () => {
  if (!dirty) return;
  clearTimeout(saveT);
  navigator.sendBeacon(`/api/project/${encodeURIComponent(pid)}/timings`,
    new Blob([JSON.stringify({lines, colors, theme})], {type:"application/json"}));
});

