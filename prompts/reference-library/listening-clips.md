# Silent listening clips — Pomplarion

Use when a guest speaks and Pomplarion stays on camera **without talking**.

1. Add clips to `data/listening-scene-map.json`
2. `python3 tools/generate_prompts.py --mode listening --episode EP001`
3. Paste `prompts/generated/listening/EP001/EP001-Lxx.json` + matching ref PNG
4. Stitch 2–3 clips (8s each) for 16–24s hold; cut on blink
5. **Guest audio only** — mute Pomplarion track

Default listen ref: `pomplarion-angle-10-profile-listen.png`