# Pomplarion Prompt Factory

Local production workflow for **Pomplarion** — crypto broadcast host avatar. Splits scripts into short **Grok Imagine image-to-video** mini-scenes with locked voice and varied camera refs.

**Repo:** https://github.com/marty-oss/pomplarion-prompt-factory  
**Sibling:** [Zorak Rogan Prompt Factory](https://github.com/marty-oss/zorak-rogan-prompt-factory)

## EP001 — Intro (Clinton Donnelly)

**16 mini-scenes (MS01–MS16)** — Pomplarion intro, first question, and Zylos Nine tangent. Clinton answers are **off-camera**.

```bash
python3 tools/generate_prompts.py --episode EP001
python3 tools/verify_voice_lock.py --episode EP001
open prompts/generated/EP001/compact/EP001-MS01-voice.json
```

## v1 scaffold

- 10 angle reference PNGs in `references/character/`
- Identity + voice lock in `config/`
- Generator tools + EP001 scene map

## Quick workflow (when episodes exist)

```bash
cd /Users/martywork/pomplarion-prompt-factory

# 1. Edit mini-scenes
open data/scene-map.json

# 2. Generate prompts (JSON + compact + TXT)
python3 tools/generate_prompts.py --episode EP001

# 3. Verify voice lock
python3 tools/verify_voice_lock.py --episode EP001

# 4. Paste into Imagine
open prompts/generated/EP001/compact/EP001-MS01-voice.json
```

## Folder layout

| Path | Purpose |
|------|---------|
| `config/pomplarion-identity.md` | Visual bible |
| `config/voice-lock.json` | Locked `voice_direction` |
| `references/character/pomplarion-angle-*.png` | Imagine start frames |
| `data/scene-map.json` | Speaking mini-scenes (empty until EP001) |
| `data/listening-scene-map.json` | Silent listen clips |
| `tools/generate_prompts.py` | Prompt generator |
| `prompts/generated/` | Output JSON / TXT / compact |

## Reference angles

Default speaking ref: `pomplarion-angle-06-front-direct.png`  
Default listening ref: `pomplarion-angle-10-profile-listen.png`

See [references/character/SOURCE-MAPPING.md](references/character/SOURCE-MAPPING.md).

## Add first episode

1. Add script under `scripts/episodes/`
2. Add `episode_id: EP001` block to `data/scene-map.json` with `mini_scenes[]`
3. Run `python3 tools/generate_prompts.py --episode EP001`
4. Lock voice in `config/voice-lock.json` after MS02 sounds right

## Listening mode

```bash
python3 tools/generate_prompts.py --mode listening --episode EP001
```

Outputs under `prompts/generated/listening/EP001/`.