# Pomplarion — Character & Voice Bible

Use across every clip. **Voice timbre is locked in** [config/voice-lock.json](config/voice-lock.json) — do not override per scene.

## Visual identity (locked)

- **Name:** Pomplarion
- **Look:** Human broadcast host with blue scaly skin; orange-glowing fin/wing structures on black over-ear headphones
- **Wardrobe:** Navy suit jacket, white dress shirt, blue-and-orange plaid tie, small Bitcoin lapel pin
- **Props:** Professional broadcast microphone with windscreen
- **Set:** Futuristic cryptocurrency broadcast studio — blue and orange HUD, live BTC tickers, charts, cinematic rim light
- **Expression guardrails:** Confident, warm, professional — never evil, angry, demonic, scary, or aggressive

## Approved voice (placeholder lock)

**Warm, confident, authoritative crypto-podcast host baritone; clear and professional.**

Same speaker, same mic tone, same pacing family on every mini-scene. Update `config/voice-lock.json` after first approved Imagine clip (anchor MS02).

Per-scene `voice_notes` in scene-map are **delivery emphasis only** — never change timbre.

## Motion style (dynamic but controlled)

- Subtle push-in when camera note requests it
- Expressive eyes, realistic blinking, small natural head movement
- Natural mouth movement synced to exact dialogue (speaking clips only)

## Hard rules for Imagine

1. **Exact dialogue only** — no improvise, paraphrase, add, or skip
2. **Speech within 0.2–0.5 seconds** — no silent lead-in (speaking clips)
3. **Same voice** — `voice_direction` identical on every JSON prompt
4. **Same visual identity** — match reference image; swap ref file for angle variety