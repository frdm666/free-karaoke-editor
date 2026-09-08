"""Audio through ffmpeg: finding the binary, decoding to PCM, re-encoding."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
from .i18n import tr
from array import array
from typing import List, Optional, Tuple
from urllib.parse import unquote

_FFMPEG: Optional[str] = None
_FFPROBE: Optional[str] = None

CODECS = {
    # name: (ffmpeg args, extension, mime)
    "mp3": (["-c:a", "libmp3lame", "-q:a", "5"], ".mp3", "audio/mpeg"),
    "opus": (["-c:a", "libopus", "-b:a", "64k", "-vbr", "on"], ".ogg", "audio/ogg"),
    "aac": (["-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart"], ".m4a", "audio/mp4"),
}


class AudioError(RuntimeError):
    pass


# A window opened by double-clicking inherits a bare PATH: neither Homebrew nor
# a pip --user install is in it, though the person has both and both work in a
# terminal. Looking in the usual places is the difference between “ffmpeg is
# not installed” and the truth.
COMMON = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
          os.path.expanduser("~/.local/bin"))


def _probe_candidates(name: str):
    yield os.environ.get(f"KARAOKE_{name.upper()}")
    yield shutil.which(name)
    # Next to the running Python. sys.executable is not always there to be
    # had — an embedded or oddly launched interpreter leaves it empty, and
    # os.path.dirname(None) is a crash, not a missing ffmpeg.
    if sys.executable:
        yield os.path.join(os.path.dirname(sys.executable), name)
    for folder in COMMON:
        yield os.path.join(folder, name)
    # Last: the copy pip can install. It is one file called something like
    # ffmpeg-macos-arm64-v7.0.2 and it brings no ffprobe at all, so a real
    # install is worth preferring wherever there is one.
    try:
        import imageio_ffmpeg
        if name == "ffmpeg":
            yield imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass


def ffmpeg() -> str:
    global _FFMPEG
    if _FFMPEG is None:
        for c in _probe_candidates("ffmpeg"):
            if c and os.path.exists(c) and os.access(c, os.X_OK):
                _FFMPEG = c
                break
        else:
            raise AudioError(
                tr("ffmpeg was not found. Install it:\n",
                   "Не найден ffmpeg. Установите его:\n")
                + "  Linux:   sudo apt install ffmpeg   (or dnf install ffmpeg)\n"
                  "  macOS:   brew install ffmpeg\n"
                  "  Windows: winget install Gyan.FFmpeg\n"
                + tr("  Or without administrator rights: pip install imageio-ffmpeg",
                     "  Либо без прав администратора: pip install imageio-ffmpeg")
            )
    return _FFMPEG


def ffprobe() -> Optional[str]:
    global _FFPROBE
    if _FFPROBE is None:
        for c in _probe_candidates("ffprobe"):
            if c and os.path.exists(c) and os.access(c, os.X_OK):
                _FFPROBE = c
                break
        else:
            _FFPROBE = ""
    return _FFPROBE or None


_ON_PATH = False


def ensure_on_path() -> None:
    """Make ffmpeg visible to third-party libraries that look it up by name.

    imageio-ffmpeg puts the binary inside the package under a name like
    ffmpeg-win64-v4.2.2.exe. Our code finds it, but openai-whisper simply calls
    “ffmpeg” through PATH and dies with WinError 2. So we put a copy with the
    expected name next to it.
    """
    global _ON_PATH
    if _ON_PATH:
        return
    _ON_PATH = True

    try:
        exe = ffmpeg()
    except AudioError:
        return

    want = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    if os.path.basename(exe).lower() == want:
        os.environ["PATH"] = os.path.dirname(exe) + os.pathsep + os.environ.get("PATH", "")
        return

    if shutil.which("ffmpeg"):
        return                                   # the system one is already there

    import tempfile
    shim_dir = os.path.join(tempfile.gettempdir(), "karaoke_ffmpeg_shim")
    os.makedirs(shim_dir, exist_ok=True)
    dst = os.path.join(shim_dir, want)
    if not os.path.exists(dst):
        try:
            os.link(exe, dst)                    # a hard link — no copying
        except Exception:
            try:
                shutil.copy2(exe, dst)
            except Exception:
                return
    os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")


def _run(cmd: List[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)


def from_uri(uri: str, tmp: str, name: str, beside: str) -> Optional[str]:
    """A track a page names, as a file on disk — or None when there is none.

    The page carries its sound either inside itself, as a data: URI that is
    decoded into `tmp` under `name` and the extension its type says, or as a
    file next to the page, named relative to it — `beside` is the page's own
    path. The video and the diagnosis each had their own copy of this.
    """
    if uri.startswith("data:"):
        head, _, b64 = uri.partition(",")
        ext = ".mp3" if "mpeg" in head else (".ogg" if "ogg" in head else ".m4a")
        path = os.path.join(tmp, name + ext)
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path
    path = os.path.join(os.path.dirname(os.path.abspath(beside)), unquote(uri))
    return path if os.path.isfile(path) else None


def duration(path: str) -> float:
    probe = ffprobe()
    if probe:
        p = _run([probe, "-v", "error", "-show_entries", "format=duration",
                  "-of", "json", path])
        if p.returncode == 0:
            try:
                return float(json.loads(p.stdout)["format"]["duration"])
            except Exception:
                pass
    # fallback: parse "Duration: 00:03:24.15" out of ffmpeg's output
    p = _run([ffmpeg(), "-i", path])
    m = re.search(rb"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", p.stderr)
    if m:
        return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    raise AudioError(tr(f"Could not work out the length of the file: {path}",
                        f"Не удалось определить длительность файла: {path}"))


def to_wav(src: str, dst: str, sample_rate: int = 44100, mono: bool = False) -> str:
    """Bring any input to WAV (demucs needs it, and it is a common denominator)."""
    cmd = [ffmpeg(), "-y", "-i", src, "-vn", "-ar", str(sample_rate),
           "-ac", "1" if mono else "2", "-c:a", "pcm_s16le", dst]
    p = _run(cmd)
    if p.returncode != 0:
        raise AudioError(tr(f"ffmpeg could not read {src}:", f"ffmpeg не смог прочитать {src}:")
                         + "\n" + p.stderr.decode(errors="replace")[-800:])
    return dst


def encode(src: str, dst_base: str, codec: str = "mp3", sample_rate: int = 44100) -> Tuple[str, str]:
    """Compress for the web. Returns (path, mime).

    The sample rate is set explicitly: the instrumental and the vocal play in
    the browser as two separate elements, and if their rates differ, one track
    runs faster than the other.
    """
    if codec not in CODECS:
        raise AudioError(tr(f"Unknown codec {codec}. Available: {', '.join(CODECS)}",
                            f"Неизвестный кодек {codec}. Доступны: {', '.join(CODECS)}"))
    args, ext, mime = CODECS[codec]
    dst = dst_base + ext
    p = _run([ffmpeg(), "-y", "-i", src, "-vn", "-ac", "2",
              "-ar", str(sample_rate), *args, dst])
    if p.returncode != 0:
        raise AudioError(tr(
            f"ffmpeg could not encode {src} to {codec}:\n"
            f"{p.stderr.decode(errors='replace')[-800:]}",
            f"ffmpeg не смог закодировать {src} в {codec}:\n"
            f"{p.stderr.decode(errors='replace')[-800:]}"))
    return dst, mime


# Levelling the voice before it is handed to the aligner. A screamed vocal is
# the widest dynamic there is: a shout point-blank and a strangled rasp one
# after the other, and the quiet half never reaches the model. This levels them
# without touching pitch or time, so every timing still means what it says.
# Measured on a nine-minute deathcore track with its real lyrics: segments the
# aligner gave up on 22 → 19, confidence 0.125 → 0.138.
LEVEL_VOICE = "highpass=f=80,dynaudnorm=f=200:g=15:p=0.9,alimiter=limit=0.95"


# How far the key may be moved. An octave either way is more than anybody
# sings, and it is also where the arithmetic stays honest: past it the tempo
# correction has to be applied twice and the sound suffers for nothing.
SHIFT_MAX = 12


def shift_pitch(src: str, dst: str, semitones: float) -> str:
    """Move a track by `semitones`, keeping its tempo. Returns the path used.

    Two ways to do it. `rubberband` is the one built for this and leaves the
    sound alone; it is not in every ffmpeg. Failing that, the old trick: play
    the file at a different rate — which moves the pitch and the tempo
    together — and put the tempo back. That one is coarser, and a singer will
    hear it on a big shift, which is the honest price of not having the good
    filter.

    A shift of nothing is not a copy: the file comes back as it was.
    """
    n = max(-SHIFT_MAX, min(SHIFT_MAX, float(semitones or 0)))
    if abs(n) < 0.01:
        return src
    ratio = 2.0 ** (n / 12.0)
    ways = [
        ["-af", f"rubberband=pitch={ratio:.6f}"],
        # asetrate moves pitch and tempo at once; atempo puts the tempo back
        ["-af", f"asetrate=44100*{ratio:.6f},aresample=44100,"
                f"atempo={1.0 / ratio:.6f}"],
    ]
    last = b""
    for way in ways:
        p = _run([ffmpeg(), "-y", "-v", "error", "-i", src, *way,
                  "-c:a", "pcm_s16le", dst])
        if p.returncode == 0 and os.path.isfile(dst):
            return dst
        last = p.stderr
    raise AudioError(tr("Could not change the key:\n",
                        "Не удалось сменить тональность:\n")
                     + last.decode(errors="replace")[-400:])


def read_pcm_mono(path: str, sample_rate: int = 16000,
                  af: Optional[str] = None) -> array:
    """Decode to mono int16 through a pipe. Returns array(\'h\')."""
    cmd = [ffmpeg(), "-v", "error", "-i", path, "-vn", "-ac", "1",
           "-ar", str(sample_rate)]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "s16le", "-"]
    p = _run(cmd)
    if p.returncode != 0:
        raise AudioError(tr(f"Could not decode {path}:", f"Не удалось декодировать {path}:")
                         + "\n" + p.stderr.decode(errors="replace")[-500:])
    data = array("h")
    data.frombytes(p.stdout[: len(p.stdout) // 2 * 2])
    return data


def rms_envelope(path: str, hop_ms: int = 20, sample_rate: int = 16000):
    """Loudness envelope: (list of RMS in [0..1], step in seconds)."""
    samples = read_pcm_mono(path, sample_rate)
    hop = max(int(sample_rate * hop_ms / 1000), 1)
    try:
        import numpy as np
        x = np.frombuffer(samples.tobytes(), dtype="<i2").astype("float32") / 32768.0
        n = len(x) // hop * hop
        if n == 0:
            return [], hop / sample_rate
        frames = x[:n].reshape(-1, hop)
        env = np.sqrt((frames ** 2).mean(axis=1))
        peak = float(env.max()) or 1.0
        return (env / peak).tolist(), hop / sample_rate
    except ImportError:
        env, peak = [], 1e-9
        for i in range(0, len(samples) - hop, hop):
            acc = 0
            for j in range(i, i + hop):
                v = samples[j] / 32768.0
                acc += v * v
            r = (acc / hop) ** 0.5
            peak = max(peak, r)
            env.append(r)
        return [e / peak for e in env], hop / sample_rate
