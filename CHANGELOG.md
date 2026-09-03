# What changed

Newest first. Each entry says what was wrong and what it means for you — the
commits themselves are one click away in the history.

*По-русски: [CHANGELOG.ru.md](CHANGELOG.ru.md)*

---

## 4.44.3

**Lines pushed off a marked stretch came out as a pile.** Mark the intro as
holding no words and the lines the aligner dropped there are moved out — but
they were moved into whatever room the aligner happened to leave, however
little that was. Four lines against a hole with the next line pressing right
behind it got a tenth of a second apiece: not a tight line, which is what was
intended, but the very pile this module exists to undo. On the timeline they
sit on top of one another; in the video they flash past unread.

The floor was already worked out — the least those syllables can honestly be
sung in — and then never used. It is used now, and the room for it is borrowed
from the lines that follow, gap by gap, only as far as their own silences can
spare and never across another mark or a line left to the original. In the
case above the lines went from a tenth of a second to six tenths. The floor
also counts the breath between one line and the next, which it did not: a run
given exactly the minimum still came out under it by a twentieth of a second
a line.

## 4.44.2

**macOS was asked the wrong question about its own folders.** The search knew
perfectly well that `pip install` on a Mac writes into
`~/Library/Python/3.x/bin` — it says so in its own comment — but it asked
Python for the scripts folder of the `posix_user` scheme, and a macOS
framework build answers that with `~/.local/bin`. The folder it meant to look
in belongs to a scheme of its own, `osx_framework_user`, and was never asked
about. The Python is asked which scheme it prefers now, where it is new enough
to say, and the macOS one is named outright where it is not.

## 4.44.1

**“yt-dlp is not installed” — said to somebody who had just installed it.**
There are several ways for that to be true at once: a machine holds more than
one Python, and pip leaves the downloader beside whichever it belongs to, in a
folder that need not be on anybody's PATH. Whatever the reason in a given
case, the old message answered it by advising the very command that had
already been run.

It now names the Python that went looking and gives the command that installs
the downloader *there* — `"/that/python" -m pip install -U yt-dlp` — which
cannot land beside the wrong one. More folders are searched first, too: every
sibling version under `~/Library/Python`, the python.org framework
directories, Homebrew's own, and where pipx keeps its venvs. And a path can
simply be written down in `settings.ini` as `yt-dlp = …`, which needs no
environment a double-clicked window would never see.

## 4.44.0

**A clip can stand behind the lyrics now, not just a picture.** Give the song
a file or a link — the one it came from will do — and the video plays it
behind the words, blurred into a slow field of colour. Because it is blurred
past recognising, the smallest copy a site offers is worth exactly as much as
the best one: a few megabytes instead of several hundred, and what the song
keeps is a few hundred pixels at four frames a second, small enough to travel
inside a packed song.

**The darkening stopped being one number.** A still cover is darkened by
whatever the singer chose; a clip will not hold still, and the number that
suited a dark shot blows out on the next cut. The band where the words stand
is measured on every field now, and the frame clamps down the instant a cut
brings something bright under the text, letting go slowly afterwards — the way
a limiter follows a sound. Easing both ways read as a frame slowly dimming
after every cut; measured across a hard cut, the worst moment went from 75 of
255 down to 55, and it settles in a fifth of a second instead of two.

**Packing kept dropping it.** A song folder skips .mp4 files when it packs,
because a rendered clip is made again in one press and weighs more than
everything else together. A backdrop is not made again — it is the one the
song was given. It travels now, and a check holds both halves of that.

## 4.43.0

**Every letter carries a dark ring now.** The words used to be readable only
because the backdrop was tame — a woven gradient, or a cover the singer had
darkened by hand. Over a bright picture a grey line melted into a grey wall,
and over anything that moves there is always a frame with something pale
exactly under a word. The outline does not care what is behind it. The name
in the corner, the opening card, the count and the labels wear one too: one
piece of writing left bare is the one that disappears.

**And a picture behind the lyrics gets a band.** A soft darkening across the
rows where the words stand, eased away above and below so its edge is never a
line anybody can see. It is laid once, into the background itself, so no frame
pays for it — and only pictures get one, since the woven gradient is quiet
already and a band on it would show as a band.

**The example in the manual was changed.** The word chosen to show a syllable
break read as something coarse in Russian. It is bells now, in both manuals
and in the tests.

## 4.42.1

**The word is spelled the way the file is named.** The project ships a file
called LICENSE and spelled the same word the British way beside it in two
places — one letter apart from its own name, which reads as carelessness in a
repository that asks to be trusted with somebody's music. The two now match,
and a check holds them there.

**This file said several things twice.** Four hundred lines of the English
changelog were a duplicate tail: every section from 4.31.0 down appeared a
second time, so anyone reading the history met the same releases twice over.
The tail is gone, and a check refuses a changelog that names a section more
than once.

**The manual caught up with the window.** The strip above the timeline, the
second press that dives to the line underneath an overlap, the frame preview,
the cover from a file, a link or the clip itself, the darkness knob, the
UltraStar and .ass exports, the packed song, the render dialog — all of it
existed and none of it was written down. Both manuals now describe them, and
the video chapter says that the lyrics ride upwards as a column, that a long
line breaks in two at a word instead of shrinking, and that the quoted line
in the countdown ends in an ellipsis.

## 4.42.0

**A word can be broken into syllables that nobody sees.** Write “for=ev=er=more”
in the lyrics and the pieces are timed one by one — a held note lights up
syllable by syllable — while the word stays whole everywhere it is read: in
the editor, on the page, in the video, in the UltraStar file and in the
subtitles. A soft hyphen does the same; an ordinary hyphen is a letter and is
left alone. The frame never breaks a line inside a word either.

**The colours are chosen in the window now.** The system's colour panel is
the system's window: it stood over the song and no press on the page could
dismiss it. The swatches open a popover of the program's own — ready colours
and a field for a code — which closes on a press anywhere outside, on another
swatch, or on Escape. The system wheel is still one press away for those who
want it.

