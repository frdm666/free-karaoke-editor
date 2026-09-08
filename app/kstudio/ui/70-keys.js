/* ================= keyboard ================= */
document.addEventListener("keydown", e => {
  if ($("scrEdit").classList.contains("hide")) return;
  if (e.target.tagName === "INPUT") return;
  const nudge = (d) => { if (sel<0) return;
    snap("nudge");                  // holding a key is one undo step
    const last = restToo() ? lines.length-1 : sel;
    for (let k=sel; k<=last; k++){
      lines[k].start+=d; lines[k].end+=d; lines[k].words.forEach(w=>w.t+=d); }
    curLine=-2; if (restToo()) layoutBlocks(); else layoutBlock(sel); touched();
    $("selNote").textContent = T.lineNo(sel+1, fmtMs(lines[sel].start)); };
  if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z" ||
       e.key === "я" || e.key === "Я")){
    e.preventDefault(); undo(); return;
  }
  if (e.ctrlKey || e.metaKey){
    const k = e.key.toLowerCase();
    if (k === "c" || k === "с"){ e.preventDefault(); copyRhythm(); return; }
    if (k === "v" || k === "м"){
      e.preventDefault(); e.shiftKey ? pasteLine() : pasteRhythm(); return; }
    if (k === "d" || k === "в"){ e.preventDefault(); duplicateLine(); return; }
  }
  switch(e.key){
    case " ": e.preventDefault(); playing?stop():play(); break;
    case "ArrowLeft": e.preventDefault(); seek(mediaTime()-5); break;
    case "ArrowRight": e.preventDefault(); seek(mediaTime()+5); break;
    // Shift+arrows pick a batch of lines; plain arrows just walk one by one.
    case "ArrowUp": e.preventDefault();
      selectLine(sel-1, !e.shiftKey, e.shiftKey ? "range" : ""); break;
    case "ArrowDown": e.preventDefault();
      selectLine(sel+1, !e.shiftKey, e.shiftKey ? "range" : ""); break;
    case "Escape": if (marked.size){ e.preventDefault(); selectLine(sel, false); } break;
    case "Delete": case "Backspace":
      // Select a line, press Delete — the obvious action that was missing.
      e.preventDefault(); delLine(); break;
    case "Home": e.preventDefault(); freeScroll = 0; selectLine(0, true); break;
    case "End": e.preventDefault(); freeScroll = 0;
                selectLine(lines.length-1, true); break;
    case "PageUp": e.preventDefault(); stageScroll(-$("stage").clientHeight*0.8); break;
    case "PageDown": e.preventDefault(); stageScroll($("stage").clientHeight*0.8); break;
    case "[": e.preventDefault(); nudge(-0.05); break;
    case "]": e.preventDefault(); nudge(0.05); break;
    case "Enter": e.preventDefault(); putHere(); break;
  }
});

