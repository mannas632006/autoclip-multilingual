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

## Command-line setup on Windows

From the repository folder in PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
winget install --id Gyan.FFmpeg -e
```

Open a new PowerShell window after installing FFmpeg, so Windows finds it, and check it with `ffmpeg -version`.

For videos without subtitles, install Whisper and a compatible audio library:

```powershell
python -m pip install faster-whisper
python -m pip install "av<15" --only-binary=:all:
```

The second line matters. `faster-whisper` pulls in the newest `av`, which no longer accepts an option faster-whisper uses, and transcription then fails with `TypeError: open() got an unexpected keyword argument 'metadata_errors'`. `--only-binary=:all:` makes pip use a ready-made Windows download instead of trying to compile it.

Then run, for example with a free Google Gemini key from aistudio.google.com:

```powershell
autoclip run "$HOME\Downloads\video.mp4" --provider gemini --model gemini-2.5-flash --api-key YOUR_KEY
```

AutoClip's own command-line progress messages are in Chinese; the clips, titles and collections it produces are in English.

## Long videos

Whisper loads the whole audio track into memory at once. On a typical laptop, videos longer than about 20 minutes can fail with `MemoryError: Unable to allocate ...` (a 72-minute lecture needed 1.3 GB for one step). Either trim the video first:

```powershell
ffmpeg -ss 0 -t 720 -i "video.mp4" -c copy "video_first12min.mp4"
```

or transcribe it in 10-minute pieces with the included script, then give AutoClip the subtitles:

```powershell
python scripts/transcribe_long.py "$HOME\Downloads\video.mp4"
autoclip run "$HOME\Downloads\video.mp4" --srt "$HOME\Downloads\video.srt" --provider gemini --model gemini-2.5-flash --api-key YOUR_KEY
```

The script writes `video.srt` next to the video and reuses the speech model AutoClip already downloaded. Options: `--language` (default `en`, or `auto`), `--model` (`tiny`, `base`, `small`, `medium`; default `base`) and `--minutes` (piece length, default 10).

If the video is on YouTube, downloading its captions is faster still:

```powershell
yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs en --convert-subs srt -o "$HOME\Downloads\video" "YOUTUBE_LINK"
```
