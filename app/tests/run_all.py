#!/usr/bin/env python3
"""Run every check in one go.

    python3 tests/run_all.py              everything that is available
    KARAOKE_HEAVY=1  … run_all.py         plus the real Whisper and Demucs
    KARAOKE_DOCKER=1 … run_all.py         plus building and running the container
    python3 tests/run_all.py --quick      Python only, no browser suites
    python3 tests/run_all.py --list       list the suites and exit

What happens:
  1. The pipeline checks (`test_pipeline.py`) — ffmpeg is all they need.
  1b. The delivery checks (`test_delivery.py`): what launches the program, how
     the files are named, whether the settings are read, which language the
     console speaks, what the video sounds like.
  2. A test song is built, and two pages: one track and one with an instrumental.
  3. The studio is started on a free port with a fresh project.
  4. The suites in tests/ui run — the window and the page, in jsdom.
  5. If puppeteer with Chrome is installed, tests/test_browser.mjs too: a real
     browser looks at the layout, which jsdom never draws.

Steps 4–5 need Node.js: `npm install jsdom` (and `puppeteer` for the fifth).
Without Node everything else still runs.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(ROOT, "tests", "ui")


# These suites need a real browser: they check what the cursor actually hits,
# and jsdom does not do hit-testing at all.
def NEEDS_BROWSER(name: str) -> bool:
    return any(k in name for k in ("real-mouse", "word-length", "replace-track", "scroll-and-end", "quiet-and-voice", "two-lanes", "requirements", "duo-layout", "multiselect", "link-live", "notext-live", "mark-live", "split-join", "clip-marks", "layout", "page-cover", "name-live", "tools-live", "timeline-live"))
sys.path.insert(0, ROOT)


def say(msg=""):
    print(msg, flush=True)


def head(title):
    say()
    say("=" * 62)
    say("  " + title)
    say("=" * 62)


def have_node() -> bool:
    return shutil.which("node") is not None


def have_module(name: str) -> bool:
    """Is the Node package installed — asked through Node itself."""
    try:
        r = subprocess.run(["node", "-e", f"import('{name}').then(()=>0)"],
                           cwd=ROOT, capture_output=True, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(url: str, seconds: float = 40) -> bool:
    until = time.time() + seconds
    while time.time() < until:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.4)
    return False


def build_pages(tmp: str) -> tuple:
    """The test song and two pages: a single track, and instrumental + vocal."""
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    from test_pipeline import TEXT, make_song  # noqa: F401

    song = os.path.join(tmp, "song.wav")
    text = os.path.join(tmp, "lyrics.txt")
    make_song(song)
    with open(text, "w", encoding="utf-8") as f:
        f.write(TEXT)

    mix = os.path.join(tmp, "one_track.html")
    stems = os.path.join(tmp, "with_instrumental.html")
    kar = os.path.join(ROOT, "karaoke.py")
    # The older suites compare against Russian labels, so a Russian page is
    # built for them. English has a suite of its own.
    base = [sys.executable, kar, song, text, "--align", "energy", "--ui-lang", "ru"]
    subprocess.run(base + ["-o", mix, "--no-separate"], cwd=ROOT,
                   capture_output=True, check=True)

    # A page with two tracks. There is no need to run Demucs for a test: a
    # second page is built from other audio and the tracks are swapped by hand.
    # The instrumental and the vocal must DIFFER, or the drift check catches
    # nothing.
    other = os.path.join(tmp, "second.wav")
    make_song(other, dur=26.0)
    quieter(other)
    alt = os.path.join(tmp, "second.html")
    subprocess.run([sys.executable, kar, other, text, "--align", "energy",
                    "--ui-lang", "ru", "-o", alt, "--no-separate"], cwd=ROOT,
                   capture_output=True, check=True)

    # And an English page — the interface-language suite checks that one.
    eng = os.path.join(tmp, "english.html")
    subprocess.run([sys.executable, kar, song, text, "--align", "energy",
                    "--ui-lang", "en", "-o", eng, "--no-separate"],
                   cwd=ROOT, capture_output=True, check=True)
    # And one with a stretch marked as holding no words: there the original
    # voice stays in the backing, or the karaoke has a hole where a vocalise was.
    keeps_one = os.path.join(tmp, "keeps-one.html")
    keeps = os.path.join(tmp, "keeps.html")
    subprocess.run([sys.executable, kar, song, text, "--align", "energy",
                    "--ui-lang", "ru", "--no-text", "0:14-0:16.5",
                    "-o", keeps_one, "--no-separate"],
                   cwd=ROOT, capture_output=True, check=True)
    two_tracks(stems, mix, alt)
    # the marked page needs two tracks as well: with one, there is no vocal to
    # leave in and nothing to check
    two_tracks(keeps, keeps_one, alt)
    return song, text, mix, stems, eng, keeps


def quieter(path: str) -> None:
    """Half as loud, so the second track differs from the first byte for byte."""
    import audioop
    import wave
    with wave.open(path, "rb") as r:
        params, frames = r.getparams(), r.readframes(r.getnframes())
    with wave.open(path, "wb") as w:
        w.setparams(params)
        w.writeframes(audioop.mul(frames, params.sampwidth, 0.5))


def payload(path: str):
    import json
    import re
    s = open(path, encoding="utf-8").read()
    m = re.search(r'(<script id="payload"[^>]*>)(.*?)(</script>)', s, re.S)
    raw = (m.group(2).replace("\\u003c", "<").replace("\\u003e", ">")
                     .replace("\\u0026", "&"))
    return s, m, json.loads(raw)


def two_tracks(dst: str, src_a: str, src_b: str) -> None:
    """Build a page with an instrumental and a vocal from two different takes."""
    import json
    import shutil as sh
    sh.copyfile(src_a, dst)
    s, m, p = payload(dst)
    _, _, b = payload(src_b)
    audio = p.get("audio") or {}
    other = (b.get("audio") or {}).get("mix")
    if "mix" in audio and other:
        audio["instrumental"] = audio.pop("mix")
        audio["vocals"] = other
    out = (json.dumps(p).replace("<", "\\u003c").replace(">", "\\u003e")
                        .replace("&", "\\u0026"))
    open(dst, "w", encoding="utf-8").write(s[:m.start(2)] + out + s[m.end(2):])


def fake_model_cache(root: str) -> str:
    """A model cache of our own: “tiny” on disk, the rest not.

    What the window says about a model depends on what lies in the cache, and
    that differs from machine to machine — on a CI runner it is empty. The stand
    gets its own XDG_CACHE_HOME so both answers are checked everywhere, and the
    real cache of whoever runs this is left alone. Nothing loads the file: the
    stand only ever times by loudness.
    """
    cache = os.path.join(root, "cache")
    os.makedirs(os.path.join(cache, "whisper"), exist_ok=True)
    stub = os.path.join(cache, "whisper", "tiny.pt")
    if not os.path.isfile(stub):
        with open(stub, "wb") as f:
            f.write(b"\0" * 1_200_000)      # above the “half-downloaded” threshold
    return cache


def start_lyrics_stub():
    """The lyrics library, played by a local stand-in.

    Nothing here may reach the internet: a check that depends on a live site
    fails on a bad day and proves nothing on a good one.
    """
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "tests", "stub_lyrics.py")],
                         stdout=subprocess.PIPE, text=True)
    url = (p.stdout.readline() or "").strip()
    return p, url


def start_studio(port: int, projects: str, song: str = "", lyrics_api: str = ""):
    # The studio window is bilingual now; the suites were written against the
    # Russian labels, so the stand runs in Russian. English has its own suite.
    env = dict(os.environ, KARAOKE_PROJECTS=projects, KARAOKE_UI_LANG="ru",
               XDG_CACHE_HOME=fake_model_cache(os.path.dirname(projects)),
               # A link is “downloaded” by a stand-in that hands over the test
               # song, and the words come from a stand-in library next door.
               KARAOKE_YTDLP=os.path.join(ROOT, "tests", "stub_ytdlp.py"),
               KARAOKE_STUB_AUDIO=song,
               KARAOKE_LYRICS_API=lyrics_api or "http://127.0.0.1:9")
    return subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "studio.py"),
         "--port", str(port), "--no-browser"],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def make_project(api: str, song: str, text: str) -> bool:
    import json
    body = json.dumps({"audio": song, "lyrics": text,
                       "align": "energy", "separate": False}).encode()
    req = urllib.request.Request(api + "/api/new", data=body,
                                 headers={"Content-Type": "application/json"})
    jid = json.load(urllib.request.urlopen(req, timeout=30))["job"]
    for _ in range(120):
        time.sleep(1)
        with urllib.request.urlopen(f"{api}/api/job?id={jid}", timeout=10) as r:
            job = json.load(r)
        if job.get("done"):
            return bool(job.get("ok"))
    return False


def run_suite(path: str, env: dict) -> tuple:
    try:
        r = subprocess.run(["node", path], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return False, "did not finish within 10 minutes"
    out = (r.stdout or "") + (r.stderr or "")
    last = out.strip().splitlines()[-1] if out.strip() else ""
    return last in ("All checks passed", "Все проверки пройдены"), out


class SKIPPED:
    returncode = 0


def main() -> int:
    args = sys.argv[1:]
    if "--list" in args:
        for f in sorted(os.listdir(UI_DIR)):
            say("  " + f)
        return 0
    quick = "--quick" in args
    # --from 31: pick up the window suites at 31 and skip what already passed.
    # Re-running the whole thing after a fix in one suite costs ten minutes.
    start_at = ""
    for i, a in enumerate(args):
        if a == "--from" and i + 1 < len(args):
            start_at = args[i + 1]
        elif a.startswith("--from="):
            start_at = a.split("=", 1)[1]

    if start_at:
        say(f"  --from {start_at}: the Python suites and the earlier window ones are skipped")
    head("1. Pipeline: the text, the timing, building the page")
    r = (SKIPPED if start_at else
         subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_pipeline.py")],
                        cwd=ROOT))
    if r.returncode != 0:
        say("\nFAILED on the pipeline checks — no point going further.")
        return 1
    head("1b. Delivery: launchers, file names, settings, console language, video")
    r = (SKIPPED if start_at else
         subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_delivery.py")],
                        cwd=ROOT))
    if r.returncode != 0:
        say("\nFAILED on the delivery checks.")
        return 1

    head("1c. Command line: options, errors, batch mode")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_cli.py")], cwd=ROOT)
    if r.returncode != 0:
        say("\nFAILED on the command-line checks.")
        return 1

    if os.environ.get("KARAOKE_HEAVY"):
        head("1c+. The real neural nets: Whisper times, Demucs separates")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_heavy.py")],
                           cwd=ROOT)
        if r.returncode != 0:
            say("\nFAILED on the neural-net checks.")
            return 1

    if os.environ.get("KARAOKE_DOCKER"):
        head("1c++. Container: the image, the window, a song built inside")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_container.py")],
                           cwd=ROOT)
        if r.returncode != 0:
            say("\nFAILED on the container checks.")
            return 1

    head("1d. The finished video: voice colours and no overlapping text")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_video_colors.py")],
                       cwd=ROOT)
    if r.returncode != 0:
        say("\nFAILED on the video checks.")
        return 1

    if quick:
        say("\n--quick: the browser suites were skipped.")
        return 0

    if not have_node():
        say("\nNode.js not found — the window and page suites were skipped.")
        say("Install Node and `npm install jsdom` to run them.")
        if os.environ.get("KARAOKE_REQUIRE_BROWSER"):
            say("KARAOKE_REQUIRE_BROWSER=1 — a skip counts as a failure.")
            return 1
        return 0
    if not have_module("jsdom"):
        say("\nNo jsdom package — the window and page suites were skipped.")
        say("Fix it with:  npm install jsdom")
        # Silence here looks exactly like “all green”, and that is how half the
        # suite went missing once: node_modules was a link to a folder that had
        # been swept away. Where the whole run is asked for, this is a failure.
        if os.environ.get("KARAOKE_REQUIRE_BROWSER"):
            head("Summary")
            say("  failed: jsdom is missing, so the window suites never ran")
            return 1
        return 0

    tmp = tempfile.mkdtemp(prefix="karaoke_tests_")
    projects = os.path.join(tmp, "projects")
    os.makedirs(projects, exist_ok=True)
    srv = lyr = None
    failed = []
    try:
        head("2. The test song and the pages")
        song, text, mix, stems, eng, keeps = build_pages(tmp)
        say(f"  built: {os.path.basename(mix)}, {os.path.basename(stems)}")

        head("3. The studio on a free port")
        port = free_port()
        api = f"http://127.0.0.1:{port}"
        lyr, lyrics_api = start_lyrics_stub()
        srv = start_studio(port, projects, song=song, lyrics_api=lyrics_api)
        if not wait_for(api + "/"):
            say("  the studio did not start — the window suites were skipped")
            return 1
        say(f"  {api} — a fresh project…")
        if not make_project(api, song, text):
            say("  the project was not built")
            return 1
        say("  the project is ready")

        env = dict(os.environ, KARAOKE_API=api, KARAOKE_ROOT=ROOT, KARAOKE_PAGE_MIX=mix,
                   KARAOKE_PAGE_STEMS=stems, KARAOKE_PAGE_EN=eng, PAGE=stems,
                   KARAOKE_PAGE_KEEPS=keeps,
                   KARAOKE_SONG=song, KARAOKE_TEXT=text,
                   KARAOKE_LYRICS_API=lyrics_api)

        head("4. The window and the page (jsdom)")
        for name in sorted(os.listdir(UI_DIR)):
            if not name.endswith(".mjs") or NEEDS_BROWSER(name):
                continue      # it needs a real browser, it goes in the next step
            if start_at and name < start_at:
                continue
            ok, out = run_suite(os.path.join(UI_DIR, name), env)
            say(f"  {'ok   ' if ok else 'FAILED'}  {name}")
            if not ok:
                failed.append(name)
                for line in [l for l in out.strip().splitlines() if "✗" in l or "FAILED" in l][:12] or out.strip().splitlines()[-12:]:
                    say("        " + line)

        head("5. A real browser")
        if have_module("puppeteer"):
            mouse = [os.path.join(UI_DIR, n) for n in sorted(os.listdir(UI_DIR))
                     if NEEDS_BROWSER(n)]
            for path in [os.path.join(ROOT, "tests", "test_browser.mjs")] + mouse:
                ok, out = run_suite(path, env)
                say(f"  {'ok   ' if ok else 'FAILED'}  {os.path.basename(path)}")
                if not ok:
                    failed.append(os.path.basename(path))
                    for line in [l for l in out.strip().splitlines() if "✗" in l or "FAILED" in l][:12] or out.strip().splitlines()[-12:]:
                        say("        " + line)
        else:
            say("  puppeteer is not installed — skipping.")
            say("  npm install puppeteer && npx puppeteer browsers install chrome")
            # A silent skip of half the checks looks exactly like “all green”.
            # On a server that is not acceptable: there we are asked to run it all.
            if os.environ.get("KARAOKE_REQUIRE_BROWSER"):
                failed.append("the browser suites were skipped")
    finally:
        for proc in (srv, lyr):
            if not proc:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    head("Summary")
    if failed:
        say("  failed: " + ", ".join(failed))
        return 1
    say("  all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