**A line named in passing is cut at a word.** The countdown's “until …” chopped
the next line at thirty-four letters wherever they fell — “before w” told the
singer nothing and read as a fault. The cut falls at the last space that fits
now, with an ellipsis to admit there is more; a word with no space in it at
all still gets the ellipsis. The editor's own hints follow the same rule.

---

## 4.41.3

**The lyrics scroll now, they do not change places.** Fading a line out where
it stood and another in where it stood was still a change of pictures, not a
movement: the text simply swapped. The whole column rides instead — when the
singing moves on, every line slides up one step in a third of a second, the
newcomer arrives from below where it had been waiting, and the line at the
top rides out of the frame, fading as it goes. Standing still, everything
sits exactly where it always sat.

---

## 4.41.2

**A line change is a crossfade, not a flash.** The fades of the last release
had both ends start from nothing: the outgoing line vanished at once, the
incoming one rose from zero, and for a fraction of a second the frame stood
empty. A seat now keeps whoever left it for a breath, fading, while the
newcomer rises over them — and the seating for a frame is decided before a
single pixel is laid, so the handover happens within that frame rather than
one behind it. A ghost wears the layer of the seat it left, too: a queue line
leaves dim, because painting it as sung lit words nobody had reached.

**The darkness percent can simply be typed.** The knob grew from a stub to
nine rems, and a field beside it takes the number outright — an exact percent
could not be felt for on a slider that narrow. The two agree in both
directions, and nonsense in the field is clamped rather than obeyed.

---

## 4.41.1

**Torn words are re-laid by the program, not by you.** On a fast, dense vocal
— the first half of a NIN song, say — the model often places the line well
and mangles the words inside it: one word swallows seconds, the rest get
slivers no one could sing, a couple land out of order. That used to be an
evening of “≡ Even words”, line after line. A repair pass now catches the
torn lines right after alignment and re-lays their words by syllables inside
the line's own span. The edges stay; a held note is recognised for what it is
and left alone; a sane line is not touched. For an already-built song the
same medicine is one press away: select the rough half by dragging across it
and hit “≡ Even words” — it has always worked on many lines at once.

---

## 4.41.0

**Lines breathe instead of blinking.** Every line now takes its seat in the
frame with a quarter-second fade, and the song's last picture breathes out
instead of switching off. A single preview frame stays steady — fades belong
to the moving film.

**The clip becomes a slow slideshow.** A cover cut from a clip now takes six
frames spread across it, and the video turns them behind the lyrics with a
slow crossfade, timed by the song's own length. A plain picture stays a
single cover; the page keeps one cover either way.

**The whole song in one strip.** Above the timeline stands a minimap: the
marks, the kept lines, the quiet stretches, the window now on screen and the
playhead. A click jumps, a drag scrubs — on an eight-minute song the wheel
was a hike, and this is a step.

**The video file is a choice now.** MP4 export opens a small dialog — size,
frames per second, quality, and whether the opening runs — remembered
between songs. And overlapping lines on the timeline are all reachable: a
still second click on the top block dives to the line underneath.

---

## 4.40.2

**The pair holds until both are done.** The overlap rule watched only the
newer line's end — and when a long line contained a short one outright, the
short one vanished from its lower seat the moment its own end passed, mid-
pair. The pair now stands until the later of the two ends, whichever line
that is.

**And an evening of torture found three more.** With three voices sounding —
a lead running over a lead, a na-na-na on top — the first lead vanished
mid-word: the pair is now found among the leads, and the backing waits for a
free seat. A long line in the SIDE seat ran off the edge of the frame — its
base font sat below the shrink floor, so it could not even shrink; the side
seat wraps and shrinks now like the main one. A mangled record with words out
of order wrote UltraStar beats that ran backwards; they leave sorted. A
corrupt zip and a nonsense darkness value answer with a calm sentence instead
of a stack trace.

---

## 4.40.1

**The slack learned where the singer stands.** The little margin that keeps a
held note from being clipped at a kept line's edge could reach into the
singer's own first word — the original bled where only they belong. The slack
and the breath-bridge now stop dead wherever their line stands: the original
gets its note, the singer gets their word, and the boundary is theirs.

**And a cover comes by link.** The cover picker takes a pasted address next
to the files: the picture is fetched — thirty megabytes at most — and judged
by its bytes, not its name.

**And the sliders reach their ends.** On some browsers the voice knob was
drawn by the system, whose thumb never touches the edges — zero looked like
ten percent. The track is the program's own now, in both the editor and the
finished page: zero stands at the left end, a hundred at the right.

**The overlap stands as a pair.** A line that runs past the start of the
next one now keeps the main seat until the NEW line is finished — the newer
one sings from the smaller seat below, the way a duet stands — and nothing
jumps seats mid-line. And a quietly kept line says “sing along with the
original” beside itself in the frame; a full-voice one carries no caption —
the voice itself says whose line it is.

**How dark the backdrop is, is yours to set.** A cover with a bright streak
in it could swallow the not-yet-sung words whatever the fixed darkening did.
Next to the cover buttons stands a small 🌗 knob — zero to ninety-five
percent, sixty-six by default, the page and the video both obeying — so every
cover can be darkened exactly as far as its own brightness demands.

---

## 4.40.0

**The original can stay quietly — to be sung along with.** “♪ Original” walks
a circle now: one press leaves the line to the original at full voice, a
second holds it back to a guide — thirty-five percent, the same level as the
“instrumental + quiet vocal” mode — for the lines meant to be sung in unison
with the artist, and a third gives the line back to you. The page, the editor
and the MP4 all honour the level; the line's tag says which of the two it is.

**An overlapping line leaves when it is done.** A line whose last word dragged
past the start of the next one vanished from the video mid-word the moment
the next began. It now holds the main seat to its own end — the next line
waits below, in the queue, where it already stood.

