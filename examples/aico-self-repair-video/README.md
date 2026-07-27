# AICO self-repair video

This package renders the real 2026-07-27 AICO self-repair case as:

- `AicoSelfRepair`: 3-minute, 1920×1080 MP4 with Chinese narration;
- `AicoSelfRepairTeaser`: 40-second, 1280×720 silent teaser used to build the README GIF.

The Telegram UI is privacy-safe reconstruction. Task IDs, roles, risk levels, terminal states,
diff summary and audit sequence come from the real case documented at
[`../../docs/showcase/aico-self-repair-case.md`](../../docs/showcase/aico-self-repair-case.md).
It intentionally includes the first failed provider run.

CosyVoice renders the script at its natural pace. The checked-in MP3 applies one uniform speed
factor, and the Remotion scene boundaries follow the measured duration of each compressed cue so
the narration and visuals stay aligned without distorting individual sentences.

```bash
npm install
/Users/wangzq/.local/bin/voice doctor
/Users/wangzq/.local/bin/voice render-srt \
  --engine cosy --srt public/narration.srt --voice female \
  -o public/audio/narration.wav
ffmpeg -i public/audio/narration.wav \
  -filter:a atempo=1.485460 -c:a libmp3lame -b:a 128k \
  public/audio/narration.mp3
npm run still
npm run render
npm run render:teaser
```

Copy verified outputs to `docs/assets/` only after visual inspection and `ffprobe` validation.
