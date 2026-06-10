# Silent listening clips — Pomplarion

Use when a guest speaks and Pomplarion stays on camera **without talking**.

## EP001 — Clinton answer after MS11 (~2:50)

1. `python3 tools/generate_prompts.py --mode listening --episode EP001`
2. Render **L01–L06** once each (8s, no speech) in Grok Imagine
3. In edit: loop **L01 → L06** until **22 clips** (176s)
4. Trim tail to **2:50 (170s)**; cut joins on blink
5. **Clinton audio only** — mute Pomplarion track

See `prompts/generated/listening/EP001/EP001-STITCH-NOTES.md` after generate.

Default listen ref: `pomplarion-angle-10-profile-listen.png`