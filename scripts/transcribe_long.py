"""Transcribe a long video to an .srt in 10-minute pieces, so Whisper never needs more than a
little memory at a time. Then give the .srt to AutoClip with --srt.

Usage (inside the AutoClip venv):
    python scripts/transcribe_long.py "C:\\path\\to\\video.mp4"
    python scripts/transcribe_long.py "C:\\path\\to\\video.mp4" --language en --model base --minutes 10

Writes <video name>.srt next to the video.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def srt_time(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def duration_of(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--language", default="en", help="spoken language code, e.g. en (default), or 'auto'")
    ap.add_argument("--model", default="base", help="tiny / base (default) / small / medium")
    ap.add_argument("--minutes", type=float, default=10, help="length of each piece (default 10)")
    args = ap.parse_args()

    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        print(f"Video not found: {video}")
        return 1
    out_path = video.with_suffix(".srt")

    # Use the same model folder AutoClip uses, so the model is not downloaded twice.
    models_dir = Path(os.environ.get("APPDATA", Path.home())) / "AutoClip" / "whisper-models" / "hub"
    from faster_whisper import WhisperModel

    print(f"Loading Whisper '{args.model}'...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8", download_root=str(models_dir))
    language = None if args.language == "auto" else args.language

    total = duration_of(video)
    piece = args.minutes * 60
    cues = []
    with tempfile.TemporaryDirectory() as tmp:
        start = 0.0
        n = 0
        while start < total:
            n += 1
            wav = Path(tmp) / f"part{n}.wav"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{piece:.3f}", "-i", str(video),
                 "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                check=True,
            )
            print(f"Part {n}: {srt_time(start)} - {srt_time(min(total, start + piece))} ...", flush=True)
            segments, _info = model.transcribe(str(wav), language=language, vad_filter=True)
            for seg in segments:
                text = (seg.text or "").strip()
                if text:
                    cues.append((start + seg.start, start + seg.end, text))
            wav.unlink(missing_ok=True)
            start += piece

    with open(out_path, "w", encoding="utf-8") as f:
        for i, (s, e, text) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{text}\n\n")
    print(f"\nDone: {len(cues)} subtitle lines written to\n{out_path}")
    return 0 if cues else 1


if __name__ == "__main__":
    sys.exit(main())
