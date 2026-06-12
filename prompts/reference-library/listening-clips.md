# Silent listening clips — Pomplarion

Use when a guest speaks and Pomplarion stays on camera **without talking**.

## EP001 — Clinton answer after MS11 (~2:50)

1. `python3 tools/generate_prompts.py --mode listening --episode EP001`
2. Render **L01–L06** once each (8s, no speech) in Grok Imagine
3. Drop raw clips in `video/raw/listening/EP001/` as `L01.mp4`, `L02.mp4`, …
4. **Improved stitch (crossfade):**
   ```bash
   python3 tools/stitch_listening_hold.py --input-dir video/raw/listening/EP001 --target 170
   ```
   Output: `video/edited/listening/EP001/hold_170s_xfade.mp4`
5. **Clinton audio only** — mute Pomplarion track

Avoid `ffmpeg -stream_loop` on a single clip — hard jumps at loop points. Crossfade multiple angles instead.

See `prompts/generated/listening/EP001/EP001-STITCH-NOTES.md` after generate.

Default listen ref: `pomplarion-angle-10-profile-listen.png`