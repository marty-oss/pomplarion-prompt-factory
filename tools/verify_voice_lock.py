#!/usr/bin/env python3
"""
Verify generated speaking prompts have consistent voice lock.

Usage:
  python3 tools/verify_voice_lock.py
  python3 tools/verify_voice_lock.py --episode EP001
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE_LOCK = ROOT / "config" / "voice-lock.json"
GENERATED = ROOT / "prompts" / "generated"

RISKY_IN_PERFORMANCE = re.compile(
    r"\b(lower voice|higher voice|deeper voice|louder|whisper|shout|change voice|different voice)\b",
    re.I,
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_speaking_json(episode: str | None):
    for ep_dir in sorted(GENERATED.iterdir()):
        if not ep_dir.is_dir() or ep_dir.name == "listening":
            continue
        if episode and ep_dir.name != episode:
            continue
        for path in sorted(ep_dir.glob("EP*-MS*.json")):
            if "compact" in path.parts:
                continue
            yield path


def verify_file(path: Path, expected_direction: str, errors: list[str]) -> None:
    data = load_json(path)
    name = path.name

    if "voice" not in data:
        errors.append(f"{name}: missing top-level 'voice' block")
        return

    voice = data["voice"]
    vd = voice.get("voice_direction", "")
    if vd != expected_direction:
        errors.append(
            f"{name}: voice.voice_direction mismatch\n"
            f"  expected: {expected_direction!r}\n"
            f"  got:      {vd!r}"
        )

    dlg = data.get("dialogue", {})
    if dlg.get("voice_direction") != vd:
        errors.append(f"{name}: dialogue.voice_direction does not match voice.voice_direction")

    if data.get("exact_dialogue") != dlg.get("spoken_lines"):
        errors.append(f"{name}: exact_dialogue != dialogue.spoken_lines")

    perf = data.get("performance", {})
    energy = perf.get("energy", "") or perf.get("facial_expression", "")
    if RISKY_IN_PERFORMANCE.search(energy):
        errors.append(f"{name}: performance contains risky vocal instruction: {energy!r}")

    anchor = voice.get("voice_anchor_mini_scene")
    if not anchor:
        errors.append(f"{name}: voice.voice_anchor_mini_scene missing")


def verify_compact(path: Path, expected_direction: str, errors: list[str]) -> None:
    data = load_json(path)
    name = path.relative_to(GENERATED)
    if data.get("voice", {}).get("voice_direction") != expected_direction:
        errors.append(f"{name}: compact voice_direction mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify voice lock on generated JSON")
    parser.add_argument("--episode", help="Episode filter (e.g. EP001)")
    args = parser.parse_args()

    if not VOICE_LOCK.is_file():
        print(f"Error: missing {VOICE_LOCK}", file=sys.stderr)
        return 1

    voice_lock = load_json(VOICE_LOCK)
    expected = voice_lock["voice_direction"]
    errors: list[str] = []
    count = 0
    compact_count = 0

    paths = list(iter_speaking_json(args.episode))
    if not paths:
        print("No speaking JSON files found.", file=sys.stderr)
        return 1

    for path in paths:
        verify_file(path, expected, errors)
        count += 1
        compact = path.parent / "compact" / path.name.replace(".json", "-voice.json")
        if compact.is_file():
            verify_compact(compact, expected, errors)
            compact_count += 1

    if errors:
        print("Voice lock verification FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"OK: {count} speaking JSON + {compact_count} compact — "
        f"identical voice_direction ({len(expected)} chars)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())