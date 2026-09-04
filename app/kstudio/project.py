"""A song project on disk: stems, timing, the vocal envelope.

The point is that the heavy work happens once. Demucs and Whisper run when the
project is created; after that an edit is just a write to project.json. No
rebuilds, no manual saving.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import time
from typing import Callable, Dict, List, Optional

from . import __version__
from .i18n import tr
from . import align as A
from . import audio as AU
from . import build as B
from . import lyrics as L
from . import separate as S

Log = Callable[[str], None]
PROJECT_FILE = "project.json"
ENVELOPE_HOP = 0.02          # step of the vocal envelope, seconds


def _noop(msg: str) -> None:
    pass


# Cyrillic in Latin letters: folder and file names must read on any system.
# “Мамины Усы” → “maminy-usy”, not mojibake in someone else's file manager.
TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u",
}


def translit(name: str) -> str:
    out = []
    for ch in name:
        low = ch.lower()
        if low in TRANSLIT:
            rep = TRANSLIT[low]
            out.append(rep.upper() if ch.isupper() and rep else rep)
        else:
            out.append(ch)
    return "".join(out)


def slugify(name: str) -> str:
    s = translit(name)
    s = re.sub(r"[^A-Za-z0-9\s-]", "", s).strip()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:60].lower() or "song"


def projects_root(base: Optional[str] = None) -> str:
    # KARAOKE_PROJECTS keeps songs outside the program folder: the tests need
    # that so they never touch real projects, and it is handy when songs live on
    # another drive.
    # One level above the program folder: the root holds only the user's files.
    home = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root = base or os.environ.get("KARAOKE_PROJECTS")
    if not root:
        root = os.path.join(home, "projects")
        # The folder used to be called “проекты” (Russian). If someone already has one
        # with songs in it, keep using it so no timing is lost on an update.
        old_ru = os.path.join(home, "проекты")
        if not os.path.isdir(root) and os.path.isdir(old_ru):
            root = old_ru
    os.makedirs(root, exist_ok=True)
    return root


# --------------------------------------------------------------------------- #

def encode_envelope(values: List[float]) -> str:
    """The envelope as base64 of 0..255 bytes — far smaller in JSON than a list."""
    return base64.b64encode(bytes(min(255, max(0, int(v * 255))) for v in values)).decode()


def build_envelope(path: str, log: Log = _noop) -> Dict:
    """Vocal loudness over time — the waveform and the phrase starts come from it."""
    try:
        env, dt = AU.rms_envelope(path, hop_ms=int(ENVELOPE_HOP * 1000))
    except Exception as e:                                   # pragma: no cover
        log(tr(f"  could not work out the waveform ({e})",
            f"  огибающую посчитать не вышло ({e})"))
        return {"hop": ENVELOPE_HOP, "data": ""}
    return {"hop": dt, "data": encode_envelope(env)}


# --------------------------------------------------------------------------- #

def create(audio_path: str, lyrics_path: str, root: str, *,
           align_engine: str = "auto", whisper_model: str = "small",
           language: str = "ru", separate: bool = True,
           device: Optional[str] = None, codec: str = "mp3",
           skip=None, separator: str = "htdemucs",
           title: Optional[str] = None, artist: Optional[str] = None,
           cover: Optional[str] = None, cover_bg: bool = False,
           title_set: bool = False,
           log: Log = _noop) -> str:
    """Build a project. Returns the path to its folder."""
    lyr = L.load(lyrics_path)
    if not lyr.lines:
        raise ValueError(tr("The lyrics file has no lines at all.",
                        "В файле с текстом не нашлось ни одной строки."))
    log(tr(f"Lyrics: {len(lyr.lines)} lines, {len(lyr.words)} words.",
           f"Текст: {len(lyr.lines)} строк, {len(lyr.words)} слов."))

    # What the song is called, in order of how much it can be trusted: a name
    # typed by hand, then what the lyrics file says, then what the song was
    # known as where it came from — a link carries its real name, while the
    # file on disk is called “Forevermore_[kBjKqBvbbjM]” because the name had
    # to survive every file system in the world.
    given, given_artist = (title or "").strip(), (artist or "").strip()
    if title_set and given:
        title = given
    else:
        title = lyr.title or given or os.path.splitext(os.path.basename(audio_path))[0]
    if given_artist and (title_set or not lyr.artist):
        lyr.artist = given_artist
    folder = os.path.join(root, slugify(title))
    n = 2
    while os.path.exists(folder):
        folder = os.path.join(root, f"{slugify(title)}-{n}")
        n += 1
    os.makedirs(folder)

    tmp = os.path.join(folder, "tmp")
    os.makedirs(tmp, exist_ok=True)
    try:
        AU.ffmpeg()
        AU.ensure_on_path()

        from . import sysinfo
        need = sysinfo.NEED_DEMUCS if (separate and S.available()) else \
            sysinfo.NEED_WHISPER.get(whisper_model, 2.2)
        ok, note = sysinfo.check(need)
        if not ok:
            log(tr("NOTE: ", "ВНИМАНИЕ: ") + note)

        log(tr("Preparing the audio…", "Готовлю звук…"))
        work = AU.to_wav(audio_path, os.path.join(tmp, "source.wav"))
        dur = AU.duration(work)
        log(tr(f"Length: {int(dur // 60)}:{int(dur % 60):02d}",
           f"Длительность: {int(dur // 60)}:{int(dur % 60):02d}"))

        instrumental = vocals = None
        if separate:
            instrumental, vocals = S.separate(work, os.path.join(tmp, "stems"),
                                              separator,
                                              device=device, log=log)

        align_src = vocals or work
        # On the separated vocal silence is real silence — the repairs may
        # trust it and move lines that lie where nobody sings.
        # Stretches with no words: from the window, and from the lyrics file
        # itself where a heading carries a time range — “[Solo 3:10-3:50]”.
        holes = A.spans(skip, dur) + A.spans(getattr(lyr, "skips", []), dur)
        lyr, engine = A.align(lyr, align_src, dur, align_engine,
                              whisper_model, language, device, log,
                              isolated=bool(vocals), skip=holes)
        log(tr(f"Timing ready ({B.ENGINE_LABEL.get(engine, engine)}).",
           f"Разметка готова ({B.ENGINE_LABEL.get(engine, engine)})."))

        log(tr("Working out the vocal waveform…", "Считаю волну вокала…"))
        envelope = build_envelope(align_src, log)

        log(tr("Saving the tracks…", "Сохраняю дорожки…"))
        tracks = {}
        if instrumental and vocals:
            tracks["instrumental"] = os.path.basename(
                AU.encode(instrumental, os.path.join(folder, "instrumental"), codec)[0])
            tracks["vocals"] = os.path.basename(
                AU.encode(vocals, os.path.join(folder, "vocals"), codec)[0])
        else:
            tracks["mix"] = os.path.basename(
                AU.encode(work, os.path.join(folder, "mix"), codec)[0])

        data = {
            "version": __version__,
            "title": title,
            "artist": lyr.artist or "",
            # A name given by hand is not to be undone by a lyrics file that
            # carries a “title:” of its own on the next re-timing.
            "titleSet": bool(title_set),
            "duration": round(dur, 3),
            "engine": engine,
            # which model timed it: a re-time must not quietly drop to another
            "model": whisper_model,
            "source_audio": os.path.abspath(audio_path),
            "source_lyrics": os.path.abspath(lyrics_path),
            "created": time.time(),
            "tracks": tracks,
            # what was said to hold no words: the editor shows it again, and a
            # re-time starts from what you told it last time
            "noText": ", ".join(f"{a:.1f}-{b:.1f}" for a, b in holes),
            # the clip's cover, and whether the karaoke stands on it
            "cover": "cover.jpg" if cover and os.path.isfile(cover) else None,
            "coverBg": bool(cover_bg and cover and os.path.isfile(cover)),
            # a stretch with nothing to sing keeps the original sound on it,
            # or the karaoke has a hole where the vocalise was
            "keepMarks": True,
            "keepSpans": [[round(a, 3), round(b, 3)] for a, b in holes],
            "envelope": envelope,
            "lines": [ln.to_json() for ln in lyr.lines],
        }
        if cover and os.path.isfile(cover):
            shutil.copyfile(cover, os.path.join(folder, "cover.jpg"))
        save(folder, data)
        log(tr("The song is ready.", "Проект готов."))
        return folder
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def save(folder: str, data: Dict) -> None:
    """Write through a temporary file: a crash halfway will not ruin the project."""
    path = os.path.join(folder, PROJECT_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def load(folder: str) -> Dict:
    with open(os.path.join(folder, PROJECT_FILE), encoding="utf-8") as f:
        return json.load(f)


def keep_spans(data: Dict) -> List[List[float]]:
    """Where the original voice is left in the backing track.

    A stretch with no words in it is a stretch with nothing to sing: mute the
    voice there and the karaoke has a hole where a vocalise or a scream was.
    So the marks that keep the timing off a stretch also keep the original
    sound on it — unless a person says otherwise, meaning to sing it themselves.
    """
    if not data.get("keepMarks", True):
        return []
    from . import align as A
    return [[round(a, 3), round(b, 3)]
            for a, b in A.spans(data.get("noText") or "", data.get("duration") or 0)]


def pack(folder: str, out_dir: str) -> str:
    """Everything a song is, in one file: the record, the audio, the cover.

    A project is a folder that stands on its own, but a folder does not travel
    — between two computers, or to somebody else, or into a backup. A zip of
    it does, and it opens back into exactly the same song.
    """
    import zipfile
    data = load(folder)
    name = slugify(data.get("title") or os.path.basename(folder))
    out = os.path.join(out_dir, name + ".karaoke.zip")
    stem, n = out[:-len(".zip")], 2
    while os.path.exists(out):
        out = f"{stem}-{n}.zip"
        n += 1
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for entry in sorted(os.listdir(folder)):
            path = os.path.join(folder, entry)
            # Only the song itself: a rendered page or clip is made again in
            # one press, and weighs more than everything else together. The
            # backdrop is the exception — it is an .mp4 the song was given,
            # not one it produced, and nothing could make it again.
            made_here = (entry.lower().endswith((".mp4", ".html"))
                         and not entry.startswith("backdrop."))
            if os.path.isfile(path) and not entry.startswith("_") \
                    and not made_here:
                z.write(path, entry)
    return out


def unpack(zip_path: str, root: str) -> str:
    """A packed song back into a folder of its own. Returns the folder."""
    import zipfile
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if "project.json" not in names:
            raise ValueError(tr("this is not a packed song: no project.json inside",
                                "это не упакованная песня: внутри нет project.json"))
        # A zip states how big it claims to unpack; a claim the size of a disk
        # is not a song. Two gigabytes holds any record with its audio.
        told = sum(i.file_size for i in z.infolist())
        if told > 2 * 1024 ** 3:
            raise ValueError(tr(f"this unpacks to {told // 1024 ** 2} MB — not a song",
                                f"это распакуется в {told // 1024 ** 2} МБ — не песня"))
        with z.open("project.json") as f:
            data = json.load(f)
        folder = os.path.join(root, slugify(data.get("title") or "song"))
        n = 2
        while os.path.exists(folder):
            folder = os.path.join(root, f"{slugify(data.get('title') or 'song')}-{n}")
            n += 1
        os.makedirs(folder)
        for entry in names:
            # A name with a path in it belongs to another folder, and a zip is
            # not to be trusted with where it unpacks: only plain names.
            if entry.endswith("/") or os.path.basename(entry) != entry \
                    or entry.startswith("."):
                continue
            with z.open(entry) as src, open(os.path.join(folder, entry), "wb") as dst:
                shutil.copyfileobj(src, dst)
    return folder


def save_lines(folder: str, lines: List[Dict], colors=None, theme=None,
               no_text=None, keep_marks=None, check_off=None,
               title=None, artist=None, cover_dark=None, grid=None) -> Dict:
    data = load(folder)
    data["lines"] = lines
    if colors:
        data["colors"] = list(colors)[:2]
    if theme:
        data["theme"] = list(theme)[:2]
    # The marks travel with the ordinary edits: dragging one on the waveform is
    # an edit like any other, and the original voice must be heard at once, not
    # after a re-timing.
    if no_text is not None:
        data["noText"] = str(no_text)
    if isinstance(grid, dict):
        # The beat grid belongs to the song, not to the window: a tempo counted
        # once should still be there tomorrow.
        data["grid"] = {"on": bool(grid.get("on")),
                        "bpm": max(20.0, min(300.0, float(grid.get("bpm") or 120))),
                        "beat0": max(0.0, float(grid.get("beat0") or 0.0)),
                        "sub": 4 if int(grid.get("sub") or 1) == 4 else 1,
                        "pulse": bool(grid.get("pulse"))}
    if keep_marks is not None:
        data["keepMarks"] = bool(keep_marks)
    if check_off is not None:
        data["checkOff"] = [str(k) for k in check_off][:500]
    if cover_dark is not None:
        # how far the cover backdrop is darkened: covers differ, and the
        # words must stay the brightest thing in the frame. Garbage in the
        # field must not fail the whole save the words travel in.
        try:
            data["coverDark"] = max(0, min(95, int(cover_dark)))
        except (TypeError, ValueError):
            pass
    # A name given by hand. It stands in the corner of the video and on its
    # opening card, and it is remembered as chosen: re-reading a lyrics file
    # with a “title:” header of its own must not quietly rename the song back.
    if title is not None:
        data["title"] = str(title).strip()[:120]
        data["titleSet"] = True
    if artist is not None:
        data["artist"] = str(artist).strip()[:120]
        data["titleSet"] = True
    data["keepSpans"] = keep_spans(data)
    data["edited"] = time.time()
    save(folder, data)
    return data


def list_all(root: str) -> List[Dict]:
    out = []
    for name in sorted(os.listdir(root)):
        folder = os.path.join(root, name)
        if not os.path.isfile(os.path.join(folder, PROJECT_FILE)):
            continue
        try:
            d = load(folder)
        except Exception:
            continue
        out.append({
            "id": name,
            "title": d.get("title") or name,
            "artist": d.get("artist") or "",
            "duration": d.get("duration") or 0,
            "lines": len(d.get("lines") or []),
            "engine": d.get("engine") or "",
            "stems": "vocals" in (d.get("tracks") or {}),
            "edited": d.get("edited") or d.get("created") or 0,
        })
    out.sort(key=lambda x: -x["edited"])
    return out


def delete(folder: str) -> None:
    shutil.rmtree(folder, ignore_errors=True)


# --------------------------------------------------------------------------- #
#  Finding suspicious lines — so misses need not be hunted by ear
# --------------------------------------------------------------------------- #

def decode_envelope(env: Dict) -> List[float]:
    raw = base64.b64decode(env.get("data") or "")
    return [b / 255.0 for b in raw]


def quiet_spans(data: Dict) -> List[Dict]:
    """Where nobody sings for a while — from the same envelope that draws the wave.

    These are the intro, the interludes and the solos. Seeing them on the
    timeline matters: no lines should land there, and loudness-based timing is
    exactly what misses in those places.
    """
    from . import report as R
    env = decode_envelope(data.get("envelope") or {})
    hop = (data.get("envelope") or {}).get("hop") or ENVELOPE_HOP
    return R.quiet_stretches(env, hop)


def keep_locked(old: List[Dict], fresh: List[Dict], log=_noop) -> int:
    """Put back the lines a person locked before the timing was redone.

    A line put right by hand is worth more than anything a model returns for
    it, and re-timing used to throw all of that away. A lock says “leave this
    one alone”. It can only be honoured while the lines still answer to each
    other one for one: with the text re-split, line seven is no longer the same
    line seven, and silently keeping its old time would be a lie.
    """
    locked = [i for i, ln in enumerate(old or []) if ln.get("lock")]
    kept = [i for i, ln in enumerate(old or []) if ln.get("keep")]
    if not locked and not kept:
        return 0
    if len(old) != len(fresh):
        if locked:
            log(tr(f"  the locks on {len(locked)} lines were dropped: the text now has "
                   f"{len(fresh)} lines instead of {len(old)}, so they are not the same lines",
                   f"  замки с {len(locked)} строк сняты: в тексте теперь {len(fresh)} строк "
                   f"вместо {len(old)}, это уже не те же самые строки"))
        return 0
    for i in locked:
        fresh[i] = dict(old[i])
    # “♪ Original” marks survive too — a re-timing must not quietly hand the
    # original's lines back to the singer. The flag carries over; the fresh
    # times stay, since the model just laid them anew.
    for i in kept:
        if i not in locked:
            fresh[i]["keep"] = True
            if old[i].get("keepSoft"):
                fresh[i]["keepSoft"] = True
    log(tr(f"  lines left as they were, locked: {len(locked)}",
           f"  строк оставлено как были, они заперты: {len(locked)}"))
    return len(locked)


def problems(data: Dict) -> List[Dict]:
    """Lines worth checking, each with a reason."""
    lines = data.get("lines") or []
    env = decode_envelope(data.get("envelope") or {})
    hop = (data.get("envelope") or {}).get("hop") or ENVELOPE_HOP
    floor = 0.0
    if env:
        ordered = sorted(env)
        floor = ordered[int(len(ordered) * 0.55)]

    def voiced_at(t: float) -> float:
        if not env:
            return 1.0
        i = int(t / hop)
        lo, hi = max(0, i - 4), min(len(env), i + 12)
        return max(env[lo:hi], default=0.0)

    # How sure the model was, measured against this very song. An absolute
    # threshold is useless here: on a clean voice everything sits high, on a
    # screamed one everything sits low, and what matters either way is the line
    # that stands out from its neighbours.
    sures = sorted(ln["sure"] for ln in lines if ln.get("sure") is not None)
    weak = (sures[len(sures) // 2] * 0.5) if len(sures) >= 8 else None

    out = []
    for i, ln in enumerate(lines):
        ws = ln.get("words") or []
        why = []

        gaps = [ws[k + 1]["t"] - (ws[k]["t"] + ws[k]["d"]) for k in range(len(ws) - 1)]
        if gaps and max(gaps) > 1.2:
            why.append((tr(f"words drift apart by {max(gaps):.1f} s",
                           f"слова разъехались на {max(gaps):.1f} с"), "gap"))

        if i and lines[i - 1]["end"] > ln["start"] + 1e-6 \
                and (lines[i - 1].get("voice") or 1) == (ln.get("voice") or 1):
            # different voices overlapping is a duet — na-na-na behind the
            # lead — and flagging it would bury real warnings under noise
            why.append((tr("overlaps the previous line", "налезает на предыдущую"),
                        "overlap"))

        # There used to be a complaint about “held too long” here — wrongly:
        # a long note, a melisma, a tail at the end of a line is ordinary music,
        # not a timing error. That call belongs to whoever listens to the song.
        # Only the impossible is left: that many syllables cannot be sung.
        syl = sum((w.get("s") or 1) for w in ws) or 1
        span = ln["end"] - ln["start"]
        if span > 0 and syl and span / syl < 0.07:
            why.append((tr(f"{syl} syllables in {span:.1f} s — nobody sings that fast",
                           f"{syl} слогов за {span:.1f} с — столько не спеть"), "fast"))

        if env and voiced_at(ln["start"]) < floor * 1.05:
            why.append((tr("starts where no vocal is heard",
                           "начинается там, где вокала не слышно"), "quietstart"))

        if weak and ln.get("sure") is not None and ln["sure"] < weak:
            why.append((tr("the model barely heard these words — the timing is a guess",
                           "модель едва расслышала эти слова — время здесь наугад"),
                        "doubt"))

        # “Ignore”, the way a spell-checker has it: a warning dismissed for this
        # line stays dismissed. The key is the line's words, not its number —
        # numbers shift when lines are split or joined.
        off = set(data.get("checkOff") or [])
        text_key = (ln.get("text") or "").strip()
        why = [(msg, kind) for msg, kind in why
               if f"{text_key}|{kind}" not in off]
        if why:
            out.append({"line": i, "text": ln.get("text", ""),
                        "start": ln["start"],
                        "why": [m for m, _ in why],
                        "kinds": [k for _, k in why]})
    return out
