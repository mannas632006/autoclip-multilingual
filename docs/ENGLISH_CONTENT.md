# English videos

AutoClip picks its instructions to the AI model from the language of the video's transcript.

- **English (and other Latin-script) transcripts** use the English prompt set in `backend/prompt/en/`. Titles, recommendations and collection names come back in the transcript's language.
- **Chinese transcripts** (and Japanese, Korean, Cyrillic and anything else that is not clearly Latin-script) use the original prompts, exactly as before.

It works the same with or without subtitles:

- **With an SRT file**: the language is read from the subtitles.
- **Without subtitles**: Whisper transcribes the audio with automatic language detection, and the language is read from that transcript.

Nothing needs configuring. The decision is written to `metadata/content_language.json` in each project, and the remaining steps (timestamps, scoring, titles, collections) all use it.

## Forcing a language

Set `AUTOCLIP_CONTENT_LANGUAGE` to `en` or `zh` (default `auto`) before starting AutoClip:

```bash
AUTOCLIP_CONTENT_LANGUAGE=en autoclip run talk.mp4
```

When it is set and Whisper's language is left on automatic, Whisper also transcribes in that language, which helps when a video opens with music and automatic detection guesses wrong. A transcription language chosen explicitly in the settings is never overridden.

## Categories

Every content category (`--category business`, `speech`, …) has an English version in `backend/prompt/en/<category>/`. Where the Chinese category has no prompt of its own (for example `knowledge` scoring and titles), the English default prompt is used, mirroring the Chinese fallback.

## Export

English title cards wrap onto two lines at word boundaries instead of being cut at 40 characters, and auto-generated cover titles wrap by word. Chinese titles render exactly as before.
