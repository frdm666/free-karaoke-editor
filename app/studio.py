#!/usr/bin/env python3
"""Karaoke Studio — a window instead of juggling files.

    py studio.py

A window opens with the list of songs and the editor. Edits go to disk at
once, nothing has to be rebuilt. The heavy parts (Demucs, Whisper) run once,
when the song is added.

Inside it is a plain local server: the browser is the window, all the work
happens in Python, which is the part with access to the files.
"""

from __future__ import annotations

import json
import math
import mimetypes
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from kstudio import i18n
from kstudio.i18n import tr
from kstudio import __version__            # noqa: E402
from kstudio import audio as AU            # noqa: E402
from kstudio import build as B             # noqa: E402
from kstudio import fetch as FE            # noqa: E402
from kstudio import findlyrics as FL       # noqa: E402
from kstudio import lang as LG            # noqa: E402
from kstudio import project as P           # noqa: E402
from kstudio import separate as S          # noqa: E402

UI = os.path.join(ROOT, "kstudio", "studio.html")
PROJECTS = P.projects_root()
JOBS: dict = {}
JOBS_LOCK = threading.Lock()


# --------------------------------------------------------------------------- #
#  Background jobs that report their progress
# --------------------------------------------------------------------------- #

def save_error(text: str) -> str:
    """Keep the whole error on disk: a console window scrolls, and it is gone.

    The job log holds one line of it; the traceback belongs somewhere a person
    can still read tomorrow, and can attach to a bug report.
    """
    path = os.path.join(PROJECTS, "last-error.txt")
    try:
        os.makedirs(PROJECTS, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S\n"))
            f.write(text)
        return path
    except OSError:
        return ""


def start_job(title: str, fn) -> str:
    jid = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[jid] = {"id": jid, "title": title, "log": [], "done": False,
                     "ok": False, "result": None, "error": None, "started": time.time()}

    def log(msg: str):
        with JOBS_LOCK:
            JOBS[jid]["log"].append(str(msg))
            del JOBS[jid]["log"][:-200]

    def run():
        try:
            res = fn(log)
            with JOBS_LOCK:
                JOBS[jid].update(done=True, ok=True, result=res)
        except Exception as e:
            from kstudio import sysinfo
            if sysinfo.is_memory_error(e):
                msg = sysinfo.memory_advice(sysinfo.NEED_DEMUCS, sysinfo.available_gb())
            else:
                msg = tr(f"Error: {e}", f"Ошибка: {e}")
                traceback.print_exc()
            for line in msg.splitlines():
                log(line)
            where = save_error(traceback.format_exc())
            if where:
                log(tr(f"The whole error is written to {where}",
                       f"Ошибка целиком записана в {where}"))
            with JOBS_LOCK:
                JOBS[jid].update(done=True, ok=False, error=msg.splitlines()[0])

    threading.Thread(target=run, daemon=True).start()
    return jid


# --------------------------------------------------------------------------- #

def dec_path(p: str) -> str:
    """Bring a path from a request into a sane shape.

    http.server parses the request line as latin-1, so non-Latin names arrive
    as garbage. We unfold %XX back into bytes and read them as UTF-8.
    """
    s = unquote(p, encoding="latin-1", errors="replace")
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def project_dir(pid: str) -> str:
    """Inside the projects folder only — a path from a request never escapes."""
    safe = os.path.basename(pid.strip().strip("/\\"))
    folder = os.path.join(PROJECTS, safe)
    if not os.path.isdir(folder) or os.path.dirname(os.path.abspath(folder)) != \
            os.path.abspath(PROJECTS):
        raise FileNotFoundError(pid)
    return folder


def incoming_dir() -> str:
    """Where everything that has no folder of its own lands: files dropped into
    the window, sound taken from a link, lyrics pasted by hand."""
    # In Latin letters: Cyrillic folder names break on non-Russian systems.
    inbox = os.path.join(PROJECTS, "_incoming")
    old = os.path.join(PROJECTS, "_входящие")
    if os.path.isdir(old) and not os.path.isdir(inbox):
        try:
            os.rename(old, inbox)                # an existing one moves by itself
        except OSError:
            inbox = old
    os.makedirs(inbox, exist_ok=True)
    return inbox


def capabilities() -> dict:
    have_ts = True
    try:
        import stable_whisper  # noqa: F401
    except ImportError:
        have_ts = False
    have_pil = True
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        have_pil = False
    ff = True
    try:
        AU.ffmpeg()
    except Exception:
        ff = False
    from kstudio import sysinfo
    return {"ffmpeg": ff, "whisper": have_ts, "demucs": S.available(),
            "pillow": have_pil, "version": __version__,
            # taking the sound out of a link, and where a suggested text
            # would come from — the window says both before it is asked
            "fetch": FE.available(), "fetchHelp": FE.how_to_install(),
            "lyricsSource": FL.SOURCE,
            "models": downloaded_models(),
            # how much memory is free and how much each model needs — so the
            # window can say “this one is heavy for your machine” beforehand
            "freeGb": sysinfo.available_gb(),
            "needGb": dict(sysinfo.NEED_WHISPER, demucs=sysinfo.NEED_DEMUCS),
            "langs": LG.NAMES}


def reveal(path: str) -> None:
    """Open the folder with the file and, if possible, highlight the file."""
    path = os.path.abspath(path)
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    if os.name == "nt":
        # /select shows the file selected — it is spotted straight away
        subprocess.Popen(["explorer", "/select,", path] if os.path.isfile(path)
                         else ["explorer", folder])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path] if os.path.isfile(path)
                         else ["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def extra_langs() -> list:
    """Language codes that have a translation file of their own."""
    folder = os.path.join(ROOT, "kstudio", "messages")
    try:
        return sorted(n[:-5] for n in os.listdir(folder)
                      if n.endswith(".json") and n != "template.json")
    except OSError:
        return []


def ui_lang() -> str:
    """Language of the window labels: env var, then settings, then “auto”."""
    val = (os.environ.get("KARAOKE_UI_LANG") or "").strip().lower()
    if val in ("en", "ru"):
        return val
    home = os.path.dirname(ROOT)
    ini = os.path.join(ROOT, "settings.ini")
    for other in (os.path.join(home, "settings.ini"),
                  os.path.join(home, "настройки.ini")):   # places from older versions
        if not os.path.isfile(ini) and os.path.isfile(other):
            ini = other
    try:
        with open(ini, encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, v = line.partition("=")
                if key.strip().lower() in ("надписи", "ui-lang"):
                    v = v.split("#")[0].strip().lower()
                    if v in ("en", "ru"):
                        return v
    except OSError:
        pass
    return "auto"


def make_report(audio: str, lyrics_path: str, opts: dict) -> dict:
    """A quick look at a pair of files — no Demucs, no Whisper, a second or two."""
    import tempfile

    from kstudio import lyrics as L
    from kstudio import report as REP

    lyr = L.load(lyrics_path)
    tmp = tempfile.mkdtemp(prefix="karaoke_rep_")
    try:
        wav = AU.to_wav(audio, os.path.join(tmp, "s.wav"))
        dur = AU.duration(wav)
        try:
            env, hop = AU.rms_envelope(wav)
        except Exception:
            env, hop = [], 0.02
        whisper = opts.get("align", "auto") != "energy" and capabilities()["whisper"]
        return REP.build(audio, lyr, dur, env, hop,
                         model=opts.get("model", "small"),
                         separate=bool(opts.get("separate", True)) and S.available(),
                         whisper=whisper,
                         language=opts.get("lang", "auto"))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def downloaded_models() -> dict:
    """Which Whisper models are already on disk.

    Otherwise the choice looks even: “medium — 1.5 GB” is no different from an
    already downloaded small, while the difference between them is several
    minutes of silence before the first timing pass. It counts the same thing
    the build log later reports.
    """
    from kstudio import models as M
    return M.whisper_all()


class Handler(BaseHTTPRequestHandler):
    server_version = "KaraokeStudio/" + __version__

    def log_message(self, fmt, *args):        # keep the console quiet
        pass

    # ---------------- sending ----------------
    def _send(self, code: int, body: bytes, ctype: str, extra: dict = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _err(self, code: int, msg: str):
        self._json({"error": msg}, code)

    def _file(self, path: str):
        """Serve audio with seeking support — the browser needs Range."""
        if not os.path.isfile(path):
            return self._err(404, tr("no such file", "нет файла"))
        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        code = 200
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
                if start >= size:
                    return self._err(416, tr("beyond the end of the file", "за пределами файла"))
                code = 206
        length = end - start + 1
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as f:
            f.seek(start)
            left = length
            while left > 0:
                chunk = f.read(min(262144, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return                       # the window closed or seeked away
                left -= len(chunk)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _local(self) -> bool:
        """Only requests to localhost are served: a page on the internet must not
        be able to reach the studio through a spoofed host name."""
        host = (self.headers.get("Host") or "").split(":")[0].strip("[]")
        return host in ("127.0.0.1", "localhost", "::1", "")

    # ---------------- routes ----------------
    def do_HEAD(self):
        self.do_GET()

    def _pick_lang(self):
        """The window language is chosen in the browser, the messages are built here.

        Without this the “Check” panel and the build log stayed Russian in an
        English window: the server knew nothing about the choice made there.
        """
        want = (self.headers.get("X-Karaoke-Lang") or "").strip().lower()
        if want in ("en", "ru"):
            i18n.set_lang(want)

    def do_GET(self):
        self._pick_lang()
        u = urlparse(self.path)
        if not self._local():
            return self._err(403, tr("this computer only", "только с этого компьютера"))
        path, q = dec_path(u.path), parse_qs(u.query)
        try:
            if path in ("/", "/index.html"):
                # Language of the window labels: from settings, otherwise from
                # the system. The button in the window still overrides it.
                with open(UI, encoding="utf-8") as f:
                    page = f.read().replace("__UI_LANG__", ui_lang())
                return self._send(200, page.encode("utf-8"),
                                  "text/html; charset=utf-8")

            if path == "/ui.js":
                with open(os.path.join(ROOT, "kstudio", "ui.js"), "rb") as f:
                    return self._send(200, f.read(),
                                      "application/javascript; charset=utf-8")

            if path == "/api/state":
                return self._json({"projects": P.list_all(PROJECTS),
                                   "uiLangs": extra_langs(),
                                   "caps": capabilities(),
                                   "projectsDir": PROJECTS})

            if path == "/api/job":
                with JOBS_LOCK:
                    job = JOBS.get(q.get("id", [""])[0])
                    return self._json(job or {"error": tr("no such task", "нет такой задачи")})

            if path == "/api/messages":
                # Extra languages live as JSON files next to the code, so adding
                # one needs no rebuild and no programming.
                code = (q.get("lang", [""])[0] or "").lower()
                if not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]+)?", code):
                    return self._err(400, tr("bad language code", "неверный код языка"))
                path_json = os.path.join(ROOT, "kstudio", "messages", code + ".json")
                if not os.path.isfile(path_json):
                    return self._json({})
                try:
                    with open(path_json, encoding="utf-8") as f:
                        return self._json(json.load(f))
                except (OSError, ValueError) as e:
                    return self._err(400, str(e))

            if path == "/api/browse":
                raw = q.get("path", [""])[0]
                try:
                    raw = raw.encode("latin-1").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
                return self._json(browse(raw, q.get("kind", ["audio"])[0]))

            m = re.match(r"^/api/project/([^/]+)$", path)
            if m:
                folder = project_dir(m.group(1))
                data = P.load(folder)
                data["problems"] = P.problems(data)
                data["quiet"] = P.quiet_spans(data)
                data["id"] = m.group(1)
                return self._json(data)

            m = re.match(r"^/api/project/([^/]+)/still$", path)
            if m:
                try:
                    at = float(q.get("at", ["0"])[0])
                except ValueError:
                    at = 0.0
                try:
                    png = still_frame(project_dir(m.group(1)), at,
                                      opening=q.get("opening", [""])[0] == "1")
                except Exception as e:
                    return self._err(400, str(e))
                return self._send(200, png, "image/png")

            m = re.match(r"^/api/project/([^/]+)/audio/([a-z]+)$", path)
            if m:
                folder = project_dir(m.group(1))
                tracks = P.load(folder).get("tracks") or {}
                name = tracks.get(m.group(2))
                if not name:
                    return self._err(404, tr("no such track", "нет такой дорожки"))
                return self._file(os.path.join(folder, name))

            return self._err(404, tr("not found", "не найдено"))
        except FileNotFoundError as e:
            # Not every missing file means a missing project: any such error
            # used to say “song not found”, leaving nowhere to look.
            self._err(404, tr("song not found", "проект не найден")
                      if "проект" in str(e).lower() or not str(e)
                      else tr(f"not found: {e}", f"не найдено: {e}"))
        except Exception as e:
            traceback.print_exc()
            self._err(500, str(e))

    def _upload(self, q):
        """A file dropped into the window. The browser gives no path, only the
        contents, so the bytes are taken and put next to the projects."""
        raw = (q.get("name", [""])[0] or "file")
        try:
            raw = raw.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        name = os.path.basename(raw.replace("\\", "/"))
        name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip() or "file"

        size = int(self.headers.get("Content-Length") or 0)
        if size <= 0:
            return self._err(400, tr("empty file", "пустой файл"))
        if size > 600 * 1024 * 1024:
            return self._err(413, tr("the file is larger than 600 MB", "файл больше 600 МБ"))

        inbox = incoming_dir()
        dst = os.path.join(inbox, name)
        stem, ext = os.path.splitext(dst)
        n = 2
        while os.path.exists(dst):
            dst = f"{stem}-{n}{ext}"
            n += 1

        left = size
        with open(dst, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(262144, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        if left > 0:
            os.remove(dst)
            return self._err(400, tr("the file did not arrive in full", "файл дошёл не полностью"))
        return self._json({"path": dst, "name": os.path.basename(dst)})

    def do_POST(self):
        self._pick_lang()
        u = urlparse(self.path)
        if not self._local():
            return self._err(403, tr("this computer only", "только с этого компьютера"))
        path = dec_path(u.path)
        q = parse_qs(u.query)
        try:
            if path == "/api/upload":
                return self._upload(q)
            body = self._body()

            if path == "/api/reveal":
                # Show the finished file in the file manager. Otherwise it has
                # to be hunted for — it sits next to the original song.
                target = body.get("path", "")
                if not os.path.exists(target):
                    return self._err(404, tr("the file is gone: ", "файла уже нет: ") + target)
                try:
                    reveal(target)
                    return self._json({"ok": True})
                except Exception as e:
                    return self._err(500, tr(f"could not open the folder: {e}", f"не вышло открыть папку: {e}"))

            if path == "/api/report":
                # The report before building: the song, the text, what to expect.
                audio, lyrics = body.get("audio", ""), body.get("lyrics", "")
                for f in (audio, lyrics):
                    if not os.path.isfile(f):
                        return self._err(400, tr(f"file not found: {f}", f"файл не найден: {f}"))
                try:
                    return self._json(make_report(audio, lyrics, body))
                except Exception as e:
                    return self._err(400, tr(f"could not make sense of the files: {e}", f"не вышло разобрать файлы: {e}"))

            if path == "/api/fetch":
                # The sound from a link. It is a long job with a log of its
                # own: a download can take a minute and can fail halfway.
                url = (body.get("url") or "").strip()
                try:
                    FE.check_url(url)
                except FE.FetchError as e:
                    return self._err(400, str(e))
                if not FE.available():
                    return self._err(400, FE.how_to_install())
                jid = start_job(tr("Taking the sound from the link",
                                   "Достаю звук по ссылке"),
                                lambda log: FE.download(url, incoming_dir(), log))
                return self._json({"job": jid})

            if path == "/api/lyrics/find":
                # A suggestion, not an answer: the words are shown to be read
                # before they are used.
                try:
                    found = FL.search(body.get("track", ""), body.get("artist", ""),
                                      float(body.get("duration") or 0))
                except FL.LyricsError as e:
                    return self._err(400, str(e))
                except Exception as e:
                    return self._err(400, str(e))
                return self._json({"source": FL.SOURCE, "found": found})

            if path == "/api/lyrics/save":
                # Lyrics pasted into the window. Everything downstream works
                # with a file on disk, so this makes one.
                text = (body.get("text") or "").strip()
                if not text:
                    return self._err(400, tr("the lyrics are empty", "текст пустой"))
                if len(text) > 400_000:
                    return self._err(413, tr("that is too much text for a song",
                                             "для песни это слишком много текста"))
                stem = re.sub(r'[<>:"|?*\\/\x00-\x1f]', "_",
                              (body.get("name") or "").strip())[:60].strip() or "lyrics"
                dst = os.path.join(incoming_dir(), stem + ".txt")
                base, n = dst[:-4], 2
                while os.path.exists(dst):
                    dst = f"{base}-{n}.txt"
                    n += 1
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(text.replace("\r\n", "\n").rstrip() + "\n")
                return self._json({"path": dst, "name": os.path.basename(dst)})

            if path == "/api/new":
                audio, lyrics = body.get("audio", ""), body.get("lyrics", "")
                for f in (audio, lyrics):
                    if not os.path.isfile(f):
                        return self._err(400, tr(f"file not found: {f}", f"файл не найден: {f}"))
                opts = dict(align_engine=body.get("align", "auto"),
                            whisper_model=body.get("model", "small"),
                            language=body.get("lang", "auto"),
                            separate=bool(body.get("separate", True)),
                            skip=body.get("noText") or "",
                            # four passes instead of one: a cleaner voice, and
                            # the timing is made from the voice
                            separator=("htdemucs_ft"
                                       if body.get("separator") == "htdemucs_ft"
                                       else "htdemucs"),
                            # a song taken from a link knows its own name;
                            # the file it landed in is called something safe
                            title=body.get("title") or "",
                            artist=body.get("artist") or "",
                            # typed into the field, not taken from a file name
                            title_set=bool(body.get("titleSet")),
                            # the clip's cover as the backdrop, if asked for
                            cover=body.get("cover") or None,
                            cover_bg=bool(body.get("coverBg")))
                jid = start_job(tr("Building the song", "Собираю песню"), lambda log: os.path.basename(
                    P.create(audio, lyrics, PROJECTS, log=log, **opts)))
                return self._json({"job": jid})

            m = re.match(r"^/api/project/([^/]+)/timings$", path)
            if m:
                folder = project_dir(m.group(1))
                lines = body.get("lines")
                if not isinstance(lines, list):
                    return self._err(400, tr("no lines", "нет строк"))
                data = P.save_lines(folder, lines, colors=body.get("colors"),
                                    theme=body.get("theme"),
                                    no_text=body.get("noText"),
                                    keep_marks=body.get("keepMarks"),
                                    check_off=body.get("checkOff"),
                                    title=body.get("title"),
                                    artist=body.get("artist"),
                                    cover_dark=body.get("coverDark"),
                                    grid=body.get("grid"))
                return self._json({"ok": True, "problems": P.problems(data)})

            m = re.match(r"^/api/project/([^/]+)/cover$", path)
            if m:
                folder = project_dir(m.group(1))
                data = P.load(folder)
                if body.get("remove"):
                    # back to the woven gradient — the cover files go too
                    for name in ["cover.jpg"] + [n for n in os.listdir(folder)
                                                 if n.startswith("cover-")
                                                 and n.endswith(".jpg")]:
                        try:
                            os.remove(os.path.join(folder, name))
                        except OSError:
                            pass
                    data["cover"] = None
                    data["coverBg"] = False
                    data["coverSet"] = None
                    P.save(folder, data)
                    return self._json({"ok": True, "cover": False})
                src = (body.get("path") or body.get("url") or "").strip()
                tmp_dl = None
                if re.match(r"^https?://", src):
                    # a link to a picture: fetched here, sized within reason,
                    # and treated like any file from then on
                    try:
                        tmp_dl = fetch_cover_url(src)
                        src = tmp_dl
                    except Exception as e:
                        return self._err(400, tr(f"could not fetch the picture: {e}",
                                                 f"не вышло скачать картинку: {e}"))
                if not os.path.isfile(src):
                    return self._err(400, tr("no such file", "нет такого файла"))
                try:
                    names = set_cover(folder, src)
                except Exception as e:
                    return self._err(400, tr(f"could not read a picture out of it: {e}",
                                             f"не вышло достать картинку: {e}"))
                finally:
                    if tmp_dl:
                        try:
                            os.remove(tmp_dl)
                        except OSError:
                            pass
                data = P.load(folder)
                data["cover"] = "cover.jpg"
                data["coverBg"] = True
                # a clip gives several frames: the video plays them as a slow
                # slideshow; a single picture stays a single picture
                data["coverSet"] = names if len(names) > 1 else None
                P.save(folder, data)
                return self._json({"ok": True, "cover": True,
                                   "frames": len(names)})

            m = re.match(r"^/api/project/([^/]+)/backdrop$", path)
            if m:
                folder = project_dir(m.group(1))
                data = P.load(folder)
                if body.get("off"):
                    for old in os.listdir(folder):
                        if old.startswith("backdrop."):
                            try:
                                os.remove(os.path.join(folder, old))
                            except OSError:
                                pass
                    data["backdrop"] = None
                    P.save(folder, data)
                    return self._json({"ok": True, "backdrop": False})
                src = (body.get("path") or body.get("url") or "").strip()
                got = None
                if re.match(r"^https?://", src):
                    # The link the song itself came from will do: the backdrop
                    # is asked for at the smallest size the site offers, since
                    # it is blurred past recognising anyway.
                    try:
                        got = FE.clip(src, folder)
                        src = got
                    except Exception as e:
                        return self._err(400, tr(f"could not fetch the clip: {e}",
                                                 f"не вышло скачать клип: {e}"))
                if not os.path.isfile(src):
                    return self._err(400, tr("no such file", "нет такого файла"))
                try:
                    name = set_backdrop(folder, src)
                except Exception as e:
                    return self._err(400, tr(f"not a clip: {e}",
                                             f"это не клип: {e}"))
                finally:
                    if got and os.path.isfile(got):
                        try:
                            os.remove(got)
                        except OSError:
                            pass
                data = P.load(folder)
                data["backdrop"] = name
                P.save(folder, data)
                return self._json({"ok": True, "backdrop": True})

            m = re.match(r"^/api/project/([^/]+)/pack$", path)
            if m:
                folder = project_dir(m.group(1))
                data = P.load(folder)
                # Next to the audio it came from, where a person will find it.
                out_dir = os.path.dirname(data.get("source_audio") or "") or PROJECTS
                if not os.path.isdir(out_dir):
                    out_dir = PROJECTS
                try:
                    return self._json({"path": P.pack(folder, out_dir)})
                except (OSError, ValueError) as e:
                    return self._err(400, str(e))

            if path == "/api/unpack":
                src = (body.get("path") or "").strip()
                if not os.path.isfile(src):
                    return self._err(400, tr("no such file", "нет такого файла"))
                try:
                    folder = P.unpack(src, PROJECTS)
                except Exception as e:
                    # a corrupt zip raises its own kind — the answer is the
                    # same calm sentence, not a stack trace
                    return self._err(400, str(e))
                return self._json({"id": os.path.basename(folder)})

            m = re.match(r"^/api/project/([^/]+)/delete$", path)
            if m:
                P.delete(project_dir(m.group(1)))
                return self._json({"ok": True})

            m = re.match(r"^/api/project/([^/]+)/track$", path)
            if m:
                folder = project_dir(m.group(1))
                src = body.get("path", "")
                kind = body.get("track", "instrumental")
                shift = bool(body.get("shift", True))
                jid = start_job(tr("Swapping the track", "Меняю дорожку"),
                                lambda log: replace_track(folder, src, kind, shift, log))
                return self._json({"job": jid})

            m = re.match(r"^/api/project/([^/]+)/realign-part$", path)
            if m:
                folder = project_dir(m.group(1))
                jid = start_job(tr("Timing a few lines again",
                                   "Размечаю несколько строк заново"),
                                lambda log: realign_part(folder, body, log))
                return self._json({"job": jid})

            m = re.match(r"^/api/project/([^/]+)/realign$", path)
            if m:
                folder = project_dir(m.group(1))
                jid = start_job(tr("Recomputing the timing", "Пересчитываю разметку"),
                                lambda log: realign(folder, body, log))
                return self._json({"job": jid})

            m = re.match(r"^/api/project/([^/]+)/export$", path)
            if m:
                folder = project_dir(m.group(1))
                kind = body.get("kind", "html")
                jid = start_job(tr("Export ", "Экспорт ") + kind,
                                lambda log: export(folder, kind, body, log))
                return self._json({"job": jid})

            return self._err(404, tr("not found", "не найдено"))
        except FileNotFoundError as e:
            # Not every missing file means a missing project: any such error
            # used to say “song not found”, leaving nowhere to look.
            self._err(404, tr("song not found", "проект не найден")
                      if "проект" in str(e).lower() or not str(e)
                      else tr(f"not found: {e}", f"не найдено: {e}"))
        except Exception as e:
            traceback.print_exc()
            self._err(500, str(e))


# --------------------------------------------------------------------------- #

AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".opus", ".aac", ".wma", ".mp4"}
TEXT_EXT = {".txt", ".lrc"}


def browse(path: str, kind: str) -> dict:
    """A simple folder browser — the browser gives us no file dialogs."""
    exts = {"audio": AUDIO_EXT, "pack": (".zip",),
            # a cover can be cut out of the clip itself, so videos count too
            "image": (".jpg", ".jpeg", ".png", ".webp", ".bmp",
                      ".mp4", ".mkv", ".webm", ".mov")}.get(kind, TEXT_EXT)
    if not path:
        path = os.path.expanduser("~")
    path = os.path.abspath(path)
    # A remembered folder can vanish: a stick was pulled out, a folder renamed.
    # Walk up until an existing one is found instead of failing with an error.
    while path and not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    if not os.path.isdir(path):
        path = os.path.expanduser("~")

    dirs, files = [], []
    try:
        for name in sorted(os.listdir(path), key=str.lower):
            full = os.path.join(path, name)
            if name.startswith("."):
                continue
            if os.path.isdir(full):
                dirs.append({"name": name, "path": full})
            elif os.path.splitext(name)[1].lower() in exts:
                files.append({"name": name, "path": full,
                              "size": os.path.getsize(full)})
    except (PermissionError, OSError):
        pass                      # no rights, or it vanished between checks

    drives = []
    if os.name == "nt":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            d = f"{letter}:\\"
            if os.path.exists(d):
                drives.append(d)

    return {"path": path, "parent": os.path.dirname(path) or path,
            "dirs": dirs, "files": files, "drives": drives}


def realign_part(folder: str, opts: dict, log) -> dict:
    """Time a handful of lines again, and leave the rest of the song alone.

    On a long song the timing is wrong in one place and right everywhere else,
    and redoing all of it costs minutes and throws away every correction made
    by hand. Here the model is shown only the stretch between the neighbours of
    the chosen lines — the same trick as with the wordless stretches — and only
    those lines are written back.
    """
    from kstudio import align as A
    from kstudio import lyrics as L

    data = P.load(folder)
    lines = data.get("lines") or []
    try:
        a = max(0, int(opts.get("from", -1)))
        b = min(len(lines) - 1, int(opts.get("to", -1)))
    except (TypeError, ValueError):
        a = b = -1
    if not lines or a < 0 or b < a:
        raise ValueError(tr("no lines were chosen to be timed again",
                            "не выбрано строк для переразметки"))

    dur = float(data["duration"])
    lo = float(lines[a - 1]["end"]) if a else 0.0
    hi = float(lines[b + 1]["start"]) if b + 1 < len(lines) else dur
    if hi - lo < 0.5:
        raise ValueError(tr("the neighbouring lines leave no room to work in",
                            "между соседними строками не осталось места"))

    text = "\n".join((ln.get("text") or "") for ln in lines[a:b + 1])
    piece = L.parse(text)
    if len(piece.lines) != b - a + 1:
        raise ValueError(tr("the chosen lines could not be read back as text",
                            "выбранные строки не удалось прочитать обратно как текст"))

    tracks = data.get("tracks") or {}
    stem = tracks.get("vocals") or tracks.get("mix") or tracks.get("instrumental")
    audio = os.path.join(folder, stem)
    AU.ensure_on_path()
    model = (opts.get("model") or data.get("model") or "small")
    log(tr(f"Timing lines {a + 1}–{b + 1} again, inside {A.mmss(lo)}–{A.mmss(hi)}, "
           f"with “{model}”",
           f"Размечаю заново строки {a + 1}–{b + 1} в пределах {A.mmss(lo)}–{A.mmss(hi)}, "
           f"моделью «{model}»"))
    # Everything outside the window is “no words here”: the model is shown the
    # stretch alone, and the times come back in the whole song's own reckoning.
    # The marks made for the song hold inside the window too — a vocalise does
    # not stop being one because only four lines are being retimed around it.
    outside = [(0.0, lo)] if lo > 0.05 else []
    if hi < dur - 0.05:
        outside.append((hi, dur))
    outside += A.spans(opts.get("noText") if opts.get("noText") is not None
                       else (data.get("noText") or ""), dur)
    piece, engine = A.align(piece, audio, dur, opts.get("align", "auto"), model,
                            opts.get("lang", "auto"), None, log,
                            isolated=bool(tracks.get("vocals")), skip=outside)

    fresh = [ln.to_json() for ln in piece.lines]
    moved = 0
    for k, got in enumerate(fresh):
        old = lines[a + k]
        if old.get("lock"):
            continue                       # locked by hand: not ours to touch
        old["start"], old["end"] = got["start"], got["end"]
        old["words"] = got["words"]
        if got.get("sure") is not None:
            old["sure"] = got["sure"]
        moved += 1
    data["lines"] = lines
    data["edited"] = time.time()
    P.save(folder, data)
    log(tr(f"Lines timed again: {moved}. The rest of the song was not touched.",
           f"Размечено заново строк: {moved}. Остальная песня не тронута."))
    return {"kind": "realign-part", "engine": engine, "lines": moved,
            "from": a, "to": b}


def realign(folder: str, opts: dict, log) -> dict:
    """Recompute the timing — for instance once stable-ts has been installed.
    The stems are already in the project, so Demucs is not run again."""
    from kstudio import align as A
    from kstudio import lyrics as L

    data = P.load(folder)
    # The text can be swapped: people re-split lines for easier singing after
    # the first build, and that is no reason to redo everything.
    fresh = (opts.get("lyrics") or "").strip()
    if fresh:
        if not os.path.isfile(fresh):
            raise FileNotFoundError(tr("lyrics file not found: ", "файл с текстом не найден: ") + fresh)
        src = fresh
        log(tr(f"Taking the lyrics from {os.path.basename(src)}",
               f"Беру текст из {os.path.basename(src)}"))
    else:
        src = data.get("source_lyrics")
        if not src or not os.path.isfile(src):
            raise FileNotFoundError(tr(
                "the source lyrics file was not found: " + str(src) +
                ". Pick a file with the “Other lyrics” button.",
                "исходный файл с текстом не найден: " + str(src) +
                ". Выберите файл кнопкой «Заменить текст»."))
    lyr = L.load(src)
    was = len(data.get("lines") or [])
    if len(lyr.lines) != was:
        log(tr(f"The text now has {len(lyr.lines)} lines instead of {was} — "
               f"the timing will be worked out for the new split.",
               f"В тексте теперь {len(lyr.lines)} строк вместо {was} — "
               f"разметка будет посчитана под новую разбивку."))
    if not lyr.lines:
        raise ValueError(tr("the lyrics file has no lines at all",
                            "в файле с текстом не нашлось ни одной строки"))

    tracks = data.get("tracks") or {}
    stem = tracks.get("vocals") or tracks.get("mix") or tracks.get("instrumental")
    audio = os.path.join(folder, stem)
    AU.ensure_on_path()
    holes = A.spans(opts.get("noText") or "", data["duration"]) + \
        A.spans(getattr(lyr, "skips", []), data["duration"])
    # A line locked by hand is a peg for the aligner: the text around it cannot
    # wander off across the song, because the model is only ever shown the
    # stretch between two pegs. The line itself is put back exactly afterwards.
    old_lines = data.get("lines") or []
    if len(old_lines) == len(lyr.lines):
        pegs = 0
        for i, was_ln in enumerate(old_lines):
            if was_ln.get("lock"):
                lyr.lines[i].start = float(was_ln.get("start") or 0.0)
                pegs += 1
        if pegs and pegs < len(lyr.lines):
            lyr.has_manual_times = True
            log(tr(f"Locked lines are used as pegs: {pegs}",
                   f"Запертые строки взяты как опорные точки: {pegs}"))
        elif pegs:
            # Everything is locked: there is nothing left for the aligner to do,
            # and pretending otherwise would rewrite the words inside the lines.
            log(tr("Every line is locked — nothing to time again.",
                   "Заперты все строки — размечать нечего."))
            return {"kind": "realign", "engine": data.get("engine", ""),
                    "lines": len(lyr.lines), "was": was}

    # The model the song was built with, unless another is asked for outright.
    # It used to fall back to “small” here: a person picked medium, pressed
    # “Re-time”, and got a worse timing than the one they were fixing.
    model = (opts.get("model") or data.get("model") or "small")
    log(tr(f"Model: {model}", f"Модель: {model}"))
    lyr, engine = A.align(lyr, audio, data["duration"],
                          opts.get("align", "auto"), model,
                          opts.get("lang", "auto"), None, log,
                          isolated=bool((data.get("tracks") or {}).get("vocals")),
                          skip=holes)
    fresh = [ln.to_json() for ln in lyr.lines]
    # A line put right by hand outweighs anything a model returns for it.
    P.keep_locked(data.get("lines") or [], fresh, log)
    data["lines"] = fresh
    data["engine"] = engine
    data["noText"] = ", ".join(f"{a:.1f}-{b:.1f}" for a, b in holes)
    data["keepSpans"] = P.keep_spans(data)
    data["model"] = model
    data["source_lyrics"] = os.path.abspath(src)
    # A name typed by hand outlives a re-timing: the header of a lyrics file
    # does not get to rename a song its owner has already named.
    if not data.get("titleSet"):
        data["title"] = lyr.title or data.get("title") or ""
    if lyr.artist and not data.get("titleSet"):
        data["artist"] = lyr.artist
    data["edited"] = time.time()
    P.save(folder, data)
    log(tr("The timing has been recomputed.", "Разметка пересчитана."))
    return {"kind": "realign", "engine": engine,
            "lines": len(lyr.lines), "was": was}


def offset_between(a: list, b: list, hop: float, limit: float = 12.0) -> float:
    """How far the second recording is shifted against the first, in seconds.

    An official instrumental almost always starts somewhere else than the
    mixed song: a different count-in, a different pause before the intro.

    Two subtleties a straightforward search gets wrong:
      • music repeats, so there are many matches — at a bar, at a verse. Among
        equally good ones we take the one CLOSEST to zero, not the first found:
        we are looking for a mismatch of the start, not for the chorus.
      • the envelope step is coarser than the ear. First we search coarsely and
        fast, then refine nearby and finish the peak off with a parabola.
    """
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    a = [x - ma for x in a]
    b = [x - mb for x in b]

    def score(sh: int, step: int = 2) -> float:
        lo, hi = max(0, -sh), min(n, n - sh)
        if hi - lo < n // 4:
            return -1e18
        s = 0.0
        for i in range(lo, hi, step):
            s += a[i] * b[i + sh]
        return s / (hi - lo)

    # 1. Coarse: look at every fourth lag and sample the signal more sparsely.
    span = int(limit / hop)
    coarse = max(1, int(0.04 / hop))
    rough = [(score(sh, 8), sh) for sh in range(-span, span + 1, coarse)]
    best_s = max(v for v, _ in rough)
    if best_s <= 0:
        return 0.0
    # Among the near-equally good peaks, take the one closest to zero.
    near = [sh for v, sh in rough if v >= best_s * 0.97]
    guess = min(near, key=abs)

    # 2. Fine: around the winner, at full resolution.
    lo, hi = guess - 2 * coarse, guess + 2 * coarse
    fine = [(score(sh), sh) for sh in range(lo, hi + 1)]
    best_s, best = max(fine)
    near = [sh for v, sh in fine if v >= best_s * 0.995]
    best = min(near, key=abs)
    best_s = dict((sh, v) for v, sh in fine)[best]

    # 3. Refine the peak with a parabola: a real shift rarely lands on a step.
    left, right = score(best - 1), score(best + 1)
    frac = 0.0
    if left > -1e17 and right > -1e17:
        denom = left - 2 * best_s + right
        if denom != 0:
            frac = max(-0.5, min(0.5, 0.5 * (left - right) / denom))
    return round((best + frac) * hop, 4)


def shift_audio(path: str, seconds: float, tmp: str) -> str:
    """Shift a recording in time: positive — later, negative — earlier."""
    out = os.path.join(tmp, "shifted.wav")
    if seconds >= 0:
        ms = int(round(seconds * 1000))
        flt = f"adelay={ms}|{ms}"
    else:
        flt = f"atrim=start={abs(seconds):.3f},asetpts=PTS-STARTPTS"
    p = subprocess.run([AU.ffmpeg(), "-y", "-loglevel", "error", "-i", path,
                        "-af", flt, out], capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(out):
        raise RuntimeError((p.stderr or tr("ffmpeg could not cope", "ffmpeg не справился")).strip()[:200])
    return out


def _best_gain(mix: str, instr: str, spans: list) -> float:
    """By how much to scale the instrumental so it cancels the original best.

    Computed on the real samples, not on the envelope: the envelope is
    normalised to each recording's own maximum, so a ratio taken from it means
    nothing. The solution is simple: k = <mix·instrumental> /
    <instrumental·instrumental> — the value at which the difference is quietest.
    """
    sr = 16000
    a = AU.read_pcm_mono(mix, sr)
    b = AU.read_pcm_mono(instr, sr)
    n = min(len(a), len(b))
    if not n:
        return 1.0
    idx = []
    for x, y in (spans or [(0, n / sr)]):
        idx.append((max(0, int(x * sr)), min(n, int(y * sr))))
    num = den = 0.0
    for lo, hi in idx:
        for i in range(lo, hi, 4):          # every fourth sample is precise enough
            av, bv = a[i], b[i]
            num += av * bv
            den += bv * bv
    if den <= 0:
        return 1.0
    return max(0.1, min(10.0, num / den))


def _rms_at(path: str, spans: list) -> float:
    """The real loudness of a recording over the given spans, unnormalised."""
    sr = 16000
    x = AU.read_pcm_mono(path, sr)
    total = cnt = 0.0
    for a, b in (spans or [(0, len(x) / sr)]):
        for i in range(max(0, int(a * sr)), min(len(x), int(b * sr)), 4):
            total += float(x[i]) ** 2
            cnt += 1
    return (total / cnt) ** 0.5 if cnt else 0.0


def _spectral_vocals(mix: str, instr: str, spans: list, out: str, log) -> Optional[str]:
    """Subtract the instrumental per frequency band, not by one volume level.

    An official instrumental hardly ever matches the one sitting under the
    voice in the song: different mastering, different equalisation, different
    level. One multiplier cannot cancel that — part of the arrangement stays in
    the “voice” and plays next to the backing track like a second, foreign
    recording.

    So the multiplier is found per frequency. Over the spans without singing,
    where both tracks ought to be the same, we compute
    H(f) = <M·conj(I)> / <|I|²> — exactly the gain and phase shift that turn the
    instrumental into its own copy from the song. Then the corrected
    instrumental is what gets subtracted.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    if not spans:
        return None

    sr = 44100
    a = np.frombuffer(AU.read_pcm_mono(mix, sr).tobytes(), dtype="<i2").astype(np.float32) / 32768.0
    b = np.frombuffer(AU.read_pcm_mono(instr, sr).tobytes(), dtype="<i2").astype(np.float32) / 32768.0
    n = min(len(a), len(b))
    N, hop = 4096, 1024                  # 93 ms window, 75 % overlap
    if n < N * 4:
        return None
    a, b = a[:n], b[:n]
    win = np.hanning(N + 1)[:N].astype(np.float32)
    frames = 1 + (n - N) // hop
    idx = np.arange(N)[None, :] + hop * np.arange(frames)[:, None]

    A = np.fft.rfft(a[idx] * win, axis=1)
    B = np.fft.rfft(b[idx] * win, axis=1)

    # frames that fall entirely inside the stretches without singing
    mask = np.zeros(frames, dtype=bool)
    for lo, hi in spans:
        i0 = max(0, int((lo * sr) // hop))
        i1 = min(frames, int(((hi * sr) - N) // hop) + 1)
        if i1 > i0:
            mask[i0:i1] = True
    if int(mask.sum()) < 12:             # nothing to measure on
        return None

    num = (A[mask] * np.conj(B[mask])).sum(axis=0)
    den = (np.abs(B[mask]) ** 2).sum(axis=0)
    quiet_bins = den < den.max() * 1e-9  # where there is no instrumental, nothing to cancel
    H = num / np.where(den > 0, den, 1.0)
    H[quiet_bins] = 0.0

    # Smooth across frequency: neighbouring bands cannot differ threefold, and
    # an estimate from a single silent stretch is noisy.
    k = 5
    pad = np.r_[H[:k][::-1], H, H[-k:][::-1]]
    H = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
    mag = np.abs(H)
    H = np.where(mag > 4.0, H / np.maximum(mag, 1e-9) * 4.0, H)

    V = A - H[None, :] * B
    frag = np.fft.irfft(V, n=N, axis=1).astype(np.float32) * win
    voice = np.zeros(n, dtype=np.float32)
    norm = np.zeros(n, dtype=np.float32)
    w2 = win ** 2
    for i in range(frames):
        j = i * hop
        voice[j:j + N] += frag[i]
        norm[j:j + N] += w2
    voice /= np.maximum(norm, 1e-6)

    import wave
    pcm = np.clip(voice, -1.0, 1.0)
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())
    log(tr("  the instrumental was matched per frequency, not by one volume",
           "  инструментал выровнен по частотам, а не одной громкостью"))
    return out


def extract_vocals(mix: str, instr: str, off: float, quiet: list, tmp: str,
                   log) -> Optional[str]:
    """Voice ≈ the original minus the instrumental.

    When the instrumental comes from the same artist and the same recording,
    the difference between the two tracks is the vocal. Otherwise the whole
    original stays as “the voice”, and a second arrangement plays on top of the
    new backing track: that is exactly what is heard as “the voice does not
    match”.

    Returns the path to the track, or None if the subtraction did not work.
    """
    # 1. Bring the original into the same time frame as the new instrumental.
    aligned = mix if abs(off) < 0.005 else shift_audio(mix, off, tmp)

    # 2. Fit the level: an instrumental almost always has a different one.
    #    Measure where nobody sings — there both tracks must sound the same.
    spans = [(q["start"], q["end"]) for q in quiet] or None
    k = _best_gain(aligned, instr, spans)
    log(tr(f"  instrumental volume matched: ×{k:.2f}",
            f"  громкость инструментала подобрана: ×{k:.2f}"))

    # 3. Subtract. amerge puts both recordings into two channels, pan takes the
    #    difference between them.
    out = os.path.join(tmp, "voice.wav")
    flt = (f"[1:a]volume={k:.4f}[i];[0:a][i]amerge=inputs=2,"
           f"pan=mono|c0=c0-c1[out]")
    p = subprocess.run([AU.ffmpeg(), "-y", "-loglevel", "error",
                        "-i", aligned, "-i", instr,
                        "-filter_complex", flt, "-map", "[out]", out],
                       capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(out):
        log(tr(f"  subtracting the instrumental failed ({(p.stderr or '').strip()[:80]})",
               f"  вычесть инструментал не вышло ({(p.stderr or '').strip()[:80]})"))
        return None

    # 3b. The same, but corrected per frequency. Usually noticeably cleaner;
    #     whichever leaves the silent stretches quieter wins.
    spec = _spectral_vocals(aligned, instr, spans, os.path.join(tmp, "voice_f.wav"), log)
    if spec and spans:
        r_plain, r_spec = _rms_at(out, spans), _rms_at(spec, spans)
        if r_spec < r_plain * 0.9:
            gain = 20 * math.log10(max(r_spec, 1e-9) / max(r_plain, 1e-9))
            log(tr(f"  per frequency, {-gain:.0f} dB less of the arrangement is left",
                   f"  по частотам аранжировки осталось на {-gain:.0f} дБ меньше"))
            out = spec
        else:
            log(tr("  plain subtraction was no worse — taking that",
                   "  простое вычитание оказалось не хуже — беру его"))

    # 4. Check that it got quieter exactly where nobody sings. If it did not,
    #    the instrumental belongs to another recording and must not be used.
    if spans:
        before, after = _rms_at(aligned, spans), _rms_at(out, spans)
        if before > 1e-6:
            drop = 20 * math.log10(max(after, 1e-9) / before)
            log(tr(f"  where nobody sings it got {-drop:.0f} dB quieter",
                   f"  в местах без пения стало тише на {-drop:.0f} дБ"))
            if drop > -4.0:
                log(tr("  the instrumental does not match the original — not extracting the voice",
                       "  инструментал не совпал с оригиналом — голос не выделяю"))
                return None
    return out


def replace_track(folder: str, src: str, kind: str, shift: bool, log) -> dict:
    """Swap a track in a finished project, leaving the timing in place.

    The point: the timing is already tuned by hand, and what is wanted is the
    real backing track — the one the artist released. Nothing has to be
    recomputed, only the audio changes.
    """
    if kind not in ("instrumental", "vocals", "mix"):
        raise ValueError(tr(f"unknown track: {kind}", f"неизвестная дорожка: {kind}"))
    if not os.path.isfile(src):
        raise FileNotFoundError(src)

    data = P.load(folder)
    tracks = dict(data.get("tracks") or {})
    old_name = tracks.get(kind)

    import tempfile
    tmp = tempfile.mkdtemp(prefix="karaoke_track_")
    try:
        AU.ffmpeg(); AU.ensure_on_path()
        log(tr(f"Preparing {os.path.basename(src)}…", f"Готовлю {os.path.basename(src)}…"))
        wav = AU.to_wav(src, os.path.join(tmp, "new.wav"))
        new_dur = AU.duration(wav)
        old_dur = float(data.get("duration") or 0)
        log(tr(f"Length of the new track: {int(new_dur//60)}:{int(new_dur%60):02d}"
               f" (in the song {int(old_dur//60)}:{int(old_dur%60):02d})",
               f"Длина новой дорожки: {int(new_dur//60)}:{int(new_dur%60):02d}"
               f" (в проекте {int(old_dur//60)}:{int(old_dur%60):02d})"))

        # The shift is measured against the track already in the project.
        off = 0.0
        ref = old_name or tracks.get("mix") or tracks.get("vocals")
        if ref:
            try:
                # A finer step means a finer shift. 10 ms is still fast, and the
                # error is half of what the usual 20 ms gives.
                ea, ha = AU.rms_envelope(os.path.join(folder, ref), hop_ms=10)
                eb, _ = AU.rms_envelope(wav, hop_ms=10)
                off = offset_between(ea, eb, ha)
            except Exception as e:                        # pragma: no cover
                log(tr(f"  could not work out the shift ({e})", f"  сдвиг определить не вышло ({e})"))
        if abs(off) >= 0.05:
            log(tr(f"The new track runs {'later' if off > 0 else 'earlier'} than the "
                   f"old one by {abs(off):.2f} s.",
                   f"Новая дорожка идёт {'позже' if off > 0 else 'раньше'} прежней "
                   f"на {abs(off):.2f} с."))
        else:
            log(tr("The start matches the previous track.", "Начало совпадает с прежней дорожкой."))

        log(tr("Encoding…", "Кодирую…"))
        name = os.path.basename(AU.encode(wav, os.path.join(folder, kind + "_new"),
                                          "mp3")[0])
        tracks[kind] = name
        made_voice = False
        if kind == "instrumental" and "mix" in tracks:
            # There was one mixed track. Keeping it as the “voice” is wrong: a
            # second arrangement would play over the new instrumental. Try to get
            # the real voice by subtraction — the original minus the instrumental.
            from kstudio import report as REP
            mix_path = os.path.join(folder, tracks["mix"])
            log(tr("Trying to extract the voice: the original minus your instrumental…",
                "Пробую выделить голос: оригинал минус ваш инструментал…"))
            try:
                menv, mhop = AU.rms_envelope(mix_path)
                quiet = REP.quiet_stretches(menv, mhop)
            except Exception:
                quiet = []
            voice = extract_vocals(mix_path, wav, off, quiet, tmp, log)
            if voice:
                tracks["vocals"] = os.path.basename(
                    AU.encode(voice, os.path.join(folder, "vocals_sub"), "mp3")[0])
                try:
                    os.remove(mix_path)
                except OSError:
                    pass
                tracks.pop("mix", None)
                data["envelope"] = P.build_envelope(voice, log)
                made_voice = True
                log(tr("The voice was extracted — that is what you sing to, and the waveform "
                       "comes from it.",
                       "Голос выделен — под него и поётся, волна на дорожке от него же."))
            else:
                # It did not work — dropping the vocal track altogether is
                # honester than passing off the whole song as the voice.
                try:
                    os.remove(mix_path)
                except OSError:
                    pass
                tracks.pop("mix", None)
                log(tr("There will be no voice: only your instrumental plays.",
                       "Голоса не будет: играет только ваша минусовка."))

        moved = 0.0
        if shift and abs(off) >= 0.02:
            for ln in data.get("lines") or []:
                ln["start"] += off; ln["end"] += off
                for w in ln.get("words") or []:
                    w["t"] += off
            moved = off
            log(tr(f"The timing was shifted by {off:+.3f} s along with the track.",
                f"Разметку сдвинул на {off:+.3f} с вслед за дорожкой."))

            # The voice too: it is still in the old time frame while the
            # instrumental has moved. Otherwise the vocal is out of step.
            voc = None if made_voice else tracks.get("vocals")
            if voc:
                try:
                    shifted = shift_audio(os.path.join(folder, voc), off, tmp)
                    new_voc = os.path.basename(
                        AU.encode(shifted, os.path.join(folder, "vocals_new"), "mp3")[0])
                    old_voc = os.path.join(folder, voc)
                    tracks["vocals"] = new_voc
                    if os.path.basename(old_voc) != new_voc:
                        try:
                            os.remove(old_voc)
                        except OSError:
                            pass
                    log(tr("The voice was moved by the same amount — it is in time with the "
                           "instrumental now.",
                           "Голос подвинут на столько же — теперь он в такт с минусовкой."))
                    data["envelope"] = P.build_envelope(shifted, log)
                except Exception as e:
                    log(tr(f"  could not move the voice ({e}) — turn it down with the slider",
                           f"  голос подвинуть не вышло ({e}) — приглушите его ползунком"))

        data["tracks"] = tracks
        data["duration"] = round(max(old_dur, new_dur), 3)
        data["edited"] = time.time()
        P.save(folder, data)

        if old_name and old_name != name:
            try:
                os.remove(os.path.join(folder, old_name))
            except OSError:
                pass
        log(tr("Done.", "Готово."))
        return {"kind": "track", "track": kind, "offset": off, "shifted": moved,
                "duration": data["duration"], "lengthDiff": round(new_dur - old_dur, 2)}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def export(folder: str, kind: str, opts: dict, log) -> dict:
    """Export: a standalone HTML page or an MP4 video."""
    data = P.load(folder)
    lyr = _lyrics_from(data)
    tracks = {}
    for name, fname in (data.get("tracks") or {}).items():
        path = os.path.join(folder, fname)
        mime = mimetypes.guess_type(path)[0] or "audio/mpeg"
        tracks[name] = (path, mime)

    out_dir = os.path.dirname(data.get("source_audio") or folder) or folder
    base = P.slugify(data.get("title") or "karaoke")

    if kind == "html":
        # A Latin name: the file travels to people where Cyrillic in file names
        # turns into mojibake.
        out = os.path.join(out_dir, base + "_karaoke.html")
        log(tr("Building the standalone page…", "Собираю автономную страницу…"))
        B.build_html(out, lyr, data["duration"], tracks, data.get("engine", ""),
                     embed=True, title=data.get("title"), artist=data.get("artist"),
                     colors=data.get("colors"), theme=data.get("theme"),
                     keep_spans=P.keep_spans(data),
                     cover_path=(os.path.join(folder, data["cover"])
                                 if data.get("coverBg") and data.get("cover") else None),
                     cover_dark=data.get("coverDark"),
                     cover_paths=([os.path.join(folder, n)
                                   for n in data.get("coverSet") or []]
                                  if data.get("coverBg") else None),
                     grid=data.get("grid"))
        log(tr(f"Done: {out}", f"Готово: {out}"))
        return {"kind": "html", "path": out}

    if kind == "ultrastar":
        from kstudio import interop
        # The singing games want the song itself beside the text. The audio it
        # was built from is named when it is still there; otherwise the track
        # the project keeps is laid out next to the file.
        src = data.get("source_audio") or ""
        if os.path.isfile(src) and os.path.dirname(os.path.abspath(src)) \
                == os.path.abspath(out_dir):
            audio_name = os.path.basename(src)
        else:
            track = (data.get("tracks") or {}).get("mix") \
                or (data.get("tracks") or {}).get("instrumental")
            if not track:
                raise ValueError(tr("the song has no audio to put beside the file",
                                    "у песни нет звука, который положить рядом"))
            audio_name = base + os.path.splitext(track)[1]
            import shutil as _sh
            _sh.copyfile(os.path.join(folder, track),
                         os.path.join(out_dir, audio_name))
            log(tr(f"The audio goes with it: {audio_name}",
                   f"Звук кладётся рядом: {audio_name}"))
        out = os.path.join(out_dir, base + ".txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(interop.ultrastar_text(data, audio_name))
        log(tr(f"Done: {out} — for UltraStar and its kin",
               f"Готово: {out} — для UltraStar и его родни"))
        return {"kind": "ultrastar", "path": out}

    if kind == "ass":
        from kstudio import interop
        out = os.path.join(out_dir, base + ".ass")
        with open(out, "w", encoding="utf-8") as f:
            f.write(interop.ass_text(data))
        log(tr(f"Done: {out} — subtitles with the karaoke sweep",
               f"Готово: {out} — субтитры с караоке-заливкой"))
        return {"kind": "ass", "path": out}

    if kind == "mp4":
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "video", os.path.join(ROOT, "tools", "video.py"))
        video = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(video)

        tmp_html = os.path.join(folder, "_render.html")
        B.build_html(tmp_html, lyr, data["duration"], tracks, data.get("engine", ""),
                     embed=True, title=data.get("title"), artist=data.get("artist"),
                     colors=data.get("colors"), theme=data.get("theme"),
                     keep_spans=P.keep_spans(data),
                     cover_path=(os.path.join(folder, data["cover"])
                                 if data.get("coverBg") and data.get("cover") else None),
                     cover_dark=data.get("coverDark"),
                     cover_paths=([os.path.join(folder, n)
                                   for n in data.get("coverSet") or []]
                                  if data.get("coverBg") else None),
                     grid=data.get("grid"))
        out = os.path.join(out_dir, base + ".mp4")

        class Args:
            pass
        a = Args()
        a.width = int(opts.get("width", 1920)); a.height = int(opts.get("height", 1080))
        a.fps = int(opts.get("fps", 30)); a.crf = int(opts.get("crf", 20))
        a.preset = opts.get("preset", "medium"); a.font = opts.get("font")
        a.start = 0.0; a.seconds = float(opts.get("seconds", 0) or 0)
        a.audio = opts.get("audio", "minus"); a.timings = None; a.output = out
        a.intro = bool(opts.get("intro", True))   # the name and a count of three
        # The clip behind the lyrics, if the song was given one. A missing
        # file is simply no backdrop: the still cover is still there.
        back = data.get("backdrop")
        a.backdrop = (os.path.join(folder, back)
                      if back and os.path.isfile(os.path.join(folder, back))
                      else None)

        log(tr("Drawing the frames…", "Рисую кадры…"))
        payload = B.read_payload(tmp_html)
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="karaoke_render_")
        try:
            wav = video.extract_audio(payload, tmp_html, tmpdir, a.audio)
            last = [""]
            def prog(msg):
                if msg != last[0]:
                    last[0] = msg
                    log(msg)
            video.render(payload, wav, out, a, on_progress=prog)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
            try:
                os.remove(tmp_html)
            except OSError:
                pass
        log(tr(f"Done: {out}", f"Готово: {out}"))
        return {"kind": "mp4", "path": out}

    raise ValueError(tr(f"unknown export kind: {kind}", f"неизвестный вид экспорта: {kind}"))


_VIDEO_MODULE = None


def _video_module():
    """tools/video.py, loaded once. “tools” is a folder of programs, not a
    package to import from — and the previews ask for it on every seek, so
    re-reading the file each time would throw away its background memo too."""
    global _VIDEO_MODULE
    if _VIDEO_MODULE is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "video", os.path.join(ROOT, "tools", "video.py"))
        _VIDEO_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_VIDEO_MODULE)
    return _VIDEO_MODULE


def fetch_cover_url(url: str) -> str:
    """A picture from a link, into a temporary file.

    Thirty megabytes is more cover than anyone prints; anything larger is
    refused rather than swallowed. The file's own bytes decide what it is —
    set_cover reads them, not the address.
    """
    import tempfile
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": f"KaraokeStudio/{__version__}"})
    fd, tmp = tempfile.mkstemp(prefix="cover_dl_",
                               suffix=os.path.splitext(url.split("?")[0])[1] or ".img")
    got = 0
    with urllib.request.urlopen(req, timeout=20) as r, os.fdopen(fd, "wb") as f:
        while True:
            chunk = r.read(262144)
            if not chunk:
                break
            got += len(chunk)
            if got > 30 * 1024 * 1024:
                f.close()
                os.remove(tmp)
                raise ValueError(tr("larger than 30 MB", "больше 30 МБ"))
            f.write(chunk)
    if not got:
        os.remove(tmp)
        raise ValueError(tr("the link answered with nothing", "по ссылке пусто"))
    return tmp


COVER_SET_N = 6


def set_cover(folder: str, src: str) -> list:
    """A picture — or frames out of a clip — become the song's cover.

    A song from a link brings its cover along; one from a file on disk had
    nowhere to get one. Any image will do. The clip itself does better: six
    frames spread across it become a slow slideshow behind the lyrics, past
    the black lead-in every video starts with. Returns the file names.
    """
    from PIL import Image
    dst = os.path.join(folder, "cover.jpg")
    for old in os.listdir(folder):
        if old.startswith("cover-") and old.endswith(".jpg"):
            try:
                os.remove(os.path.join(folder, old))
            except OSError:
                pass
    # The bytes decide, not the name: a picture fetched from a link may carry
    # any extension or none. Whatever Pillow cannot read is tried as a clip.
    try:
        img = Image.open(src)
        img = img.convert("RGB")
        img.thumbnail((1280, 1280))
        img.save(dst, "JPEG", quality=88)
        return ["cover.jpg"]
    except Exception:
        pass
    # a clip: frames spread from a tenth to nine tenths of its length
    import subprocess as sp
    length = AU.duration(src)
    out = []
    for i in range(COVER_SET_N):
        at = max(length * (0.1 + 0.8 * i / max(COVER_SET_N - 1, 1)), 1.0)
        name = "cover.jpg" if i == 0 else f"cover-{i + 1}.jpg"
        p = sp.run([AU.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.1f}", "-i", src,
                    "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2",
                    os.path.join(folder, name)],
                   stdout=sp.PIPE, stderr=sp.PIPE)
        if p.returncode == 0 and os.path.isfile(os.path.join(folder, name)):
            out.append(name)
        elif i == 0:
            raise ValueError(p.stderr.decode(errors="replace")[-120:]
                             or tr("not a picture and not a clip",
                                   "не картинка и не клип"))
    return out


BACKDROP_W = 320
BACKDROP_FPS = 4


def set_backdrop(folder: str, src: str) -> str:
    """A clip to stand behind the lyrics, kept small on purpose.

    The render blurs the backdrop into a field 160 pixels wide, so carrying a
    full copy of a video around a song folder would be paying for detail that
    is thrown away before the first frame is drawn. What is kept is a few
    hundred pixels at four frames a second — a handful of megabytes for any
    song, small enough to travel inside a packed one.
    """
    import subprocess as sp
    for old in os.listdir(folder):
        if old.startswith("backdrop.") :
            try:
                os.remove(os.path.join(folder, old))
            except OSError:
                pass
    dst = os.path.join(folder, "backdrop.mp4")
    p = sp.run([AU.ffmpeg(), "-y", "-v", "error", "-i", src, "-an", "-sn",
                "-vf", (f"fps={BACKDROP_FPS},scale={BACKDROP_W}:-2"),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "32",
                "-pix_fmt", "yuv420p", dst],
               stdout=sp.PIPE, stderr=sp.PIPE)
    if p.returncode != 0 or not os.path.isfile(dst):
        raise ValueError(p.stderr.decode(errors="replace")[-160:]
                         or tr("not a clip", "не клип"))
    return "backdrop.mp4"


def still_frame(folder: str, at: float, opening: bool = False) -> bytes:
    """One frame of the clip as it will be, drawn now and shown at once.

    Rendering a whole file to see whether a line sits where it should is
    minutes; this is the same drawing code on one frame, so what the window
    shows cannot differ from what the clip will hold. The song's own track
    stands in for the karaoke audio — nothing is heard here, only its length
    is needed.
    """
    import shutil
    import tempfile
    video = _video_module()

    data = P.load(folder)
    tracks = data.get("tracks") or {}
    name = tracks.get("instrumental") or tracks.get("mix") or next(iter(tracks.values()), "")
    if not name:
        raise ValueError(tr("the song has no audio", "у песни нет звука"))

    tmp = tempfile.mkdtemp(prefix="karaoke_still_")
    try:
        page = os.path.join(tmp, "page.html")
        B.build_html(page, _lyrics_from(data), data["duration"], {}, data.get("engine", ""),
                     embed=False, title=data.get("title"), artist=data.get("artist"),
                     colors=data.get("colors"), theme=data.get("theme"),
                     keep_spans=P.keep_spans(data),
                     cover_path=(os.path.join(folder, data["cover"])
                                 if data.get("coverBg") and data.get("cover") else None),
                     cover_dark=data.get("coverDark"),
                     cover_paths=([os.path.join(folder, n)
                                   for n in data.get("coverSet") or []]
                                  if data.get("coverBg") else None),
                     grid=data.get("grid"))
        payload = B.read_payload(page)

        class Args:
            width, height, fps, crf = 1280, 720, 30, 20
            preset, font, timings = "medium", None, None
            start, seconds, audio = 0.0, 0.0, "minus"
            intro = True
        a = Args()
        back = data.get("backdrop")
        a.backdrop = (os.path.join(folder, back)
                      if back and os.path.isfile(os.path.join(folder, back))
                      else None)
        # Asked in the song's own time; the clip counts from its first frame,
        # and between the two stands the opening.
        lead = video.intro_lead(a, str(data.get("title") or "").strip())
        a.still = (min(lead, video.INTRO_CARD / 2) if opening
                   else lead + max(0.0, at))
        a.output = os.path.join(tmp, "frame.png")
        video.render(payload, os.path.join(folder, name), a.output, a)
        with open(a.output, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _lyrics_from(data: dict):
    """Rebuild the lyrics object from the saved timing — for export."""
    from kstudio.lyrics import Line, Lyrics, Word
    lyr = Lyrics(title=data.get("title"), artist=data.get("artist"))
    for l in data.get("lines") or []:
        words = []
        for w in l.get("words") or []:
            wd = Word(w["w"], syllables=w.get("s") or 1)
            wd.start = float(w["t"])
            wd.end = wd.start + float(w["d"])
            wd.glue = bool(w.get("g"))       # a syllable stays a syllable
            words.append(wd)
        ln = Line(text=l.get("text", ""), words=words, section=l.get("section"),
                  backing=bool(l.get("backing")), voice=int(l.get("voice") or 1),
                  keep=bool(l.get("keep")),
                  keep_soft=bool(l.get("keepSoft")))
        ln.start, ln.end = float(l.get("start", 0)), float(l.get("end", 0))
        lyr.lines.append(ln)
    return lyr


# --------------------------------------------------------------------------- #

def free_port(preferred: int = 8770) -> int:
    for port in range(preferred, preferred + 40):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0


def open_window(url: str) -> None:
    """An app window: no address bar, no tabs, if Chrome or Edge is around."""
    if os.name == "nt":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
        for exe in candidates:
            if os.path.isfile(exe):
                try:
                    subprocess.Popen([exe, f"--app={url}",
                                      "--window-size=1280,860"])
                    return
                except Exception:
                    pass
    webbrowser.open(url)


def parse_args(argv):
    """Option parsing. There used to be none: --port was silently ignored, the
    port was picked automatically, and it was a mystery where things went."""
    port, no_browser, host = None, False, "127.0.0.1"
    args = list(argv)
    while args:
        a = args.pop(0)
        if a in ("--no-browser", "-n"):
            no_browser = True
        elif a in ("--port", "-p"):
            if not args or not args[0].isdigit():
                raise SystemExit(tr("--port needs a port number, for example: --port 8770",
                                    "После --port нужен номер порта, например: --port 8770"))
            port = int(args.pop(0))
        elif a.startswith("--port="):
            port = int(a.split("=", 1)[1])
        elif a in ("--host",):
            # Inside a container the request arrives from outside it, so the
            # server has to listen on 0.0.0.0. Publish the port to 127.0.0.1
            # on the host and it stays as private as before.
            if not args:
                raise SystemExit(tr("--host needs an address, for example: --host 0.0.0.0",
                                    "После --host нужен адрес, например: --host 0.0.0.0"))
            host = args.pop(0)
        elif a.startswith("--host="):
            host = a.split("=", 1)[1]
        elif a in ("-h", "--help"):
            print("py studio.py [--port 8770] [--host 127.0.0.1] [--no-browser]")
            raise SystemExit(0)
        else:
            raise SystemExit(tr(f"Unknown option: {a}", f"Не понял ключ: {a}"))
    return port, no_browser, host


def main(argv=None) -> int:
    want, no_browser, host = parse_args(sys.argv[1:] if argv is None else argv)
    if want is None:
        port = free_port()
        if not port:
            print(tr("Could not find a free port.", "Не нашёл свободный порт."), file=sys.stderr)
            return 1
    else:
        # A port was named explicitly, so that is the one expected. Quietly
        # moving to the next one is wrong: requests will go to the named port and
        # land either nowhere or in someone else's studio holding it.
        port = want
        with socket.socket() as probe:
            try:
                probe.bind((host, port))
            except OSError:
                print(tr(f"Port {port} is taken — the studio may already be running.",
                         f"Порт {port} уже занят — возможно, студия уже запущена."),
                      file=sys.stderr)
                print(tr(f"Open http://127.0.0.1:{port}/ or pick another port: "
                         f"--port {port + 1}",
                         f"Откройте http://127.0.0.1:{port}/ или укажите другой "
                         f"порт: --port {port + 1}"), file=sys.stderr)
                return 1
    url = f"http://127.0.0.1:{port}/"

    caps = capabilities()
    print("=" * 58)
    print(tr("  KARAOKE STUDIO", "  КАРАОКЕ-СТУДИЯ"), __version__)
    print("=" * 58)
    print(tr(f"Songs: {PROJECTS}", f"Проекты: {PROJECTS}"))
    if not caps["ffmpeg"]:
        print(tr("\nffmpeg was not found — nothing works without it.",
                  "\nffmpeg не найден — без него ничего не заработает."))
        print(tr("Run Install.bat (install.command on macOS)\n",
                  "Запустите Install.bat\n"))
    print(tr(f"Window: {url}", f"Окно: {url}"))
    print(tr("To finish, close this console window or press Ctrl+C.\n",
                  "Чтобы закончить — закройте это окно консоли или нажмите Ctrl+C.\n"))

    srv = ThreadingHTTPServer((host, port), Handler)
    if not no_browser:
        threading.Timer(0.6, lambda: open_window(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print(tr("\nClosing the studio.", "\nЗакрываю студию."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
