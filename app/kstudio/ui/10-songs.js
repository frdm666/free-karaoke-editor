/* ================= song list ================= */
let caps = {}, lastData = null;
async function loadList(){
  const st = await api("/api/state");
  caps = st.caps;
  extraLangs = st.uiLangs || [];
  labelLang();
  const notes = [];
  if (!caps.ffmpeg) notes.push(T.noFfmpeg);
  if (!caps.whisper) notes.push(T.noStable);
  if (!caps.demucs) notes.push(T.noDemucs);
  $("capNote").textContent = notes.join(" · ");

  const box = $("cards"); box.innerHTML = "";
  $("emptyNote").classList.toggle("hide", st.projects.length > 0);
  st.projects.forEach(p => {
    const el = document.createElement("div");
    el.className = "card";
    el.dataset.id = p.id;               // the card says which song it is
    el.innerHTML = `<div class="t"><b></b><span></span></div>
      <div class="badge">${p.stems ? T.twoTracks : T.oneTrack}</div>
      <div class="badge">${fmt(p.duration)}</div>
      <button class="del" title="${T.removeSong}">✕</button>`;
    el.querySelector("b").textContent = p.title;
    el.querySelector("span").textContent =
      (p.artist ? p.artist + " · " : "") + T.linesN(p.lines);
    el.addEventListener("click", () => openProject(p.id));
    el.querySelector(".del").addEventListener("click", async ev => {
      ev.stopPropagation();
      if (!confirm(T.askRemove(p.title))) return;
      try{ await api(`/api/project/${encodeURIComponent(p.id)}/delete`, {});
        toast(T.removed); loadList(); }catch(e){ toast(e.message); }
    });
    box.appendChild(el);
  });
  screen("scrList");
}
// Mark which models are already on disk: the difference between “here” and
// “will download now” is minutes of waiting before the first alignment, and the
// size in megabytes alone does not show it.
function heavy(model){
  // Heavy for this machine: not forbidden, but pretending all are equal is a lie.
  const need = (caps.needGb || {})[model], free = caps.freeGb;
  return (need && free && free < need) ? need : 0;
}
function markModels(){
  const have = caps.models || {};
  [...$("selModel").options].forEach(o => {
    const base = T[o.dataset.t] || o.textContent;
    o.textContent = base + (have[o.value] ? T.modelHave
                                          : T.modelGet)
                  + (heavy(o.value) ? T.modelHeavy : "");
  });
}
function modelNote(){
  const v = $("selModel").value, have = (caps.models || {})[v];
  const slow = $("selAlign").value !== "energy";
  const need = heavy(v);
  let s = "";
  if (slow){
    s = have ? T.noteReady : T.noteDownload;
    if (need)
      s += T.needRam(need, caps.freeGb.toFixed(1)) + T.noteSlow;
  }
  if (slow && $("selLang").value !== "auto")
    s += T.langManual($("selLang").selectedOptions[0].textContent);
  else if (slow)
    s += T.noteLangAuto;
  $("modelNote").textContent = s;
  $("modelNote").classList.toggle("warnish", !!need && slow);
}
// Whisper needs the language: with the wrong one the timing falls apart. The
// window used to send Russian silently, with nowhere to choose.
//
// The choice is NOT carried over to the next song. It used to be, and that is
// worse than it sounds: for a song in another language the window quietly
// answered with the previous one instead of reading the text, and detection —
// which is right almost every time — never ran at all.
function fillLangs(){
  const sel = $("selLang"), names = caps.langs || {auto: T.detectByText};
  // Language names are written in the languages themselves and are not
  // translated. “Detect from the text”, though, is a window label.
  if (sel.options.length){
    const a = [...sel.options].find(o => o.value === "auto");
    if (a) a.textContent = T.detectByText;
    return;                                    // the list of languages never changes
  }
  for (const [code, name] of Object.entries(names)){
    const o = document.createElement("option");
    o.value = code; o.textContent = code === "auto" ? T.detectByText : name;
    sel.appendChild(o);
  }
  sel.value = "auto";
}
/* ---------- the report before building ----------
   Building takes minutes, and half the mistakes are visible beforehand: the
   wrong text, the wrong language, not enough memory. Show that before the
   button is pressed. */
