#!/usr/bin/env python3
"""
Stitch silent listening clips with trim + crossfade for smoother continuity.

Usage:
  python3 tools/stitch_listening_hold.py --input-dir video/raw/listening/EP001 --target 60
  python3 tools/stitch_listening_hold.py --clips video/raw/listening/EP001/L01.mp4 ... --target 170
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FFMPEG = (
    Path.home()
    / "Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
)


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        return explicit
    if DEFAULT_FFMPEG.is_file():
        return str(DEFAULT_FFMPEG)
    return "ffmpeg"


def probe_duration(ffmpeg: str, path: Path) -> float:
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for line in (proc.stderr or "").splitlines():
        if "Duration:" in line:
            ts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = ts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not probe duration: {path}")


def collect_clips(input_dir: Path | None, clip_args: list[str]) -> list[Path]:
    if clip_args:
        return [Path(c).resolve() for c in clip_args]
    if not input_dir:
        raise SystemExit("Provide --input-dir or --clips")
    clips = sorted(input_dir.glob("L*.mp4"))
    if not clips:
        clips = sorted(input_dir.glob("*.mp4"))
    return [c for c in clips if "REFERENCE" not in c.name.upper()]


def trim_clip(
    ffmpeg: str,
    clip: Path,
    out: Path,
    *,
    trim_start: float,
    trim_end: float,
    crf: int,
) -> float:
    dur = probe_duration(ffmpeg, clip)
    length = max(1.0, dur - trim_start - trim_end)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(trim_start),
        "-i",
        str(clip),
        "-t",
        str(length),
        "-an",
        "-vf",
        "fps=24,format=yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return probe_duration(ffmpeg, out)


def xfade_pair(
    ffmpeg: str,
    left: Path,
    right: Path,
    out: Path,
    *,
    fade: float,
    crf: int,
) -> float:
    left_dur = probe_duration(ffmpeg, left)
    offset = max(0.0, left_dur - fade)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(left),
        "-i",
        str(right),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[outv]",
        "-map",
        "[outv]",
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return probe_duration(ffmpeg, out)


def extend_to_target(
    ffmpeg: str,
    segment: Path,
    out: Path,
    *,
    target_sec: float,
    fade: float,
    crf: int,
    work: Path,
) -> float:
    current = segment
    current_dur = probe_duration(ffmpeg, current)
    i = 0
    while current_dur < target_sec - 0.05:
        nxt = work / f"extend_{i:02d}.mp4"
        current_dur = xfade_pair(
            ffmpeg, current, segment, nxt, fade=fade, crf=crf
        )
        current = nxt
        i += 1

    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(current),
        "-t",
        str(target_sec),
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-an",
        "-movflags",
        "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return probe_duration(ffmpeg, out)


def stitch_clips(
    ffmpeg: str,
    clips: list[Path],
    output: Path,
    *,
    target_sec: float,
    trim_start: float,
    trim_end: float,
    fade: float,
    crf: int,
) -> dict:
    if not clips:
        raise SystemExit("No input clips found")

    work = output.parent / f".stitch_work_{output.stem}"
    work.mkdir(parents=True, exist_ok=True)

    trimmed: list[Path] = []
    trim_durs: list[float] = []
    for i, clip in enumerate(clips):
        out = work / f"trim_{i:02d}.mp4"
        d = trim_clip(
            ffmpeg,
            clip,
            out,
            trim_start=trim_start,
            trim_end=trim_end,
            crf=crf,
        )
        trimmed.append(out)
        trim_durs.append(d)

    current = trimmed[0]
    for i, nxt in enumerate(trimmed[1:], start=1):
        merged = work / f"merge_{i:02d}.mp4"
        xfade_pair(ffmpeg, current, nxt, merged, fade=fade, crf=crf)
        current = merged

    segment_dur = probe_duration(ffmpeg, current)
    final_dur = extend_to_target(
        ffmpeg,
        current,
        output,
        target_sec=target_sec,
        fade=fade,
        crf=crf,
        work=work,
    )

    meta = {
        "clips": [str(c) for c in clips],
        "trim_start": trim_start,
        "trim_end": trim_end,
        "fade_sec": fade,
        "segment_sec": round(segment_dur, 2),
        "target_sec": target_sec,
        "output_sec": round(final_dur, 2),
        "output": str(output),
    }
    (output.parent / f"{output.stem}.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return meta


def main() -> None:
    p = argparse.ArgumentParser(description="Crossfade-stitch silent listening holds")
    p.add_argument("--input-dir", type=Path, help="Folder with L01.mp4, L02.mp4, ...")
    p.add_argument("--clips", nargs="*", help="Explicit clip paths")
    p.add_argument("--target", type=float, default=60.0, help="Output duration seconds")
    p.add_argument("--output", type=Path, help="Output mp4 path")
    p.add_argument("--trim-start", type=float, default=0.35, help="Trim head seconds")
    p.add_argument("--trim-end", type=float, default=0.45, help="Trim tail seconds")
    p.add_argument("--fade", type=float, default=0.4, help="Crossfade duration seconds")
    p.add_argument("--crf", type=int, default=18)
    p.add_argument("--ffmpeg", type=str, default=None)
    args = p.parse_args()

    ffmpeg = find_ffmpeg(args.ffmpeg)
    clips = collect_clips(args.input_dir, args.clips)
    out = args.output
    if not out:
        tag = int(args.target)
        out = ROOT / "video" / "edited" / "listening" / "EP001" / f"hold_{tag}s_xfade.mp4"

    meta = stitch_clips(
        ffmpeg,
        clips,
        out.resolve(),
        target_sec=args.target,
        trim_start=args.trim_start,
        trim_end=args.trim_end,
        fade=args.fade,
        crf=args.crf,
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()