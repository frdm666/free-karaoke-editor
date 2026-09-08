/* ================= audio ================= */
let ctx=null, bufs=null, gains=null, srcs=null, audioNames=["mix"];
let waStart=0, waOffset=0, playing=false, dur=0, voiceLevel=0, hasStems=false;
/* ---------- sound ---------- */
function mediaTime(){
  // While paused, waOffset is the truth: a seek moves it at once.
  return playing ? Math.min(Math.max(waOffset + (ctx.currentTime - waStart), waOffset), dur)
                 : waOffset;
}
async function loadAudio(pid, tracks){
  ctx = new (window.AudioContext||window.webkitAudioContext)();
  hasStems = !!(tracks.instrumental && tracks.vocals);
  const names = hasStems ? ["instrumental","vocals"] : [Object.keys(tracks)[0]];
  audioNames = names;
  const raw = await Promise.all(names.map(n =>
    fetch(`/api/project/${encodeURIComponent(pid)}/audio/${n}`).then(r => r.arrayBuffer())));
  bufs = await Promise.all(raw.map(b => ctx.decodeAudioData(b)));
  gains = bufs.map(() => { const g = ctx.createGain(); g.connect(ctx.destination); return g; });
  dur = bufs[0].duration;
  $("grpVoice").classList.toggle("hide", !hasStems);
  setVoice(0);
}
function stopSrcs(){ if(!srcs) return;
  srcs.forEach(s => { try{ s.onended=null; s.stop(); }catch(e){} }); srcs=null; }
function playFrom(t){
  stopSrcs();
  t = clamp(t, 0, Math.max(dur-0.02, 0));
  srcs = bufs.map((b,i) => { const s=ctx.createBufferSource(); s.buffer=b;
    s.connect(gains[i]); return s; });
  const at = ctx.currentTime + 0.03;
  srcs.forEach(s => s.start(at, t));
  srcs[0].onended = () => { if (playing && mediaTime() >= dur-0.2){ stop(); } stopSrcs(); };
  waStart = at; waOffset = t; playing = true;
  $("btnPlay").textContent = "⏸";
}
function play(){ if(!bufs) return; if (ctx.state==="suspended") ctx.resume();
  if (waOffset >= dur-0.05) waOffset = 0;
  playFrom(waOffset); }
function stop(){ if(!playing) return; waOffset = mediaTime(); playing=false; stopSrcs();
  $("btnPlay").textContent="▶"; }
function seek(t){ waOffset = clamp(t,0,dur); curLine=-2;
  stillFollow();                        // the open frame moves with the song
  if (playing) playFrom(waOffset); else stopSrcs(); }
// On marked lines the voice always plays: that is audible here, not only in
// the finished karaoke.
let keepOn = 0;                 // how loud the original stays right now
function inKeep(t){
  // How loud the original stays here: 1 where it sings alone, 0.35 where it
  // is a guide to sing along with, 0 everywhere else. A breath between two
  // kept lines is kept too, unless the singer's own line stands in it —
  // muting the model's guess of a line end chewed a held word in half.
  // Where the singer's own line sounds, the original gets no slack and no
  // bridge: kept voice bleeding over their first word is the chew, mirrored.
  let humanAt = false;
  for (let i = 0; i < lines.length; i++){
    const ln = lines[i];
    if (!ln.keep && ln.words && ln.words.length && !ln.backing
        && ln.start <= t && t < ln.end){ humanAt = true; break; }
  }
  let best = 0, prevEnd = -1, prevLvl = 0, bridge = 0;
  for (let i = 0; i < lines.length; i++){
    const ln = lines[i];
    if (!ln.keep) continue;
    const lvl = ln.keepSoft ? 0.35 : 1;
    const pad = humanAt ? 0 : 0.25;
    if (ln.start - pad <= t && t < ln.end + pad) best = Math.max(best, lvl);
    if (ln.end <= t && t - ln.end <= 2.0){ prevEnd = ln.end; prevLvl = lvl; }
    if (t < ln.start && ln.start - t <= 2.0 && prevEnd >= 0
        && ln.start - prevEnd <= 2.0)
      bridge = Math.max(bridge, Math.max(prevLvl, lvl));
  }
  if (!humanAt) best = Math.max(best, bridge);
  if (best >= 1) return 1;
  // A marked stretch has no words to sing, so the original voice stays there —
  // and the editor must sound like the finished page, not unlike it.
  if ($("chkKeepMarks") && $("chkKeepMarks").checked)
    for (let i = 0; i < marks.length; i++)
      if (marks[i][0] - 0.12 <= t && t < marks[i][1] + 0.12) return 1;
  return best;
}
function applyVoice(){
  const lvl = keepOn ? Math.max(keepOn, voiceLevel) : voiceLevel;
  if (gains){ gains[0].gain.value = 1;
    if (hasStems){
      const g = gains[1].gain;
      if (g.setTargetAtTime) g.setTargetAtTime(lvl, ctx.currentTime, 0.03);
      else g.value = lvl;
    } }
}
function setVoice(v){ voiceLevel = clamp(v,0,1);
  applyVoice();
  $("rVoice").value = Math.round(voiceLevel*100);
  $("vVoice").textContent = Math.round(voiceLevel*100)+"%"; }
$("btnPlay").addEventListener("click", () => playing ? stop() : play());
$("rVoice").addEventListener("input", e => setVoice(e.target.value/100));

