/* ================= the drawing loop ================= */
function tick(){
  if (!$("scrEdit").classList.contains("hide")){
    const t = mediaTime();
    if (loopSel && sel>=0 && playing){
      const a=Math.max(0,lines[sel].start-0.6), b=lines[sel].end+0.5;
      if (t > b || t < a-0.1) seek(a);
    }
    showWait(t, idxAt(t));
    const kp = hasStems && playing ? inKeep(t) : 0;
    if (kp !== keepOn){ keepOn = kp; applyVoice(); }
    let idx=-1;
    for (let i=0;i<lines.length;i++){ if (lines[i].start <= t) idx=i; else break; }
    // The song is over — turn the highlight off. Otherwise the last line hangs
    // lit until the end of the recording and looks forgotten.
    if (idx === lines.length - 1 && idx >= 0 && t > lines[idx].end + 0.25) idx = -1;
    // The second voice can sound together with the first: the neighbour whose
    // time covers this moment and whose voice differs is the duet partner. It
    // used to sit unlit while its words were being sung.
    let duoIdx = -1;
    if (idx >= 0)
      for (const j of [idx - 1, idx + 1])
        if (j >= 0 && j < lines.length && lines[j].start <= t && t < lines[j].end
            && (lines[j].voice === 2) !== (lines[idx].voice === 2)){
          duoIdx = j;
          break;
        }
    if (idx !== curLine || duoIdx !== curDuo){
      lineEls.forEach((L,i)=>{
        L.el.classList.toggle("back", !!lines[i].backing);
        L.el.classList.toggle("v2", lines[i].voice === 2);
        L.el.classList.toggle("keep", !!lines[i].keep);
        L.el.classList.toggle("cur", i===idx || i===duoIdx);
        L.el.classList.toggle("done", i<Math.min(idx, duoIdx < 0 ? idx : duoIdx));
        if (i!==idx && i!==duoIdx) L.hls.forEach(h=>h.style.width="0");
      });
      curLine = idx; curDuo = duoIdx; centerLine(idx);
    }
    const fill = i => {
      const L=lineEls[i], ln=lines[i];
      for (let j=0;j<ln.words.length;j++){
        const w=ln.words[j], p = w.d>0 ? clamp((t-w.t)/w.d,0,1) : (t>=w.t?1:0);
        const want = p>=1?"100%":(p<=0?"0px":(p*100).toFixed(1)+"%");
        if (L.hls[j].style.width !== want) L.hls[j].style.width = want;
      }
    };
    if (idx>=0) fill(idx);
    if (duoIdx>=0) fill(duoIdx);
    $("tCur").textContent = fmtMs(t);
    // The view is not recomputed while dragging — otherwise the timeline
    // slides under the cursor — but an edit made DURING a drag still shows:
    // its handler marks the wave dirty, and the mark is honoured here.
    const kq2 = pps(), v0 = viewStart();
    const sig = v0.toFixed(2) + "|" + kq2.toFixed(2) + "|"
      + Math.round(t * kq2) + "|" + sel + "|" + curLine + "|"
      + $("tlwrap").clientWidth + "x" + $("tlwrap").clientHeight
      + "@" + devicePixelRatio;
    if (waveDirty || (!drag && !wdrag && sig !== waveSig)){
      waveDirty = false; waveSig = sig;
      paintWave();
      paintMap();
    }
    if (!drag && !wdrag) drawBlocks();
  }
  requestAnimationFrame(tick);
}

