/* ---------- suspicious lines ---------- */
// The summary of the song. Such a report already existed before building; after
// the long part it is needed just as much — what came out and where to look.
function drawSummary(data){
  const box = $("sum");
  const words = lines.reduce((n, l) => n + (l.words ? l.words.length : 0), 0);
  const sung = lines.reduce((n, l) => n + (l.end - l.start), 0);
  const q = quiet || [];
  const qTotal = q.reduce((n, x) => n + (x.end - x.start), 0);
  const v2 = lines.filter(l => l.voice === 2).length;
  const kept = lines.filter(l => l.keep).length;
  const cells = [
    [T.rLength, fmt(dur)],
    [T.sSung, Math.round(100 * sung / (dur || 1)) + "%"],
    [T.rLines, String(lines.length)],
    [T.rWords, String(words)],
    [T.rQuiet, q.length ? T.rQuietN(q.length, Math.round(qTotal)) : T.sNone],
    [T.sEngine, (data && data.engine) || "—"],
  ];
  if (v2) cells.push([T.sVoice2, T.sLines(v2)]);
  if (kept) cells.push([T.sKept, T.sLines(kept)]);
  box.innerHTML = cells.map(([k, v]) =>
    `<div class="c"><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join("");
  if (q.length){
    // The program hears these stretches itself. Until now it only pointed at
    // them and left the marking to the mouse — on a screamed song that is the
    // same handful of minutes, every time.
    const d = document.createElement("div");
    d.className = "c wide";
    d.append(T.quietAt);
    q.slice(0, 12).forEach(x => {
      const chip = document.createElement("span");
      chip.className = "qchip" + (markedAlready(x) ? " taken" : "");
      const u = document.createElement("u");
      u.textContent = fmt(x.start) + "–" + fmt(x.end);
      u.addEventListener("click", () => seek(Math.max(0, x.start - 0.5)));
      chip.append(u);
      if (!markedAlready(x)){
        const add = document.createElement("i");
        add.textContent = "＋";
        add.title = T.quietTake;
        add.addEventListener("click", ev => { ev.stopPropagation(); takeQuiet([x]); });
        chip.append(add);
      } else chip.title = T.quietTaken;
      d.append(chip);
    });
    if (q.length > 12) d.append(T.andMore(q.length - 12));
    if (q.some(x => !markedAlready(x))){
      const all = document.createElement("button");
      all.className = "words";
      all.textContent = T.quietTakeAll;
      all.addEventListener("click", () => takeQuiet(q));
      d.append(all);
    }
    box.appendChild(d);
  }
}
function showProblems(list){
  const box=$("probs"); box.innerHTML="";
  const restore = () => {
    if (!checkOff.length) return;
    const r = document.createElement("div");
    r.className = "ignored-note";
    r.textContent = T.restoreIgnored(checkOff.length);
    r.addEventListener("click", async () => {
      checkOff = [];
      touched();
      await flush();
      openProject(pid);
    });
    box.appendChild(r);
  };
  if (!list || !list.length){
    box.innerHTML='<div class="allgood">' + T.allGood + '</div>';
    restore();
    lineEls.forEach(L => L.el.querySelectorAll(".bad").forEach(x=>x.remove()));
    window.__badLines = new Set(); layoutBlocks(); return;
  }
  const bad = new Set(list.map(p=>p.line));
  lineEls.forEach((L,i) => {
    L.el.querySelectorAll(".bad").forEach(x=>x.remove());
    if (bad.has(i)){ const s=document.createElement("span"); s.className="bad";
      s.textContent="●"; L.el.appendChild(s); }
  });
  list.forEach(p => {
    const e=document.createElement("div"); e.className="prob";
    e.innerHTML=`<b></b><span></span><div class="tm">${fmtMs(p.start)}</div>`
      + `<button class="ign" title=""></button>`;
    const ign = e.querySelector(".ign");
    ign.textContent = "✕";
    ign.title = T.ignoreHint;
    ign.addEventListener("click", ev => {
      // “Ignore”, the way a spell-checker has it: this warning, this line —
      // keyed to the words, so it survives lines being split or renumbered.
      ev.stopPropagation();
      (p.kinds || []).forEach(k => {
        const key = (p.text || "").trim() + "|" + k;
        if (!checkOff.includes(key)) checkOff.push(key);
      });
      touched();
      showProblems(list.filter(x => x !== p));
      toast(T.ignored);
    });
    e.querySelector("b").textContent = (p.line+1)+". "+p.text;
    e.querySelector("span").textContent = p.why.join(" · ");
    e.addEventListener("click", ()=>selectLine(p.line, true));
    box.appendChild(e);
  });
  restore();
  window.__badLines = bad;
  layoutBlocks();
}

