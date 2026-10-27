#!/usr/bin/env python3
"""Convert Puzzle Pits .WAV sound effects into modern audio files.

Usage:  python3 DOS/Tools/wav2modern.py [--formats wav,ogg] [--out DIR]

The game's sounds (Game/PITS95/*.WAV) are 8-bit unsigned mono PCM at
11025 Hz. Their headers carry a corrupt byte-rate field (0x112B0000 instead
of 11025), which some strict decoders reject. This script parses the RIFF
chunks itself, converts the samples to 16-bit signed PCM and writes clean
files (by default into DOS/Assets/Sounds/). The sample rate is kept at
11025 Hz; no resampling or filtering is applied.

Formats:
  wav   16-bit PCM WAV with a correct header (Python standard library only)
  flac  lossless FLAC              (needs ffmpeg)
  ogg   Ogg Vorbis, quality 6      (needs ffmpeg)
  opus  Ogg Opus, 64 kbit/s        (needs ffmpeg; resampled to 48 kHz)
  mp3   MP3, VBR quality 2         (needs ffmpeg)
"""

import argparse
import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

DOS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.join(DOS_DIR, "Game", "PITS95")
DEFAULT_OUT = os.path.join(DOS_DIR, "Assets", "Sounds")

FFMPEG_ARGS = {
    "flac": ["-c:a", "flac"],
    "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
    "opus": ["-c:a", "libopus", "-b:a", "64k"],
    "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
}
FORMATS = ["wav"] + list(FFMPEG_ARGS)


def read_wav(path):
    """Return (sample_rate, channels, bits, data) from a RIFF/WAVE file.

    Walks the chunks directly and ignores the derived byte-rate and
    block-align fields, which are wrong in the original files.
    """
    data = open(path, "rb").read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("%s: not a RIFF/WAVE file" % path)
    fmt = pcm = None
    p = 12
    while p + 8 <= len(data):
        kind, size = data[p:p + 4], struct.unpack_from("<I", data, p + 4)[0]
        body = data[p + 8:p + 8 + size]
        if kind == b"fmt ":
            fmt = struct.unpack_from("<HHIIHH", body)
        elif kind == b"data":
            pcm = body
        p += 8 + size + (size & 1)
    if fmt is None or pcm is None:
        raise ValueError("%s: missing fmt or data chunk" % path)
    tag, channels, rate, _byte_rate, _align, bits = fmt
    if tag != 1 or bits not in (8, 16):
        raise ValueError("%s: unsupported encoding (tag %d, %d bits)" % (path, tag, bits))
    return rate, channels, bits, pcm


def to_16bit(bits, pcm):
    if bits == 16:
        return pcm
    # 8-bit WAV is unsigned with silence at 128; 16-bit is signed.
    return b"".join(struct.pack("<h", (s - 128) << 8) for s in pcm)


def write_wav16(path, rate, channels, pcm16):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm16)


def encode(ffmpeg, src_wav, dest, fmt):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", src_wav]
    cmd += FFMPEG_ARGS[fmt] + [dest]
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="output directory (default: DOS/Assets/Sounds)")
    parser.add_argument("--formats", default="wav,ogg",
                        help="comma-separated list from: %s (default: wav,ogg)"
                             % ",".join(FORMATS))
    args = parser.parse_args()

    formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    unknown = [f for f in formats if f not in FORMATS]
    if unknown:
        parser.error("unknown format(s): %s" % ", ".join(unknown))
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg and any(f in FFMPEG_ARGS for f in formats):
        skipped = [f for f in formats if f in FFMPEG_ARGS]
        print("ffmpeg not found; skipping %s" % ", ".join(skipped), file=sys.stderr)
        formats = [f for f in formats if f not in FFMPEG_ARGS]

    sources = sorted(glob.glob(os.path.join(GAME_DIR, "*.WAV")))
    if not sources:
        sys.exit("no .WAV files found in %s" % GAME_DIR)
    os.makedirs(args.out, exist_ok=True)

    written = 0
    with tempfile.TemporaryDirectory() as tmp:
        for src in sources:
            name = os.path.splitext(os.path.basename(src))[0].lower()
            rate, channels, bits, pcm = read_wav(src)
            clean = os.path.join(tmp, name + ".wav")
            write_wav16(clean, rate, channels, to_16bit(bits, pcm))
            for fmt in formats:
                dest = os.path.join(args.out, "%s.%s" % (name, fmt))
                if fmt == "wav":
                    shutil.copyfile(clean, dest)
                else:
                    encode(ffmpeg, clean, dest, fmt)
                written += 1
            print("%-10s %5d Hz, %d-bit, %.2f s" %
                  (name, rate, bits, len(pcm) / (rate * channels * bits // 8)))

    print("Wrote %d files to %s" % (written, args.out))


if __name__ == "__main__":
    main()
