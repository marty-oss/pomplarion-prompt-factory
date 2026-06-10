# Grok Imagine troubleshooting — Pomplarion

## Grok adds speech on listening clips

- Use `listening_silent` JSON only; `exact_dialogue` must be empty
- Reinforce `no_speech_rules` and `host_voice: NONE`
- Shorter clip (8s) often helps

## Voice drift (speaking clips)

- Use compact JSON: `prompts/generated/EPxxx/compact/EPxxx-MSxx-voice.json`
- Anchor MS02 in same Imagine session
- Run `python3 tools/verify_voice_lock.py`
- Optional: ElevenLabs Voice Changer on stitched master

## Wrong character / wardrobe

- Re-attach correct `pomplarion-angle-*.png`
- Reinforce: navy suit, blue scales, fin headphones, BTC studio in prompt

## Same angle repeating

- Change reference image per mini-scene (see SOURCE-MAPPING.md)