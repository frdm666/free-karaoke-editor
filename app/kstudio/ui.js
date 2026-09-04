/* Karaoke Studio — the application window.
   The data lives on the server; every edit goes to disk right away. */
(function(){
"use strict";
const $ = id => document.getElementById(id);

/* ================= labels =================
   The markup is written in English; here live the Russian translation and
   everything assembled on the fly. The key is the same in both dictionaries. */
const STR = {
  en: {
    appTitle: "Karaoke Studio", addSong: "＋ Add a song",
    emptyTtl: "Nothing here yet",
    emptyBody: 'Press “Add a song” and point to two files: the song itself and ' +
      'its lyrics.<br>The program works out the instrumental and the timing once — ' +
      'after that your edits save themselves, nothing has to be rebuilt.' +
      '<div style="margin-top:18px; color:var(--accent)">You can also just drop ' +
      'both files into this window.</div>',
    back: "← Back", newSong: "New song", fileSong: "Song file",
    fileLyrics: "Lyrics file", choose: "Choose…",
    lyricsPh: "txt — one line of the song per line of the file",
    langAlign: "Language and timing",
    alignExact: "Accurate (Whisper), if available",
    alignFast: "Fast, without a neural net",
    langTitle: "Language of the lyrics", instrumental: "Instrumental",
    build: "Build", working: "Working…", toList: "← To the list", songs: "← Songs",
    savedNote: "saved", otherLyrics: "⇄ Other lyrics",
    lyricsHint: "Take a different lyrics file and time the song to it",
    ownTrack: "♪ My instrumental",
    trackHint: "Use the artist's real instrumental instead of the separated one",
    realign: "↻ Re-time",
    realignHint: "Re-read the same lyrics file from disk and time it again — if you edited it",
    exportHtml: "Standalone HTML", exportMp4: "MP4 video",
    summary: "Summary", check: "Check", openFolder: "Open folder", hide: "Hide",
    timeline: "Timeline", noLine: "no line selected",
    lineStartsHere: "⌖ Line starts here", andRest: "and all after it",
    lineText: "✎ Line text", textHint: "Fix the words of the selected line (or double-click it)",
    undo: "↶ Undo", undoHint: "Undo the last change (Ctrl+Z)",
    addLine: "＋ line",
    addLineHint: "Insert a line after the selected one — if it was missing from the lyrics",
    delLine: "－ line", delLineHint: "Delete the selected line from the lyrics",
    voiceHint: "Second voice for the selected line: another singer or another way " +
      "of singing. Painted in the second colour",
    keep: "♪ Original",
    keepHint: "Keep the original voice on this line: backing vocals, speech, a bit "
      + "that matters to the story. Pressed again, the original goes quiet — "
      + "a guide to sing along with. A third press gives the line back to you",
    colorsHint: "What the singing is lit with: first colour is the main voice, " +
      "second is the second voice",
    voices: "voices", voice1: "Main voice", voice2: "Second voice",
    themeHint: "Page look: background and text colour. If the text blends into the " +
      "background, the program fixes it",
    bgText: "background and text", bg: "Background", textColor: "Text colour",
    loop: "↻ Loop", loopHint: "Play the selected line over and over",
    snapAll: "Snap all to the vocal",
    snapHint: "Move every line to the nearest moment singing starts",
    // One gesture stays in sight; the rest waits under the cursor. The full
    // paragraph pushed the timeline up on every screen for the sake of a
    // first day that only happens once.
    howtoShort: "Click a line → play up to where it starts being sung → <b>Enter</b>.",
    howtoMore: "Blue blocks are lines, the yellow ones under them are that "
      + "line's words. Drag the middle to move, drag the edges to set the "
      + "length (Alt squeezes the whole line). Fine-tune a line with [ and ]. "
      + "Made a mistake — Ctrl+Z. The lyrics scroll with the wheel, Home and "
      + "End jump to the ends. Press and drag across the lines to pick "
      + "several — or Shift+click, Ctrl+click to add one. Voice, “original”, "
      + "delete and paste then work on all of them at once.",
    voice: "Voice", cancel: "Cancel", dropBig: "Drop the files here",
    dropSub: "the song and the lyrics — or one at a time",
    langUi: "Interface language",
    langMissing: code => `No translation file for “${code}” yet`,
    pasteHint: "Paste the copied rhythm into the selected line (Ctrl+V). With " +
      "“and all after it” — into every later line with the same text.",
    linesPicked: n => `${n} lines picked`,
    voiceManyOn: (v, n) => `Voice ${v} for ${n} lines`,
    keepManyMsg: (to, n) => !to.keep ? `${n} lines are sung by you again`
      : to.keepSoft ? `${n} lines: the original stays quiet, sing along`
                    : `${n} lines are left to the original`,
    delAskMany: n => `Delete ${n} lines from the lyrics?`,
    linesDeleted: n => `${n} lines deleted`,
    pasteLine: "⧉ Paste line",
    pasteLineHint: "Insert the copied lines below the selected one, keeping the " +
      "gaps between them (Ctrl+Shift+V). Nothing existing is overwritten — use " +
      "“Paste rhythm” if you only want the word layout.",
    lineReplaced: "The line was replaced by the copied one",
    linePasted: "The copied line was put below",
    linesReplaced: n => `${n} lines replaced by the copied one`,
    copiedLine: t => `Copied: “${t}”`,
    copiedLines: n => `Copied: ${n} lines`,
    linesPasted: n => `${n} lines pasted below`,
    copyRhythm: "⧉ Copy", pasteRhythm: n => `⧉ Paste rhythm${n > 1 ? " ×" + n : ""}`,
    rhythmHint: "Copy the selected line — words, rhythm, voice, marks — then paste " +
      "either its rhythm or the whole line into another one. " +
      "one with the same words (Ctrl+C / Ctrl+V). “and all after it” pastes into every " +
      "later line with the same text. Ctrl+D duplicates the line.",
    rhythmCopied: n => `Rhythm copied: ${n} words`,
    rhythmPasted: "The line now has the same rhythm",
    rhythmPastedN: n => `Rhythm applied to ${n} lines`,
    rhythmNone: "Nothing copied yet — press “Rhythm” on a line you like",
    rhythmMismatch: (a, b) => `The line has ${b} words and the copied one has ${a} — ` +
      "the rhythm does not fit",
    lineCopied: "The line was duplicated below",
    langSwitched: "Interface language: English",
    offsetDiff: v => `the start differed by ${v} s`,
    lengthDiff: v => `the length differs by ${v} s — check the end`,
    realignStats: (was, now) => `Done: ${was} lines before, ${now} now`,
    withModel: m => `\n\nThe timing is made with the “${m}” model, the same one it was built with.`,
    serverDown: "The server is not answering",
    model_tiny: "tiny — 75 MB", model_base: "base — 140 MB",
    model_small: "small — 480 MB", model_medium: "medium — 1.5 GB",
    model_turbo: "large-v3-turbo — 1.6 GB, nearly large at medium’s speed",
    model_large_v3: "large-v3 — 3 GB",
    fineSep: "separate finely",
    coverBg: "clip cover as backdrop",
    coverHint: "Put the clip's cover behind the lyrics — blurred hard and "
      + "darkened, so the words stay readable — on the finished page and in "
      + "the MP4. It appears when the song comes from a link.",
    fineSepHint: "Four passes over the song instead of one (htdemucs_ft): the "
      + "voice comes out cleaner, and the timing is made from that voice. "
      + "About four times longer, and 300 MB more to download the first time.",
    askRemove: t => `Remove “${t}” from the studio?\n\nThe original song and lyrics stay where they are.`,
    lookingAt: "Looking at what this song is…",
    badFiles: "Could not make sense of the files: ",
    allGood: "Nothing suspicious.<br>The lines sit where the singing is.",
    wordHint: w => `“${w}”: drag the middle to move, the edges to stretch`,
    wordAt: (w, t) => `word “${w}”: ${t}`,
    wordSpan: (w, a, b, d) => `word “${w}”: ${a} … ${b} (${d} s)`,
    lineEndAt: (n, t) => `line ${n}: end ${t}`,
    lineAt: (n, t) => `line ${n}: ${t}`,
    movedN: n => `Lines moved: ${n}`,
    lineSetRest: n => `Line ${n} and all after it have been shifted`,
    lineSet: n => `Line ${n} starts here`,
    needRam: (need, free) => ` It needs about ${need} GB of memory, and ${free} GB is free`,
    langManual: name => ` Language set by hand: ${name}.`,
    badReply: "bad answer from the server",
    noFfmpeg: "no ffmpeg — run Install.bat (install.command on macOS)",
    noStable: "without stable-ts the timing is approximate",
    noDemucs: "without demucs there will be no instrumental",
    twoTracks: "instrumental + vocal",
    oneTrack: "single track",
    removeSong: "Remove song",
    linesN: n => n + " lines",
    removed: "Removed",
    modelHave: " · already on disk",
    modelGet: " · downloads when building",
    modelHeavy: " · heavy for this machine",
    noteReady: "The model is on disk — timing starts right away.",
    noteDownload: "The model is not here yet: it downloads before timing, which can take a few minutes. The progress shows in the build log.",
    noteSlow: " — this will be very slow. A smaller model is safer, or close other programs.",
    noteLangAuto: " The language will be worked out from the text — the build log will name it.",
    detectByText: "work out from the text",
    rLength: "Length",
    rQuiet: "No singing",
    rQuietN: (n, sec) => n + " spots · " + sec + " s",
    rQuietNone: "none long",
    rLines: "Lines",
    rWords: "Words",
    rRepeats: "Repeats",
    rLang: "Language",
    planSep: "instrumental",
    planWhisper: m => "Whisper timing (" + m + ")",
    planEnergy: "timing by loudness",
    andMore: n => " and " + n + " more",
    willDo: "I will do: ",
    takes: " · takes ",
    langFromText: " · language worked out from the text",
    quietAt: "No singing: ",
    quietTake: "Mark this stretch as holding no words",
    quietTaken: "Already marked as holding no words",
    quietTakeAll: "mark them all",
    quietAdded: n => (n === 1 ? "One stretch is marked" : n + " stretches are marked")
      + " as holding no words. The next timing will keep the lines out of them.",
    quietNothingNew: "Every stretch here is marked already",
    aboutSec: n => "about " + n + " s",
    aboutMin: n => "about " + n + " min",
    aboutHour: (h, m) => "about " + h + " h " + m + " min",
    veryRough: " (very roughly)",
    noStableWarn: "stable-ts is not installed — the timing will be approximate, line by line.",
    pickTrack: "Choose the real instrumental",
    pickLyrics: "Choose the file with the new lyrics",
    pickFile: "Choose a file",
    mb: " MB",
    noFiles: "Nothing suitable here",
    dropUnknown: "I don\u2019t understand these files: a song (mp3, wav…) and lyrics (txt) are needed",
    taking: n => "Taking " + n + "…",
    filesOk: "Files accepted — press “Build”",
    filesHalf: "The second file is missing",
    dropFail: "Could not take the file: ",
    pickBoth: "Point to both files",
    noTextLabel: "Where there are no words",
    clipMarks: "↹ Trim by the marks",
    clipHint: "Cut the line spans back out of the marked stretches: a line next "
      + "to a hole reaches across it, and a couple of words end up lasting a "
      + "minute. Nothing is timed again.",
    clipNoMarks: "Nothing is marked yet",
    clipNothing: "No line reaches into a marked stretch",
    clipDone: n => `Trimmed: ${n} lines`,
    clipMoved: (n, m) => `Trimmed: ${n}, moved out of the marked stretches: ${m}`,
    edgeLimit: "The edge has met the outermost word — hold Alt and drag to squeeze the whole line",
    fitLine: "⤢ Fit the line",
    fitHint: "Zoom the timeline so the selected line fills it — the words come "
      + "apart and can be taken one by one.",
    markMode: "✂ No words here",
    keepMarks: "original on the marks",
    keepMarksHint: "On a marked stretch there is nothing to sing, so the "
      + "original voice is left in the backing there — a vocalise or a scream "
      + "is heard instead of a hole. Switch it off if you mean to sing it.",
    realignPart: "↻ These lines",
    realignPartHint: "Time only the selected lines again, between their timed "
      + "neighbours. The rest of the song — and everything you put right by "
      + "hand — is left as it is. On a long song it takes seconds, not minutes.",
    realignPartAsk: (a, b) => "Time lines " + a + "–" + b + " again?\n\n"
      + "The rest of the song is not touched.",
    realignPartDone: n => "Timed again: " + n + " lines",
    splitLine: "⤸ Split",
    splitHint: "Cut the selected line in two where the singing pauses longest "
      + "inside it. The words keep their times — nothing is timed again.",
    joinLine: "⤹ Join",
    joinHint: "Join the selected line with the one after it. The words keep "
      + "their times.",
    lineSplit: "The line was cut in two",
    lineJoined: "The lines were joined",
    splitTooShort: "There is nothing to cut: the line has one word",
    joinNoNext: "There is no line after this one",
    joinAcrossSection: "The next line starts a new part of the song — join would hide its heading",
    ignoreHint: "Dismiss this warning for this line — the way a spell-checker "
      + "does. It stays dismissed; the link under the list brings them all back.",
    ignored: "Dismissed. The link under the list brings them back.",
    restoreIgnored: n => `dismissed: ${n} — bring them back`,
    evenWords: "≡ Even words",
    evenHint: "Re-lay the words of the selected lines by syllables, inside each "
      + "line's own span — the edges stay put. Works on locked lines too: the "
      + "lock guards against the model, not against you.",
    evenDone: n => `Words re-laid in ${n} ${n === 1 ? "line" : "lines"}`,
    lockLine: "🔒 Lock",
    lockHint: "Leave the selected lines as they are when the timing is redone: "
      + "what you put right by hand outweighs anything the model returns for it.",
    lockedN: n => `Locked: ${n}. Re-timing will leave them alone.`,
    unlockedN: n => `Unlocked: ${n}.`,
    markHint: "Mark the stretches on the waveform: press and drag over a "
      + "vocalise or an intro, click a mark to take it off. Then “Re-time”.",
    markOn: "Drag over the waveform to mark where there are no words. Click a mark to remove it.",
    markOff: "Marking is off",
    markAdded: (a, b) => `Marked: ${a}–${b}. Press “Re-time” to use it.`,
    markGone: "The mark is gone",
    waveNoText: "no words",
    noTextPh: "0:00-0:42, 3:10-3:50 — an intro, a vocalise, a solo",
    noTextHint: "A vocalise, a wordless scream and a sung line are all voice: no "
      + "measurement tells them apart, and the timing crawls onto them. Naming a "
      + "stretch keeps words off it — it says nothing about the rest of the song, "
      + "and claims no words for it. The same can be written in the lyrics file: "
      + "[Solo 3:10-3:50].",
    // a link instead of a file, and the lyrics that go with it
    linkPh: "…or a link to a video — the sound will be taken out of it",
    fetchGo: "Take the sound",
    linkNeedUrl: "Paste a link into the field first",
    linkWorking: "Taking the sound from the link…",
    linkGot: n => "The sound is here: " + n,
    linkFail: m => "It did not download: " + m +
      " — try another link, or choose a file on the disk",
    pasteText: "Paste the text",
    pastePh: "One line of the song per line. Repeats written out as many times as they are sung.",
    useText: "Use this text",
    hideText: "Hide",
    pasteEmpty: "There is nothing in the box yet",
    textSaved: "The lyrics are in place",
    countLines: n => n + (n === 1 ? " line" : " lines"),
    lyricsSearching: "Looking for the lyrics by the name of the song…",
    lyricsFoundN: (n, src) => "Found on " + src + ": " + n +
      (n === 1 ? " text. Read it before using — " : " texts. Read before using — ") +
      "a wrong one lays wrong lines over the whole song.",
    lyricsNone: src => "Nothing was found on " + src +
      ". Choose a file, or paste the text by hand.",
    lyricsUse: "Take it",
    lyricsUseTimed: "Take it with the timing",
    lyricsWordsOnly: "words only",
    lyricsHasTimes: "comes with a timing",
    lyricsTook: "The text is in the box below — read it, correct it if need be.",
    lyricsTookTimed: "Taken with the library's own times: they are pegs — every "
      + "few lines is fixed to its place, and the words in between are laid "
      + "out by the model. If the recording is another take, look the pegs "
      + "over before building.",
    pastedIntoBox: "That is the lyrics, not a path to a file: the lines are in the "
      + "box below, whole, and saved as a text file.",
    linkMoved: "That is a link — it has gone into the field below, press “Take the sound”.",
    jobBuild: "Building the song",
    jobFail: "It did not work",
    hotkeys: "Space — play · ← → seek · [ ] shift the line by 50 ms",
    nothingToUndo: "Nothing to undo",
    undone: "Undone",
    sec: " s",
    theEnd: "End",
    tillEnd: "to the end of the recording",
    interlude: "Interlude",
    intro: "Intro",
    till: "to “",
    quote: "”",
    colorFixed: "The text blended into the background — the colour was fixed so it reads",
    voiceBtn: n => "◑ Voice " + n,
    voiceNone: "◑ Voice",
    pickLineFirst: "Select a line first",
    voice2On: "This line is sung by the second voice",
    voice1On: "This line is sung by the main voice",
    keepYes: "♪ Original: yes",
    keepSoftYes: "♪ Original: quiet",
    keepOnMsg: "The original voice stays on this line. Press again for a "
      + "quiet original — to sing along with",
    keepSoftMsg: "The original stays quiet here — a guide to sing along "
      + "with. Press again to give the line back to you",
    keepOffMsg: "You sing this line again",
    sungByOriginal: "original sings",
    sungTogether: "sing along with the original",
    saving: "saving…",
    nameHint: "The song's name — click to fix it. It stands in the corner of "
      + "the video, on its opening card and on the finished page, and it is "
      + "what the exported files are called.",
    moreExpHint: "The other ways out: an UltraStar file for the singing "
      + "games, .ass subtitles with the karaoke sweep, or the whole song "
      + "packed into one file to carry elsewhere.",
    exportUs: "UltraStar (.txt)",
    exportAss: "Subtitles (.ass)",
    jobUs: "Writing the UltraStar file",
    jobAss: "Writing the subtitles",
    packSong: "⇩ Pack",
    packHint: "Put the whole song into one file — the timing, the audio, the "
      + "cover — to carry to another computer or to keep. A rendered page or "
      + "clip is not packed: they are made again in one press.",
    packing: "Packing the song…",
    packed: "The song is packed",
    openPack: "Open a packed song",
    unpackHint: "Take a packed song — a .karaoke.zip — and put it back among "
      + "the songs, exactly as it was.",
    unpacked: "The song is here, as it was",
    expTitle: "The video file",
    expSize: "Size",
    expFps: "Frames per second",
    expQ: "Quality",
    expQBest: "better and heavier",
    expQNorm: "the usual",
    expQLight: "lighter file",
    expIntroLbl: "the opening: the name and a count of three",
    expGo: "Render",
    swMore: "wheel…",
    coverBtn: "⛰ Cover",
    coverPickHint: "Put a picture behind the lyrics — blurred and darkened — "
      + "on the finished page and in the MP4. Any image works, and so does "
      + "the clip itself: a frame is cut out of a picked video.",
    coverOffHint: "Take the cover away — back to the plain background.",
    backdropBtn: "\ud83c\udf9e Clip behind",
    backdropHint: "Put a clip behind the lyrics instead of a still. It is "
      + "blurred into a slow field of colour, so the smallest copy a link "
      + "offers is as good as the best one — and the words keep their ring "
      + "over whatever moves under them.",
    backdropOffHint: "Take the clip away — back to the still backdrop.",
    pickBackdrop: "A clip to stand behind the lyrics",
    backdropUrlPh: "a link to the clip — the song's own will do",
    backdropWait: "Taking the clip\u2026 this can take a minute",
    backdropSet: "The clip stands behind the lyrics now",
    backdropGone: "The clip is gone — the still backdrop is back",
    gridOn: "\u2669 Grid",
    gridHint: "A grid of beats over the timeline, the way a sequencer has one: "
      + "bars of four, and sixteenths when the zoom is close enough for them "
      + "to be told apart. While it is on, a dragged line snaps to the beat "
      + "instead of to the sound. Type the tempo, or tap it in; “\u2316 1” "
      + "says the playhead is on beat one. Hold Alt while dragging to place a "
      + "line exactly where your hand puts it.",
    beatOne: "\u2316 1",
    tapTempo: "\u21e5 Tap",
    sixteenths: "16ths",
    pulseOn: "pulse in the video",
    pulseHint: "Show the beat in the video: four quiet dots in the bottom "
      + "corner, one to a beat of the bar, so a singer can see where the bar "
      + "is without anything coming between them and the words. It is drawn "
      + "from the tempo you typed, so it is exactly as right as that number.",
    beatOneSet: at => "Beat one is at " + at,
    tapMore: n => "Keep tapping — " + n + " more",
    tapDone: bpm => "Tempo: " + bpm + " BPM, counted from beat one here",
    coverUrlPh: "…or paste a link to a picture",
    coverUrlGo: "take it",
    coverUrlBad: "That is not a link: it should start with http",
    coverDarkHint: "How dark the cover backdrop is. Darker reads better; "
      + "lighter shows more of the picture. The page and the video both obey.",
    coverSet: "The cover is on: it stands behind the lyrics, blurred",
    coverGone: "The cover is off — the plain background is back",
    pickCover: "A picture for the cover — or a clip to cut one from",
    showFrame: "▣ Frame",
    showOpening: "Opening",
    stillHint: "Show what the video will look like at this moment — without "
      + "rendering it. The same drawing the clip is made of.",
    stillAt: t => "the clip at " + t,
    stillOpeningAt: "the opening",
    stillFailed: "The frame could not be drawn: ",
    nameLabel: "What the song is called",
    nameNewHint: "Filled in from the link, or from the name of the file. It "
      + "stands in the corner of the video, on its opening card and on the "
      + "finished page — and it can be changed later, in the corner of the editor.",
    namePlaceTitle: "song",
    namePlaceArtist: "artist",
    nameFixed: "The song is called that from now on",
    lineDove: n => `Line ${n} — the one underneath`,
    savedOk: "saved",
    saveBad: "not saved",
    saveErr: m => "Not saved: " + m + ". Your edits are safe, I will try again.",
    unsaved: "not saved",
    sSung: "Sung",
    sEngine: "Timing",
    sVoice2: "Second voice",
    sKept: "Original sings",
    sLines: n => n + " ln.",
    sNone: "none",
    waveQuiet: "no singing",
    gripStart: "Line start",
    gripEnd: "Line end",
    wordStart: "Word start",
    wordEnd: "Word end",
    backLast: "◀ last line ",
    ago: " ago",
    addAfter: "Select the line to insert after first",
    newLineText: "new line",
    delLast: "This is the last line — nothing to delete",
    lineDeleted: "Line deleted",
    delAsk: t => "Delete the line “" + t + "” from the lyrics?",
    lineTextAria: n => "Line text " + n,
    lineTextFixed: "Line text fixed",
    noVocalWave: "No vocal track — nothing to snap to",
    allInPlace: "Everything is already in place",
    replTrack: "Changing the instrumental",
    replDone: "Instrumental replaced",
    shiftedToo: "the timing was shifted with it",
    realignNew: "Timing to the new lyrics",
    realignSame: "Recomputing the timing",
    realignDone: "Timing recomputed",
    askLyrics: "Take a different lyrics file and time the song to it?\n\nYour timing edits for this song will be replaced.",
    askRealign: "Re-read the lyrics file and time it again?\n\nIt takes the same file used for the build — with every change you made in it.\n\nYour timing edits for this song will be replaced.",
    jobHtml: "Building a standalone HTML",
    jobReady: "Done",
    jobVideo: "Rendering the video",
    videoReady: "Video ready",
    lineNo: (n, t) => "line " + n + ": " + t,
  },
  ru: {
    appTitle: "Караоке-студия", addSong: "＋ Добавить песню",
    emptyTtl: "Здесь пока пусто",
    emptyBody: 'Нажмите «Добавить песню» и укажите два файла: саму песню и ' +
      'текст.<br>Программа один раз посчитает минусовку и разметку — дальше ' +
      'правки сохраняются сами, пересобирать ничего не нужно.' +
      '<div style="margin-top:18px; color:var(--accent)">Можно просто перетащить ' +
      'оба файла в это окно.</div>',
    back: "← Назад", newSong: "Новая песня", fileSong: "Файл песни",
    fileLyrics: "Файл с текстом", choose: "Выбрать…",
    lyricsPh: "txt — одна строка песни на строку файла",
    langAlign: "Язык и разметка",
    alignExact: "Точно (Whisper), если доступен",
    alignFast: "Быстро, без нейросети",
    langTitle: "Язык текста песни", instrumental: "Минусовка",
    build: "Собрать", working: "Работаю…", toList: "← К списку", songs: "← Песни",
    savedNote: "сохранено", otherLyrics: "⇄ Другой текст",
    lyricsHint: "Взять другой файл с текстом и разметить песню под него",
    ownTrack: "♪ Своя минусовка",
    trackHint: "Подставить настоящую минусовку от исполнителя вместо разделённой",
    realign: "↻ Разметить заново",
    realignHint: "Перечитать тот же файл с текстом с диска и разметить заново — " +
      "если вы его отредактировали",
    exportHtml: "Отдельный HTML", exportMp4: "Видео MP4",
    summary: "Сводка", check: "Проверить", openFolder: "Открыть папку",
    hide: "Скрыть", timeline: "Дорожка", noLine: "строка не выбрана",
    lineStartsHere: "⌖ Начало строки — сюда", andRest: "и все следующие",
    lineText: "✎ Текст строки",
    textHint: "Исправить слова выбранной строки (или двойной щелчок по ней)",
    undo: "↶ Отменить", undoHint: "Отменить последнюю правку (Ctrl+Z)",
    addLine: "＋ строка",
    addLineHint: "Вставить строку после выбранной — если её забыли в тексте",
    delLine: "－ строка", delLineHint: "Удалить выбранную строку из текста песни",
    voiceHint: "Второй голос для выбранной строки: другой певец или другая манера " +
      "пения. Красится вторым цветом",
    keep: "♪ Оригинал",
    keepHint: "Оставить на этой строке оригинальный голос: подпевка, речь, важный "
      + "для истории кусок. Второе нажатие делает оригинал тише — подсказкой, "
      + "чтобы петь в унисон. Третье возвращает строку вам",
    colorsHint: "Чем подсвечивается пение: первый цвет — основной голос, второй — " +
      "второй голос",
    voices: "голоса", voice1: "Основной голос", voice2: "Второй голос",
    themeHint: "Оформление страницы: фон и цвет букв. Если буквы сливаются с фоном, " +
      "программа их поправит",
    bgText: "фон и буквы", bg: "Фон", textColor: "Цвет букв",
    loop: "↻ Повторять", loopHint: "Играть выбранную строку по кругу",
    snapAll: "Подогнать все к голосу",
    snapHint: "Подвинуть все строки к ближайшему началу пения",
    howtoShort: "Щёлкните строку → доиграйте до места, где её начинают петь → <b>Enter</b>.",
    howtoMore: "Синие блоки — строки, жёлтые под ними — слова этой строки. За "
      + "середину — подвинуть, за края — задать длину (Alt сжимает всю "
      + "строку). Точная подгонка строки — [ и ]. Ошиблись — Ctrl+Z. Текст "
      + "листается колесом, Home и End — к началу и концу. Зажмите и "
      + "проведите по строкам — выделятся все, по которым провели. Иначе "
      + "Shift+щелчок или Ctrl+щелчок. Голос, «оригинал», удаление и вставка "
      + "работают сразу по всем выделенным.",
    voice: "Голос", cancel: "Отмена", dropBig: "Отпустите файлы здесь",
    dropSub: "песня и текст — или каждый по отдельности",
    langUi: "Язык надписей",
    langMissing: code => `Для «${code}» перевода пока нет`,
    pasteHint: "Вставить скопированный ритм в выбранную строку (Ctrl+V). " +
      "С галочкой «и все следующие» — во все последующие строки с тем же текстом.",
    linesPicked: n => `выделено строк: ${n}`,
    voiceManyOn: (v, n) => `Голос ${v} у ${n} строк`,
    keepManyMsg: (to, n) => !to.keep ? `${n} строк снова поёте вы`
      : to.keepSoft ? `${n} строк: оригинал потише — пойте вместе с ним`
                    : `Оригинал оставлен на ${n} строках`,
    delAskMany: n => `Удалить ${n} строк из текста песни?`,
    linesDeleted: n => `Удалено строк: ${n}`,
    pasteLine: "⧉ Вставить строку",
    pasteLineHint: "Вставить скопированные строки ниже выбранной, сохранив " +
      "расстояния между ними (Ctrl+Shift+V). Ничего не затирается — если нужна " +
      "только раскладка слов, есть «Вставить ритм».",
    lineReplaced: "Строка заменена скопированной",
    linePasted: "Скопированная строка вставлена ниже",
    linesReplaced: n => `Заменено строк: ${n}`,
    copiedLine: t => `Скопировано: «${t}»`,
    copiedLines: n => `Скопировано строк: ${n}`,
    linesPasted: n => `Вставлено строк ниже: ${n}`,
    copyRhythm: "⧉ Копировать", pasteRhythm: n => `⧉ Вставить ритм${n > 1 ? " ×" + n : ""}`,
    rhythmHint: "Скопировать выбранную строку — слова, ритм, голос, пометки — и " +
      "вставить в другую либо её ритм, либо строку целиком. " +
      "такую же (Ctrl+C / Ctrl+V). С галочкой «и все следующие» вставится во все " +
      "последующие строки с тем же текстом. Ctrl+D — дублировать строку.",
    rhythmCopied: n => `Ритм скопирован: ${n} слов`,
    rhythmPasted: "Строка получила тот же ритм",
    rhythmPastedN: n => `Ритм применён к строкам: ${n}`,
    rhythmNone: "Ещё нечего вставлять — нажмите «Ритм» на понравившейся строке",
    rhythmMismatch: (a, b) => `В строке ${b} слов, а в скопированной ${a} — ` +
      "ритм не подойдёт",
    lineCopied: "Строка продублирована ниже",
    langSwitched: "Язык надписей: Русский",
    offsetDiff: v => `начало отличалось на ${v} с`,
    lengthDiff: v => `длина отличается на ${v} с — проверьте конец`,
    realignStats: (was, now) => `Готово: строк было ${was}, стало ${now}`,
    withModel: m => `\n\nРазметка считается моделью «${m}» — той же, что и при сборке.`,
    serverDown: "Сервер не отвечает",
    model_tiny: "tiny — 75 МБ", model_base: "base — 140 МБ",
    model_small: "small — 480 МБ", model_medium: "medium — 1,5 ГБ",
    model_turbo: "large-v3-turbo — 1,6 ГБ, почти large на скорости medium",
    model_large_v3: "large-v3 — 3 ГБ",
    fineSep: "отделять тщательно",
    coverBg: "фон — обложка клипа",
    coverHint: "Подложить обложку клипа под текст — сильно размытую и "
      + "затемнённую, чтобы слова читались, — на готовой странице и в MP4. "
      + "Появляется, когда песня пришла по ссылке.",
    fineSepHint: "Четыре прохода по песне вместо одного (htdemucs_ft): вокал "
      + "выходит чище, а разметка считается именно по нему. Примерно вчетверо "
      + "дольше, и при первом запуске качается ещё 300 МБ.",
    askRemove: t => `Убрать «${t}» из студии?\n\nИсходная песня и текст останутся на месте.`,
    lookingAt: "Смотрю, что за песня…",
    badFiles: "Не вышло разобрать файлы: ",
    allGood: "Ничего подозрительного.<br>Строки стоят там, где поётся.",
    wordHint: w => `«${w}»: за середину — подвинуть, за края — растянуть`,
    wordAt: (w, t) => `слово «${w}»: ${t}`,
    wordSpan: (w, a, b, d) => `слово «${w}»: ${a} … ${b} (${d} с)`,
    lineEndAt: (n, t) => `строка ${n}: конец ${t}`,
    lineAt: (n, t) => `строка ${n}: ${t}`,
    movedN: n => `Подвинул строк: ${n}`,
    lineSetRest: n => `Строка ${n} и все следующие сдвинуты`,
    lineSet: n => `Строка ${n} встала сюда`,
    needRam: (need, free) => ` Ей нужно около ${need} ГБ памяти, а свободно ${free} ГБ`,
    langManual: name => ` Язык задан вручную: ${name}.`,
    badReply: "плохой ответ сервера",
    noFfmpeg: "нет ffmpeg — запустите Install.bat",
    noStable: "без stable-ts разметка приблизительная",
    noDemucs: "без demucs не будет минусовки",
    twoTracks: "минус + голос",
    oneTrack: "одна дорожка",
    removeSong: "Убрать песню",
    linesN: n => n + " строк",
    removed: "Убрано",
    modelHave: " · уже скачана",
    modelGet: " · скачается при сборке",
    modelHeavy: " · тяжёлая для этой машины",
    noteReady: "Модель на диске — разметка начнётся сразу.",
    noteDownload: "Модели ещё нет: перед разметкой она скачается, это может занять несколько минут. Прогресс будет видно в логе сборки.",
    noteSlow: " — считать будет очень долго. Надёжнее взять модель поменьше или закрыть лишние программы.",
    noteLangAuto: " Язык определится по тексту — он будет назван в логе сборки.",
    detectByText: "определить по тексту",
    rLength: "Длина",
    rQuiet: "Без пения",
    rQuietN: (n, sec) => n + " мест · " + sec + " с",
    rQuietNone: "нет длинных",
    rLines: "Строк",
    rWords: "Слов",
    rRepeats: "Повторов",
    rLang: "Язык",
    planSep: "минусовка",
    planWhisper: m => "разметка Whisper (" + m + ")",
    planEnergy: "разметка по энергии",
    andMore: n => " и ещё " + n,
    willDo: "Сделаю: ",
    takes: " · займёт ",
    langFromText: " · язык определён по тексту",
    quietAt: "Без пения: ",
    quietTake: "Отметить кусок как «тут нет текста»",
    quietTaken: "Уже отмечено как «тут нет текста»",
    quietTakeAll: "отметить все",
    quietAdded: n => "Отмечено кусков: " + n
      + ". Следующая разметка не будет класть в них строки.",
    quietNothingNew: "Здесь и так всё отмечено",
    aboutSec: n => "около " + n + " с",
    aboutMin: n => "около " + n + " мин",
    aboutHour: (h, m) => "около " + h + " ч " + m + " мин",
    veryRough: " (очень грубо)",
    noStableWarn: "stable-ts не установлен — разметка будет приблизительной, по строкам.",
    pickTrack: "Выберите настоящую минусовку",
    pickLyrics: "Выберите файл с новым текстом",
    pickFile: "Выберите файл",
    mb: " МБ",
    noFiles: "Подходящих файлов здесь нет",
    dropUnknown: "Не понял файлы: нужна песня (mp3, wav…) и текст (txt)",
    taking: n => "Принимаю " + n + "…",
    filesOk: "Файлы приняты — нажмите «Собрать»",
    filesHalf: "Не хватает второго файла",
    dropFail: "Не получилось принять файл: ",
    pickBoth: "Укажите оба файла",
    noTextLabel: "Где текста нет",
    clipMarks: "↹ Обрезать по отметкам",
    clipHint: "Обрезать длины строк по отмеченным пустотам: строка рядом с ямой "
      + "тянется через неё, и пара слов оказывается длиной в минуту. Заново "
      + "ничего не размечается.",
    clipNoMarks: "Пока ничего не отмечено",
    clipNothing: "Ни одна строка не залезает в отмеченные пустоты",
    clipDone: n => `Подрезано строк: ${n}`,
    clipMoved: (n, m) => `Подрезано: ${n}, вынесено из отмеченных пустот: ${m}`,
    edgeLimit: "Край упёрся в крайнее слово — с зажатым Alt тянется вся строка целиком",
    fitLine: "⤢ По строке",
    fitHint: "Приблизить линейку так, чтобы выбранная строка заняла её целиком — "
      + "слова разойдутся, и их можно брать поодиночке.",
    markMode: "✂ Здесь нет текста",
    keepMarks: "оригинал на отметках",
    keepMarksHint: "На отмеченном куске петь нечего, поэтому там в минусовке "
      + "остаётся оригинальный голос — вокализ или крик звучит, а не проваливается "
      + "в тишину. Снимите галку, если хотите спеть это сами.",
    realignPart: "↻ Только эти",
    realignPartHint: "Разметить заново только выбранные строки, между их "
      + "размеченными соседями. Остальная песня — и всё, что вы выправили "
      + "руками, — остаётся как есть. На длинной песне это секунды, а не минуты.",
    realignPartAsk: (a, b) => "Разметить заново строки " + a + "–" + b + "?\n\n"
      + "Остальная песня не тронется.",
    realignPartDone: n => "Размечено заново строк: " + n,
    splitLine: "⤸ Разрезать",
    splitHint: "Разрезать выбранную строку надвое там, где внутри неё дольше "
      + "всего молчат. Времена слов сохраняются — заново ничего не размечается.",
    joinLine: "⤹ Склеить",
    joinHint: "Склеить выбранную строку со следующей. Времена слов сохраняются.",
    lineSplit: "Строка разрезана надвое",
    lineJoined: "Строки склеены",
    splitTooShort: "Резать нечего: в строке одно слово",
    joinNoNext: "После этой строки нет следующей",
    joinAcrossSection: "Следующая строка начинает новую часть песни — склейка спрячет её заголовок",
    ignoreHint: "Скрыть это предупреждение для этой строки — как «пропустить» в "
      + "проверке правописания. Останется скрытым; ссылка под списком вернёт все.",
    ignored: "Скрыто. Ссылка под списком вернёт обратно.",
    restoreIgnored: n => `скрыто: ${n} — вернуть`,
    evenWords: "≡ Слова ровно",
    evenHint: "Переложить слова выбранных строк по слогам внутри их собственных "
      + "границ — края не двигаются. Работает и на запертых: замок защищает от "
      + "модели, а не от вас.",
    evenDone: n => `Слова переложены: строк ${n}`,
    lockLine: "🔒 Замок",
    lockHint: "Оставить выбранные строки как есть при переразметке: выправленное "
      + "руками важнее всего, что вернёт про них модель.",
    lockedN: n => `Заперто строк: ${n}. Переразметка их не тронет.`,
    unlockedN: n => `Отперто строк: ${n}.`,
    markHint: "Отметить куски прямо на волне: нажать и провести по вокализу или "
      + "вступлению, щелчок по отметке — снять её. Потом «Разметить заново».",
    markOn: "Проведите мышью по волне там, где текста нет. Щелчок по отметке — снять.",
    markOff: "Разметка кусков выключена",
    markAdded: (a, b) => `Отмечено: ${a}–${b}. Нажмите «Разметить заново», чтобы учесть.`,
    markGone: "Отметка снята",
    waveNoText: "нет текста",
    noTextPh: "0:00-0:42, 3:10-3:50 — вступление, вокализ, соло",
    noTextHint: "Вокализ, крик без слов и спетая строка — всё это голос: ничем их "
      + "не отличить, и разметка на них наползает. Названный кусок слова обойдут — "
      + "про остальную песню это не говорит ничего и текста ей не приписывает. "
      + "То же можно написать прямо в файле с текстом: [Соло 3:10-3:50].",
    // ссылка вместо файла и текст к ней
    linkPh: "…или ссылка на видео — звук достанется из неё",
    fetchGo: "Достать звук",
    linkNeedUrl: "Сначала вставьте ссылку в поле",
    linkWorking: "Достаю звук по ссылке…",
    linkGot: n => "Звук на месте: " + n,
    linkFail: m => "Не скачалось: " + m +
      " — попробуйте другую ссылку или выберите файл на диске",
    pasteText: "Вставить текст",
    pastePh: "Строка песни — строка файла. Повторы выписаны столько раз, сколько поются.",
    useText: "Взять этот текст",
    hideText: "Свернуть",
    pasteEmpty: "В поле пока пусто",
    textSaved: "Текст на месте",
    countLines: n => n + " " + (n % 10 === 1 && n % 100 !== 11 ? "строка"
      : ([2,3,4].includes(n % 10) && ![12,13,14].includes(n % 100)) ? "строки" : "строк"),
    lyricsSearching: "Ищу текст по названию песни…",
    lyricsFoundN: (n, src) => "Нашлось на " + src + ": " + n +
      (n % 10 === 1 && n % 100 !== 11 ? " текст" :
       ([2,3,4].includes(n % 10) && ![12,13,14].includes(n % 100)) ? " текста" : " текстов") +
      ". Прочитайте перед тем, как брать: чужой текст ляжет неправильными строками на всю песню.",
    lyricsNone: src => "На " + src +
      " ничего не нашлось. Выберите файл или вставьте текст руками.",
    lyricsUse: "Взять",
    lyricsUseTimed: "Взять с разметкой",
    lyricsWordsOnly: "только слова",
    lyricsHasTimes: "есть готовая разметка",
    lyricsTook: "Текст в поле ниже — прочитайте, поправьте, если надо.",
    lyricsTookTimed: "Взято вместе с временами библиотеки: это опоры — каждые "
      + "несколько строк привязаны к своему месту, а слова между ними разложит "
      + "модель. Если запись другая версия, просмотрите опоры перед сборкой.",
    pastedIntoBox: "Это текст песни, а не путь к файлу: строки целиком лежат в поле "
      + "ниже и сохранены текстовым файлом.",
    linkMoved: "Это ссылка — она перенесена в поле ниже, нажмите «Достать звук».",
    jobBuild: "Собираю песню",
    jobFail: "Не получилось",
    hotkeys: "Пробел — пуск · ← → перемотка · [ ] сдвиг строки на 50 мс",
    nothingToUndo: "Отменять нечего",
    undone: "Отменено",
    sec: " с",
    theEnd: "Конец",
    tillEnd: "до конца записи",
    interlude: "Проигрыш",
    intro: "Вступление",
    till: "до «",
    quote: "»",
    colorFixed: "Буквы сливались с фоном — цвет подправлен, чтобы читалось",
    voiceBtn: n => "◑ Голос " + n,
    voiceNone: "◑ Голос",
    pickLineFirst: "Сначала выберите строку",
    voice2On: "Строка поётся вторым голосом",
    voice1On: "Строка поётся основным голосом",
    keepYes: "♪ Оригинал: да",
    keepSoftYes: "♪ Оригинал: тихо",
    keepOnMsg: "На этой строке останется оригинальный голос. Нажмите ещё "
      + "раз — оригинал потише, чтобы петь в унисон",
    keepSoftMsg: "Оригинал здесь звучит потише — как подсказка, петь вместе "
      + "с ним. Ещё нажатие вернёт строку вам",
    keepOffMsg: "Строку снова поёт человек",
    sungByOriginal: "поёт оригинал",
    sungTogether: "в унисон с оригиналом",
    saving: "сохраняю…",
    nameHint: "Название песни — нажмите, чтобы поправить. Оно стоит в углу "
      + "ролика, на его заставке и на готовой странице, и по нему называются "
      + "выгруженные файлы.",
    moreExpHint: "Другие выходы: файл UltraStar для игр, где поют, "
      + ".ass-субтитры с караоке-заливкой — или вся песня одним файлом, "
      + "чтобы унести с собой.",
    exportUs: "UltraStar (.txt)",
    exportAss: "Субтитры (.ass)",
    jobUs: "Пишу файл UltraStar",
    jobAss: "Пишу субтитры",
    packSong: "⇩ Упаковать",
    packHint: "Положить песню целиком в один файл — разметку, звук, обложку, — "
      + "чтобы перенести на другой компьютер или сохранить. Готовая страница "
      + "и ролик не пакуются: они делаются заново одним нажатием.",
    packing: "Упаковываю песню…",
    packed: "Песня упакована",
    openPack: "Открыть пакет",
    unpackHint: "Взять упакованную песню — .karaoke.zip — и вернуть её к "
      + "остальным ровно такой, какой она была.",
    unpacked: "Песня на месте, как была",
    expTitle: "Файл видео",
    expSize: "Размер",
    expFps: "Кадров в секунду",
    expQ: "Качество",
    expQBest: "лучше и тяжелее",
    expQNorm: "обычное",
    expQLight: "полегче файл",
    expIntroLbl: "заставка: название и счёт до трёх",
    expGo: "Рендерить",
    swMore: "круг…",
    coverBtn: "⛰ Обложка",
    coverPickHint: "Подложить картинку под текст — размытую и затемнённую — "
      + "на готовой странице и в MP4. Подойдёт любая картинка или сам клип: "
      + "из выбранного видео вырежется кадр.",
    coverOffHint: "Убрать обложку — вернуть обычный фон.",
    backdropBtn: "\ud83c\udf9e Клип сзади",
    backdropHint: "Поставить за текстом клип вместо неподвижной картинки. Он "
      + "размывается в медленное поле цвета, поэтому самая мелкая копия по "
      + "ссылке ничем не хуже лучшей, а у слов остаётся обводка поверх всего, "
      + "что под ними движется.",
    backdropOffHint: "Убрать клип — вернуть неподвижный фон.",
    pickBackdrop: "Клип, который встанет за текстом",
    backdropUrlPh: "ссылка на клип — подойдёт та же, что у песни",
    backdropWait: "Достаю клип\u2026 это может занять минуту",
    backdropSet: "Клип встал за текстом",
    backdropGone: "Клип убран — вернулся неподвижный фон",
    gridOn: "\u2669 Сетка",
    gridHint: "Сетка долей поверх дорожки, как в секвенсоре: такты по четыре, "
      + "а шестнадцатые — когда масштаб достаточно крупный, чтобы их можно "
      + "было различить. Пока она включена, строка при перетаскивании липнет "
      + "к доле, а не к звуку. Темп наберите или отстучите; «\u2316 1» "
      + "говорит, что курсор стоит на первой доле такта. Alt при "
      + "перетаскивании ставит строку ровно туда, куда ведёт рука.",
    beatOne: "\u2316 1",
    tapTempo: "\u21e5 Отстучать",
    sixteenths: "16-е",
    pulseOn: "пульс в ролике",
    pulseHint: "Показывать долю в ролике: четыре тихие точки в нижнем углу, "
      + "по одной на долю такта, чтобы певец видел, где такт, и между ним и "
      + "словами при этом ничего не стояло. Рисуется по набранному вами "
      + "темпу — значит, ровно настолько же верен, насколько верно это число.",
    beatOneSet: at => "Первая доля на " + at,
    tapMore: n => "Стучите дальше — ещё " + n,
    tapDone: bpm => "Темп: " + bpm + " BPM, отсчёт от первой доли здесь",
    coverUrlPh: "…или вставьте ссылку на картинку",
    coverUrlGo: "взять",
    coverUrlBad: "Это не ссылка: она начинается с http",
    coverDarkHint: "Насколько затемнён фон-обложка. Темнее — читается лучше, "
      + "светлее — виднее картинка. Слушаются и страница, и видео.",
    coverSet: "Обложка стоит: она за текстом, размытая",
    coverGone: "Обложка убрана — обычный фон вернулся",
    pickCover: "Картинка для обложки — или клип, из которого её вырезать",
    showFrame: "▣ Кадр",
    showOpening: "Заставка",
    stillHint: "Показать, как будет выглядеть видео в этот момент, — не "
      + "рендеря его. Рисуется тем же кодом, что и сам ролик.",
    stillAt: t => "ролик на " + t,
    stillOpeningAt: "заставка",
    stillFailed: "Кадр не нарисовался: ",
    nameLabel: "Как называется песня",
    nameNewHint: "Заполняется из ссылки или из имени файла. Это имя стоит в "
      + "углу ролика, на его заставке и на готовой странице — и его можно "
      + "поменять потом, в углу редактора.",
    namePlaceTitle: "песня",
    namePlaceArtist: "артист",
    nameFixed: "Теперь песня называется так",
    lineDove: n => `Строка ${n} — та, что под верхней`,
    savedOk: "сохранено",
    saveBad: "не сохранилось",
    saveErr: m => "Не сохранилось: " + m + ". Правки в окне целы, попробую снова.",
    unsaved: "не сохранено",
    sSung: "Поётся",
    sEngine: "Разметка",
    sVoice2: "Второй голос",
    sKept: "Поёт оригинал",
    sLines: n => n + " стр.",
    sNone: "нет",
    waveQuiet: "без пения",
    gripStart: "Начало строки",
    gripEnd: "Конец строки",
    wordStart: "Начало слова",
    wordEnd: "Конец слова",
    backLast: "◀ последняя строка ",
    ago: " назад",
    addAfter: "Сначала выберите строку, после которой вставить",
    newLineText: "новая строка",
    delLast: "Это последняя строка — удалять нечего",
    lineDeleted: "Строка удалена",
    delAsk: t => "Удалить строку «" + t + "» из текста песни?",
    lineTextAria: n => "Текст строки " + n,
    lineTextFixed: "Текст строки исправлен",
    noVocalWave: "Волны вокала нет — прилипать не к чему",
    allInPlace: "Всё и так на местах",
    replTrack: "Меняю минусовку",
    replDone: "Минусовка заменена",
    shiftedToo: "разметку сдвинул следом",
    realignNew: "Размечаю под новый текст",
    realignSame: "Пересчитываю разметку",
    realignDone: "Разметка пересчитана",
    askLyrics: "Взять другой файл с текстом и разметить песню под него?\n\nВаши правки времени у этой песни будут заменены.",
    askRealign: "Перечитать файл с текстом и разметить заново?\n\nБерётся тот же файл, что и при сборке — со всеми правками, которые вы в нём сделали.\n\nВаши правки времени у этой песни будут заменены.",
    jobHtml: "Собираю отдельный HTML",
    jobReady: "Готово",
    jobVideo: "Рисую видео",
    videoReady: "Видео готово",
    lineNo: (n, t) => "строка " + n + ": " + t,
  },
};
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
  if (pickTarget === "cover") coverUrlRow(body);
  if (pickTarget === "backdrop") backdropUrlRow(body);
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

/* ================= the project and its timing ================= */
let pid=null, data=null, lines=[], envelope=[], envHop=0.02, onsets=[];
let sel=-1, curLine=-1, curDuo=-1, loopSel=false, saveT=0;

async function openProject(id){
  pid = id;
  data = await api("/api/project/"+encodeURIComponent(id));
  lines = data.lines;
  envelope = decodeEnv(data.envelope);
  quiet = data.quiet || [];
  envHop = (data.envelope||{}).hop || 0.02;
  onsets = findOnsets();
  figureDoubt();
  sel = -1; curLine = -2; waOffset = 0; playing = false;
  songName = data.title || "";
  songArtist = data.artist || "";
  showName();
  fillNoText(data);
  $("hint").textContent = T.hotkeys;
  showMade("");
  refreshCover();
  refreshBackdrop();
  const gsav = data.grid || {};
  grid = {on: !!gsav.on, bpm: clamp(+gsav.bpm || 120, 20, 300),
          beat0: +gsav.beat0 || 0, sub: gsav.sub === 4 ? 4 : 1,
          pulse: !!gsav.pulse};
  showGrid();
  colors = (Array.isArray(data.colors) && data.colors.length === 2)
    ? data.colors.slice() : ["#4de1ff", "#ff8ad1"];
  theme = (Array.isArray(data.theme) && data.theme.length === 2)
    ? data.theme.slice() : ["#0a0b14", "#e8ebf5"];
  applyColors();
  screen("scrEdit");
  buildLines();
  makeBlocks();
  centerLine(0);                    // text in sight at once, not at the bottom edge
  showProblems(data.problems);
  await loadAudio(id, data.tracks);
  lastData = data;
  $("zoomNote").textContent = zoomText();
  drawSummary(data);            // the length is known only after the audio loads
  $("tDur").textContent = fmt(dur);
  drawWave();
  requestAnimationFrame(tick);
}
function decodeEnv(env){
  if (!env || !env.data) return [];
  const bin = atob(env.data), out = new Float32Array(bin.length);
  for (let i=0;i<bin.length;i++) out[i] = bin.charCodeAt(i)/255;
  return out;
}
function findOnsets(){
  if (!envelope.length) return [];
  const sorted = Array.from(envelope).sort((a,b)=>a-b);
  const floor = sorted[Math.floor(sorted.length*0.15)];
  const peak  = sorted[Math.floor(sorted.length*0.98)];
  const rng = Math.max(peak-floor, 1e-6);
  const on = floor + 0.20*rng, off = floor + 0.11*rng;
  const res=[]; let active=false, start=0;
  for (let i=0;i<envelope.length;i++){
    if (!active && envelope[i] >= on){ active=true; start=i;
      while (start>0 && i-start < 10 && envelope[start-1] > off*0.7) start--;
    } else if (active && envelope[i] < off){
      active=false;
      if ((i-start)*envHop >= 0.18) res.push(start*envHop);
    }
  }
  return res;
}

/* ---------- the lyrics ---------- */
let quiet = [];                 // stretches where nobody sings for a while
const lineEls=[];
function buildLines(){
  const box=$("scroll"); box.innerHTML=""; lineEls.length=0;
  lines.forEach((ln,i) => {
    const el=document.createElement("div");
    el.className = "ln" + (ln.backing ? " back" : "") + (ln.voice === 2 ? " v2" : "")
      + (ln.keep ? " keep" : "");
    ln.words.forEach((w,j) => {
      // a syllable reads on to the word before it — the mark that split it
      // is a timing device, never a letter
      const after = ln.words[j+1];
      const txt = w.w + (after && !after.g ? " " : "");
      const sp=document.createElement("span"); sp.className="w";
      const hl=document.createElement("span"); hl.className="hl"; hl.textContent=txt;
      sp.appendChild(hl); sp.appendChild(document.createTextNode(txt));
      el.appendChild(sp);
    });
    el.addEventListener("click", e => {
      if (skipClick){ skipClick = false; return; }   // that was the end of a drag
      selectLine(i, !e.shiftKey && !e.ctrlKey && !e.metaKey,
        e.shiftKey ? "range" : (e.ctrlKey || e.metaKey) ? "add" : "");
    });
    el.addEventListener("dblclick", () => editText(i));
    box.appendChild(el);
    // the “original sings” tag is not a word, there is nothing to highlight
    lineEls.push({el, hls:[...el.children].filter(e=>e.className==="w")
                                          .map(s=>s.firstChild)});
    if (ln.keep) markKeep(i);
  });
}
/* Several lines can be selected: moving a chunk to the second voice or deleting
   a stray repeat as a batch is ordinary work, and doing it one by one is slow.
   When `marked` is empty we work with the single line `sel`. */
const marked = new Set();
// The selection anchor: Shift extends the range from it. Without one,
// Shift+arrow restarted the selection at the current line and it never grew.
let anchor = -1;
function targets(){
  return marked.size ? [...marked].sort((a, b) => a - b) : (sel >= 0 ? [sel] : []);
}
function paintMarks(){
  lineEls.forEach((L, k) => L.el.classList.toggle("mark", marked.has(k)));
  blockEls.forEach((e, k) => e.classList.toggle("mark", marked.has(k)));
}
/* Drag selection: press on a line, drag across its neighbours, they get picked.
   That is how lists work everywhere, and it is exactly what was missing: Shift
   and Ctrl have to be known, while press-and-drag does not. */
let picking = null, skipClick = false;
function lineIndexFromEvent(e){
  const el = e.target && e.target.closest ? e.target.closest(".ln") : null;
  if (!el) return -1;
  return lineEls.findIndex(L => L.el === el);
}
function pickRange(a, b){
  marked.clear();
  for (let k = Math.min(a, b); k <= Math.max(a, b); k++) marked.add(k);
  sel = b;
  lineEls.forEach((L, k) => L.el.classList.toggle("sel", k === sel));
  paintMarks();
  $("selNote").textContent = marked.size > 1
    ? T.linesPicked(marked.size) : T.lineNo(sel + 1, fmtMs(lines[sel].start));
  $("selNote").classList.toggle("many", marked.size > 1);
  layoutBlocks();
  refreshVoice(); refreshKeep(); refreshRhythm();
}
$("scroll").addEventListener("pointerdown", e => {
  // The “click after a drag” flag lives exactly until the next press: otherwise,
  // if no click followed the drag, it would swallow the next real one.
  skipClick = false;
  if (editingText >= 0 || e.button !== 0) return;
  const i = lineIndexFromEvent(e);
  if (i < 0) return;
  // Pointer capture is not taken immediately: while this is still an ordinary
  // click it must not retarget the click from the line to the stage, which
  // would break selecting a single line.
  picking = {from: i, last: i, moved: false, id: e.pointerId};
});
$("stage").addEventListener("pointermove", e => {
  if (!picking) return;
  // While dragging, look up the line under the cursor: the event target stays
  // the same once the stage has captured the pointer.
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const ln = el && el.closest ? el.closest(".ln") : null;
  const i = ln ? lineEls.findIndex(L => L.el === ln) : -1;
  if (i < 0 || i === picking.last) return;
  picking.last = i;
  if (!picking.moved){
    picking.moved = true;
    try { $("stage").setPointerCapture(picking.id); } catch (err) {}
  }
  document.body.classList.add("picking");
  anchor = picking.from;
  pickRange(picking.from, i);
});
window.addEventListener("pointerup", e => {
  if (!picking) return;
  const was = picking;
  picking = null;
  document.body.classList.remove("picking");
  if (was.moved){
    try { $("stage").releasePointerCapture(was.id); } catch (err) {}
    skipClick = true;                   // a click after a drag resets nothing
    return;
  }
  // The stage keeps scrolling under the cursor while the song plays: by the
  // time the browser assembles a click, the pressed line is no longer the one
  // under the pointer, and the click landed on a neighbour — or nowhere. The
  // press is what the person meant, so the press is what selects.
  skipClick = true;
  selectLine(was.from, !e.shiftKey && !e.ctrlKey && !e.metaKey,
    e.shiftKey ? "range" : (e.ctrlKey || e.metaKey) ? "add" : "");
});

function selectLine(i, jump, mode){
  const prev = sel, was = sel;
  sel = clamp(i, 0, lines.length-1);
  if (mode === "add"){                       // Ctrl — add or remove one
    if (!marked.size && was >= 0) marked.add(was);
    if (marked.has(sel) && marked.size > 1) marked.delete(sel); else marked.add(sel);
    anchor = sel;
  } else if (mode === "range"){              // Shift — the whole run from the anchor
    const from = anchor >= 0 ? anchor : (was < 0 ? sel : was);
    marked.clear();
    for (let k = Math.min(from, sel); k <= Math.max(from, sel); k++) marked.add(k);
    anchor = from;
  } else {
    marked.clear();
    anchor = sel;
  }
  lineEls.forEach((L,k)=>L.el.classList.toggle("sel", k===sel));
  paintMarks();
  $("selNote").textContent = marked.size > 1
    ? T.linesPicked(marked.size)
    : T.lineNo(sel+1, fmtMs(lines[sel].start));
  $("selNote").classList.toggle("many", marked.size > 1);
  if (jump) seek(Math.max(0, lines[sel].start - 0.7));
  if (prev >= 0) layoutBlock(prev);
  layoutBlock(sel);
  makeWords();                       // the word row always belongs to the selected line
  refreshVoice(); refreshKeep(); refreshRhythm();
}
// Scrolling the lyrics by hand. The only way used to be ↑ ↓ one line at a
// time — you never get back to the start of a long song like that.
let freeScroll = 0, scrollY = 0;
function stageScroll(dy){
  const box = $("scroll"), stage = $("stage");
  const max = Math.max(0, box.scrollHeight - stage.clientHeight);
  scrollY = clamp(scrollY + dy, 0, max);
  box.style.transition = "none";
  box.style.transform = `translateY(${-scrollY}px)`;
  freeScroll = Date.now();            // let go of auto-centring for a while
}
$("stage").addEventListener("wheel", e => {
  e.preventDefault();
  stageScroll(e.deltaY * (e.deltaMode === 1 ? 24 : 1));
}, {passive:false});

function centerLine(i){
  // While a person scrolls, do not yank the text out from under them.
  if (Date.now() - freeScroll < 2500) return;
  $("scroll").style.transition = "";
  // Before a line is chosen, show the first one: the text padding is set in
  // fractions of the WINDOW while the stage is shorter, so without centring the
  // text ends up at the bottom edge or past it.
  if (i < 0) i = 0;
  if (!lineEls[i]) return;
  const el=lineEls[i].el;
  scrollY = el.offsetTop + el.offsetHeight/2 - $("stage").clientHeight/2;
  $("scroll").style.transform = `translateY(${-scrollY}px)`;
}

/* ---------- saving ---------- */
/* ---------- undo ----------
   Edits go to disk by themselves, so there is no “close without saving” here,
   and undo is the only protection from a wrong move. We keep snapshots of the
   lines: there are few of them, and this way no inverse action has to be
   written for every kind of edit. */
const past = [];
let lastSnap = {what: "", at: 0};
function snap(what){
  // A run of identical small steps (holding [ or ]) is one undo step, or it
  // would take fifty presses to get back to where things were.
  const now = Date.now();
  if (what && what === lastSnap.what && now - lastSnap.at < 900){
    lastSnap.at = now;
    return;
  }
  lastSnap = {what: what || "", at: now};
  past.push(JSON.stringify(lines));
  if (past.length > 120) past.shift();
  refreshUndo();
}
function undo(){
  if (!past.length){ refreshUndo(); return toast(T.nothingToUndo); }
  lines = JSON.parse(past.pop());
  lastSnap = {what: "", at: 0};
  buildLines(); makeBlocks();
  selectLine(clamp(sel, 0, lines.length - 1), false);
  curLine = -2;
  refreshUndo(); touched();
  toast(T.undone);
}
function refreshUndo(){ $("btnUndo").disabled = past.length === 0; }

/* ---------- countdown to the singing ---------- */
// While nobody sings the stage is empty and it is impossible to tell whether
// the song is running. A moving countdown means everything else moves too.
function idxAt(t){
  let idx = -1;
  for (let i=0;i<lines.length;i++){ if (lines[i].start <= t) idx = i; else break; }
  return (idx >= 0 && t < lines[idx].end) ? idx : -1;
}
let waitFrom = 0;
function showWait(t, cur){
  const box = $("wait");
  // A short gap between lines needs no countdown: it is obvious anyway, and a
  // label flashing for half a second only gets in the way.
  // Ten seconds, not five: a gap shorter than that is a breath between lines,
  // and counting it down draws the eye away from the singing for nothing.
  const MIN_GAP = 10.0;
  if (cur >= 0){ box.classList.add("hide"); return; }
  // Seconds, not milliseconds: this is “how long to wait”, not timing.
  const left = s => s >= 60 ? fmt(s) : Math.ceil(s) + T.sec;
  // the wait is until the singer's own next line — a backing na-na-na in the
  // middle of the gap is not what the countdown is for
  const next = lines.find(l => l.start > t && !l.backing);
  if (!next){                              // the song is over
    if (dur - t < 3){ box.classList.add("hide"); return; }
    box.classList.remove("hide");
    $("waitTtl").textContent = T.theEnd;
    $("waitNum").textContent = left(Math.max(0, dur - t));
    $("waitTxt").textContent = T.tillEnd;
    $("waitFill").style.width = dur ? (100 * t / dur).toFixed(1) + "%" : "0";
    return;
  }
  const prev = lines.filter(l => l.end <= t).pop();
  const from = prev ? prev.end : 0;
  const span = Math.max(next.start - from, 0.001);
  if (span < MIN_GAP){ box.classList.add("hide"); return; }
  box.classList.remove("hide");
  $("waitTtl").textContent = prev ? T.interlude : T.intro;
  $("waitNum").textContent = left(next.start - t);
  $("waitTxt").textContent = T.till + shortLine(next.text, 32) + T.quote;
  $("waitFill").style.width = (100 * clamp((t - from) / span, 0, 1)).toFixed(1) + "%";
  waitFrom = from;
}

/* ---------- two voices and their colours ---------- */
// Vocals sometimes overlap: a lead and a backing part, a clean voice and a
// scream. A line can be given the second voice — it is painted in the second
// colour both here and on the finished page.
let colors = ["#4de1ff", "#ff8ad1"];
let theme = ["#0a0b14", "#e8ebf5"];      // background and text colour

/* Readability. A person picks the colours, but letters that blend into the
   background are not a style, they are a broken page. The hue is kept, the
   lightness is moved. */
function rgbOf(c){
  c = String(c || "").trim().replace("#", "");
  if (c.length === 3) c = c.split("").map(x => x + x).join("");
  if (!/^[0-9a-f]{6}$/i.test(c)) return null;
  return [0,2,4].map(i => parseInt(c.slice(i,i+2), 16));
}
function lum(rgb){
  const f = v => (v/=255) <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
  return 0.2126*f(rgb[0]) + 0.7152*f(rgb[1]) + 0.0722*f(rgb[2]);
}
function contrast(a, b){
  const ra = rgbOf(a), rb = rgbOf(b);
  if (!ra || !rb) return 21;
  const la = lum(ra), lb = lum(rb);
  return (Math.max(la,lb)+0.05) / (Math.min(la,lb)+0.05);
}
function hex(rgb){ return "#" + rgb.map(v => clamp(Math.round(v),0,255)
                                              .toString(16).padStart(2,"0")).join(""); }
function readable(bg, text, need){
  need = need || 4.5;
  if (contrast(bg, text) >= need) return {color: text, fixed: false};
  const up = lum(rgbOf(bg) || [0,0,0]) < 0.5;
  let c = rgbOf(text) || [128,128,128];
  for (let i = 0; i < 64; i++){
    c = c.map(v => up ? Math.min(255, v + (255-v)*0.08 + 2) : Math.max(0, v - v*0.08 - 2));
    if (contrast(bg, hex(c)) >= need) return {color: hex(c), fixed: true};
  }
  return {color: up ? "#ffffff" : "#000000", fixed: true};
}
function applyColors(){
  const root = document.documentElement.style;
  root.setProperty("--accent", colors[0]);
  root.setProperty("--accent-2", colors[1]);
  $("col1").value = colors[0]; $("col2").value = colors[1];
  root.setProperty("--bg", theme[0]);
  root.setProperty("--bg2", theme[0]);
  root.setProperty("--text", theme[1]);
  const t = rgbOf(theme[1]), b = rgbOf(theme[0]);
  if (t && b) root.setProperty("--dim", hex(t.map((v,i) => v*0.55 + b[i]*0.45)));
  $("colBg").value = theme[0]; $("colTx").value = theme[1];
  document.querySelectorAll(".sw").forEach(b => {
    b.style.background = $(b.dataset.for).value;
  });
}

/* ---------- choosing a colour ----------
   The system's colour panel is the system's window: pressing anywhere on the
   page leaves it standing, and it covers the very song it is meant to dress.
   So the swatches open a popover of our own — a row of ready colours and a
   field for a code — and the wheel stays one press away for those who want it. */
const SWATCHES = [
  "#4de1ff", "#7ee08a", "#ffcc4d", "#ff8ad1", "#ff7a7a", "#b98cff", "#9ad0ff", "#ffffff",
  "#1fb6d6", "#3fa85a", "#d19b1f", "#d1568f", "#c14b4b", "#7d55c7", "#5a7fa8", "#c8ccd8",
  "#0a0b14", "#141830", "#1d2436", "#2b2f45", "#3a3f58", "#5d6480", "#8b93b0", "#e8ebf5",
];
let swFor = null;
function closeSw(){ $("swPop").classList.add("hide"); swFor = null; }
function openSw(btn){
  const id = btn.dataset.for;
  swFor = id;
  const pop = $("swPop"), grid = $("swGrid");
  grid.replaceChildren();
  SWATCHES.forEach(c => {
    const b = document.createElement("button");
    b.style.background = c;
    b.title = c;
    b.addEventListener("click", () => setSw(c));
    grid.appendChild(b);
  });
  $("swHex").value = $(id).value;
  pop.classList.remove("hide");
  // under the swatch, and never off the edge of the window
  const r = btn.getBoundingClientRect(), pr = pop.getBoundingClientRect();
  pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pr.width - 8)) + "px";
  pop.style.top = Math.max(8, r.top - pr.height - 8) + "px";
}
function setSw(value){
  if (!swFor || !/^#[0-9a-f]{6}$/i.test(value)) return;
  const inp = $(swFor);
  inp.value = value;
  inp.dispatchEvent(new Event("input", {bubbles: true}));
  $("swHex").value = value;
  document.querySelectorAll(".sw").forEach(b => {
    b.style.background = $(b.dataset.for).value;
  });
}
document.querySelectorAll(".sw").forEach(b => {
  // the press must not reach the page, or the popover would close itself
  // before the click that opens it ever landed
  b.addEventListener("pointerdown", e => e.stopPropagation());
  b.addEventListener("click", e => {
    e.stopPropagation();
    if (swFor === b.dataset.for) return closeSw();
    openSw(b);
  });
});
$("swHex").addEventListener("input", () => setSw($("swHex").value.trim()));
$("swHex").addEventListener("keydown", e => {
  e.stopPropagation();
  if (e.key === "Enter" || e.key === "Escape") closeSw();
});
$("swPop").addEventListener("click", e => e.stopPropagation());
$("swPop").addEventListener("pointerdown", e => e.stopPropagation());
$("swMore").addEventListener("click", () => {
  const id = swFor;
  closeSw();
  if (id) $(id).click();          // the system wheel, for those who want it
});
// A press anywhere outside — on the page, on another swatch, on the song —
// puts the popover away.
document.addEventListener("pointerdown", () => { if (swFor) closeSw(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSw(); });
function pickTheme(i, val){
  if (theme[i] === val) return;
  theme[i] = val;
  const r = readable(theme[0], theme[1]);
  theme[1] = r.color;
  applyColors(); touched();
  if (r.fixed) toast(T.colorFixed);
}
$("colBg").addEventListener("input", e => pickTheme(0, e.target.value));
$("colTx").addEventListener("input", e => pickTheme(1, e.target.value));
function pickColor(i, val){
  if (colors[i] === val) return;
  colors[i] = val; applyColors(); touched();
}
$("col1").addEventListener("input", e => pickColor(0, e.target.value));
$("col2").addEventListener("input", e => pickColor(1, e.target.value));

// A line named in passing is cut at a word, never inside one: “…before w”
// says nothing and reads as a fault. The ellipsis admits there is more.
function shortLine(text, most){
  const s = String(text || "").split(/\s+/).filter(Boolean).join(" ");
  if (s.length <= most) return s;
  const cut = s.slice(0, most);
  const sp = cut.lastIndexOf(" ");
  return (sp >= most / 2 ? cut.slice(0, sp) : cut).replace(/[\s,.;:—-]+$/, "") + "…";
}

function voiceOf(ln){ return (ln && ln.voice === 2) ? 2 : 1; }
function refreshVoice(){
  $("btnVoice").textContent = sel < 0 ? T.voiceNone : T.voiceBtn(voiceOf(lines[sel]));
  $("btnVoice").classList.toggle("on", sel >= 0 && voiceOf(lines[sel]) === 2);
}
function toggleVoice(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  const to = voiceOf(lines[idx[0]]) === 2 ? 1 : 2;
  idx.forEach(i => {
    lines[i].voice = to;
    lineEls[i].el.classList.toggle("v2", to === 2);
    if (blockEls[i]) blockEls[i].classList.toggle("v2", to === 2);
  });
  updateLanes();
  refreshVoice(); touched();
  toast(idx.length > 1 ? T.voiceManyOn(to, idx.length)
                       : (to === 2 ? T.voice2On : T.voice1On));
}
$("btnVoice").addEventListener("click", toggleVoice);

// Sometimes a piece is not meant to be sung: backing vocals, speech, a moment
// that matters to the story. Such a line is marked, and in the finished karaoke
// the original is heard there again.
function refreshKeep(){
  const ln = sel >= 0 ? lines[sel] : null;
  const on = !!(ln && ln.keep);
  $("btnKeep").classList.toggle("on", on);
  $("btnKeep").textContent = !on ? T.keep
    : (ln.keepSoft ? T.keepSoftYes : T.keepYes);
}
function toggleKeep(){
  // Three states in a circle: not kept → the original at full voice (not
  // yours to sing) → the original held back to a guide (sing along with it)
  // → not kept. One button, because the choice is one choice.
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  const head = lines[idx[0]];
  const to = !head.keep ? {keep: true, keepSoft: false}
    : !head.keepSoft ? {keep: true, keepSoft: true}
    : {keep: false, keepSoft: false};
  idx.forEach(i => {
    lines[i].keep = to.keep;
    lines[i].keepSoft = to.keepSoft;
    lineEls[i].el.classList.toggle("keep", to.keep);
    markKeep(i);
    if (blockEls[i]) blockEls[i].classList.toggle("keep", to.keep);
  });
  refreshKeep(); touched();
  toast(idx.length > 1 ? T.keepManyMsg(to, idx.length)
    : to.keepSoft ? T.keepSoftMsg : (to.keep ? T.keepOnMsg : T.keepOffMsg));
}
// A tag right in the text: one glance says this line is not yours to sing.
function markKeep(i){
  const el = lineEls[i] && lineEls[i].el;
  if (!el) return;
  const old = el.querySelector(".kp");
  if (old) old.remove();
  if (!lines[i].keep) return;
  const kp = document.createElement("i");
  kp.className = "kp";
  kp.textContent = lines[i].keepSoft ? T.sungTogether : T.sungByOriginal;
  el.appendChild(kp);
}
$("btnKeep").addEventListener("click", toggleKeep);

/* ---------- a line put right by hand ----------
   Re-timing used to throw away every hand-made correction along with the rest.
   A lock says “leave this one alone”: the model gets no vote on it. */
function toggleLock(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  const to = !lines[idx[0]].lock;
  idx.forEach(i => {
    lines[i].lock = to;
    if (blockEls[i]) blockEls[i].classList.toggle("lock", to);
  });
  touched();
  toast(to ? T.lockedN(idx.length) : T.unlockedN(idx.length));
}
$("btnLock").addEventListener("click", toggleLock);

/* ---------- re-laying the words inside a line ----------
   The line's edges are right — set by hand, perhaps locked — and the words
   inside are a mess: an article under its neighbour, lengths from a bad pass.
   Re-spread them by syllables within the line's own span. The lock is no
   obstacle: it guards against the model, not against the person. */
$("btnEven").addEventListener("click", () => {
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  snap("");
  idx.forEach(i => spread(lines[i]));
  layoutBlocks(); layoutWords(); touched();
  toast(T.evenDone(idx.length));
});

/* ---------- timing a few lines again ----------
   The timing is wrong in one place and right everywhere else; redoing all of
   it costs minutes and throws away the corrections made by hand. */
$("btnRealignPart").addEventListener("click", async () => {
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  const a = Math.min(...idx), b = Math.max(...idx);
  if (!confirm(T.realignPartAsk(a + 1, b + 1))) return;
  await flush();
  try{
    const j = await api("/api/project/" + encodeURIComponent(pid) + "/realign-part",
      {from: a, to: b, align: caps.whisper ? "auto" : "energy", lang: langOf(),
       noText: ($("edNoText").value || "").trim()});
    watchJob(j.job, T.realignPart, r => {
      openProject(pid);
      toast(T.realignPartDone((r && r.lines) || 0));
    });
  }catch(e){ toast(e.message); }
});

/* ---------- copying a line and its rhythm ----------
   A chorus is sung the same way every time, and timing it again from scratch is
   wasted work. A line that is already right can be copied whole (Ctrl+D), or
   only its word layout can be taken and applied to the same line elsewhere. */
let clip = null;                  // {text, words:[{w, dt, d}]}
function sameText(i){
  return !!(clip && lines[i] &&
            clip.items.some(c => c.text.trim() === lines[i].text.trim()));
}
function copyRhythm(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  // Copy everything selected: the words, the layout, the voice, the marks and
  // the gaps between lines. Later either the rhythm alone or the lines
  // themselves can be pasted — one of them or the whole batch.
  const base = lines[idx[0]].start;
  clip = {
    span: lines[idx[idx.length - 1]].end - base,
    items: idx.map(i => {
      const ln = lines[i];
      return {text: ln.text, voice: voiceOf(ln), keep: !!ln.keep,
              backing: !!ln.backing, at: ln.start - base, len: ln.end - ln.start,
              words: ln.words.map(w => ({w: w.w, s: w.s, dt: w.t - ln.start, d: w.d}))};
    }),
  };
  refreshRhythm();
  toast(idx.length > 1 ? T.copiedLines(idx.length)
                       : T.copiedLine(shortLine(lines[idx[0]].text, 30)));
}
// Put a copy into a line: text, words and marks from the copy, place from the target.
function putLine(ln, item, start){
  ln.text = item.text;
  ln.voice = item.voice;
  ln.keep = item.keep;
  ln.backing = item.backing;
  ln.section = ln.section || null;
  ln.start = start;
  ln.end = start + Math.max(item.len, MIN_W * item.words.length);
  ln.words = item.words.map(c => ({w: c.w, s: c.s, t: start + c.dt, d: c.d}));
  const last = ln.words[ln.words.length - 1];
  if (last) ln.end = Math.max(ln.end, last.t + last.d);
}
function pasteLine(){
  if (!clip) return toast(T.rhythmNone);
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  // “Paste” means “add”, not “overwrite”: the copies go in after the selection
  // and nothing that already exists disappears.
  const after = idx[idx.length - 1];
  const cur = lines[after], next = lines[after + 1];
  const start = cur.end;
  const span = Math.max(clip.span, 0.4);
  const room = next ? Math.max(next.start - start, 0.4) : Infinity;
  const k = Math.min(1, room / span);
  snap("");
  const made = clip.items.map(item => {
    const ln = {text: "", words: [], section: null};
    putLine(ln, {...item, len: item.len * k,
                 words: item.words.map(w => ({...w, dt: w.dt * k,
                                              d: Math.max(w.d * k, MIN_W)}))},
            start + item.at * k);
    return ln;
  });
  lines.splice(after + 1, 0, ...made);
  marked.clear();
  buildLines(); makeBlocks(); updateLanes();
  selectLine(after + 1, false); curLine = -2; touched();
  toast(made.length > 1 ? T.linesPasted(made.length) : T.linePasted);
}
function applyRhythm(i, item){
  const ln = lines[i];
  if (ln.words.length !== item.words.length) return false;
  item.words.forEach((c, j) => { ln.words[j].t = ln.start + c.dt; ln.words[j].d = c.d; });
  const last = ln.words[ln.words.length - 1];
  ln.end = Math.max(ln.end, last.t + last.d);
  return true;
}
function pasteRhythm(){
  if (!clip) return toast(T.rhythmNone);
  if (sel < 0) return toast(T.pickLineFirst);
  // One line — or every later line with the same text, if the box is ticked.
  const idx = marked.size ? targets()
            : restToo() ? lines.map((l, i) => i).filter(i => i >= sel && sameText(i))
            : [sel];
  const list = idx.length ? idx : [sel];
  const one = clip.items.length === 1;
  const src = k => one ? clip.items[0] : clip.items[k % clip.items.length];
  const bad = list.filter((i, k) => lines[i].words.length !== src(k).words.length);
  if (bad.length === list.length)
    return toast(T.rhythmMismatch(src(0).words.length, lines[sel].words.length));
  snap("");
  let done = 0;
  list.forEach((i, k) => { if (applyRhythm(i, src(k))) done++; });
  layoutBlocks(); makeWords(); curLine = -2; touched();
  toast(done > 1 ? T.rhythmPastedN(done) : T.rhythmPasted);
}
// A whole copy of a line — when a repeat is missing from the text and the
// timing of the original is already good.
function duplicateLine(){
  if (sel < 0) return toast(T.pickLineFirst);
  const cur = lines[sel], next = lines[sel + 1];
  const span = Math.max(cur.end - cur.start, MIN_W * cur.words.length, 0.4);
  const start = cur.end;
  // The copy goes right after the original. If there is less room before the
  // next line than the line takes, the copy is squeezed — otherwise it would
  // run into its neighbour at once.
  const room = next ? Math.max(next.start - start, MIN_W * cur.words.length) : Infinity;
  const k = Math.min(1, room / span);
  const copy = {
    text: cur.text, section: null, backing: cur.backing,
    voice: cur.voice, keep: cur.keep, start, end: start + span * k,
    words: cur.words.map(w => ({w: w.w, s: w.s,
                                t: start + (w.t - cur.start) * k,
                                d: Math.max(w.d * k, MIN_W)})),
  };
  const last = copy.words[copy.words.length - 1];
  if (last) copy.end = Math.max(copy.end, last.t + last.d);
  snap("");
  lines.splice(sel + 1, 0, copy);
  buildLines(); makeBlocks(); selectLine(sel + 1, false); touched();
  toast(T.lineCopied);
}
function refreshRhythm(){
  const n = clip ? lines.filter((l, i) => sameText(i)).length : 0;
  $("btnPaste").disabled = !clip;
  $("btnPasteLine").disabled = !clip;
  $("btnPaste").textContent = T.pasteRhythm(n);
  $("btnPaste").classList.toggle("on", !!clip && sel >= 0 && sameText(sel));
}
$("btnRhythm").addEventListener("click", copyRhythm);
$("btnPaste").addEventListener("click", pasteRhythm);
$("btnPasteLine").addEventListener("click", pasteLine);
$("btnUndo").addEventListener("click", undo);

// The save state is always visible instead of flashing for a second: one has
// to know whether an edit is on disk without guessing.
let dirty = false, saving = null;
function saveState(kind, text){
  const n = $("savedNote");
  n.className = "saved on " + kind;
  n.textContent = text;
}
async function saveNow(){
  if (!dirty) return;
  dirty = false;
  saveState("busy", T.saving);
  try{
    const r = await api(`/api/project/${encodeURIComponent(pid)}/timings`,
      {lines, colors, theme,
       noText: ($("edNoText").value || "").trim(),
       keepMarks: $("chkKeepMarks") ? $("chkKeepMarks").checked : true,
       checkOff, title: songName, artist: songArtist,
       coverDark: (data && data.coverDark != null) ? data.coverDark : undefined,
       grid: (data && data.grid) ? data.grid : undefined});
    showProblems(r.problems);
    saveState("ok", T.savedOk);
  }catch(e){
    dirty = true;                       // not saved — the edit is still ours
    saveState("bad", T.saveBad);
    toast(T.saveErr(e.message));
    clearTimeout(saveT); saveT = setTimeout(() => { saving = saveNow(); }, 3000);
  }
}
function touched(){
  dirty = true;
  saveState("busy", T.unsaved);
  clearTimeout(saveT);
  saveT = setTimeout(() => { saving = saveNow(); }, 350);
}
// Before exporting, wait for the edit to reach the disk: the server builds the
// file from what it has, and without this the page could carry the old timing.
async function flush(){
  clearTimeout(saveT);
  if (dirty) saving = saveNow();
  await saving;
}

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

/* ================= the timeline ================= */
let zoom = 15;                  // how many seconds are visible
function pps(){ return $("tlwrap").clientWidth / zoom; }   // pixels per second
function viewStart(){ return clamp(mediaTime() - zoom*0.35, 0, Math.max(dur-zoom,0)); }
function xOf(t){ return (t - viewStart()) * pps(); }
function tOf(x){ return viewStart() + x / pps(); }

// Painting the waveform is the priciest thing this window does, and it used
// to happen sixty times a second whether anything moved or not — a paused
// editor warmed the room. It now runs only when the picture would differ:
// every place that changes the data marks it dirty, and the clock tick
// repaints on the mark or once the view itself has moved a pixel.
let waveDirty = true, waveSig = "";
function drawWave(){ waveDirty = true; }
// The whole song in one strip: the marks, the kept lines, the quiet
// stretches, and the window that is on screen right now. Click or drag to
// jump — on a long song the wheel is a hike, and this is a step.
function paintMap(){
  // Decoration must never take the editor down with it: a canvas without
  // some method (a test stand's stub, an odd browser) skips the strip.
  try{ paintMapInner(); }catch(e){}
}
function paintMapInner(){
  const c = $("mmap");
  if (!c || !dur) return;
  const w = c.clientWidth, h = c.clientHeight;
  if (!w) return;
  const pw = Math.round(w * devicePixelRatio), ph = Math.round(h * devicePixelRatio);
  if (c.width !== pw || c.height !== ph){ c.width = pw; c.height = ph; }
  const g = c.getContext("2d");
  if (g.setTransform) g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  else g.scale(devicePixelRatio, devicePixelRatio);
  g.clearRect(0, 0, w, h);
  const X = t => t / dur * w;
  // quiet stretches: a shade dimmer than the strip itself
  g.fillStyle = "rgba(0,0,0,.35)";
  (quiet || []).forEach(q => g.fillRect(X(q.start), 0, X(q.end) - X(q.start), h));
  // “no words here” marks, in the warning colour
  g.fillStyle = "rgba(255,204,77,.28)";
  marks.forEach(([a, b]) => g.fillRect(X(a), 0, X(b) - X(a), h));
  // the lines: thin ticks along the base; kept ones taller and in their hue
  lines.forEach(ln => {
    const x = X(ln.start), wd = Math.max(1, X(ln.end) - x);
    if (ln.keep){
      g.fillStyle = ln.keepSoft ? "rgba(126,224,138,.5)" : "rgba(126,224,138,.8)";
      g.fillRect(x, 2, wd, h - 4);
    } else {
      g.fillStyle = ln.voice === 2 ? colors[1] : colors[0];
      g.globalAlpha = 0.55;
      g.fillRect(x, h - 6, wd, 4);
      g.globalAlpha = 1;
    }
  });
  // the window now on screen
  const v0 = viewStart(), v1 = v0 + zoom;
  g.strokeStyle = "rgba(255,255,255,.65)";
  g.lineWidth = 1;
  g.strokeRect(X(v0) + 0.5, 0.5, Math.max(2, X(v1) - X(v0)) - 1, h - 1);
  // the playhead
  g.fillStyle = colors[0];
  g.fillRect(X(mediaTime()) - 0.5, 0, 1.5, h);
}

function paintWave(){
  const c=$("wave"), w=$("tlwrap").clientWidth, h=$("tlwrap").clientHeight;
  // Reallocating the canvas buffer on every repaint fed the garbage
  // collector for nothing: the size only changes when the window does.
  const pw = Math.round(w*devicePixelRatio), ph = Math.round(h*devicePixelRatio);
  if (c.width !== pw || c.height !== ph){ c.width = pw; c.height = ph; }
  const g=c.getContext("2d");
  // setTransform resets the scale absolutely; the test stands' canvas stub
  // knows only scale, where nothing accumulates anyway
  if (g.setTransform) g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  else g.scale(devicePixelRatio, devicePixelRatio);
  g.clearRect(0,0,w,h);

  // Stretches without singing — intro, interlude, solo. They are shaded: no
  // line belongs there, and the eye catches it at once.
  const kq = pps(), vq = viewStart();
  quiet.forEach(q => {
    const x = (q.start - vq) * kq, wd = (q.end - q.start) * kq;
    if (x + wd < 0 || x > w) return;
    g.fillStyle = "rgba(255,255,255,.05)";
    g.fillRect(x, 0, wd, h);
    g.fillStyle = "rgba(139,147,176,.85)";
    g.font = "10px system-ui, sans-serif";
    if (wd > 74) g.fillText(T.waveQuiet, x + 6, 12);
  });

  // The beat grid, under everything a person put there: bars carry a line
  // through the whole height, beats a shorter one, sixteenths only a tick —
  // and only while there is room enough for them to be told apart.
  if (grid.on){
    const st = gridStep();
    if (st > 0 && st * kq > 3){
      const first = Math.floor((vq - grid.beat0) / st) - 1;
      const beats = grid.sub || 1;
      for (let n = first; ; n++){
        const t = grid.beat0 + n * st;
        const x = (t - vq) * kq;
        if (x > w) break;
        if (x < 0) continue;
        // which of the four beats of a bar this is, and whether it is a beat
        // at all rather than a subdivision between two
        const idx = Math.round((t - grid.beat0) / st);
        const onBeat = idx % beats === 0;
        const onBar = idx % (beats * 4) === 0;
        g.fillStyle = onBar ? "rgba(255,204,77,.30)"
                    : onBeat ? "rgba(255,255,255,.16)"
                             : "rgba(255,255,255,.07)";
        g.fillRect(Math.round(x), onBar ? 0 : (onBeat ? 0 : h * 0.62),
                   onBar ? 2 : 1, onBar ? h : (onBeat ? h : h * 0.38));
      }
    }
  }

  // The marks a person made, and the one being dragged right now.
  const all = marks.concat(markFrom !== null && markTo !== null
                           ? [[Math.min(markFrom, markTo), Math.max(markFrom, markTo)]] : []);
  all.forEach(([a, b], i) => {
    const x = (a - vq) * kq, wd = (b - a) * kq;
    if (x + wd < 0 || x > w) return;
    g.fillStyle = i < marks.length ? "rgba(255,204,77,.16)" : "rgba(255,204,77,.28)";
    g.fillRect(x, 0, wd, h);
    g.fillStyle = "rgba(255,204,77,.55)";
    g.fillRect(x, 0, 1.5, h);
    g.fillRect(x + wd - 1.5, 0, 1.5, h);
    if (wd > 60){
      g.fillStyle = "rgba(255,204,77,.9)";
      g.font = "10px system-ui, sans-serif";
      g.fillText(T.waveNoText, x + 6, h - 6);
    }
  });

  if (!envelope.length) return;
  const v0=viewStart(), mid=40;
  g.fillStyle="rgba(120,150,190,.42)";
  for (let x=0; x<w; x++){
    const t=v0 + x/w*zoom, i=Math.floor(t/envHop);
    if (i<0 || i>=envelope.length) continue;
    const a=Math.min(envelope[i]*1.7,1)*34;
    g.fillRect(x, mid-a, 1, a*2);
  }
  g.strokeStyle="rgba(255,204,77,.35)"; g.lineWidth=1;
  onsets.forEach(t => { const x=xOf(t); if (x>=0&&x<=w){
    g.beginPath(); g.moveTo(x+.5,4); g.lineTo(x+.5,76); g.stroke(); } });

  // The words of every line, always in sight: a thin band along the bottom of
  // the wave, one box per word, neighbouring lines in alternating shades — so
  // the whole layout can be watched without selecting anything. The selected
  // line's own lane below stays the place to grab and drag.
  const wy = h - 11, wh = 7;
  if (kq < 8) return;          // words this small are noise, and the costliest kind
  lines.forEach((ln, li) => {
    if (!ln.words || ln.end == null || ln.start == null) return;
    if (ln.end < vq || ln.start > vq + zoom) return;
    g.fillStyle = li % 2 ? "rgba(255,204,77,.30)" : "rgba(150,175,215,.38)";
    ln.words.forEach(word => {
      const x = (word.t - vq) * kq, wd = Math.max((word.d || 0) * kq, 1.5);
      if (x + wd < 0 || x > w) return;
      g.fillRect(x, wy, Math.max(wd - 1, 1), wh);
    });
  });
}
/* The blocks are created once and live in a container that is simply shifted.
   Rebuilding them every frame means 60 DOM rebuilds a second, which visibly
   slows the window down on a song of sixty lines. */
// Lines the model barely heard, measured against this song and not against a
// number picked in advance: on a screamed vocal every word sits low, and what
// gives a bad line away is standing out from its neighbours.
let weakBelow = null;
function figureDoubt(){
  const got = lines.map(l => l.sure).filter(v => typeof v === "number").sort((a, b) => a - b);
  weakBelow = got.length >= 8 ? got[got.length >> 1] * 0.5 : null;
}
function doubtful(ln){
  return weakBelow !== null && typeof ln.sure === "number" && ln.sure < weakBelow;
}
const blockEls = [];
function makeBlocks(){
  const box = $("blocks");
  box.innerHTML = ""; blockEls.length = 0;
  lines.forEach((ln, i) => {
    const e = document.createElement("div");
    e.className = "blk" + (ln.voice === 2 ? " v2" : "") + (ln.keep ? " keep" : "")
                + (doubtful(ln) ? " doubt" : "") + (ln.lock ? " lock" : "");
    e.dataset.i = i;
    e.appendChild(document.createTextNode((i+1) + ". " + ln.text));
    // Grips on both sides: the right one moves the end of the line, the left
    // one the start. There used to be no left grip, so the start could not be
    // moved without moving the whole line.
    for (const side of ["left", "right"]){
      const grip = document.createElement("div");
      grip.className = "grip " + side;
      grip.dataset.grip = side;
      grip.title = side === "left" ? T.gripStart : T.gripEnd;
      e.appendChild(grip);
    }
    box.appendChild(e);
    blockEls.push(e);
  });
  updateLanes();
  layoutBlocks();
  paintMarks();          // the blocks are rebuilt — the marks have to come back
}
// The second lane is only needed when the song has a second voice: otherwise
// the timeline would be twice as tall for nothing.
function updateLanes(){
  const two = lines.some(l => l.voice === 2);
  const wrap = $("tlwrap");
  if (wrap.classList.contains("twolane") === two) return;
  wrap.classList.toggle("twolane", two);
  drawWave();                       // the canvas under the timeline changed height
}
function layoutBlock(i){
  const e = blockEls[i], ln = lines[i];
  if (!e) return;
  const k = pps();
  e.style.left = (ln.start * k) + "px";
  e.style.width = Math.max((ln.end - ln.start) * k, 14) + "px";
  e.classList.toggle("sel", i === sel);
  e.classList.toggle("bad", !!(window.__badLines && window.__badLines.has(i)));
}
function layoutBlocks(){
  for (let i = 0; i < blockEls.length; i++) layoutBlock(i);
  makeWords();
  showNextHint();
}
// An empty timeline window looks broken: not a single line in sight and no clue
// what is ahead. A hint at the edge says where things are going and how long.
function showNextHint(){
  const box = $("tlnext");
  if (!box) return;
  const w = $("tlwrap").clientWidth, a = viewStart(), b = a + zoom;
  const visible = lines.some(l => l.end > a && l.start < b);
  if (visible || !lines.length){ box.classList.add("hide"); return; }
  const t = mediaTime();
  const next = lines.find(l => l.start >= b);
  const back = !next;
  const target = next || lines.filter(l => l.end <= a).pop() || lines[0];
  const away = back ? t - target.end : target.start - t;
  box.classList.toggle("back", back);
  box.classList.remove("hide");
  box.innerHTML = (back ? T.backLast : "")
    + `<b>${esc(target.text.slice(0, 40))}</b> `
    + (back ? "" : "▶ ")
    + (away >= 60 ? fmt(away) : Math.max(0, Math.round(away)) + T.sec)
    + (back ? T.ago : "");
}

/* ---------- the words of the selected line ----------
   Singing inside a line is uneven: a pause, a stretched word, a patter. The
   syllable layout knows nothing of that, so every word can be moved on its own. */
const wordEls = [];
function makeWords(){
  const box = $("words");
  if (!box) return;
  const ln = sel >= 0 ? lines[sel] : null;
  if (!ln){ box.innerHTML = ""; wordEls.length = 0; return; }
  if (wordEls.length !== ln.words.length || box.dataset.line !== String(sel)){
    box.innerHTML = ""; wordEls.length = 0;
    box.dataset.line = String(sel);
    ln.words.forEach((w, j) => {
      const e = document.createElement("div");
      e.className = "wrd"; e.dataset.j = j;
      e.title = T.wordHint(w.w);
      const t = document.createElement("span");
      t.className = "wtx"; t.textContent = w.w;
      e.appendChild(t);
      // A word has edges like a line: start on the left, end on the right.
      // Without them a word's length could not be set at all — it simply ran
      // to its neighbour.
      for (const side of ["left", "right"]){
        const g = document.createElement("div");
        g.className = "wgrip " + side;
        g.dataset.wgrip = side;
        g.title = side === "left" ? T.wordStart : T.wordEnd;
        e.appendChild(g);
      }
      box.appendChild(e); wordEls.push(e);
    });
  }
  layoutWords();
}
function layoutWords(){
  const ln = sel >= 0 ? lines[sel] : null;
  if (!ln) return;
  const k = pps();
  // Words overlap in time more often than not, and an article the aligner gave
  // no time of its own starts exactly where its neighbour does — drawn as they
  // are, such chips lie on top of each other and the small one cannot even be
  // grabbed. Each chip is given a sliver of its own and trimmed short of the
  // next one: the drawing steps aside, the times stay exactly as they are.
  let prevRight = -1e9;
  wordEls.forEach((e, j) => {
    const w = ln.words[j];
    if (!w) return;
    const left = Math.max(w.t * k, prevRight + 1);
    let width = Math.max(w.d * k, 12);
    const next = ln.words[j + 1];
    if (next){
      // Twelve pixels is the least a finger or a cursor can take hold of:
      // a sliver thinner than that is visible and still ungrabbable.
      const nextLeft = Math.max(next.t * k, left + 13);
      width = Math.max(12, Math.min(width, nextLeft - left - 1));
    }
    prevRight = left + width;
    e.style.left = left + "px";
    e.style.width = width + "px";
    // on a narrow word the label is unreadable anyway — show no stub
    e.classList.toggle("tiny", width < 26);
  });
}
// No word collapses to zero: the highlight would flash past it instantly.
const MIN_W = 0.06;

// Words are no longer glued end to end. A word's length used to mean “up to
// the next one”, so where a word ENDS could not be set at all — the neighbour
// had to be moved. Now each has its own start and length, and a gap between
// words is allowed: pauses inside a line are normal in a song.
function editWord(j, mode, t0, d0, dt){
  const ln = lines[sel], w = ln.words[j];
  const prev = ln.words[j-1], next = ln.words[j+1];

  // Neighbours GIVE WAY instead of holding a wall. Words in a line sit end to
  // end, and forbidding overlap locks every word between its own neighbours so
  // it cannot move at all — which is exactly what used to happen.
  // The bound is not the neighbour's edge but the edge of THE ONE AFTER IT: a
  // neighbour may shrink, but not vanish.
  // The outer words are bounded only by the song. Pinning them to the edges of
  // their own line is wrong: lines sit end to end, and the last word could not
  // be moved by even a millisecond. The line stretches after it, and if it runs
  // into the next one the “Check” panel says so — that is what it is for.
  const floor = prev ? prev.t + MIN_W : 0;
  const ceil  = next ? next.t + next.d - MIN_W
                     : Math.max(ln.end, dur || t0 + d0 + 10);

  if (mode === "left"){
    // move the start, the end stays put — that is how length is set
    const end = t0 + d0;
    w.t = clamp(t0 + dt, floor, end - MIN_W);
    w.d = end - w.t;
  } else if (mode === "right"){
    w.t = t0;
    w.d = clamp(d0 + dt, MIN_W, ceil - t0);
  } else {
    w.t = clamp(t0 + dt, floor, Math.max(floor, ceil - d0));
    w.d = d0;
  }

  // Once moved, push the neighbours back exactly as far as we ran into them.
  if (prev && prev.t + prev.d > w.t) prev.d = Math.max(MIN_W, w.t - prev.t);
  if (next && w.t + w.d > next.t){
    const nEnd = next.t + next.d;
    next.t = w.t + w.d;
    next.d = Math.max(MIN_W, nEnd - next.t);
  }
  // A word may go past the old bounds of its line — the line stretches after
  // it, or the last word would hit an invisible wall.
  ln.start = Math.min(ln.start, ln.words[0].t);
  const last = ln.words[ln.words.length - 1];
  ln.end = Math.max(ln.end, last.t + last.d);
  layoutWords(); layoutBlock(sel);
}
function drawBlocks(){                       // once a frame — one container shift
  $("tlscroll").style.transform = "translateX(" + (-viewStart() * pps()) + "px)";
  $("phead").style.left = xOf(mediaTime()) + "px";
  showNextHint();
}

/* ---------- dragging the blocks ---------- */
let drag=null, wdrag=null, diveAt=null;
$("blocks").addEventListener("dblclick", e => {
  const blk = e.target.closest(".blk"); if (!blk) return;
  editText(+blk.dataset.i);          // edit the text where the line is seen
});
// The edge stops at the outermost word: beyond that the line can only be
// squeezed whole, and there is no way to guess that without being told.
let saidLimit = 0;
function hitLimit(){
  if (Date.now() - saidLimit < 4000) return;
  saidLimit = Date.now();
  toast(T.edgeLimit);
}
$("blocks").addEventListener("pointerdown", e => {
  const blk = e.target.closest(".blk"); if (!blk) return;
  const i = +blk.dataset.i;
  // Overlapping blocks stack, and the top one used to swallow every press:
  // the line underneath could not be reached at all. The press keeps its old
  // meaning — select and maybe drag — and a SECOND press on the same spot,
  // released without moving, dives to the line underneath (see pointerup).
  diveAt = (!e.shiftKey && !e.ctrlKey && !e.metaKey && i === sel)
    ? {x: e.clientX, t: viewStart() + (e.clientX -
         $("tlwrap").getBoundingClientRect().left) / pps()}
    : null;
  selectLine(i, false, e.shiftKey ? "range" : (e.ctrlKey || e.metaKey) ? "add" : "");
  if (marked.size > 1) return;               // a batch is selected, not dragged
  snap("");                       // a snapshot before the edit, while data is whole
  drag = {i, x0:e.clientX, start:lines[i].start, end:lines[i].end,
          words: lines[i].words.map(w=>w.t),
          durs: lines[i].words.map(w=>w.d),      // keep hand-tuned word lengths
          grip: e.target.dataset.grip || "",
          // Alt squeezes the whole line into the new span instead of stretching
          // the outermost word alone: for a line that grabbed a minute and a
          // half, moving one word is no use at all.
          all: e.altKey};
  $("tlwrap").classList.add("drag");
  e.preventDefault();
});
// A word is dragged the same way as a line, but only it is changed.
$("words").addEventListener("pointerdown", e => {
  const el = e.target.closest(".wrd"); if (!el || sel < 0) return;
  const j = +el.dataset.j, w = lines[sel].words[j];
  snap("");
  wdrag = {j, x0:e.clientX, t0:w.t, d0:w.d,
           mode: e.target.dataset.wgrip || "move"};
  el.classList.add("on");
  $("tlwrap").classList.add("drag");
  e.preventDefault();
});
window.addEventListener("pointermove", e => {
  if (wdrag){
    const dt = (e.clientX - wdrag.x0) / $("tlwrap").clientWidth * zoom;
    editWord(wdrag.j, wdrag.mode, wdrag.t0, wdrag.d0, dt);
    const w = lines[sel].words[wdrag.j];
    $("selNote").textContent = wdrag.mode === "move"
      ? T.wordAt(w.w, fmtMs(w.t))
      : T.wordSpan(w.w, fmtMs(w.t), fmtMs(w.t + w.d), w.d.toFixed(2));
    return;
  }
  if (!drag) return;
  const dt = (e.clientX - drag.x0) / $("tlwrap").clientWidth * zoom;
  // Hold Alt to place a line exactly where the hand puts it: the magnet that
  // pulls to the start of a phrase is a help until the moment it is not, and
  // then there was no way to overrule it.
  const free = e.altKey;
  const ln = lines[drag.i];
  if (drag.grip && drag.all){
    // The whole line into the new span: every word moves, in proportion to its
    // syllables. This is what narrowing a line that swallowed an interlude
    // actually means.
    if (drag.grip === "right")
      ln.end = Math.max(drag.start + 0.3, drag.end + dt);
    else
      ln.start = clamp(drag.start + dt, 0, drag.end - 0.3);
    spread(ln);
  } else if (drag.grip === "right"){
    // Dragging the right edge stretches the LAST word; the rest stay exactly
    // where they were. This used to recompute the whole line, changing timing
    // that had been tuned by hand for no reason at all.
    const last = ln.words.length - 1;
    const floor = last >= 0 ? drag.words[last] + MIN_W : drag.start + 0.2;
    ln.end = Math.max(floor, drag.end + dt);
    if (last >= 0) ln.words[last].d = ln.end - ln.words[last].t;
    if (ln.end <= floor + 0.001) hitLimit();
  } else if (drag.grip === "left"){
    // The left edge does the same to the FIRST word: the line end is untouched.
    const w0 = ln.words[0];
    const ceil = w0 ? (drag.words[0] + drag.durs[0]) - MIN_W : drag.end - 0.2;
    let ns = clamp(drag.start + dt, 0, ceil);
    if (ns >= ceil - 0.001) hitLimit();
    const snap2 = free ? null : (grid.on ? nearestBeat(ns) : nearestOnset(ns));
    if (snap2 !== null && Math.abs(snap2 - ns) < zoom*0.012) ns = clamp(snap2, 0, ceil);
    ln.start = ns;
    if (w0){ w0.t = ns; w0.d = (drag.words[0] + drag.durs[0]) - ns; }
  } else {
    let ns = Math.max(0, drag.start + dt);
    // With the grid on, the beat is what a line belongs to; without it, the
    // start of a phrase in the sound.
    const snap = free ? null : (grid.on ? nearestBeat(ns) : nearestOnset(ns));
    if (snap !== null && Math.abs(snap-ns) < zoom*0.012) ns = snap;
    const d = ns - drag.start;
    ln.start = ns; ln.end = drag.end + d;
    ln.words.forEach((w,k) => w.t = drag.words[k] + d);
  }
  layoutBlock(drag.i); layoutWords();
  $("selNote").textContent = drag.grip === "right"
    ? T.lineEndAt(drag.i+1, fmtMs(ln.end))
    : T.lineAt(drag.i+1, fmtMs(ln.start));
});
window.addEventListener("pointerup", e => {
  if (wdrag){
    wdrag = null;
    wordEls.forEach(e => e.classList.remove("on"));
    $("tlwrap").classList.remove("drag"); curLine=-2; touched();
    return;
  }
  // A still second click on an already-selected block dives to the line
  // beneath it: overlapping lines can all be reached now, not only the top.
  if (diveAt && Math.abs(e.clientX - diveAt.x) < 3){
    const pile = [];
    for (let k = 0; k < lines.length; k++)
      if (lines[k].start <= diveAt.t && diveAt.t <= lines[k].end) pile.push(k);
    if (pile.length > 1){
      const at = pile.indexOf(sel);
      const next = pile[(at >= 0 ? at + 1 : 0) % pile.length];
      diveAt = null;
      if (drag){ drag = null; $("tlwrap").classList.remove("drag"); past.pop(); refreshUndo(); }
      selectLine(next, false);
      toast(T.lineDove(next + 1));
      return;
    }
  }
  diveAt = null;
  if (!drag) return;
  drag = null; $("tlwrap").classList.remove("drag"); curLine=-2; touched();
});
function nearestOnset(t){
  if (!onsets.length) return null;
  let best=null, bd=1e9;
  for (const o of onsets){ const d=Math.abs(o-t); if (d<bd){ bd=d; best=o; } }
  return best;
}
/* ---------- editing the text itself ---------- */
// A typo in the source txt used to need a full rebuild — which threw away all
// the hand tuning. Here a line is fixed in place: its time stays, and the words
// are laid out inside it again.
function syllables(word){
  const m = word.toLowerCase().match(/[аеёиоуыэюяaeiouy]/g);
  return Math.max(1, m ? m.length : 1);        // syllables are counted by vowels
}
// The word as sung, stripped of everything that is not sung: dots on a scream,
// commas, case. Two words that match here are the same word.
function normTok(w){ return w.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ""); }
function retext(i, text){
  const parts = text.trim().split(/\s+/).filter(Boolean);
  const ln = lines[i];
  if (!parts.length || parts.join(" ") === ln.text) return false;
  ln.text = parts.join(" ");
  // Editing the text can turn a line into backing vocals and back.
  ln.backing = /^\(.*\)$/.test(ln.text.trim());
  // Dots added to a long scream, one word fixed in the middle: where the words
  // are the same words, their times are THEIR times — laying the whole line
  // out anew threw away exactly the rhythm the person had already set. Only
  // the changed stretch is laid out, in the gap the change occupies.
  const old = ln.words;
  const oldN = old.map(w => normTok(w.w)), newN = parts.map(normTok);
  let pre = 0;
  while (pre < old.length && pre < parts.length
         && oldN[pre] && oldN[pre] === newN[pre]) pre++;
  let suf = 0;
  while (suf < old.length - pre && suf < parts.length - pre
         && oldN[old.length - 1 - suf]
         && oldN[old.length - 1 - suf] === newN[parts.length - 1 - suf]) suf++;
  const words = [];
  for (let k = 0; k < pre; k++)
    words.push({w: parts[k], t: old[k].t, d: old[k].d, s: syllables(parts[k])});
  const mid = parts.slice(pre, parts.length - suf);
  if (mid.length){
    const gapStart = pre ? old[pre - 1].t + old[pre - 1].d : ln.start;
    const gapEnd = suf ? old[old.length - suf].t : ln.end;
    const lo = Math.min(gapStart, gapEnd);
    const hi = Math.max(gapEnd, lo + MIN_W * mid.length);
    const syl = mid.reduce((a, w) => a + syllables(w), 0) || 1;
    let acc = 0;
    mid.forEach(w => {
      const t0 = lo + (hi - lo) * acc / syl;
      acc += syllables(w);
      const t1 = lo + (hi - lo) * acc / syl;
      words.push({w, t: t0, d: Math.max(t1 - t0, MIN_W), s: syllables(w)});
    });
  }
  for (let k = old.length - suf; k < old.length; k++){
    const w = parts[parts.length - (old.length - k)];
    words.push({w, t: old[k].t, d: old[k].d, s: syllables(w)});
  }
  ln.words = words;
  ln.start = words[0].t;
  ln.end = Math.max(words[words.length - 1].t + (words[words.length - 1].d || 0),
                    ln.start + 0.2);
  return true;
}
// A missing or a stray line is as much a mistake in the text as a typo, and
// rebuilding the whole song over it makes no more sense.
function addLine(){
  if (sel < 0) return toast(T.addAfter);
  const cur = lines[sel];
  const next = lines[sel + 1];
  // A new line takes the gap up to the next one, but no more than two seconds:
  // there is no point filling a long pause after a solo. The gap can even be
  // negative — neighbouring lines may already overlap — and then a short piece
  // is taken; the “Check” panel will point at the overlap anyway.
  const start = cur.end;
  const room = next ? next.start - start : Infinity;
  const end = start + Math.max(0.4, Math.min(2, room));
  // `section` is a heading that STARTS at this line. An inserted line must not
  // carry one, or “[Chorus]” would appear in the song twice.
  const ln = {text: T.newLineText, start, end: Math.max(end, start + 0.4),
              section: null, backing: false, words: []};
  ln.words = ln.text.split(" ").map(w => ({w, t: start, d: 0, s: syllables(w)}));
  spread(ln);
  snap("");
  lines.splice(sel + 1, 0, ln);
  buildLines(); makeBlocks(); selectLine(sel + 1, false); touched();
  editText(sel);                       // let the real text be typed straight away
}
/* ---------- splitting a line, and joining two ----------
   The most ordinary correction there is: a long line sung in two breaths, or
   two short ones that are really one phrase. Neither needs a model — the words
   and their times are already known, only the grouping changes. Before this,
   it meant editing the file on disk and timing the whole song again. */
function splitLine(){
  if (sel < 0) return toast(T.pickLineFirst);
  const ln = lines[sel];
  if (!ln.words || ln.words.length < 2) return toast(T.splitTooShort);
  // Where the singing pauses longest inside the line: that is where a person
  // draws breath, and where the line wants to be cut.
  let at = 1, widest = -1;
  for (let i = 1; i < ln.words.length; i++){
    const gap = ln.words[i].t - (ln.words[i - 1].t + (ln.words[i - 1].d || 0));
    if (gap > widest){ widest = gap; at = i; }
  }
  snap("");
  const tail = ln.words.slice(at), head = ln.words.slice(0, at);
  const cut = tail[0].t;
  const second = {
    text: tail.map(w => w.w).join(" "),
    start: cut, end: ln.end,
    section: null, backing: ln.backing, voice: ln.voice,
    keep: ln.keep, lock: ln.lock, words: tail,
  };
  ln.words = head;
  ln.text = head.map(w => w.w).join(" ");
  // Words can overlap slightly, so the last word of the first half may reach
  // past where the second half begins. A line must never end after the next
  // one starts — the highlight would jump back and forth.
  const headEnd = head[head.length - 1].t + (head[head.length - 1].d || 0);
  ln.end = Math.max(ln.start + 0.05, Math.min(headEnd, cut));
  lines.splice(sel + 1, 0, second);
  buildLines(); makeBlocks(); selectLine(sel + 1, false); touched();
  toast(T.lineSplit);
}
function joinLine(){
  if (sel < 0) return toast(T.pickLineFirst);
  if (sel + 1 >= lines.length) return toast(T.joinNoNext);
  const a = lines[sel], b = lines[sel + 1];
  if (b.section) return toast(T.joinAcrossSection);
  snap("");
  a.words = a.words.concat(b.words);
  a.text = (a.text + " " + b.text).replace(/\s+/g, " ").trim();
  a.end = b.end;
  a.keep = a.keep || b.keep;
  a.lock = a.lock || b.lock;
  lines.splice(sel + 1, 1);
  marked.clear();
  buildLines(); makeBlocks(); selectLine(sel, false); touched();
  toast(T.lineJoined);
}
$("btnSplit").addEventListener("click", splitLine);
$("btnJoin").addEventListener("click", joinLine);

function delLine(){
  const idx = targets();
  if (!idx.length) return toast(T.pickLineFirst);
  if (lines.length <= idx.length) return toast(T.delLast);
  const what = idx.length > 1 ? T.delAskMany(idx.length) : T.delAsk(lines[idx[0]].text);
  if (!confirm(what)) return;
  snap("");
  idx.slice().reverse().forEach(i => lines.splice(i, 1));
  const keep = clamp(idx[0], 0, lines.length - 1);
  marked.clear();
  buildLines(); makeBlocks(); selectLine(keep, false); touched();
  toast(idx.length > 1 ? T.linesDeleted(idx.length) : T.lineDeleted);
}
// Editing the text had to be guessed: a double click on a line is not what
// comes to mind while looking at the timeline. The button says it out loud.
$("btnText").addEventListener("click", () => {
  if (sel < 0) return toast(T.pickLineFirst);
  editText(sel);
});
$("btnAddLine").addEventListener("click", addLine);
$("btnDelLine").addEventListener("click", delLine);

let editingText = -1;
function editText(i){
  if (editingText >= 0) return;
  if (i < 0 || !lines[i]) return;
  selectLine(i, false);
  centerLine(i);                   // the line may be off-stage — bring it into view
  editingText = i;
  const el = lineEls[i].el, ln = lines[i];
  const inp = document.createElement("input");
  inp.className = "lnedit"; inp.value = ln.text;
  inp.setAttribute("aria-label", T.lineTextAria(i+1));
  el.replaceChildren(inp);
  inp.focus(); inp.select();

  const finish = (save) => {
    if (editingText < 0) return;
    editingText = -1;
    if (save) snap("");
    const changed = save && retext(i, inp.value);
    // nothing changed, so there must be no undo step, or the button would stay
    // lit over an empty history and do nothing when pressed
    if (save && !changed){ past.pop(); refreshUndo(); }
    buildLines();                       // rebuild the stage: the word count changed
    makeBlocks();                       // and the label on the timeline too
    selectLine(i, false);
    if (changed){ touched(); toast(T.lineTextFixed); }
  };
  inp.addEventListener("keydown", e => {
    e.stopPropagation();                // or Enter and Space would hit the hotkeys
    if (e.key === "Enter"){ e.preventDefault(); finish(true); }
    if (e.key === "Escape"){ e.preventDefault(); finish(false); }
  });
  inp.addEventListener("blur", () => finish(true));
  inp.addEventListener("click", e => e.stopPropagation());
  inp.addEventListener("dblclick", e => e.stopPropagation());
}

let songName = "", songArtist = "", namingNow = false;

function showName(){
  $("edTitle").textContent = songName + (songArtist ? " — " + songArtist : "");
}

// The name is not only a label in the window: it stands in the corner of the
// video, on its opening card, on the page, and it names the exported files.
// Taken from a file name or a lyrics header it is often wrong, and there was
// no way to say otherwise.
function editName(){
  if (namingNow) return;
  namingNow = true;
  const h = $("edTitle"), was = h.textContent;
  const box = document.createElement("span");
  box.className = "nameEdit";
  const t = document.createElement("input");
  t.className = "t"; t.value = songName; t.placeholder = T.namePlaceTitle;
  t.setAttribute("aria-label", T.namePlaceTitle);
  const dash = document.createElement("span");
  dash.textContent = "—";
  const a = document.createElement("input");
  a.className = "a"; a.value = songArtist; a.placeholder = T.namePlaceArtist;
  a.setAttribute("aria-label", T.namePlaceArtist);
  box.append(t, dash, a);
  h.replaceChildren(box);
  t.focus(); t.select();

  const finish = (save) => {
    if (!namingNow) return;
    namingNow = false;
    const nt = t.value.trim(), na = a.value.trim();
    const changed = save && (nt !== songName || na !== songArtist);
    if (changed){ songName = nt; songArtist = na; }
    h.replaceChildren();
    showName();
    if (!songName && !songArtist) h.textContent = was;   // nothing to show
    if (changed){ touched(); toast(T.nameFixed); }
  };
  for (const inp of [t, a]){
    inp.addEventListener("keydown", e => {
      e.stopPropagation();              // Enter and Space belong to the stage
      if (e.key === "Enter"){ e.preventDefault(); finish(true); }
      if (e.key === "Escape"){ e.preventDefault(); finish(false); }
    });
    inp.addEventListener("blur", () => {
      // Moving between the two fields is not leaving the name.
      setTimeout(() => { if (![t, a].includes(document.activeElement)) finish(true); }, 0);
    });
  }
}

function spread(ln){
  const total = ln.words.reduce((s,w)=>s+(w.s||1),0)||1;
  // The span used to be forced up to 0.15 s here — and on a narrow line the
  // words were laid out WIDER than the line itself, spilling out of the block.
  // No invented lengths: if a line is too short for its words, the line grows.
  const need = ln.words.length * MIN_W;
  if (ln.end - ln.start < need) ln.end = ln.start + need;
  const span = ln.end - ln.start;
  let acc=0;
  ln.words.forEach(w => { w.t = ln.start + span*acc/total; acc += (w.s||1);
    w.d = ln.start + span*acc/total - w.t; });
}

/* ---------- seeking along the timeline ---------- */
$("tlwrap").addEventListener("pointerdown", e => {
  // While marking, the timeline is for marking: a press on an existing mark
  // takes it off, a press anywhere else starts a new one.
  if (marking){
    const t = tOf(e.offsetX), at = markAt(t);
    if (at >= 0){
      marks.splice(at, 1);
      marksToField();
      touched();
      toast(T.markGone);
      drawWave();
      return;
    }
    markFrom = t; markTo = t;
    return;
  }
  // Empty timeline space means seeking. What lies on it does not: a line block
  // and a word chip are dragged, not seeked. Without this rule, grabbing a word
  // first seeked the song and the stage jumped to another line under your hand.
  if (e.target.closest(".blk") || e.target.closest(".wrd")) return;
  seek(tOf(e.offsetX));
});
/* ---------- marking the stretches that hold no words ----------
   A vocalise is voice: nothing measurable tells it from a sung line. The
   timeline is where a person can see it — a loud stretch with no lines under
   it — so that is where it should be possible to say so, with the mouse,
   instead of reading seconds off and typing them into a field. */
let marks = [], marking = false, markFrom = null, markTo = null;

// A stretch the program heard is “taken” once a mark of ours covers it.
function markedAlready(q){
  return marks.some(([a, b]) => a <= q.start + 0.2 && b >= q.end - 0.2);
}
// Taking them is an edit like any other: undoable, saved, and the waveform
// shows the result at once.
function takeQuiet(list){
  const fresh = list.filter(x => !markedAlready(x));
  if (!fresh.length) return toast(T.quietNothingNew);
  snap("");
  let n = 0;
  fresh.forEach(x => { if (addMark(x.start, x.end)) n++; });
  if (!n){ past.pop(); refreshUndo(); return toast(T.quietNothingNew); }
  touched();
  drawWave();
  drawSummary(lastData);
  toast(T.quietAdded(n));
}

function marksFromField(){
  marks = ($("edNoText").value || "").split(/[;,]/).map(part => {
    const m = part.trim().match(/^([\d:.,]+)\s*[-–—]\s*([\d:.,]+)$/);
    if (!m) return null;
    const sec = v => v.split(":").reduce((a, x) => a * 60 + parseFloat(x.replace(",", ".")), 0);
    const a = sec(m[1]), b = sec(m[2]);
    return (isFinite(a) && isFinite(b) && b > a) ? [a, b] : null;
  }).filter(Boolean).sort((x, y) => x[0] - y[0]);
}
// “0:42.5” — a tenth of a second is as fine as anyone can hear a boundary, and
// finer than that turns the field into a wall of digits.
function markTime(t){
  const m = Math.floor(Math.max(0, t) / 60), r = Math.max(0, t) - m * 60;
  return m + ":" + (r < 10 ? "0" : "") + r.toFixed(1);
}
function marksToField(){
  $("edNoText").value = marks.map(([a, b]) => markTime(a) + "-" + markTime(b)).join(", ");
}
function addMark(a, b){
  if (b - a < 0.3) return false;                 // a click, not a stretch
  marks.push([Math.max(0, a), Math.min(dur, b)]);
  marks.sort((x, y) => x[0] - y[0]);
  // touching marks are one mark: two halves of the same solo help nobody
  for (let i = marks.length - 1; i > 0; i--)
    if (marks[i][0] <= marks[i - 1][1] + 0.05){
      marks[i - 1][1] = Math.max(marks[i - 1][1], marks[i][1]);
      marks.splice(i, 1);
    }
  marksToField();
  return true;
}
function markAt(t){
  return marks.findIndex(([a, b]) => t >= a && t <= b);
}
function setMarking(on){
  marking = on;
  $("btnMark").classList.toggle("on", on);
  document.body.classList.toggle("marking", on);
  markFrom = markTo = null;
  toast(on ? T.markOn : T.markOff);
  drawWave();
}
$("btnMark").addEventListener("click", () => setMarking(!marking));

// A line next to a hole reaches across it: the aligner had to end it somewhere.
// The marks already say where the emptiness is — so cut the spans back to them,
// without timing anything again.
$("btnClip").addEventListener("click", () => {
  if (!marks.length) return toast(T.clipNoMarks);
  snap("");
  let n = 0;
  lines.forEach(ln => {
    let a = ln.start, b = ln.end;
    marks.forEach(([lo, hi]) => {
      if (b <= lo || a >= hi) return;          // nowhere near this hole
      if (a >= lo && b <= hi) return;          // wholly inside: moving it is another matter
      if (a < lo && b <= hi) b = lo;
      else if (a >= lo && a < hi && b > hi) a = hi;
      else if (a < lo && hi < b){ if (lo - a >= b - hi) b = lo; else a = hi; }
    });
    if (Math.abs(a - ln.start) < 0.01 && Math.abs(b - ln.end) < 0.01) return;
    if (b - a < 0.2) return;                   // nothing usable would be left
    ln.start = a; ln.end = b; spread(ln); n++;
  });
  // …and the lines that sit wholly inside a hole: trimming cannot help them,
  // they have to leave it. They are pushed to the singing that follows, at a
  // sung pace, pressed against the line that comes after them — the same
  // reasoning the timing itself uses.
  let moved = 0;
  const inHole = ln => marks.find(([lo, hi]) => ln.start >= lo - 0.25 && ln.end <= hi + 0.25);
  for (let i = 0; i < lines.length; i++){
    const hole = inHole(lines[i]);
    if (!hole) continue;
    let j = i;
    while (j + 1 < lines.length && inHole(lines[j + 1])) j++;
    const run = lines.slice(i, j + 1);
    const nextStart = j + 1 < lines.length ? lines[j + 1].start
                                           : (dur || data.duration || 0);
    const prevEnd = i > 0 ? lines[i - 1].end : 0;
    // after the hole if there is room there, otherwise before it
    let lo = Math.max(hole[1], prevEnd), hi = nextStart;
    if (hi - lo < 0.5){ lo = prevEnd; hi = Math.min(hole[0], nextStart); }
    const syl = run.reduce((a, ln) => a + ln.words.reduce((b, w) => b + (w.s || 1), 0), 0) || 1;
    const need = run.reduce((a, ln) => a + ln.words.length, 0) * MIN_W;
    if (hi - lo < 0.25){
      // no room between the neighbours at all: right against the hole then,
      // cramped on purpose — better a tight line in the right place than
      // words over the stretch that was marked
      lo = hole[1];
      hi = lo + Math.max(0.3, 0.12 * run.reduce((a, ln) => a + ln.words.length, 0));
    }
    const span = Math.min(hi - lo, Math.max(syl * 0.45, need));
    let base = hi - span, acc = 0;
    run.forEach(ln => {
      const own = ln.words.reduce((b, w) => b + (w.s || 1), 0) || 1;
      ln.start = base + span * acc / syl;
      acc += own;
      ln.end = Math.max(base + span * acc / syl - 0.05, ln.start + 0.2);
      spread(ln);
      moved++;
    });
    i = j;
  }
  if (!n && !moved){ past.pop(); return toast(T.clipNothing); }
  curLine = -2; layoutBlocks(); touched(); refreshUndo();
  toast(moved ? T.clipMoved(n, moved) : T.clipDone(n));
});

$("tlwrap").addEventListener("pointermove", e => {
  if (!marking || markFrom === null) return;
  markTo = tOf(e.offsetX);
  drawWave();
});
window.addEventListener("pointerup", () => {
  if (!marking || markFrom === null) return;
  const a = Math.min(markFrom, markTo === null ? markFrom : markTo);
  const b = Math.max(markFrom, markTo === null ? markFrom : markTo);
  markFrom = markTo = null;
  if (addMark(a, b)){ toast(T.markAdded(markTime(a), markTime(b))); touched(); }
  drawWave();
});

/* ---------- the beat grid ----------
   A song at one tempo is a ruler: every line begins on a beat, and placing
   them by eye against a waveform is doing arithmetic with a magnifying glass.
   Four beats to a bar, sixteenths when the zoom is close enough for them to
   mean anything, and the lines snap to it while it is on. Nothing here guesses
   at the music: the tempo is typed, or tapped in, and the first beat is put
   where the playhead stands. */
let grid = {on: false, bpm: 120, beat0: 0, sub: 1, pulse: false};

function gridStep(){
  const bpm = clamp(+grid.bpm || 120, 20, 300);
  return 60 / bpm / (grid.sub || 1);
}
function nearestBeat(t){
  const st = gridStep();
  if (!(st > 0)) return null;
  return grid.beat0 + Math.round((t - grid.beat0) / st) * st;
}
function showGrid(){
  $("chkGrid").checked = !!grid.on;
  $("chkSixteen").checked = grid.sub === 4;
  $("chkPulse").checked = !!grid.pulse;
  if (document.activeElement !== $("nBpm")) $("nBpm").value = grid.bpm;
}
function saveGrid(){
  if (!data) return;
  data.grid = {on: !!grid.on, bpm: +grid.bpm, beat0: +grid.beat0,
               sub: grid.sub, pulse: !!grid.pulse};
  touched();
  drawWave(); drawBlocks();
}
$("chkGrid").addEventListener("change", () => {
  grid.on = $("chkGrid").checked; saveGrid();
});
$("chkSixteen").addEventListener("change", () => {
  grid.sub = $("chkSixteen").checked ? 4 : 1; saveGrid();
});
// The pulse is for the video, not for the window: a person can work with the
// grid on the timeline and want nothing of it in the clip, or the other way.
$("chkPulse").addEventListener("change", () => {
  grid.pulse = $("chkPulse").checked;
  saveGrid();
  if (!$("stillBox").classList.contains("hide")) showStill(stillT, false);
});
$("nBpm").addEventListener("input", () => {
  grid.bpm = clamp(+$("nBpm").value || 120, 20, 300); saveGrid();
});
$("nBpm").addEventListener("keydown", e => {
  e.stopPropagation();                    // digits are digits, not hotkeys
  if (e.key === "Enter"){ e.preventDefault(); $("nBpm").blur(); }
});
$("btnBeatOne").addEventListener("click", () => {
  grid.beat0 = mediaTime();
  if (!grid.on){ grid.on = true; showGrid(); }
  saveGrid();
  toast(T.beatOneSet(fmtMs(grid.beat0)));
});
// Tapping is how a person knows a tempo without being told it: four taps or
// more, and the spacing between them is the answer. Taps more than three
// seconds apart start a new count — that is somebody coming back to it later,
// not a very slow song.
let taps = [];
$("btnTapTempo").addEventListener("click", () => {
  const now = performance.now() / 1000;
  if (taps.length && now - taps[taps.length - 1] > 3) taps = [];
  taps.push(now);
  if (taps.length < 4){ toast(T.tapMore(4 - taps.length)); return; }
  taps = taps.slice(-8);
  const span = taps[taps.length - 1] - taps[0];
  const bpm = clamp(60 * (taps.length - 1) / span, 20, 300);
  grid.bpm = Math.round(bpm * 10) / 10;
  grid.beat0 = mediaTime();
  grid.on = true;
  showGrid(); saveGrid();
  toast(T.tapDone(grid.bpm));
});

// Half a second across the window is close enough to place a word by eye. The
// floor used to be four seconds, and at four seconds the magnet still reaches
// a couple of frames either side — so the one thing a person could do about it,
// zoom in further, was the one thing they could not do.
function setZoom(z){ zoom=clamp(z,0.5,120);
  $("zoomNote").textContent=zoomText(); layoutBlocks(); drawWave(); drawBlocks(); }
function zoomText(){
  return (zoom < 2 ? zoom.toFixed(1) : String(Math.round(zoom))) + T.sec;
}
$("btnZoomIn").addEventListener("click", ()=>setZoom(zoom/1.6));
// A line is a couple of seconds long and the view is fifteen: to see the words
// apart one had to zoom in by hand every time. This does it in one press.
$("btnFit").addEventListener("click", () => {
  if (sel < 0) return toast(T.pickLineFirst);
  const ln = lines[sel];
  const span = Math.max(ln.end - ln.start, 0.4);
  setZoom(clamp(span * 1.6, 4, 120));
  seek(Math.max(0, ln.start - span * 0.15));
});
$("btnZoomOut").addEventListener("click", ()=>setZoom(zoom*1.6));

/* ---------- tidy everything up ---------- */
$("btnSnap").addEventListener("click", () => {
  if (!onsets.length) return toast(T.noVocalWave);
  let n=0;
  snap("");
  lines.forEach(ln => {
    const o = nearestOnset(ln.start);
    if (o === null || Math.abs(o-ln.start) > 0.7) return;
    const d = o - ln.start;
    if (Math.abs(d) < 0.01) return;
    ln.start += d; ln.end += d; ln.words.forEach(w=>w.t += d); n++;
  });
  if (!n) past.pop();               // nothing moved — nothing to undo
  curLine=-2; layoutBlocks(); touched(); refreshUndo();
  toast(n ? T.movedN(n) : T.allInPlace);
});

/* ---------- looping a line ---------- */
function restToo(){ return $("chkRest").checked; }
function putHere(){
  if (sel < 0) return toast(T.pickLineFirst);
  const d = mediaTime() - lines[sel].start;
  snap("");
  const last = restToo() ? lines.length - 1 : sel;
  for (let k = sel; k <= last; k++){
    lines[k].start += d; lines[k].end += d;
    lines[k].words.forEach(w => w.t += d);
  }
  curLine = -2; layoutBlocks(); touched();
  $("selNote").textContent = T.lineNo(sel+1, fmtMs(lines[sel].start));
  toast(restToo() ? T.lineSetRest(sel+1) : T.lineSet(sel+1));
}
$("btnHere").addEventListener("click", putHere);

$("btnLoop").addEventListener("click", () => {
  if (sel < 0) return toast(T.pickLineFirst);
  loopSel = !loopSel;
  $("btnLoop").classList.toggle("on", loopSel);
  if (loopSel){ seek(Math.max(0, lines[sel].start-0.6)); play(); }
});

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
    if (!$("stillBox").classList.contains("hide")) showStill(stillT, false);
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
// A cover can come by link too: a row above the files takes the address.
function coverUrlRow(box){
  const r = document.createElement("div");
  r.className = "row urlrow";
  r.innerHTML = '<span class="ic">🔗</span>' +
    '<input class="nm" type="text">' +
    '<button class="words"></button>';
  const inp = r.querySelector("input");
  inp.placeholder = T.coverUrlPh;
  const btn = r.querySelector("button");
  btn.textContent = T.coverUrlGo;
  const go = () => {
    const url = inp.value.trim();
    if (!/^https?:\/\//.test(url)) return toast(T.coverUrlBad);
    $("browser").classList.add("hide");
    takeCover(null, url);
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
    if (!$("stillBox").classList.contains("hide")) showStill(stillT, false);
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
    if (!$("stillBox").classList.contains("hide")) showStill(stillT, false);
  }catch(e){ toast(e.message); }
}
function backdropUrlRow(box){
  const r = document.createElement("div");
  r.className = "row urlrow";
  r.innerHTML = '<span class="ic">🔗</span>' +
    '<input class="nm" type="text">' +
    '<button class="words"></button>';
  const inp = r.querySelector("input");
  inp.placeholder = T.backdropUrlPh;
  const btn = r.querySelector("button");
  btn.textContent = T.coverUrlGo;
  const go = () => {
    const url = inp.value.trim();
    if (!/^https?:\/\//.test(url)) return toast(T.coverUrlBad);
    $("browser").classList.add("hide");
    takeBackdrop(null, url);
  };
  btn.addEventListener("click", go);
  inp.addEventListener("keydown", e => {
    e.stopPropagation();
    if (e.key === "Enter") go();
  });
  inp.addEventListener("click", e => e.stopPropagation());
  box.appendChild(r);
}
$("btnClipBg").addEventListener("click", () => openBrowser("backdrop"));
$("btnClipBgOff").addEventListener("click", async () => {
  try{
    await api(`/api/project/${encodeURIComponent(pid)}/backdrop`, {off: true});
    data.backdrop = null;
    refreshBackdrop(); toast(T.backdropGone);
    if (!$("stillBox").classList.contains("hide")) showStill(stillT, false);
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
                intro: $("expIntro").checked};
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