**A long line wraps instead of shrinking.** A line too wide for the frame
used to shrink until it fit — down to letters read only from the front row.
It wraps onto a second row now, split between words and balanced, and the
sweep lights row after row; everything below yields to the taller line. The
font gives way only when even two rows cannot hold it.

**The cover is yours to change.** A song from a file on disk had nowhere to
get a cover, and one from a link had no way to swap it. “⛰ Cover” in the
editor takes any picture — or the clip itself: a frame is cut from a third of
the way in, past the black lead-in. One more press takes it away.

**And the original's own lines live inside the marks.** An intro sung by the
artist — its lines marked “♪ Original”, the stretch marked as holding no
words — used to be expelled from the stretch by the mark passes, and the kept
voice went with it: the intro fell silent. A kept line now stands wherever
the original sings, the marks notwithstanding, and the “♪” marks survive a
re-timing the way locks do.

**A held word is no longer chewed in half.** The ends of kept lines are the
model's guesses, and the voice they guard is real: between two “♪ Original”
lines the mute used to fall exactly where a note was held across the breath —
the sound dropped and came back mid-word. Kept stretches now carry a little
slack at the edges, and the breath between two kept lines stays kept — unless
your own line stands in it, which is exactly where the mute belongs. The
page, the editor and the MP4 follow the same rule.

---

## 4.39.0

**Slowed listening is gone.** It stretched the sound and kept the pitch — but
the stage lived at its own pace regardless, so the one thing it promised, a
slow look at the words as they light up, it did not deliver. A feature that
lies is worse than no feature: removed, together with its hidden players and
its speed menu. The scrub cursor and a click on any line do the same work,
honestly.

**The control bar holds its edges.** The play button and the clock stand on
the left edge, the voice knob on the right, the hint floats between — instead
of everything bunching in one corner of the row.

---

## 4.38.0

