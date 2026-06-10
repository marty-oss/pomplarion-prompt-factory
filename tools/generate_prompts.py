#!/usr/bin/env python3
"""
Generate Grok Imagine prompt files from scene maps.

Modes:
  speaking  — MS dialogue clips from data/scene-map.json (default)
  listening — silent listen clips from data/listening-scene-map.json
  all       — both

Usage:
  python tools/generate_prompts.py --episode EP001
  python tools/generate_prompts.py --mode listening --episode EP001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCENE_MAP = ROOT / "data" / "scene-map.json"
LISTENING_SCENE_MAP = ROOT / "data" / "listening-scene-map.json"
VOICE_LOCK = ROOT / "config" / "voice-lock.json"
LISTENING_PRESETS = ROOT / "config" / "listening-presets.json"
TEMPLATE_TXT = ROOT / "prompts" / "_template-fallback.txt"
TEMPLATE_LISTENING_TXT = ROOT / "prompts" / "_template-listening-fallback.txt"
OUTPUT_DIR = ROOT / "prompts" / "generated"
LISTENING_OUTPUT_DIR = ROOT / "prompts" / "generated" / "listening"
COMPACT_SUBDIR = "compact"

# Substrings that may override locked voice if placed in performance/voice_notes
RISKY_VOCAL_TOKENS = (
    "lower voice",
    "higher voice",
    "deeper voice",
    "louder",
    "whisper",
    "shout",
    "baritone",
    "pitch",
    "gravelly tone",
    "change voice",
    "different voice",
)

CONSISTENCY_RULES = [
    "Keep the same Pomplarion face and head shape.",
    "Keep the same blue scaly skin texture and orange-glowing fin structures on the headphones.",
    "Keep the same navy suit, white shirt, blue-orange plaid tie, Bitcoin lapel pin, black headphones, microphone, and blue-orange crypto broadcast studio.",
    "Do not redesign the character.",
    "Do not change the background HUD or wardrobe.",
    "Do not make him look evil, angry, demonic, scary, or aggressive.",
]

CHARACTER_NAME = "Pomplarion"
CHARACTER_DESCRIPTION = (
    "A confident crypto broadcast host seated at a desk, wearing a navy suit and headphones, "
    "speaking into a professional broadcast microphone."
)
SETTING = (
    "Futuristic blue-and-orange cryptocurrency broadcast studio with live Bitcoin HUD, "
    "charts, tickers, and cinematic rim lighting."
)
ANGLE_VARIATION_NOTE = (
    "Swap reference files across mini-scenes for natural angle variety "
    "while keeping the same Pomplarion face, blue scales, fin headphones, suit, tie, and crypto studio."
)

PERFORMANCE_AVOID = [
    "evil expression",
    "angry face",
    "demonic look",
    "sharp aggressive movements",
    "overacting",
    "wide scary grin",
    "camera shake",
    "changing the character design",
    "voice change",
    "dialogue improvisation",
]

TXT_PLACEHOLDERS = (
    "{{dialogue}}",
    "{{speech_start_sec}}",
    "{{voice_direction}}",
    "{{continuity_instruction}}",
    "{{delivery_emphasis}}",
    "{{reference_image}}",
    "{{camera_angle}}",
    "{{performance_notes}}",
    "{{motion_notes}}",
    "{{duration_sec}}",
)

LISTENING_TXT_PLACEHOLDERS = (
    "{{duration_sec}}",
    "{{motion_notes}}",
    "{{performance_notes}}",
    "{{reference_image}}",
    "{{camera_angle}}",
)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def fill_template(template: str, values: dict[str, str], placeholders: tuple[str, ...]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    for placeholder in placeholders:
        if placeholder in out:
            raise ValueError(f"Unfilled placeholder remains: {placeholder}")
    return out


def validate_reference(path_str: str, warnings: list[str]) -> None:
    rel = ROOT / path_str
    if not rel.is_file():
        warnings.append(f"Reference image not found: {path_str}")


def iter_mini_scenes(data: dict, episode_filter: str | None):
    for episode in data.get("episodes", []):
        eid = episode.get("episode_id", "")
        if episode_filter and eid != episode_filter:
            continue
        default_ref = (
            episode.get("default_reference_image")
            or data.get("default_reference_image", "")
        )
        for scene in episode.get("scenes", []):
            for ms in scene.get("mini_scenes", []):
                yield eid, default_ref, episode, scene, ms


def check_risky_vocal_tokens(
    uid: str, ms: dict[str, Any], warnings: list[str]
) -> None:
    for field in ("performance_notes", "voice_notes"):
        text = (ms.get(field) or "").lower()
        if not text:
            continue
        for token in RISKY_VOCAL_TOKENS:
            if token in text:
                warnings.append(
                    f"[{uid}] {field} contains risky vocal token '{token}' "
                    f"(may override voice lock)"
                )


def build_voice_block(
    voice_lock: dict,
    episode: dict[str, Any],
) -> dict[str, Any]:
    cal_ref = episode.get("voice_calibration_reference_image", "")
    block: dict[str, Any] = {
        "voice_direction": voice_lock["voice_direction"],
        "voice_continuity": voice_lock["continuity_instruction"],
        "delivery": voice_lock["delivery"],
        "voice_anchor_mini_scene": voice_lock.get("voice_anchor_mini_scene", "MS02"),
        "voice_anchor_instruction": voice_lock.get(
            "voice_anchor_instruction",
            "Match the approved anchor clip voice on every mini-scene.",
        ),
        "mic_proximity": voice_lock.get(
            "mic_proximity",
            "Close broadcast microphone, consistent proximity and room tone.",
        ),
        "vocal_energy_rule": voice_lock.get(
            "vocal_energy_rule",
            "Change emphasis and expression only — do not change pitch, timbre, accent, or mic tone.",
        ),
        "voice_negatives": voice_lock.get("voice_negatives", []),
    }
    if cal_ref:
        block["reference_image_for_calibration"] = cal_ref
        if episode.get("voice_calibration_note"):
            block["calibration_note"] = episode["voice_calibration_note"]
    return block


def iter_listen_clips(data: dict, episode_filter: str | None):
    for episode in data.get("episodes", []):
        eid = episode.get("episode_id", "")
        if episode_filter and eid != episode_filter:
            continue
        default_ref = data.get("default_reference_image", "")
        stitch_group = episode.get("stitch_group", "guest_hold")
        for clip in episode.get("clips", []):
            yield eid, default_ref, stitch_group, clip


def build_speech_rules(voice_lock: dict) -> list[str]:
    return [
        f"Begin speaking within {voice_lock['speech_start_sec']} seconds.",
        "No silent opening.",
        "No breathing before the first word.",
        "Say exact_dialogue only. Do not improvise, paraphrase, add, or skip words.",
        "Do not repeat lines from earlier mini-scenes.",
    ]


def build_json_prompt(
    eid: str,
    mid: str,
    ms: dict[str, Any],
    ref: str,
    voice_lock: dict,
    episode: dict[str, Any],
) -> dict[str, Any]:
    dialogue = (ms.get("dialogue") or "").strip()
    duration = ms.get("duration_sec", 5)
    delivery = (ms.get("voice_notes") or "").strip() or "Natural podcast delivery."
    camera = ms.get("camera_angle", "Medium close-up, straight-on")
    performance = ms.get("performance_notes", "Calm confident podcast host")
    motion = ms.get(
        "motion_notes",
        "Static camera with very subtle slow push-in; realistic blinking; natural mouth movement",
    )
    voice = build_voice_block(voice_lock, episode)
    speech_rules = build_speech_rules(voice_lock)

    # Voice-first key order for Grok Imagine weighting
    return {
        "exact_dialogue": dialogue,
        "voice": voice,
        "speech_start_sec": voice_lock["speech_start_sec"],
        "speech_rules": speech_rules,
        "crossfade": {
            "start": ms.get(
                "crossfade_start",
                "Begin speech within 0.2-0.5 seconds; neutral mouth before first word.",
            ),
            "end": ms.get(
                "crossfade_end",
                "End mid-natural motion for crossfade-friendly cut.",
            ),
        },
        "prompt_pack_name": f"{CHARACTER_NAME} {eid} - {mid}",
        "format": "image_to_video_talking_head",
        "reference_image": {
            "path": ref,
            "instruction": (
                "Use the uploaded image as the exact character and scene reference. "
                "This file sets the camera angle and framing — match it. "
                "Text camera notes support the shot but do not override the reference composition."
            ),
            "angle_variation_note": ANGLE_VARIATION_NOTE,
            "consistency_rules": CONSISTENCY_RULES,
        },
        "scene": {
            "type": "ultra-realistic UGC talking-head podcast video",
            "character_name": CHARACTER_NAME,
            "character_description": CHARACTER_DESCRIPTION,
            "setting": SETTING,
            "camera": {
                "framing": camera,
                "angle": camera,
                "movement": motion,
                "eye_contact": "Direct eye contact with the camera",
            },
            "lighting": {
                "style": "Cinematic but natural",
                "key_light": "Soft light on the face",
                "rim_light": "Warm red rim light from the background",
                "mood": "Podcast studio, polished, calm, not horror",
            },
        },
        "performance": {
            "energy": performance,
            "facial_expression": performance,
            "head_motion": "Subtle head nods, slight head tilts, slow natural movement back to center",
            "eye_motion": "Realistic blinking, steady eye contact",
            "body_motion": "Grounded posture, relaxed shoulders, slight forward lean toward the microphone",
            "hands": "Minimal movement, small natural gestures near the desk only if visible",
            "avoid": PERFORMANCE_AVOID + list(voice_lock.get("voice_negatives", [])),
        },
        "dialogue": {
            "spoken_lines": dialogue,
            "voice_direction": voice["voice_direction"],
            "voice_continuity": voice["voice_continuity"],
            "delivery": voice["delivery"],
            "delivery_emphasis": delivery,
            "strict_rules": [
                "Exact dialogue only",
                "No improvise",
                "No paraphrase",
                "No add words",
                "No skip words",
            ],
            "timing_notes": [
                f"Speech starts within {voice_lock['speech_start_sec']} seconds",
                "No silent opening",
                "No breathing before speech",
            ],
            "lipsync": "Accurate mouth movement synced to the dialogue. Natural jaw and lip motion. No exaggerated mouth shapes.",
        },
        "ending_state": {
            "action": "Finish naturally after the last word while holding eye contact.",
            "pose": "Relaxed shoulders, calm face, microphone still in front of him.",
            "transition": ms.get(
                "crossfade_end",
                "End mid-natural motion for clean edit to next mini-scene.",
            ),
        },
        "duration": f"{duration} seconds",
        "quality": {
            "realism": "ultra-realistic",
            "resolution_style": "high-detail cinematic video",
            "motion_style": "natural subtle podcast movement",
            "continuity": ms.get(
                "continuity_notes",
                "Same character, same wardrobe, same studio",
            ),
        },
    }


def build_compact_json_prompt(
    eid: str,
    mid: str,
    ms: dict[str, Any],
    ref: str,
    voice_lock: dict,
    episode: dict[str, Any],
) -> dict[str, Any]:
    """Short voice-first pack when full JSON still drifts."""
    voice = build_voice_block(voice_lock, episode)
    return {
        "exact_dialogue": (ms.get("dialogue") or "").strip(),
        "voice": voice,
        "speech_start_sec": voice_lock["speech_start_sec"],
        "speech_rules": build_speech_rules(voice_lock),
        "reference_image": {"path": ref},
        "prompt_pack_name": f"{CHARACTER_NAME} {eid} - {mid} (compact voice)",
        "format": "image_to_video_talking_head_compact",
    }


def build_listening_json_prompt(
    eid: str,
    lid: str,
    clip: dict[str, Any],
    ref: str,
    presets: dict[str, Any],
) -> dict[str, Any]:
    duration = clip.get("duration_sec", presets.get("duration_sec", 8))
    camera = clip.get("camera_angle", "Medium close-up, listening")
    performance = clip.get("performance_notes", "Attentive silent listener")
    motion = clip.get(
        "motion_notes",
        "Slow breathing, realistic blinking, small head movements; mouth closed",
    )

    return {
        "clip_type": presets.get("clip_type", "listening_silent"),
        "exact_dialogue": "",
        "no_speech_rules": presets.get("no_speech_rules", []),
        "duration_sec": duration,
        "prompt_pack_name": f"{CHARACTER_NAME} {eid} - {lid} (silent listen)",
        "format": "image_to_video_silent_listening",
        "reference_image": {
            "path": ref,
            "instruction": (
                "Use the uploaded image as the exact character and scene reference. "
                "Match camera angle and framing. Host is listening, not speaking."
            ),
            "consistency_rules": CONSISTENCY_RULES,
        },
        "scene": {
            "type": "ultra-realistic silent podcast reaction shot",
            "character_name": CHARACTER_NAME,
            "character_description": (
                "Crypto broadcast host seated at desk with headphones and microphone, "
                "listening attentively to an off-screen guest."
            ),
            "setting": "Blue-orange crypto broadcast studio; same as speaking scenes.",
            "camera": {
                "framing": camera,
                "angle": camera,
                "movement": "Static camera or very subtle slow drift; no sudden moves",
                "eye_contact": "Eyes toward guest or lens — attentive listen, not performing to camera",
            },
        },
        "performance": {
            "energy": performance,
            "facial_expression": "Calm attentive listener; neutral or faint closed-mouth expression",
            "head_motion": "Micro-nods and slight tilts only; return to center",
            "eye_motion": "Natural blinking every 3-5 seconds; subtle eye tracking",
            "body_motion": presets.get("motion_rules", []),
            "mouth": presets.get("mouth_rules", []),
            "hands": "Still or minimal idle movement on desk",
            "avoid": presets.get("avoid", []),
        },
        "audio": {
            "host_voice": "NONE — completely silent",
            "ambient": "Optional very subtle room tone only; no host speech",
        },
        "ending_state": {
            "action": "Hold attentive listen pose through full duration.",
            "pose": "Breathing visible, eyes alive, mouth at rest.",
            "transition": "End mid-blink or mid-nod for invisible stitch to next listen clip.",
        },
        "duration": f"{duration} seconds",
        "stitch_group": clip.get("stitch_group", presets.get("stitch_group", "guest_hold")),
        "quality": {
            "realism": "ultra-realistic",
            "motion_style": "natural idle listening — breathing, blink, micro head movement",
            "continuity": clip.get("continuity_notes", "Same Pomplarion identity and studio"),
        },
    }


def build_txt_fallback(
    ms: dict[str, Any],
    ref: str,
    voice_lock: dict,
    template: str,
) -> str:
    return fill_template(
        template,
        {
            "dialogue": (ms.get("dialogue") or "").strip(),
            "speech_start_sec": voice_lock["speech_start_sec"],
            "voice_direction": voice_lock["voice_direction"],
            "continuity_instruction": voice_lock["continuity_instruction"],
            "delivery_emphasis": (ms.get("voice_notes") or "").strip()
            or "Natural podcast delivery.",
            "reference_image": ref,
            "camera_angle": ms.get("camera_angle", "Medium close-up"),
            "performance_notes": ms.get(
                "performance_notes", "Calm confident podcast host"
            ),
            "motion_notes": ms.get(
                "motion_notes",
                "Subtle push-in, expressive eyes, realistic blinking",
            ),
            "duration_sec": str(ms.get("duration_sec", 5)),
        },
        TXT_PLACEHOLDERS,
    )


def build_listening_txt_fallback(
    clip: dict[str, Any],
    ref: str,
    template: str,
) -> str:
    return fill_template(
        template,
        {
            "duration_sec": str(clip.get("duration_sec", 8)),
            "motion_notes": clip.get(
                "motion_notes",
                "Breathing, blinking, small head movements; mouth closed",
            ),
            "performance_notes": clip.get(
                "performance_notes", "Attentive silent listener"
            ),
            "reference_image": ref,
            "camera_angle": clip.get("camera_angle", "Medium close-up listen"),
        },
        LISTENING_TXT_PLACEHOLDERS,
    )


def write_stitch_notes(eid: str, clip_ids: list[str], presets: dict[str, Any]) -> None:
    dur = presets.get("duration_sec", 8)
    n = presets.get("stitch_clips_recommended", 3)
    target = presets.get("stitch_target_seconds", "16 to 24")
    lines = [
        f"# {eid} — Silent listening stitch notes",
        "",
        "Use when a guest speaks and Pomplarion stays on camera **without talking**.",
        "",
        "## Render",
        "",
        f"Generate **{n} clips** at **{dur}s** each (e.g. `{'`, `'.join(clip_ids[:n])}`).",
        "Paste `EP001-Lxx.json` into Grok Imagine with matching reference PNG.",
        "",
        "## Stitch in edit",
        "",
        f"- Cut order: **{' → '.join(clip_ids[:n])}** (or any 3 from L01–L06)",
        "- Cut on **blink** or **micro-nod** for invisible joins",
        f"- Target total hold: **{target} seconds** ({n} × {dur}s)",
        "- Audio: **guest only** — mute Pomplarion track",
        "",
        "## All listen clips",
        "",
    ]
    for lid in clip_ids:
        lines.append(f"- `{eid}-{lid}.json` + ref from listening-scene-map")
    out = LISTENING_OUTPUT_DIR / eid / f"{eid}-STITCH-NOTES.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_speaking(
    episode_filter: str | None = None,
    output_format: str = "both",
    compact: bool = True,
) -> int:
    data = load_json(SCENE_MAP)
    voice_lock = load_json(VOICE_LOCK)
    write_json = output_format in ("json", "both")
    write_txt = output_format in ("txt", "both")
    template_txt = load_text(TEMPLATE_TXT) if write_txt else ""

    warnings: list[str] = []
    seen_ids: set[str] = set()
    count = 0
    json_count = 0
    compact_count = 0
    txt_count = 0

    for eid, default_ref, episode, _scene, ms in iter_mini_scenes(data, episode_filter):
        mid = ms.get("mini_scene_id", "")
        if not mid:
            warnings.append(f"[{eid}] mini-scene missing mini_scene_id")
            continue

        uid = f"{eid}-{mid}"
        if uid in seen_ids:
            warnings.append(f"Duplicate mini_scene_id: {uid}")
        seen_ids.add(uid)

        check_risky_vocal_tokens(uid, ms, warnings)

        dialogue = (ms.get("dialogue") or "").strip()
        if not dialogue:
            warnings.append(f"[{uid}] empty dialogue")

        ref = ms.get("reference_image") or default_ref
        if ref:
            validate_reference(ref, warnings)

        out_ep = OUTPUT_DIR / eid
        out_ep.mkdir(parents=True, exist_ok=True)

        if write_json:
            payload = build_json_prompt(eid, mid, ms, ref, voice_lock, episode)
            (out_ep / f"{eid}-{mid}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            json_count += 1

        if compact and write_json:
            compact_dir = out_ep / COMPACT_SUBDIR
            compact_dir.mkdir(parents=True, exist_ok=True)
            compact_payload = build_compact_json_prompt(
                eid, mid, ms, ref, voice_lock, episode
            )
            (compact_dir / f"{eid}-{mid}-voice.json").write_text(
                json.dumps(compact_payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            compact_count += 1

        if write_txt:
            body = build_txt_fallback(ms, ref, voice_lock, template_txt)
            (out_ep / f"{eid}-{mid}.txt").write_text(body, encoding="utf-8")
            txt_count += 1

        count += 1

    if warnings:
        print("Warnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    compact_msg = f" + {compact_count} compact" if compact and write_json else ""
    print(
        f"Speaking: {count} mini-scene(s) — {json_count} JSON{compact_msg} + {txt_count} TXT → {OUTPUT_DIR}"
    )
    return count


def generate_listening(
    episode_filter: str | None = None,
    output_format: str = "both",
) -> int:
    data = load_json(LISTENING_SCENE_MAP)
    presets = load_json(LISTENING_PRESETS)
    template_txt = (
        load_text(TEMPLATE_LISTENING_TXT) if output_format in ("txt", "both") else ""
    )

    warnings: list[str] = []
    seen_ids: set[str] = set()
    count = 0
    json_count = 0
    txt_count = 0
    episode_clips: dict[str, list[str]] = {}

    for eid, default_ref, stitch_group, clip in iter_listen_clips(data, episode_filter):
        lid = clip.get("listen_id", "")
        if not lid:
            warnings.append(f"[{eid}] clip missing listen_id")
            continue

        uid = f"{eid}-{lid}"
        if uid in seen_ids:
            warnings.append(f"Duplicate listen_id: {uid}")
        seen_ids.add(uid)

        ref = clip.get("reference_image") or default_ref
        if ref:
            validate_reference(ref, warnings)

        clip_out = dict(clip)
        clip_out.setdefault("stitch_group", stitch_group)

        out_ep = LISTENING_OUTPUT_DIR / eid
        out_ep.mkdir(parents=True, exist_ok=True)
        episode_clips.setdefault(eid, []).append(lid)

        if output_format in ("json", "both"):
            payload = build_listening_json_prompt(eid, lid, clip_out, ref, presets)
            (out_ep / f"{eid}-{lid}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            json_count += 1

        if output_format in ("txt", "both"):
            body = build_listening_txt_fallback(clip_out, ref, template_txt)
            (out_ep / f"{eid}-{lid}.txt").write_text(body, encoding="utf-8")
            txt_count += 1

        count += 1

    for eid, lids in episode_clips.items():
        write_stitch_notes(eid, sorted(lids), presets)

    if warnings:
        print("Warnings:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    print(
        f"Listening: {count} clip(s) — {json_count} JSON + {txt_count} TXT → {LISTENING_OUTPUT_DIR}"
    )
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Grok Imagine prompts")
    parser.add_argument("--episode", help="Episode id filter (e.g. EP001)")
    parser.add_argument(
        "--mode",
        choices=("speaking", "listening", "all"),
        default="speaking",
        help="speaking (MS), listening (silent L), or all",
    )
    parser.add_argument(
        "--format",
        choices=("json", "txt", "both"),
        default="both",
    )
    parser.add_argument(
        "--no-compact",
        action="store_true",
        help="Skip compact voice-first JSON in prompts/generated/EPxxx/compact/",
    )
    args = parser.parse_args()

    try:
        total = 0
        if args.mode in ("speaking", "all"):
            total += generate_speaking(
                args.episode, args.format, compact=not args.no_compact
            )
        if args.mode in ("listening", "all"):
            total += generate_listening(args.episode, args.format)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if total == 0:
        print(
            "No clips matched. Add episodes to data/scene-map.json or "
            "data/listening-scene-map.json, then regenerate.",
            file=sys.stderr,
        )
        sys.exit(0)


if __name__ == "__main__":
    main()