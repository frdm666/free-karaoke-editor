/* Any language beyond these two is a JSON file in kstudio/messages: the server
   lists what it has, the window loads the file and falls back to English for
   whatever is missing. A half-finished translation is still useful. */
const LANG_UI_KEY = "karaoke-studio-lang";
let extraLangs = [];
async function loadLang(code){
  if (STR[code]) return true;
  try {
    const msgs = await api("/api/messages?lang=" + encodeURIComponent(code));
    if (!msgs || !Object.keys(msgs).length) return false;
    const filled = {};
    for (const [k, v] of Object.entries(msgs)) if (v) filled[k] = v;
    STR[code] = {...STR.en, ...filled};
    return true;
  } catch (e) { return false; }
}
let LANG = (() => {
  try { const v = localStorage.getItem(LANG_UI_KEY); if (STR[v]) return v; } catch(e){}
  const want = (window.KARAOKE_UI_LANG || "auto");
  if (STR[want]) return want;
  const nav = (navigator.language || "en").slice(0,2).toLowerCase();
  return STR[nav] ? nav : "en";
})();
let T = STR[LANG];
function applyLang(root){
  const box = root || document;
  box.querySelectorAll("[data-t]").forEach(e => {
    const v = T[e.dataset.t];
    if (typeof v === "string") e.innerHTML = v;
  });
  box.querySelectorAll("[data-tt]").forEach(e => {
    const v = T[e.dataset.tt];
    if (typeof v === "string") e.title = v;
  });
  box.querySelectorAll("[data-tp]").forEach(e => {
    const v = T[e.dataset.tp];
    if (typeof v === "string") e.placeholder = v;
  });
  document.documentElement.lang = LANG;
  // The tab title is part of the window too — it must not stay in one language.
  if (typeof T.appTitle === "string") document.title = T.appTitle;
}
const clamp = (v,a,b) => v<a?a:(v>b?b:v);
const fmt = s => { s=Math.max(0,s|0); return (s/60|0)+":"+String(s%60).padStart(2,"0"); };
const fmtMs = s => { s=Math.max(0,s); const m=s/60|0, r=s-m*60;
  return m+":"+(r<10?"0":"")+r.toFixed(3); };
let toastT=0;
function toast(msg){ const e=$("toast"); e.textContent=msg; e.classList.add("show");
  clearTimeout(toastT); toastT=setTimeout(()=>e.classList.remove("show"),2300); }

async function api(path, body){
  // Server messages — the “Check” panel, the build log — must follow the window
  // language, and that choice lives here. So the server has to be told.
  const head = {"X-Karaoke-Lang": LANG};
  const r = await fetch(path, body
    ? {method:"POST", headers:{...head, "Content-Type":"application/json"},
       body: JSON.stringify(body)}
    : {headers: head});
  const j = await r.json().catch(()=>({error: T.badReply}));
  if (j && j.error) throw new Error(j.error);
  return j;
}
// Labels are put in place before the list is drawn for the first time.
applyLang();
function labelLang(){
  // The button shows the language it switches TO — clearer than the current one.
  const ring = ["en", "ru", ...extraLangs];
  const next = ring[(ring.indexOf(LANG) + 1) % ring.length];
  $("btnLang").textContent = next.toUpperCase();
}
labelLang();
$("btnLang").addEventListener("click", async () => {
  const ring = ["en", "ru", ...extraLangs];
  const next = ring[(ring.indexOf(LANG) + 1) % ring.length];
  if (!(await loadLang(next))) return toast(T.langMissing(next));
  LANG = next; T = STR[LANG];
  try { localStorage.setItem(LANG_UI_KEY, LANG); } catch(e){}
  applyLang(); labelLang(); relabel();
  toast(T.langSwitched || next.toUpperCase());
});
// Some labels are assembled on the fly — those are redrawn separately.
function relabel(){
  if (!$("scrEdit").classList.contains("hide")){
    $("hint").textContent = T.hotkeys;
    if (sel >= 0) $("selNote").textContent = T.lineNo(sel+1, fmtMs(lines[sel].start));
    else $("selNote").textContent = T.noLine;
    refreshVoice(); refreshKeep(); refreshRhythm(); drawSummary(lastData);
    $("zoomNote").textContent = zoomText();
    // The reasons in “Check” come from the server — ask again in the new language.
    api(`/api/project/${encodeURIComponent(pid)}`)
      .then(d => showProblems(d.problems)).catch(() => {});
    buildLines(); makeBlocks(); curLine = -2;
  }
  if (!$("scrList").classList.contains("hide")) loadList();
  if (!$("scrNew").classList.contains("hide")){ fillLangs(); markModels(); modelNote();
    reportKey = ""; askReport(); }
}

function screen(name){
  ["scrList","scrNew","scrJob","scrEdit"].forEach(id =>
    $(id).classList.toggle("hide", id !== name));
}