**The frame preview answers three and a half times faster.** Every “▣ Frame”
was painting its background from scratch — a gradient laid down pixel by
pixel in Python, or a cover blurred anew — and re-reading the renderer's own
file for good measure. The background is remembered now (and handed out as a
copy, since the render letters the song's name straight into it), the
gradient is drawn as a one-pixel column stretched wide — the same picture to
the last pixel — and the renderer is loaded once. Fifty milliseconds instead
of one hundred and eighty: scrubbing feels like scrubbing.

**Two holes closed before anyone fell in.** A word carrying braces or a
backslash — “{evil}” — would have broken every subtitle tag after it in an
exported .ass; such characters now leave as their harmless lookalikes. And a
packed song that claims to unpack into gigabytes is refused by its own
manifest before a byte lands on the disk.

---

## 4.37.0

**The timing leaves for other worlds.** Behind the new “⇪” in the editor:
an UltraStar file for the singing games — fifty-millisecond beats, a duet
part for the second voice, every note freestyle because nothing here measures
pitch and nothing will be invented — and .ass subtitles whose karaoke sweep
runs word by word in the project's own colours, the second voice in a style
of its own. “⇩ Pack” moved in there too, off the crowded shelf.

**The little things joined hands.** The lyrics search now answers in
“⇄ Other lyrics” as well, not only while building — found records stand above
the file list, and a timed one is taken with its pegs. The “▣ Frame” follows
a seek and steps by arrows. A .karaoke.zip dropped into the window opens
itself. And the long explanations on the build screen folded into hover
tooltips behind a small “?” — the form got shorter, the words are one hover
away, and not a letter of any song was touched.

---

## 4.36.0

**A found text brings its own timing.** The lyrics library answers with the
time of every line — and until now those times were stripped off and the model
left to rediscover them, badly. A record that has them shows “comes with a
timing”, and “Take it with the timing” keeps them as pegs: sparse ones — the
first line, every real pause, one in a few lines — so the model still lays out
the words between them, and a record made from another master cannot bake its
drift into the whole song. “Words only” is still there.

**The heard silences become marks with one press.** The program already finds
the stretches where nobody sings and shows them in the summary; turning them
into “no words here” marks still meant drawing each one with the mouse. Every
stretch now carries a “＋”, and “mark them all” takes the rest — undoable,
saved, drawn on the waveform at once.

**A frame of the clip, without rendering the clip.** “▣ Frame” next to the
timeline shows what the video will hold at the playhead — the very same
drawing code, one frame, a moment instead of minutes. The opening card can be
looked at the same way.

**A song travels in one file.** “⇩ Pack” puts the whole project — the timing,
the audio, the cover — into one `.karaoke.zip` next to the song it was made
from; “Open a packed song” on the first screen puts it back, the same song, on
any computer. Finished pages and clips are not packed: they are made again in
one press and weigh more than everything else together.

**The name is asked for up front.** The build screen has fields for the song
and the artist — filled from the link or from the file's name, and standing
above whatever a lyrics file might say once they are typed by hand.

**And it all runs cooler.** The editor repainted its waveform sixty times a
second whether anything moved or not — a paused window warmed the room. It now
repaints only when the picture would differ. The video renderer stopped
lettering the song's name onto each of thousands of frames — it is painted
into the background once — and stopped throwing away every typeset line when
its shelf filled: a twenty-second 1080p clip renders about a sixth faster.

---

## 4.35.0

**The song is called what you call it.** The name in the corner of the video —
the same one on the opening card, on the finished page and on the exported
files — was whatever the audio file happened to be called, or whatever stood
in the lyrics header. Click it in the editor and type: the song, the artist,
Enter. A name given by hand is remembered as given: re-reading a lyrics file
with a “title:” of its own no longer renames the song behind your back.

**The count-in shows the words instead of hiding them.** The figure filled the
frame, and the first line appeared only when the music did — too late to read
it. The count now stands small in the seat where the singing will be, with the
first lines already under it, laid out exactly as they will be when the song
starts, so nothing jumps at the moment it does.

---

## 4.34.0

**A clip opens instead of starting.** The song's name stands large for three
seconds, then a count of three, and only then the music — which waits exactly
as long, so nobody is caught mid-breath with the first line already gone. A
song with no name is simply counted in; `--no-intro` starts with the music as
before, and a sample cut from the middle of a song never gets the card.

**The backing no longer keeps the ending to itself.** The stage was cleared by
asking the list of lines which one was last — and the last sound is not always
the last line: a na-na-na is written under the lead it answers. So the backing
hung alone at the end of the song, and a lead still singing over a backing that
had finished could be blanked mid-word. The song now ends when its last sound
does, whichever line held it.

---

## 4.33.1

**The dots in the video count a wait, and nothing else.** Three grey dots sat
under every line being sung, with the next line already spelled out in the
queue below them — decoration where a cue was meant. They now appear only when
the singing has stopped and the pause is long enough to be worth counting, and
they light up as the line comes in. Between lines that follow each other, the
frame is clean.

**A song that has ended looks ended.** The last line used to hang lit through
the whole outro, as if the picture had frozen on it. It stays five seconds —
long enough to let go of the note — and then the stage empties; on a long tail
the strip at the top keeps saying how much of the recording is left. Both rules
are measured in the rendered frames themselves, not in the code that draws
them.

**And it says it in the song's language.** “INTRO”, “until”, “END” came out
in whatever language the program itself was speaking — English words hanging
over a Russian song. The countdown now takes its language from the lyrics it
stands among; the log at the keyboard keeps speaking the program's, because
that one is read by a person, not by the frame.

---

## 4.33.0

**The clip stays in the picture.** A song brought in by link now keeps the
clip's cover: a checkbox appears next to the found lyrics, and with it on, the
cover lies behind the words — on the page and in the video alike — blurred and
dimmed so the text stays the brightest thing in the frame. Untick it and the
woven gradient is back. A song from a file on disk is untouched: no cover, no
checkbox. And this one was tested down to the pixels: a build with a plain red
cover must actually show red through the blur, or the suite goes red itself —
a payload field nobody can see is not a feature.

**The song's name in the video grew up.** It sat in the corner in the caption
size, small enough to read only from the front row — and the countdown pill
could lean against it. The name now has a font of its own, half again larger,
a long "Title — Artist" trims itself with an ellipsis instead of running off
the frame, and the pill moved down a step: the two never share a pixel row,
which is now a test, not a hope.

---

## 4.32.0

**The marks are law now, not a wish.** The gentler passes moved lines out of a
marked stretch only where there was room, and left them inside with a note when
the neighbours pressed right against the hole — which is exactly where a
screamed song puts them. A final pass now forces out whatever still overlaps a
mark: onto the singing at a sung pace where there is room, and squeezed in
tight right after the mark where there is none — cramped on purpose, with a
loud note in the log. Better a tight line in the right place than words over
the stretch you marked. The same guarantee runs in both engines, in partial
re-timing and in “↹ Trim by the marks”. The crack lines used to slip through —
starting a hair before the hole, too little left to trim — is closed.

**An article no longer hides under its neighbour.** The aligner gives a short
word no time of its own: “A” and “chilling” started at the same instant, and
the small chip vanished under the big one — it could not even be grabbed. The
chips are laid in a ladder now: every word gets a visible sliver of its own,
trimmed short of the next. The times underneath stay exactly as they are.

**“≡ Even words”.** The line's edges are right — set by hand, perhaps locked —
and the words inside are a mess. The new button re-lays the words of the
selected lines by syllables within each line's own span; the edges stay put.
It works on locked lines too: the lock guards against the model, not against
you.

**The countdown is the singer's cue, so it aims at the singer's line.** The
dots and the wait pill — in the video, on the page and in the studio — used to
count down to whatever line came next, and sometimes that was the backing:
“words in 10 s… to (Na-na-na)”. All three skip backing lines now and count to
the next lead, and the video's queue of coming lines is built from the leads
the same way.

**A duet is drawn as a duet.** On the studio stage the second voice sounding
with the first used to sit unlit — one line of the two being sung. Both light
up now, and the words of both fill as they are sung. In the video the two full-
size rows used to collide with the countdown dots; the lead now sits exactly
where a solo line sits, and the backing is smaller, right-aligned, tucked under
it like a reply — with its own highlight, and the dots move out of its way.
And when the lead ends while the na-na-na carries on, the backing keeps that
side seat instead of being promoted to the main one, full size, in the way of
the lead text: the main seat stays empty, the queue below points at the next
lead line.

**The aligner never hears the backing text.** Alignment is linear: asked to
place the na-na-na BETWEEN the lead lines, it dragged whole choruses into
silence it could hear perfectly well was empty, just to make room. The model
is now given the lead lines alone — they anchor cleanly — and the backing is
placed by rule: a tail split off a lead line lies over that line, a duet; a
standalone backing line takes the gap after its lead, at a sung pace. Both are
one drag away from anywhere better, and the log counts what was kept from the
model and what was placed.

**Two people singing at once is a duet, not a defect.** The na-na-na behind a
lead line is meant to overlap it: lines of different voices are no longer
pulled apart by the repairs, and the Check panel no longer flags them. And a
backing tail written on the lead line — “try too hard (Na-na-na)” — is split
off into a line of its own, second voice, so the lead singer is not shown the
na-na-na as their own words. Brackets in the middle of a line stay put; `(x2)`
is still a repeat, `(Chorus)` is still a heading.

**The video frame reads forward, not back.** The line already sung is gone —
the eye never returns to it. The current line sits just above centre, the next
waits under it, and the one after that shows fainter still: a queue, not a
history.

**The Check panel scrolls, and warnings can be dismissed.** The list refused
to shrink below its content, grew past the panel and was clipped — which read
as “the scrolling is broken” and showed one warning of many. And every warning
now carries a ✕, the way a spell-checker has “ignore”: dismissed for that
line, keyed to its words rather than its number, so it survives splits,
renumbering and reopening. A link under the list brings them all back.

**The video's countdown is readable, and its dots count properly.** The pill —
“words in N seconds” — is half again bigger and brighter, still in the top
strip where no lyrics are ever drawn, still gone the moment singing starts.
The three dots before a line now divide the wait into three equal thirds of
itself — a 2.6-second pause no longer starves the first dot — and the video and
the player share one formula: the video's own arithmetic used to jump straight
to two, and the first dot never showed alone.

**Slowed listening, same pitch.** A speed switch by the Voice slider — 1×,
0.75×, 0.5× — for catching mistakes while editing: time stretches, the pitch
stays. Playback only: the song, the timing and the video are untouched. At 1×
the sample-precise engine runs exactly as before.

**Dots on a scream no longer break the line's rhythm.** Editing a line's text
used to lay every word out anew — appending “...” to a long scream threw away
exactly the rhythm already set. Words that stayed the same words now keep their
own times; only the changed stretch is laid out, in the gap it occupies.
Fixing one word in the middle leaves its neighbours untouched.

**“⧉ Paste rhythm” came back to life.** The paste-the-text button on the build
screen was given the same id the editor's paste-rhythm button already had; the
browser answers such a name with the first element it finds, every handler
landed on the invisible one, and the visible button spent three versions grey
with no error anywhere. The ids are apart now, and a check fails on any
duplicated id in either page — the whole class of this bug, not this one case.

**A press selects the line that was pressed.** The stage keeps scrolling while
the song plays: by the time the browser assembled a click, the line under the
cursor was the neighbour of the one actually pressed. Selection now happens on
the press itself.

**An article is grabbable again.** The aligner collapses a short word onto its
neighbour — “A” and “chilling” at the same instant, the article with no time of
its own. It now gets its sliver back, just before the neighbour, where it was
sung; a chain of squeezed words unfolds one by one. And no chip on the word
lane is drawn thinner than twelve pixels — visible but ungrabbable is not
visible enough.

**The whole layout, always in sight.** A thin band along the bottom of the
waveform now shows the words of every line, neighbouring lines in alternating
shades — the timeline can be watched without selecting anything. The selected
line's own lane stays the place to grab and drag.

---

## 4.31.0

**The log now says how much is left.** The alignment used to report only how
long it had been running: its own counter was switched off by the way we called
the library, and the progress it handed us was zero from beginning to end. Now
the line reads “running 2:30, done 34%, about 4:50 left” — the remainder
measured at this machine's own pace, and not shown at all when the end is
seconds away. The countdown to the next line, in the studio and in the video,
now waits for a real pause: ten seconds, not five — anything shorter is a
breath between lines.

**Word chips no longer lie on each other.** A sung word runs into the next one
more often than not, and drawn by their durations the chips overlapped at any
zoom. A chip now stops where the next word begins — the times themselves are
untouched. “⤢ Fit the line” zooms the timeline to the selected line in one
press, and dragging an edge with **Alt** held squeezes the whole line instead
of stretching its outermost word — which is what narrowing a line that
swallowed an interlude actually means. When an edge meets the outermost word,
the window now says so instead of silently refusing.

**The marks now push back.** A line next to a marked stretch used to reach
across it — the aligner has to end a line somewhere — and five words lasted a
minute and a half. Line spans are now cut back out of the marked stretches
during the timing, and “↹ Trim by the marks” does the same to an already built
song, moving lines that sit wholly inside a hole onto the singing that follows.
The MP4 keeps the original voice on the marked stretches too, as the page
already did. And a partial re-timing heeds the marks inside its window — a
vocalise does not stop being one because only four lines are retimed around it.

**“This part is sung from about here.”** A time in square brackets before a
line — `[2:27] Remember this day` — is a peg, not a timing: the song is aligned
stretch by stretch between pegs, and the model never hears the audio beyond
them, so a line cannot wander into a vocalise three minutes away. A locked line
works as a peg on re-timing. Pegs out of order are dropped with a word in the
log; without stable-ts each stretch is laid out by loudness, still inside its
own pegs, and the engine is named honestly.

**The window is watched for layout accidents now.** A suite drives the studio
through five window sizes and three screens and fails on anything overlapping,
anything running off the edge, and any control squeezed to a sliver — the two
layout bugs that reached a person did so because nothing was looking.

---

## 4.30.0

**A vocalise is heard, not muted.** “♪ Original” keeps the recorded voice on a
line — but a vocalise has no lines at all, so there was nothing to put the mark
on, and the karaoke came out with a hole exactly where the song is loudest. A
stretch marked as holding no words now keeps the original voice in the backing:
in the studio, in the standalone page and in the MP4. The switch beside the
marks turns it off, for when you mean to sing it yourself. Marks are saved as
soon as they are made now, like any other edit, instead of waiting for a
re-timing.

**A song keeps the name it came with.** The file a link lands in is called
something that survives every file system — `Forevermore_[kBjKqBvbbjM]` — and
that name was showing up as the title of the song. The real name and artist now
travel with the download; a `title:` line in the lyrics file still outranks
both, being the most deliberate of the three.

**Cutting a line in two, and joining two into one.** The most ordinary
correction there is — a long line sung in two breaths, two short ones that are
really one phrase — used to mean editing the file on disk and timing the whole
song again. “⤸ Split” cuts the selected line where the singing pauses longest
inside it; “⤹ Join” puts it back together with the next. Neither times anything
again: the words keep the times they had, only the grouping changes. Joining
across the start of a new part of the song is refused — it would hide the
heading.

---

## 4.29.0

**Marking the wordless stretches with the mouse.** Reading seconds off a player
and typing them into a field was the step people gave up on. “✂ No words here”
on the timeline: press and drag over a vocalise, click a mark to take it off.
The field and the mouse are one thing underneath — type and the marks appear on
the waveform, drag and they appear in the field.

**A few lines can be timed again on their own.** Select what went wrong, press
“↻ These lines”, and the model is shown only the stretch between their timed
neighbours. On a nine-minute song that is seconds instead of minutes, and
nothing else in the song moves.

**A lock on a line.** What you put right by hand outweighs anything a model
returns for it, and re-timing used to throw all of it away. Locked lines are
left alone by both kinds of re-timing. Re-split the lyrics into a different
number of lines and the locks are dropped with a word in the log, because line
seven is then no longer the same line seven.

**What the model was unsure of is now visible.** The probability it returns per
word was averaged into one line of the log and thrown away. It is now kept with
the words, a line is judged by its least certain one, and lines far below their
neighbours are drawn with a dashed border and named in the panel. The measure
is the song itself, so a scream and a whisper are judged each on their own
terms; a song where everything sits equally low is not painted amber from end
to end.

**Two more models.** `large-v3-turbo` in the list — nearly `large-v3` at about
the speed of `medium`, 1.6 GB instead of 3. And “separate finely” next to the
instrumental switch: four passes instead of one, a cleaner voice, and the
timing is made from that voice.

**Silence, asked as a question that can be answered.** Whether a line sits where
nobody sings used to be measured against the song's own middle — which called a
whispered verse silent and a song loud from end to end silent throughout. For
moving lines the question is narrower: is there any voice at all? A hundredth
of the loudest moment answers it, and a whisper stands well above that.

**A way to measure instead of guessing.** `app/tools/bench.py` prints one row
per way of handing a song to the aligner — mix, separated voice, levelled voice
— with the segments it gave up on, its confidence, and the share of lines left
in a pile. No reference timing is needed, so it works on your own music.

---

## 4.28.0

**The checks now walk the hard road themselves.** Three of them were added
where there was nothing: a whole song is built with wordless stretches marked
and the lines are looked at afterwards — both when the marks come from the
field and when they come from the lyrics file; a running studio is asked to
re-time and must keep the model the song was built with, must heed the marks
and must shrug off nonsense typed into the field; and a real browser fills the
field, builds the song, checks that nothing landed on the marked stretch, that
the marks come back into the editor, and that the labels keep off the colour
swatches at three window widths. The old checks that read the source code
instead of running it are gone — they were a stand-in for these.

**The voice is levelled out before the aligner hears it.** A screamed vocal is
the widest dynamic there is — a shout point-blank, then a strangled rasp — and
the quiet half never reached the model at all. The separated voice now goes
through a levelling pass on its way to the aligner: pitch and time are
untouched, so every timing still means exactly what it says, and only what the
model hears is changed. Measured on a nine-minute deathcore track with its real
lyrics: segments the aligner gave up on 27 → 22 → 19 for mix → separated voice
→ levelled voice, and confidence 0.114 → 0.125 → 0.138.

**A re-time no longer quietly swaps the model.** A song built with medium came
back timed with small: the re-timing path had a default of its own and never
looked at what the song was made with. The model is now written down with the
song, re-timing uses it, and the question that asks whether to re-time names it
outright.

**A label printed itself over the colour swatches.** In a narrow window the
“background and text” caption was squeezed into the swatches next to it instead
of the row wrapping. It cannot be squeezed any more.

**“There are no words here” — now you can say it, and it is heeded.** A
vocalise, a scream with nothing to write down, a hummed intro: all of it is
voice, nothing measurable tells it from a sung line, and the timing crawled onto
it. The window now has a field for such stretches — `0:00-0:42, 3:10-3:50` —
under the model and the language, and the same field sits in the editor next to
“Re-time”, where the timeline is already in front of you. The same can be
written in the lyrics file, as a heading carrying a time range: `[Guitar solo
3:10-3:50]`, `[нет текста 1:02-1:40]`, or the bare `[6:20-7:05]` — the heading
still names the part of the song.

Those stretches are cut out of the audio the aligner is given, so there is
nothing there to lay words on, and afterwards the repairs treat them as silence:
a line that landed inside is moved onto real singing between its neighbours. It
is a “keep off” and nothing more — marking one solo claims no words for the rest
of the song. The marks are saved with the song, so the next re-time starts from
them.

**Lines laid where nobody sings are moved onto the singing.** The aligner has
to put every word somewhere, and over an interlude or a solo it puts them on
the music: the line looks timed, the karaoke shows words, and no voice is
there. On the separated vocal such a stretch is real silence — so after the
timing the program now checks every line against that silence, and a run of
lines lying wholly inside it is moved to the nearest stretch of actual singing
between its timed neighbours, at a sung pace, pressed against the line that
follows. When there is no singing between the neighbours at all, the lines stay
and the log says so: perhaps this recording simply does not sing them. On a
plain mix, with no separation, nothing is moved — a quiet verse must not be
mistaken for an interlude. For screamed and growled vocal, where the aligner
loses its footing most, this is the difference between words over a guitar solo
and words where the voice is.

**A song from a link.** Under the field for the song file there is now a field
for a link: paste one, press “Take the sound”, and the audio is pulled out of
the video and put where a dropped file goes. The work is done by `yt-dlp` —
a few megabytes, no neural nets, offered by the setup as step six. Without it
the window says so before a link is pasted, and choosing a file still works.
When a download fails — a private video, a dead link, nothing at that address
— what the downloader itself said is shown, and the field stays open for
another link.

**A link to nowhere, in the repository since the first day.** `app/node_modules`
was committed as a symlink pointing into a temporary folder on the machine
that made it — so everyone who cloned got a dangling link where the test
packages should go. It is gone, and `.gitignore` now names the folder in the
form that catches a symlink too. Nothing a person runs was affected; the
checks were.

**A missing jsdom looked exactly like success.** When the package could not be
found, the window and page suites were skipped and the run still ended with
“nothing failed”. That is how half the suite went quiet for a whole run here.
Where the whole set is asked for — `KARAOKE_REQUIRE_BROWSER=1`, which is how it
runs on the server — a missing jsdom is now a failure that says so.

**The name of the ffmpeg file was enough to stop a download.** yt-dlp is handed
a folder and looks inside it for “ffmpeg” and “ffprobe”. The copy pip installs
— imageio-ffmpeg, which the setup offers when the system has none — is a single
file named after its platform and version, with no ffprobe beside it at all.
Given that folder, yt-dlp fell over an empty path and said “expected str,
bytes or os.PathLike object, not NoneType”, and the window passed that on as
the reason the song had not downloaded. Now it is handed a folder where those
two names really do point at whatever was found, and when there is no ffprobe
anywhere the video simply comes down whole — the program takes the sound out of
it afterwards, as it always did. A real ffmpeg, which brings ffprobe with it,
is now preferred over the pip copy.

**Where the program looks for what it did not install.** A window opened by
double-clicking inherits a bare `PATH`: Homebrew is not in it, and neither is
the folder pip writes commands into — though the person has both and both work
in a terminal. On macOS `pip install yt-dlp` puts the command in
`~/Library/Python/3.x/bin`, which nothing on that list knows about. ffmpeg and
yt-dlp are now looked for in those usual places as well, so “not installed” is
said only when it is true.

**“expected str, bytes or os.PathLike object, not NoneType”.** A fault of ours
wearing the clothes of an answer about the song. Two places asked a Python that
cannot say where it lives for its own folder, and `os.path.dirname(None)` is
not a missing file — it is a crash. Both are guarded, the message now says what
kind of error it was, and the window points at `projects/last-error.txt`, where
the whole of it is written.

**“The page needs to be reloaded” is not about your ffmpeg.** YouTube answers a
player client it does not care for with a refusal that says nothing about the
video, and that refusal was handed straight to the person as the answer. The
same link goes through as another client, so it is now asked again — android,
then ios, then tv — before anyone is told it did not work. A refusal that is
about the video (“this video is private”) is not asked again: it would only
make you wait four times for one answer. If every client is turned away, the
message says what is left to do — `pip install -U yt-dlp`, and cookies for a
video that asks you to sign in, through the new `yt-dlp-args` in
`settings.ini`.

**Lyrics pasted into the field made for a path came out as one long run.** A
one-line field cannot hold line breaks, and a song copied off a lyrics site
arrived as a single line — with the site's own footer stuck to the end of it. A
paste that is plainly the words themselves now goes to the box below, whole,
and is saved as a text file from there. A link pasted into the field for the
song file moves down to the field for links by itself.

**And the words to go with it.** Once the sound is here, the lyrics are looked
for by the name of the song on [LRCLIB](https://lrclib.net), an open library
that needs neither key nor account. What comes back is a suggestion and is
treated as one: each says who sings it, how many lines it has and where it came
from, and it lands in a box to be read first. A wrong text lays wrong lines
over the whole song, so nothing is ever taken silently.

**How to update, in writing.** Taking the repository with `git clone` was
mentioned as a way past the macOS refusal, and there it stopped: nothing said
what an update does to the songs already made, so nobody had a reason to trust
`git pull` with them. All three documents now say it — one command, and
`projects/` and `app/settings.ini` are outside the repository and are not
touched — along with how to carry songs over from a folder that came from a
ZIP, and what to do when a pull refuses because a file was edited.

**The lyrics now have three ways in.** A file, as before; a text that was found;
or the words pasted into the window by hand — typed, corrected, taken from
anywhere. Pasted text is written into `projects/_incoming` as a `.txt`, so
everything downstream treats it exactly like a file of your own.

**A job that fell over let you out.** The progress screen had one way to end
badly: it kept spinning, with no “← To the list”. The job's own error came back
through the reader that treats an error as a broken request, which stopped the
polling on the very answer that had to be shown. Now the failure is named, the
reason stays in the log, and the way back is there.

---

## 4.27.1

**A license.** [LICENSE](LICENSE) — MIT. Without one, an open repository says
“all rights reserved” by default, whatever the README promises.

**Your settings are yours.** `app/settings.ini` has left the repository:
`app/settings.example.ini` is the documented reference, and the first run of
`Install.bat` / `install.command` makes your copy from it. An update can no
longer overwrite what you chose, and with no settings file at all the program
uses its defaults.

**A dozen lines dumped at one instant, and the karaoke leapt through half the
lyrics.** On a quiet intro or a whispered verse Whisper finds nothing to hold on
to and returns a whole stretch of text at the single moment where it did hear
something — seven lines inside a fifth of a second. The program now sees such a
pile and spreads it out, at a sung pace, against the line that follows it. It
does not fill the whole gap: a gap may hold a breath, an intro or humming, and
covering that with lyrics claims as singing what is not sung. Lines that are
timed right are never touched, and a pile with nowhere to go — when the
neighbouring lines contradict each other — is left alone and named in the log:
which lines, at what second, and what to do about them.

**What the aligner mutters now lands in the log.** stable-ts says the single
most useful thing it has to say — “12/34 segments failed to align” — through a
Python warning, into a console window nobody is watching. It is now written to
the job log along with what it means: that many lines got no timing of their own
and will come out piled in one spot.

**An error no longer flashes past.** When a job falls over, the whole traceback
is written to `projects/last-error.txt` with the time, and the log says where it
is. One line of it was always shown; the rest used to scroll away.

**macOS refuses the first double-click, and the documentation now says why.**
A file that came from the internet carries a mark, and `studio.command` is not
signed by a paid Apple developer account — so the first attempt to open it is
answered with “the file cannot be checked for malware”. Nothing was scanned and
nothing was found, but it reads like a virus report, and there was not a word
about it in the README. Now all three documents a newcomer opens carry the
three ways through: starting it from the Terminal, letting the file through in
Privacy & Security, or taking the mark off the folder with `xattr`. Taking the
repository with `git clone` instead of a ZIP avoids the whole thing.

**The setup on macOS stopped after every single step.** `install.command`
installs ffmpeg with pip and then, in the same breath, asks Python whether it is
there. On macOS pip puts the package into the user's own site-packages — a
folder that often did not exist when the window opened, so it is not on the
search path and what was installed a second ago is invisible. The setup decided
the install had failed and gave up; the next step was reachable only by starting
the whole thing again, and then the same thing happened there. Each package is
now checked by a fresh Python, which reads the folders as they are now, and the
search path is refreshed after every install. On Windows nothing changed —
there pip writes where the program is already looking.

**One unfinished step no longer ends the setup.** Whatever could not be done is
named once at the end, and the steps below it — down to making your
`settings.ini` — run anyway. The advice now fits the machine it is printed on:
macOS used to be told `winget install Gyan.FFmpeg`, a command that exists only
on Windows, and the closing lines pointed at `.bat` files that a Mac cannot
open.

**Words with no audio under them are no longer laid over wordless singing.**
When a piled-up run repeats, word for word, a block of lines that IS timed, the
program leaves it where it is instead of spreading it: there is a reason no
audio was found for it, and a stretch of humming or vocalise is not a place to
paint lyrics over. Which of the two reasons it is, is told apart by the rest of
the song — either the lyrics file holds one repetition more than is sung, or the
aligner locked onto the wrong repetition and the whole timing is out by a pass.
Both are named in the log, with what to do about them.

**A stretch of song with no lyrics under it is now reported.** If the text ends
at 1:50 while the singing goes on to 2:50, the alignment did not stumble on a
line, it lost its place — and the log says so, along with the way out: re-time
with the loudness engine, which spreads the lines over the whole song.

**A song in another language kept the language of the previous one.**
The window remembered the language picked last time and used it for the next
song. If you had ever chosen “русский” by hand, an English text was handed to
Whisper as Russian — and the timing came out badly split, with no hint as to
why. Now every song starts from **“detect from the text”**; a choice made for
one song no longer decides the next. Re-timing (“Time it again”) reads the
language off the text too, instead of a remembered one.

**The report warns when the alphabet does not match.** If you do pick a
language by hand and the lyrics are not even written in its alphabet, the
report says so before the long part starts: *“The lyrics are not written in the
alphabet of the chosen language (русский). They look like english.”* Telling
alphabets apart is never a guess, so this never cries wolf about a genuinely
mixed text.

**English words are split into syllables properly.** Word length is what
spreads the time inside a line, and three endings used to lie: “lit-tle” and
“peo-ple” counted as one syllable, “walked” and “danced” as two, “makes” as
two. An English verse now lands much closer to how it is actually sung.

## 4.27.0 — first public version

The program as published: the Studio window, the standalone HTML page, the MP4
render, two voices, your own instrumental, the container, and the checks.

Fixed on the way to publishing:

- **The voice did not match a backing track of your own.** An official
  instrumental is mastered differently from the one under the vocal, so
  subtracting it with a single volume level left part of the arrangement in the
  “voice”. It is now subtracted per frequency band, over the spans without
  singing.
- **Both voices came out the same colour in the finished MP4** — the render
  used hard-coded colours instead of the ones from the page.
- **Pasted lines replaced the target instead of being inserted.** Now they are
  always inserted below the selection, and nothing is overwritten.
- **Several lines could not be selected at all** — dragging, Shift+click and
  Ctrl+click did nothing. Selection marks also vanished whenever the timeline
  was rebuilt.
- **Cyrillic names in file paths.** Song folders and finished files are named in
  Latin letters now (“Мамины Усы” → `maminy-usy`), so they open the same way on
  any system.
- **Nothing showed during the intro and the long interludes** — the slider moved
  and the screen stayed empty. A countdown to the next line now runs at the top,
  both in the Studio and in the video. Short pauses are not counted.
- **No report before the long part**, and none before the video render either.
- **Small type** everywhere: sizes are now in `rem` with `clamp`, so labels grow
  with the window and stay readable on a big screen.
- **A silent skip of the browser checks looked green.** With
  `KARAOKE_REQUIRE_BROWSER=1` it is a failure — the point of running them on a
  server is running them all.

## The language of the program

Published in English: the window, the finished page, the messages, the
documentation, the comments in the code and the checks. Russian is a switch in
the header (RU / EN) and [README.ru.md](README.ru.md); any other language is a
file in `app/kstudio/messages/`, with no code to edit.

## Checks

Every push runs the whole suite on a clean Ubuntu — see
[tests.yml](.github/workflows/tests.yml). Two differences from a working machine
were caught the hard way and are now covered: a runner has **no neural nets
installed** and an **empty model cache**, and the checks must be honest in both
worlds.
 A speed switch by the Voice slider — 1×,
0.75×, 0.5× — for catching mistakes while editing: time stretches, the pitch
stays. Playback only: the song, the timing and the video are untouched. At 1×
the sample-precise engine runs exactly as before.

**Dots on a scream no longer break the line's rhythm.** Editing a line's text
used to lay every word out anew — appending “...” to a long scream threw away
exactly the rhythm already set. Words that stayed the same words now keep their
own times; only the changed stretch is laid out, in the gap it occupies.
Fixing one word in the middle leaves its neighbours untouched.

**“⧉ Paste rhythm” came back to life.** The paste-the-text button on the build
screen was given the same id the editor's paste-rhythm button already had; the
browser answers such a name with the first element it finds, every handler
landed on the invisible one, and the visible button spent three versions grey
with no error anywhere. The ids are apart now, and a check fails on any
duplicated id in either page — the whole class of this bug, not this one case.

**A press selects the line that was pressed.** The stage keeps scrolling while
the song plays: by the time the browser assembled a click, the line under the
cursor was the neighbour of the one actually pressed. Selection now happens on
the press itself.

**An article is grabbable again.** The aligner collapses a short word onto its
neighbour — “A” and “chilling” at the same instant, the article with no time of
its own. It now gets its sliver back, just before the neighbour, where it was
sung; a chain of squeezed words unfolds one by one. And no chip on the word
lane is drawn thinner than twelve pixels — visible but ungrabbable is not
visible enough.

**The whole layout, always in sight.** A thin band along the bottom of the
waveform now shows the words of every line, neighbouring lines in alternating
shades — the timeline can be watched without selecting anything. The selected
line's own lane stays the place to grab and drag.

---

