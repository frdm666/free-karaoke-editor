# Karaoke Studio

[![tests](https://github.com/frdm666/free-karaoke-editor/actions/workflows/tests.yml/badge.svg)](https://github.com/frdm666/free-karaoke-editor/actions/workflows/tests.yml)

**A song + its lyrics → one offline HTML page.** The lyrics scroll, every word
lights up as it is sung, a slider brings the original voice back, and the whole
thing is a single file you can open by double-clicking — no internet, no
account, no subscription.

*По-русски: [README.ru.md](README.ru.md)* · *what changed: [CHANGELOG.md](CHANGELOG.md)*

![Karaoke Studio: the editor with the lyrics stage, the summary and the timeline](app/docs/studio.png)

| | |
|---|---|
| **Timing** | word-by-word, by Whisper (`stable-ts`) — or instantly by loudness |
| **Instrumental** | separated with Demucs, or use the artist's own — the voice is then extracted per frequency band |
| **Editing** | a window where lines and single words are dragged into place; every change saves itself |
| **Two voices** | a lead and a backing part, their own colours, two lanes, simultaneous lines side by side |
| **Output** | one standalone HTML, an `.lrc`, or an MP4 for YouTube |
| **Languages** | interface in English and Russian, lyrics in 14 |

## Start in three steps

1. Install Python 3.8+ from <https://python.org> (on Windows tick
   **“Add Python to PATH”**).
2. Run **`Install.bat`** (Windows) or **`install.command`** (macOS) — it checks
   ffmpeg and installs the Python libraries.
3. Run **`Studio.bat`** / **`studio.command`**, drop a song and a lyrics file
   into the window, press **Build**.

From the command line, without the window:

```bash
python app/karaoke.py song.mp3 lyrics.txt
```

---

## What you need

* Python 3.8 or newer — <https://python.org>
  (on Windows tick **“Add Python to PATH”** during installation)
* ffmpeg — installed for you by `Install.bat` / `install.command`

Everything else the setup script offers to install: `stable-ts` for word-level
timing, `demucs` for the instrumental, `pillow` for the MP4 render.

No `.exe` bundle is shipped on purpose: the program should work on macOS the
same way it works on Windows, and the source has to stay readable — that is the
point of publishing it.

## First run

| Windows | macOS / Linux |
|---|---|
| `Install.bat` | `install.command` (or `python3 app/tools/setup_check.py`) |
| `Studio.bat` | `studio.command` (or `python3 app/studio.py`) |
| `Make-karaoke.bat` — drag a song and lyrics onto it | `make-karaoke.command` |
| `Make-video.bat` — drag a built page onto it | `python3 app/tools/video.py page.html` |

Songs live in `projects/`. The timing is saved to disk as you edit; nothing is
rebuilt.

## macOS: “the file cannot be checked for malware”

The first double-click on `studio.command` or `install.command` is refused by
macOS. Nothing was scanned and nothing was found: a file that came from the
internet carries a mark, this one is not signed by a paid Apple developer
account, and that is the whole message. The script is twenty readable lines —
it looks for `python3` and starts `app/studio.py`.

Any one of these is enough:

* **Start it from the Terminal** — the mark stops double-clicks, not commands:

  ```bash
  cd ~/Downloads/karaoke && python3 app/studio.py
  ```

  (type `cd ` and drag the folder into the Terminal window to get the path)

* **Let the file through once.** System Settings → Privacy & Security →
  scroll to the bottom, where the blocked file is named → **Open Anyway**. On
  macOS 14 and older: Control-click the file → **Open** → **Open**.

* **Take the mark off the whole folder.** The second command puts back the
  right to run, which unpacking with Finder often drops:

  ```bash
  xattr -dr com.apple.quarantine ~/Downloads/karaoke
  chmod +x ~/Downloads/karaoke/*.command
  ```

Cloning instead of downloading the ZIP avoids all of it — files that arrive
through git are never marked, updates included:

```bash
git clone https://github.com/frdm666/free-karaoke-editor.git
```

## Updating

Taken with `git clone` once, the program updates with one command afterwards:

```bash
cd ~/Documents/karaoke && git pull
```

Nothing of yours is touched by it. The songs — `projects/`, with the timings
and the finished pages — and your `app/settings.ini` are not in the repository
at all: an update replaces the program and the documentation and never looks at
those two. Files that arrive through git carry no quarantine mark either, so
macOS does not have to be talked round again after every update.

Coming from a downloaded ZIP that already has songs in it: clone next to it,
carry the two things across, and the old folder can go.

```bash
cp -R ~/Downloads/karaoke/projects/. ~/Documents/karaoke/projects/
```

```bash
cp ~/Downloads/karaoke/app/settings.ini ~/Documents/karaoke/app/settings.ini
```

Two things people trip over:

* `git pull` refuses when a file of the program has been edited.
  `git checkout -- <file>` puts that one back, `git reset --hard origin/main`
  puts all of them back. Your songs and settings sit outside the repository and
  are not affected by either.
* When an update brings a new dependency — `yt-dlp` for links did — run the
  setup once more: `python3 app/tools/setup_check.py`. It skips whatever is
  already installed.

## What is in the folder

```
Install.bat  install.command    set up (once)
Studio.bat   studio.command     open the program window
README.md    README.ru.md       this text (English / Russian)
CHANGELOG.md CHANGELOG.ru.md    what changed, newest first
projects/                       your songs
app/                            the program itself
```

Nothing else sits in the root. Inside `app/`: the code, `settings.example.ini`,
`START-HERE.txt`, the server notes, the tests, and `Make-karaoke.bat` /
`Make-video.bat` for people who like dragging files from the file manager.
Songs live in `projects/` and are left alone by updates — only the `app` folder
is replaced.

Song folders are named in plain Latin letters — a name in any other alphabet
is transliterated — so they open the same way on any system. The finished HTML
and MP4 follow the same rule.

## A song from a link

Next to the field for the song file there is a field for a link. Paste one,
press **Take the sound**, and the audio is pulled out of the video and put next
to the projects — the same place a dropped file lands. It needs `yt-dlp`:

```bash
pip install yt-dlp
```

The setup also writes down the Python it installed into, and the launchers
read that first — so whatever put the libraries on the disk is what opens the
program. Without it a machine with several Pythons could install into one and
start on another, which is the same thing wearing a different hat every time.

If pip answers `externally-managed-environment`, that is PEP 668: the Python
itself forbids installing into it, and Homebrew ships it that way. `Install.bat`
and `install.command` know that refusal and put the packages in your own folder
instead — so run the setup rather than pip by hand.

If the window still says it is not installed after you installed it, the two
are talking about different Pythons: a machine holds several, a terminal
reaches one and a double-clicked window finds another, and pip leaves yt-dlp
beside whichever it belongs to. The message names the Python that went looking
and gives the command that installs it there. You can also point straight at
your copy in `settings.ini`:

```ini
yt-dlp = /opt/homebrew/bin/yt-dlp
```

Without it the window says so before anything is pasted, and the file picker is
still there. If the download fails — a private video, a dead link, a country
block — the reason the downloader gave is shown as it is, and the field is
still open for another link.

The editor's “⇪” exports the timing for other programs: an UltraStar file
for the singing games (notes freestyle — pitch is not measured, so none is
invented) and .ass subtitles with a word-by-word karaoke sweep in the
project's colours.

When the song's name finds the words on the lyrics library, a record that
carries its own timing says so — and “Take it with the timing” keeps those
times as sparse pegs: the model still lays out the words between them, but a
line can no longer wander across the song. The stretches where nobody sings
are offered as “no words here” marks with one press. And “⇩ Pack” in the
editor puts the whole song into one `.karaoke.zip`, which “Open a packed
song” restores on any other computer.

The cover can also be set or changed later — “⛰ Cover” in the editor takes
any picture, or cuts a frame out of a clip you point it at.

The clip's cover comes along with the sound. A checkbox appears next to the
found lyrics — leave it on, and the cover lies behind the words on the page
and in the video, blurred and dimmed so the text stays the brightest thing in
the frame; untick it for the plain woven background. A song taken from a file
on disk has no cover and no checkbox.

YouTube sometimes turns a player client away with something that says nothing
about the video — “The page needs to be reloaded”, or a format list with
nothing in it. The same link goes through as another client, so it is asked
again (android, ios, tv) before you are told it did not work. If every one of
them is turned away, two things are usually left: the downloader is older than
the site — `pip install -U yt-dlp` — or the video wants you to be signed in,
which means cookies:

```ini
yt-dlp-args = --cookies-from-browser chrome
```

That line goes into `app/settings.ini`; `KARAOKE_YTDLP_ARGS` does the same from
the environment. Everything in it is passed to `yt-dlp` as it is.

The song keeps the name it had where it came from — the file it landed in is
called something that survives every file system (`Forevermore_[kBjKqBvbbjM]`),
and that is not what you see in the studio. A `title:` line in the lyrics file
still outranks it.

Once the sound is here, the words are looked for by the name of the song, on
[LRCLIB](https://lrclib.net) — an open library that needs no key and no
account. What comes back is a **suggestion**: each one says who sings it, how
many lines it has and where it came from, and it lands in a box to be read
before it is used. A wrong text lays wrong lines over the whole song, which is
why it is never taken silently.

The lyrics have three ways in, and all three end in the same place:

* **a file** — the `Choose…` button, an ordinary `.txt`;
* **a suggestion** — `Take it` next to one of the texts that were found;
* **by hand** — `Paste the text`, type or paste it into the box, `Use this
  text`. What you paste is written into `projects/_incoming` as a `.txt`, so
  everything downstream works exactly as it does with a file of your own.

Whether you may download a particular recording, and what you may do with the
words, is yours to judge: the program runs `yt-dlp` and asks an open library,
and neither of those decides that for you.

## The lyrics file

One line of the song per line of the file. Blank lines are ignored.

```
title: Song name
artist: The Band

[Verse]
First line as it is sung
Second line
(and this is a backing vocal)
```

* `[Square brackets]` on their own line — a section heading, not sung.
* `(Round brackets)` — a **sung** line, the way backing vocals are usually
  written. It gets the second voice and its own colour. `(Chorus)` and other
  section names are recognised by their first word and stay headings.
* Punctuation on its own — a dash, an ellipsis — is kept and shown; it sticks to
  the neighbouring word.
* `[00:12.34] line` — a ready LRC timing. If the file has them, alignment is
  skipped.
* `for=ev=er=more` — a syllable break. The pieces are timed one by one, so a held
  note lights up syllable by syllable, and the mark itself is never shown: on
  screen, on the page and in the video the word is whole. A soft hyphen works
  the same way; an ordinary hyphen is a letter and stays where it is.

### Who sings, and how many times

The voice can be set in the text itself:

```
The first voice sings an ordinary line
2: and the second one sings this
(backing vocals too — they are the second voice by default)

[voice 2]
From here the second voice sings everything,
this as well,
[voice 1]
and here the first one is back.
```

`2:` at the start of a line applies to that line only. `[voice 2]` switches
every following line until told otherwise.

Repeats are written at the end of a line:

```
Chorus x4
```

The program spreads it into four lines by itself. `x4` and `×4` both work (the
Cyrillic х too), brackets are allowed — `(x4)` — and the number can be 2 to 99.
A section heading is not repeated with the line, and if the file has manual LRC
timings, repeats are left alone: every line there has its own time.

## Where there are no words

A vocalise, a scream with nothing to write down, a hummed intro — all of that is
voice. Nothing measurable tells it from a sung line, so the timing crawls onto
it and the karaoke shows words over music nobody sings. Only a person knows the
difference, and there are two places to say it.

In the window, under the model and the language, a field takes the stretches:

```
0:00-0:42, 3:10-3:50
```

The same can be written in the lyrics file itself — a heading with a time range
in it. The heading still names the part, and the range says nothing is sung
there:

```
[Guitar solo 3:10-3:50]
[no words here 1:02-1:40]
[6:20-7:05]
```

What it does: those stretches are cut out of what the aligner hears, so nothing
can be laid on them, and the repairs afterwards treat them as silence — a line
that landed there is moved onto real singing between its neighbours. What it
does **not** do: it makes no claim about the rest of the song. Marking one solo
does not promise words everywhere else; it only keeps them off the solo.

The same field sits in the editor next to “Re-time”, where the timeline is in
front of you: the shaded stretches are the ones without singing, and a vocalise
is the loud one with no lines under it. Mark it, press “Re-time”, and the words
stay off. The marks are saved with the song, so the next re-time starts from
them.

## Screamed, growled, whispered

The aligner does not transcribe: it takes the words you gave it and lays them
on the audio. That is why an unintelligible vocal is not hopeless — but it is
where the timing goes wrong most often, so the program leans on three things
here, and two of them are yours to set.

**Keep the instrumental on.** The timing is worked out from the separated voice,
never from the mix: guitars and drums are simply not there for the model to
mishear. Switching the instrumental off makes the timing much worse on a heavy
song. Measured on a nine-minute deathcore track: segments the aligner gave up on
fell from 27 to 22 the moment the voice was separated.

**The voice is levelled before the model hears it.** A scream point-blank and a
strangled rasp in the same song differ by a factor of thirty, and the quiet half
used to reach the model as nothing at all. Levelling is automatic and touches
neither pitch nor time — on the same track it took those 22 failed segments down
to 19 and lifted confidence from 0.125 to 0.138. Nothing to switch on.

**Say where there are no words.** A vocalise, a wordless scream, a hummed intro
— see the section above. This is the one thing no measurement can do for you,
and on this kind of music it is worth the minute it takes.

Beyond that, two switches worth having on a strong machine:

* **`large-v3-turbo`** in the model list — the same encoder as `large-v3` with a
  much smaller decoder: nearly its accuracy at about the speed of `medium`, and
  1.6 GB instead of 3. On a screamed vocal the model is doing the hardest work
  it ever does, and this is the cheapest way to give it a better one.
* **“Separate finely”** next to the instrumental switch — four passes over the
  song instead of one (`htdemucs_ft`). The voice comes out cleaner, and since
  the timing is made from that voice, the timing gets cleaner with it. About
  four times longer, and 300 MB more to download the first time.

And pick the language of the song by hand instead of leaving it to be worked
out. A re-time uses the model the song was built with, and says which one that
is before it starts.

## Putting a stubborn song right

Five things in the editor, meant for the song that came out wrong in one place
and right everywhere else.

**A vocalise is heard, not muted.** A marked stretch has nothing to sing over,
so the original voice is left in the backing there — the scream or the humming
is heard, instead of a hole where the song is at its loudest. The switch beside
the marks turns it off, for when you mean to sing it yourself.

**Cut a line in two, or join two into one.** “⤸ Split” cuts the selected line
where the singing pauses longest inside it — where a person draws breath. “⤹
Join” puts it back together with the line after it. Neither times anything
again: the words keep the times they had, only the grouping changes.

**Mark the wordless stretches with the mouse.** “✂ No words here” on the
timeline: press and drag over a vocalise or an intro, and it is marked; click a
mark to take it off. Typing seconds into the field does the same, and the two
are one and the same underneath. Then press “Re-time”.

**Time a few lines again, not the whole song.** Select the lines that are
wrong and press “↻ These lines”. The model is shown only the stretch between
their timed neighbours, so on a nine-minute song it takes seconds instead of
minutes — and everything else stays exactly as it is.

**Lock what you put right by hand.** “🔒 Lock” on the selected lines: re-timing
leaves them alone, whole or in part. If the lyrics are re-split into a
different number of lines the locks are dropped and the log says so — line
seven is no longer the same line seven.

**Look at what the model was unsure of.** Lines it barely heard are drawn with
a dashed border on the timeline and named in the panel of lines worth checking.
The measure is the song itself: a line is doubtful when it sits far below its
neighbours, so this works the same on a whisper and on a scream.

**Measure instead of guessing.** `python3 app/tools/bench.py song.mp3 lyrics.txt`
prints one row per way of handing the song to the aligner — the mix, the
separated voice, the levelled voice — with the segments it gave up on, its
confidence, and the share of lines left in a pile. Add `--models small,medium`
to compare models. It needs no “right answer” to compare against, so it works
on your own music.

## The finished page

* Space — play/pause, `←` `→` — seek, `F` — full screen, `M` — voice on/off.
* **Voice** slider: 0 % — instrumental only, 100 % — the original.
* **Offset** slider — moves the whole text against the music.
* `RU` / `EN` button — the language of the labels, remembered per song.
* **Edit** — move a line to the current second, shift everything after it, tap
  the song through by pressing Space on every line, undo, save the page with
  your edits.

## Finding your way around a long song

Above the timeline stands a strip with the whole song on it: the marked
stretches, the lines left to the original, the quiet places, the window you
are looking at and the playhead. A click on it jumps, a drag scrubs — on an
eight-minute song the wheel is a hike and this is a step.

Where two lines overlap, their blocks lie on top of each other. The first
press takes the upper one, as always; a second press on the same spot,
without moving the mouse, dives to the line underneath, so both can be
edited.

**`▣ Frame`** draws what the video will look like at the playhead — the same
drawing the clip is made of, in a moment rather than the minutes a render
takes. It follows a seek, and the arrows beside it step through the song.

**`⛰ Cover`** puts a picture behind the lyrics, blurred and darkened: any
image, a pasted link to one, or the clip itself — six frames are cut across
it and the video turns them slowly, one into the next. The 🌗 knob beside it
sets how dark the backdrop stands, from nothing to almost black; the number
can simply be typed.

**`🎞 Clip behind`** puts a moving clip behind the lyrics instead of a still
— a file, or a link (the song's own will do). It is blurred into a slow field
of colour, so the smallest copy a site offers is worth exactly as much as the
best one, and what the song keeps is a few hundred pixels at four frames a
second: small enough to travel inside a packed song. The darkening is no
longer a fixed number either — the band where the words stand is measured on
every field, and the frame clamps down the instant a cut brings something
bright under the text, letting go slowly afterwards. `🎞✕` takes it away.

**`⇪`** holds the other ways out: an UltraStar file for the singing games,
`.ass` subtitles with a word-by-word karaoke sweep, and **`⇩ Pack`** — the
whole song in one `.karaoke.zip` to carry to another computer, which “Open a
packed song” unpacks exactly as it was. A pack dropped into the window opens
itself.

**`MP4 video`** asks first: the size, the frames per second, the quality and
whether the opening runs. What you choose is remembered for the next song.

## Tune one line, reuse it

A chorus is sung the same way every time. **⧉ Rhythm** remembers the word
layout inside the selected line, **⧉ Paste rhythm** applies it to another line
with the same number of words — the line's start does not move, only the
pattern inside it. With “and all after it” the rhythm goes into every later
line with the same text; the button says how many were found. `Ctrl+D`
duplicates a line entirely, right below the original, and `Ctrl+Shift+V` puts
the copied line in place of the selected one.

Several lines at once: **press and drag across the lines** — the simplest way —
or **Shift**+click (Shift+arrows) for a run and **Ctrl**+click to add one.
Copying takes everything selected: a block of lines can be pasted elsewhere,
keeping the gaps between them. Voice, “original”, delete and paste then apply to the
whole batch.

## Two voices, colours and “the original sings this”

Vocals overlap: a lead and a backing, a clean voice and a scream. A line can be
given the **second voice** (`◑ Voice` in the Studio, or automatically when the
line is wholly in round brackets):

* in the Studio the timeline splits into **two lanes**, so the blocks stop
  covering each other;
* on the finished page such a line is highlighted in the **second colour**;
* lines that sound at the same time are highlighted **together**.

**`♪ Original`** marks a line you are not meant to sing — backing vocals,
speech, a bit that matters to the story. The original voice comes back exactly
there, whatever the Voice slider says, and fades out again at the end of the
stretch. In the MP4 the same stretch is mixed with the vocal. Pressed again,
the same button holds the original back to a quiet guide — for lines meant to
be sung **along with** the artist, in unison; a third press gives the line
back to you.

Colours are the four swatches on the timeline: the first pair is the
highlight (main voice, second voice), the second is the page look (background
and text). Text that blends into its background is corrected automatically —
the hue stays yours, the lightness moves until the contrast is at least 4.5.

From the command line: `--colors "#4de1ff,#ff8ad1"`, `--theme "#0a0b14,#e8ebf5"`.

## Your own instrumental

If the artist released a real instrumental, put it in instead of the separated
one: **♪ My instrumental** in the Studio. The offset is measured by
cross-correlation (worst error in testing: 1.2 ms) and the timing follows it.

The voice is then extracted by subtraction — the original minus your
instrumental — **per frequency band**, not by one volume level. An official
instrumental is almost never mixed like the same arrangement inside the song:
different mastering, different EQ, different level. A single multiplier cannot
cancel that, and the leftovers sound like a second, foreign recording playing
next to the minus. Measured on a deliberately mismatched pair: 29 dB of
arrangement suppression against 17 dB for plain subtraction, with the voice
intact (27 dB signal-to-noise).

If the stretches without singing do not get at least 4 dB quieter, the
instrumental is treated as belonging to another recording and no voice is
extracted at all — only your instrumental plays.

## Before and after the long part

Before building, the program prints a report: length, stretches without
singing, lines and words, repeats, the language it detected, what it is about
to do and roughly how long that takes.

After building, the Studio shows a **Summary** on the right: length, how much
of the song is sung, lines and words, stretches without singing (clickable),
which engine did the timing, how many lines belong to the second voice and how
many are left to the original.

While nothing is being sung — an intro or a long instrumental — a strip at the
top of the stage counts down to the next line and names it. Gaps shorter than
five seconds are not counted down; they are obvious anyway.

## Command line

```
python app/karaoke.py AUDIO LYRICS [-o FILE.html]

timing
  --align {auto,whisper,energy,none}   alignment engine
  --whisper-model tiny|base|small|medium|large-v3-turbo|large-v3
  --lang ru                            language of the lyrics
  --no-text "0:00-0:42, 3:10-3:50"     stretches that hold no words at all
  --device cuda|cpu
  --timings timings.json               take ready timings (exported from the player)

audio
  --no-separate                        no instrumental (fast)
  --codec mp3|opus|aac                 mp3 — maximum compatibility

output
  --no-embed                           do not embed the audio, put files alongside
  --lrc                                also save an .lrc
  --title / --artist                   override the captions
  --colors "#4de1ff,#ff8ad1"           highlight colours: main voice, second voice
  --theme "#0a0b14,#e8ebf5"            page look: background and text
  --ui-lang auto|en|ru                 language of the labels on the page
```

`app/settings.ini` holds the same options for the launcher scripts, with English
key names (the Russian ones still work). That file is yours: it is not in the
repository, so an update never overwrites it. `Install.bat` /
`install.command` make it on the first run from `app/settings.example.ini`,
which is the documented reference — copy it by hand if you prefer. Without any
settings file the program simply uses its defaults.

## Language

The finished page and the Studio window are bilingual, English and Russian,
with a switch in each. The program's own messages follow `ui-lang` in
`settings.ini`, then the system language. Language *names* in the picker are
written in their own language and are never translated.

## Adding a language

The window and the finished page speak English and Russian. Another language is
a JSON file — no code, no rebuild:

1. Copy `app/kstudio/messages/template.json` to `<code>.json` (`de.json`,
   `uk.json`, `pl.json`…).
2. Translate the values. An empty value falls back to English, so a
   half-finished file is already useful.
3. Reload the window: the language button cycles through everything it finds.

Pull requests with translations are welcome — that is the easiest way to help.

## Video for YouTube

![A frame from the rendered video: the intro countdown above the lyrics](app/docs/video.png)

```bash
python app/tools/video.py page.html -o clip.mp4
```

1920×1080 by default, `--audio minus|guide|original`, `--seconds N` to render a
short sample first, `--backdrop FILE` to stand a clip behind the lyrics. Before drawing, the video prints its own report — song,
length, lines, where two voices sing at once, stretches left to the original,
colours, audio mode, number of frames — so a wrong file or forgotten marks show
up before the long part, not after it.

Every clip opens with the song's name held large for three seconds, then a
count of three, and only then the music: a karaoke that starts on the first
frame catches everybody mid-breath. The count is small and the first lines
stand under it, already where they will be when the singing starts. The name
is the one you gave the song — click it in the editor's corner to change it.
`--no-intro` starts with the song instead, and a sample cut from the middle
(`--start`) never gets the card.

During the intro and long instrumental stretches the video shows a countdown at
the top — how long until the next line, which line it is, and a bar filling to
its start. Gaps shorter than five seconds are not counted down. Its words are
written in the language of the lyrics, not of the program.

Once the last line has been sung the frame holds it for five seconds and then
empties, instead of leaving it lit to the end of the recording.

The lines do not blink from one to the next: the whole column rides upwards,
the sung line leaving through the top while the one after it comes up from
below — the text scrolls rather than changes. A line too long for the frame
breaks in two at a word, at full size, instead of shrinking until it cannot
be read across a room; the line quoted in the countdown is cut at a word and
finished with an ellipsis rather than mid-word.

Every letter carries a dark outline, and a picture behind the lyrics gets a
soft dark band under the rows where the words stand. Until now the words were
readable only because the backdrop was tame: over a bright cover a grey line
could melt into a grey wall. The ring does not care what is behind it — the
name in the corner, the opening card and the labels carry one too.

If a cover was chosen in the editor it stands behind the lyrics — blurred,
darkened to the depth you set, and, when the cover is the clip itself, turned
slowly from one frame into the next.

The video takes the colours and the look from the page: the second voice is
painted in its own colour, and when two voices sing at once they are drawn on
two rows — the first voice above, the second below, in a fixed order.

## In a container

If you would rather not install PyTorch and the rest on your own machine — or
simply do not want to run software from the internet outside a box:

```bash
cd app && docker compose up --build     # then open http://127.0.0.1:8770/
```

Songs stay in `projects/` next to the launchers, and the music you want to
import goes into `music/` (mounted read only, created on first run). The models are downloaded once
into a named volume, so a rebuild does not fetch them again. The port is
published to `127.0.0.1` only, exactly like the local run.

Without compose:

```bash
docker build -t karaoke app
docker run --rm -p 127.0.0.1:8770:8770 \
  -v "$PWD/projects:/songs" -v "$HOME/Music:/music:ro" karaoke
```

**GPU.** For an NVIDIA card install the container toolkit on the host and add
`--gpus all` (or uncomment the `deploy:` block in `docker-compose.yml`). Whisper
and Demucs then use the card; without it everything still works on the CPU, only
slower. Apple silicon cannot be passed into a container at all — there the local
run is the fast one.

## Tests

```bash
python3 app/tests/run_all.py
```

The same checks run on GitHub on every push — the badge at the top of this page
is their result, and the “Actions” tab shows what exactly ran. Nothing has to be
installed to look. To run the container check as well (it builds the image and
makes a song inside it):

```bash
KARAOKE_HEAVY=1  python3 app/tests/run_all.py   # real Whisper and Demucs
KARAOKE_DOCKER=1 python3 app/tests/run_all.py   # build the image, run it
```

The everyday run keeps away from the neural nets on purpose: it feeds ready word
times and checks everything around them, which takes seconds instead of minutes.
`KARAOKE_HEAVY=1` runs the real thing — aligns with Whisper `tiny` and separates
with Demucs, then checks that the stems add back up to the original recording.

Runs the pipeline checks, the delivery checks (launchers, file names, settings,
the language of the console, the audio of the video), 38 suites in jsdom and 8
in a real Chrome — hit-testing and layout, which jsdom does not do at all.

## Limits

* The lyrics must match the recording: alignment lines up text with audio, it
  does not transcribe it.
* Rap and dense mixes are harder; an instrumental helps a lot, and on screamed
  vocals so does marking the stretches that hold no words.
* Nothing can tell a vocalise from a sung line by listening: it is voice either
  way. Only you can say where the words are not.
* Syllables are exact for Russian (by vowels) and a heuristic for the Latin
  script — good enough to spread the time inside a line, and it still lies on
  loanwords: `karaoke` counts as 2, not 4.
* Whisper needs memory: `small` about 2 GB, `medium` about 5 GB.

## Questions, bugs, ideas

Open an issue — questions, bug reports and suggestions are all welcome. If
something went wrong, the two most useful things to attach are the text from
the job window (it now prints a report before the long steps) and the last
lines from the console.

## License

MIT — see [LICENSE](LICENSE). Do what you like with it: use it, change it, pass
it on, build something of your own on top. The songs you make with it are
yours, and nothing in this program lays a claim to them.

## Support

If this saved you some time, you can send a coffee:

- **TON / USDT (TON):** `UQBQ4Ghnv2pl7R9b9AlTFpWV3tVbfhRXV4tVRTPux_Seg4SV`
