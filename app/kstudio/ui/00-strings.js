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
    expKey: "Key",
    expKeyOrig: "as recorded",
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
    dotsLongOn: "dots on long waits",
    cutFrom: "\u27E4 from here", cutTo: "\u27E5 to here",
    cutAll: "\u27F2 whole song",
    cutFromHint: "The song starts here for whoever sings it. Two minutes of "
      + "silence, a hidden track, a long lead-in — none of it has to travel "
      + "with the karaoke. The recording is untouched: this is a setting, and "
      + "it can be moved or dropped tomorrow.",
    cutToHint: "And ends here.",
    cutAllHint: "Back to the whole song.",
    cutSet: at => "The song is given as " + at,
    cutGone: "The whole song again",
    holdsOn: "bar on waits in a line",
    holdsHint: "A pause inside a line — a held note, an answer from the guitar "
      + "— shows itself: a bar grows under the word that will end it, so the "
      + "singer knows something is still coming and how near. Without it the "
      + "sweep just stops, which reads like the end of the line.",
    melodyOn: "melody over the words",
    melodyHint: "Draw the melody over the words: a bar to a word, standing as "
      + "high as that word is sung. A map to sing by, never a score. Off by "
      + "default — the words come first, and this is a strong thing to put "
      + "beside them uninvited. The notes are measured and kept either way.",
    dotsLongHint: "The three guide dots count down the seconds before a line. "
      + "On a wait long enough for the panel at the top of the frame they "
      + "stand down, so one pause is not counted twice over. Tick this for "
      + "both at once.",
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
    expKey: "Тональность",
    expKeyOrig: "как в записи",
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
    dotsLongOn: "точки и на долгих паузах",
    cutFrom: "\u27E4 отсюда", cutTo: "\u27E5 досюда",
    cutAll: "\u27F2 вся песня",
    cutFromHint: "Отсюда песня начинается для того, кто её поёт. Две минуты "
      + "тишины, спрятанный трек, длинное вступление — ничему из этого не "
      + "обязательно ехать вместе с караоке. Запись не трогается: это "
      + "настройка, её можно подвинуть или снять завтра.",
    cutToHint: "И досюда кончается.",
    cutAllHint: "Вернуть песню целиком.",
    cutSet: at => "Песня отдаётся куском " + at,
    cutGone: "Снова вся песня",
    holdsOn: "полоска пауз в строке",
    holdsHint: "Пауза внутри строки — тянутая нота, ответ гитары — показывает "
      + "себя: под словом, которое её закончит, растёт полоска, и певец знает, "
      + "что продолжение будет и насколько близко. Без неё заливка просто "
      + "останавливается, а это читается как конец строки.",
    melodyOn: "мелодия над словами",
    melodyHint: "Рисовать мелодию над словами: столбик над каждым словом на "
      + "той высоте, на какой оно поётся. Карта, по которой поют, и никогда "
      + "не оценка. По умолчанию выключено — слова важнее, а это сильная "
      + "вещь, чтобы ставить её рядом без спроса. Ноты меряются и хранятся в "
      + "любом случае.",
    dotsLongHint: "Три точки отсчитывают секунды перед строкой. На паузе, "
      + "достаточно длинной для таблички вверху кадра, они уступают ей место, "
      + "чтобы одна пауза не отсчитывалась дважды. Поставьте галку, если "
      + "нужно и то, и другое.",
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