let reportT = 0, reportKey = "";
function askReport(){
  const audio = $("inAudio").value.trim(), lyrics = $("inLyrics").value.trim();
  const box = $("report");
  if (!audio || !lyrics){ box.classList.add("hide"); reportKey = ""; return; }
  const key = [audio, lyrics, $("selAlign").value, $("selModel").value,
               $("selLang").value, $("chkSep").checked].join("|");
  if (key === reportKey) return;                 // nothing has changed
  reportKey = key;
  box.classList.remove("hide");
  box.innerHTML = '<div class="busy">' + esc(T.lookingAt) + '</div>';
  clearTimeout(reportT);
  reportT = setTimeout(async () => {
    try{
      const r = await api("/api/report", {audio, lyrics, align: $("selAlign").value,
        model: $("selModel").value, lang: $("selLang").value,
        separate: $("chkSep").checked});
      if (key === reportKey) drawReport(r);
    }catch(e){
      if (key === reportKey)
        box.innerHTML = '<div class="note">' + esc(T.badFiles) +
                        esc(e.message) + '</div>';
    }
  }, 250);
}
function esc(s){ const d = document.createElement("div"); d.textContent = s;
                 return d.innerHTML; }
function drawReport(r){
  const box = $("report"), a = r.audio, t = r.text, p = r.plan;
  const q = a.quiet || [];
  const cells = [
    [T.rLength, fmt(a.duration)],
    // What matters for karaoke is not the tempo but where the text is silent:
    // intro, interlude, solo. No line should end up in there.
    [T.rQuiet, q.length ? T.rQuietN(q.length, Math.round(a.quietTotal))
                        : T.rQuietNone],
    [T.rLines, String(t.lines)],
    [T.rWords, String(t.words)],
    [T.rRepeats, String(t.repeats)],
    [T.rLang, r.language.name],
  ];
  const steps = [];
  if (p.separate) steps.push(T.planSep);
  steps.push(p.whisper ? T.planWhisper(p.model) : T.planEnergy);
  const where = q.length
    ? '<div class="plan">' + T.quietAt +
      q.slice(0,4).map(x => fmt(x.start) + "–" + fmt(x.end)).join(", ") +
      (q.length > 4 ? T.andMore(q.length - 4) : "") + "</div>"
    : "";
  box.innerHTML =
    '<div class="grid">' +
    cells.map(([k, v]) => `<div class="cell"><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join("") +
    '</div><div class="plan">' + T.willDo + esc(steps.join(", ")) +
    T.takes + esc(humanTime(p.seconds)) + T.veryRough +
    (r.language.auto ? T.langFromText : "") + '</div>' +
    where + r.notes.map(n => `<div class="note">! ${esc(n)}</div>`).join("");
}
function humanTime(sec){
  if (sec < 90) return T.aboutSec(Math.max(sec, 5));
  const m = sec/60|0;
  return m < 60 ? T.aboutMin(m) : T.aboutHour(m/60|0, m%60);
}
["inAudio","inLyrics"].forEach(id =>
  $(id).addEventListener("input", askReport));
["selAlign","selModel","selLang","chkSep"].forEach(id =>
  $(id).addEventListener("change", askReport));

$("selLang").addEventListener("change", modelNote);
$("selModel").addEventListener("change", modelNote);
$("selAlign").addEventListener("change", modelNote);

$("btnAdd").addEventListener("click", () => {
  $("newWarn").textContent = caps.whisper ? "" :
    T.noStableWarn;
  $("selAlign").value = caps.whisper ? "auto" : "energy";
  $("selLang").value = "auto";        // every song starts from its own text
  $("chkSep").checked = !!caps.demucs;
  $("chkFine").checked = false;
  $("chkFine").disabled = !caps.demucs;
  fillLangs(); markModels(); modelNote();
  resetLink();
  reportKey = ""; askReport();
  screen("scrNew");
});
// “Separate finely” has nothing to do while the instrumental is off: the timing
// would be made from the mix, and no separator would run at all.
$("chkSep").addEventListener("change", () => {
  $("chkFine").disabled = !$("chkSep").checked || !caps.demucs;
  if ($("chkFine").disabled) $("chkFine").checked = false;
});
$("btnBackNew").addEventListener("click", loadList);

