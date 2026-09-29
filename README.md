<div align="center">

<img src="src-tauri/icons/128x128.png" alt="AutoClip Multilingual" width="72" height="72">

# AutoClip Multilingual

### AI highlight clipping for English and Chinese videos

Turn long talks, podcasts, lectures and interviews into short, titled, ranked clips, in the language of the video.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mannas632006/autoclip-multilingual?style=flat-square)](https://github.com/mannas632006/autoclip-multilingual/stargazers)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](#quick-start)
[![Based on AutoClip](https://img.shields.io/badge/based%20on-zhouxiaoka%2Fautoclip-555?style=flat-square)](https://github.com/zhouxiaoka/autoclip)

[What's new](#whats-new-in-this-fork) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Troubleshooting](#troubleshooting) · [Report an issue](https://github.com/mannas632006/autoclip-multilingual/issues)

</div>

AutoClip Multilingual reads a video's transcript, finds the moments worth sharing, scores them, writes titles, groups related clips into collections, and cuts the video with FFmpeg. It is built on [AutoClip](https://github.com/zhouxiaoka/autoclip) by zhouxiaoka, an open-source clipping tool designed for Chinese content.

The original works well on Chinese videos, but every instruction it sends to the AI model is written in Chinese, with Chinese examples and Chinese keyword lists. On an English video, that meant Chinese-style titles, a scoring step aimed at Chinese platforms, and collections that never formed. **This fork makes English a first-class language**: it detects the transcript's language and runs the whole pipeline with English instructions, while Chinese videos behave exactly as before.

```text
Video (with or without subtitles) → Whisper transcript → language detection
  → topic outline → timestamps → scoring → titles → collections → clips and exports
```

![Video import and project management](docs/images/home-v1.4.0.png)

<table>
  <tr>
    <td width="50%" align="center"><strong>AI-generated clips</strong></td>
    <td width="50%" align="center"><strong>Studio preview and editing</strong></td>
  </tr>
  <tr>
    <td><a href="docs/images/clips-v1.4.0.png"><img src="docs/images/clips-v1.4.0.png" alt="AI-generated clips" width="100%"></a></td>
    <td><a href="docs/images/studio-v1.4.0.png"><img src="docs/images/studio-v1.4.0.png" alt="Studio preview and editing" width="100%"></a></td>
  </tr>
</table>

<sub>Screenshots from the upstream AutoClip v1.4.0 interface, which this fork shares.</sub>

## What's new in this fork

| Area | Upstream AutoClip | AutoClip Multilingual |
| --- | --- | --- |
| **Language of the AI instructions** | Chinese only, for every video | Detected from the transcript: English (and other Latin-script) videos get a full English instruction set; Chinese videos keep the originals |
| **Content categories** | 7 category-specific Chinese prompt sets | All 7 categories (business, commentary, entertainment, how-to, knowledge, opinion, talks) translated, 38 English prompt files in total |
| **Titles and recommendations** | Written for Chinese platforms | Written in the video's language, for YouTube, TikTok and Reels audiences |
| **Scoring** | Can silently fall back to a flat 0.5 score for every clip when the model's reply doesn't match the expected format | English scoring asks for a compact reply that AutoClip always parses, so clips are ranked by real scores |
| **Collections** | Backup grouping uses Chinese keywords only, so English clips never matched | English theme keywords (whole-word matching) plus English collection names |
| **Category prompt formats** | Several Chinese category prompts ask for output the code can't read (the outline step can fail outright) | English category prompts use the formats the code actually reads |
| **Title cards and covers** | Cut at a fixed character count, which splits English words | Wrapped at word boundaries onto two lines |
| **Regenerate title / collection name** | Always used the Chinese instructions | Picks the language from the clip itself |
| **Long videos on a laptop** | Whisper can run out of memory on long videos | `scripts/transcribe_long.py` transcribes in 10-minute pieces |
| **Windows command-line setup** | Not documented; Whisper fails with the current `av` library | Step-by-step guide, including the fix |
| **Language override** | None | `AUTOCLIP_CONTENT_LANGUAGE=en` or `zh` forces a language (and Whisper's language too) |

Everything else (the clip-finding logic, timestamp snapping, duration rules, score thresholds, FFmpeg cutting, export presets, publishing, the desktop UI and the MCP server) is the same as upstream.

### Verified, not assumed

- **Chinese is unchanged, byte for byte.** The same Chinese video was run through the original code and this fork: the instructions sent to the model and every output file were identical.
- **32 new automated tests** cover language detection, prompt selection for every category, the output formats, title wrapping and the scoring reply, and the existing 680+ tests still pass.
- **Real-world run.** An English video transcribed locally by Whisper and analyzed by Google Gemini produced 4 clips ranked 95 / 93 / 88 / 85 with English titles, in under 4 minutes on a laptop.

## Quick start

| Your workflow | Option | Includes the English support? |
| --- | --- | --- |
| Command line / automation / agents | **CLI** (below) | ✅ Yes |
| Self-hosted web interface | **Docker** (below) | ✅ Yes, built from this repository |
| Desktop app | Upstream installers | ❌ No. The published `.dmg` / `.exe` installers are built from the original project |

### 1. Install (command line)

You need Python 3.10+ (3.11 recommended) and FFmpeg.

<details open>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
git clone https://github.com/mannas632006/autoclip-multilingual.git
cd autoclip-multilingual
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
winget install --id Gyan.FFmpeg -e
```

Open a new PowerShell window after installing FFmpeg, go back to the folder and activate the venv again. If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

</details>

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
git clone https://github.com/mannas632006/autoclip-multilingual.git
cd autoclip-multilingual
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
# FFmpeg: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Debian/Ubuntu)
```

</details>

### 2. Enable transcription (for videos without subtitles)

```bash
python -m pip install faster-whisper
python -m pip install "av<15" --only-binary=:all:
```

The second line is required: the newest `av` library breaks faster-whisper with `unexpected keyword argument 'metadata_errors'`. The speech model (about 145 MB) downloads automatically on first use. If you already have subtitles, skip this step and pass them with `--srt`.

### 3. Get a model key

Any supported provider works. Free options:

| Provider | How | Flags |
| --- | --- | --- |
| **Google Gemini** (free tier) | Key from [aistudio.google.com](https://aistudio.google.com) | `--provider gemini --model gemini-2.5-flash --api-key KEY` |
| **Groq** (free tier) | Key from [console.groq.com](https://console.groq.com) | `--provider openai --base-url https://api.groq.com/openai/v1 --model llama-3.3-70b-versatile --api-key KEY` |
| **Ollama** (local, no key) | Install Ollama, run `ollama pull qwen2.5:7b` | `--provider ollama` |

Paid options include OpenAI, DeepSeek, Qwen (DashScope), Kimi, GLM and Grok; run `autoclip providers` for the full list. Small local models follow the strict output formats less reliably than cloud models.

### 4. Clip a video

```bash
autoclip run "path/to/video.mp4" --provider gemini --model gemini-2.5-flash --api-key YOUR_KEY
```

With existing subtitles (faster, and usually more accurate):

```bash
autoclip run "path/to/video.mp4" --srt "path/to/video.srt" --provider gemini --model gemini-2.5-flash --api-key YOUR_KEY
```

At the end AutoClip prints each clip with its score, time range and title, plus the folder it saved them in. The summary line is in Chinese ("完成 4 切片 · 0 合集" means "done: 4 clips, 0 collections"):

```text
完成  4 切片 · 0 合集 · 221s
    95  00:00:04,620 → 00:03:06,180  Cut PowerPoint time: ChatGPT generates outlines & refines slides
    93  00:04:52,920 → 00:07:15,720  PowerPoint magic: Import Word outline, get instant designs & images
    88  00:03:06,640 → 00:04:50,700  PowerPoint prep: Use Word to structure your ChatGPT content
    85  00:07:18,440 → 00:08:18,220  Polish & present: AI saves hours on PowerPoint design
```

The progress messages are printed in Chinese too; the clips, titles and collections are in the video's language.

### 5. Export for Shorts, TikTok or Reels

```bash
autoclip export PROJECT_ID --preset shorts     # 9:16, captions + title card, 60 s max
autoclip export PROJECT_ID --preset douyin     # 9:16 with a blurred background, no length limit
autoclip list                                  # your projects
autoclip show PROJECT_ID                       # clips, scores and file paths
```

Other presets: `xiaohongshu`, `bilibili` (16:9) and `original`. Add `--data-dir FOLDER` before the command (for example `autoclip --data-dir ~/Videos/AutoClip run ...`) to choose where projects are stored.

<details>
<summary><strong>Docker / web interface</strong></summary>

Requires Docker and Docker Compose v2. The image is built from this repository, so it includes the English support.

```bash
git clone https://github.com/mannas632006/autoclip-multilingual.git
cd autoclip-multilingual
cp env.example .env        # set LLM_PROVIDER and the matching API key, e.g. LLM_PROVIDER=gemini and API_GEMINI_API_KEY=...
mkdir -p data logs uploads
docker compose up -d --build
```

Open <http://localhost:3000>. The API documentation is at <http://localhost:8000/docs>. See the [Docker guide](docs/DOCKER.en.md) for details.

</details>

<details>
<summary><strong>MCP server (use AutoClip from Claude, Cursor and other agents)</strong></summary>

```bash
autoclip mcp
```

In your MCP client, set `command` to the absolute path of `autoclip` inside your virtual environment and `args` to `["mcp"]`. The server exposes tools to clip a video, check job status, read projects, export and publish. See the [CLI / MCP guide (Chinese)](docs/CLI_AND_MCP.md).

</details>

## How it works

| Step | What happens | Language-aware in this fork |
| --- | --- | --- |
| 0. Transcript | Uses your SRT, or transcribes locally with Whisper (automatic language detection) | Whisper can be pinned with `AUTOCLIP_CONTENT_LANGUAGE` |
| 1. Outline | The model lists the video's topics | ✅ Language detected here; English instructions and English duration rules |
| 2. Timestamps | The model locates each topic; AutoClip snaps times to subtitle boundaries and enforces length limits | ✅ |
| 3. Scoring | The model scores each segment 0–1 and writes a one-line recommendation; clips above 0.7 are kept (at least 2–3 are always kept) | ✅ Compact reply format; transcript excerpt scaled for English |
| 4. Titles | One title per clip | ✅ |
| 5. Collections | The model groups related clips; keyword matching is the backup | ✅ English keyword themes and names |
| 6. Cutting | FFmpeg cuts each clip and joins collections | Unchanged |

Clip length adapts to the video: under 8 minutes aims for 30–90 s clips, 8–30 minutes for 1–3 minutes, longer videos for 2–6 minutes.

### Language detection

After the transcript is ready, AutoClip compares Chinese, Japanese and Korean characters against Latin letters. Clearly Latin-script text uses the English instructions, and the model is told to answer in the transcript's own language. Everything else uses the original Chinese instructions. The decision is saved to `metadata/content_language.json` in each project.

To force a language:

```bash
AUTOCLIP_CONTENT_LANGUAGE=en autoclip run video.mp4 ...     # macOS / Linux
$env:AUTOCLIP_CONTENT_LANGUAGE="en"; autoclip run video.mp4 ...   # Windows PowerShell
```

This also pins Whisper's language, which helps when a video opens with music and automatic detection guesses wrong.

## What else AutoClip can do

These features come from upstream AutoClip and work the same in this fork. Click any thumbnail to view the full image.

<table>
  <tr>
    <td width="50%" valign="top">
      <h4>Import footage</h4>
      <p>Local videos, YouTube or Bilibili links, with optional SRT subtitles.</p>
      <a href="docs/images/feature-import.png"><img src="docs/images/feature-import.png" alt="Import footage" width="420"></a>
    </td>
    <td width="50%" valign="top">
      <h4>Find highlights</h4>
      <p>Topic outlines, timelines, highlight scores and clip titles from the transcript.</p>
      <a href="docs/images/clips-v1.4.0.png"><img src="docs/images/clips-v1.4.0.png" alt="Find highlights" width="260"></a>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h4>Clips and collections</h4>
      <p>Generate clips and suggested collections, then reorder them manually.</p>
      <a href="docs/images/feature-collections.png"><img src="docs/images/feature-collections.png" alt="Clips and collections" width="420"></a>
    </td>
    <td width="50%" valign="top">
      <h4>Export for publishing</h4>
      <p>Presets for YouTube Shorts, Douyin, Xiaohongshu and Bilibili, with burned-in subtitles and title cards.</p>
      <a href="docs/images/feature-export.png"><img src="docs/images/feature-export.png" alt="Export for publishing" width="420"></a>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h4>Covers and publishing</h4>
      <p>Generate covers and publish now or on a schedule to TikTok, Instagram, YouTube, X, LinkedIn and more through your own Upload-Post account, or to Bilibili.</p>
      <a href="docs/images/feature-publish.png"><img src="docs/images/feature-publish.png" alt="Publishing" width="200"></a>
      <a href="docs/images/feature-cover.png"><img src="docs/images/feature-cover.png" alt="Cover settings" width="200"></a>
    </td>
    <td width="50%" valign="top">
      <h4>Publishing calendar</h4>
      <p>Review publishing history, manage scheduled posts, or simply download your clips.</p>
      <a href="docs/images/feature-calendar.png"><img src="docs/images/feature-calendar.png" alt="Publishing calendar" width="420"></a>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h4>Choose your model</h4>
      <p>Gemini, OpenAI-compatible APIs, DeepSeek, Qwen and other cloud services, or local models through Ollama and LM Studio.</p>
      <a href="docs/images/feature-models.png"><img src="docs/images/feature-models.png" alt="Model settings" width="420"></a>
    </td>
    <td width="50%" valign="top">
      <h4>Automate your workflow</h4>
      <p>Script runs with the CLI, or call the same pipeline from an MCP client.</p>
      <a href="docs/images/feature-cli.png"><img src="docs/images/feature-cli.png" alt="Command line" width="420"></a>
    </td>
  </tr>
  <tr>
    <td colspan="2" align="center" valign="top">
      <h4>Multilingual interface</h4>
      <p>The app interface is available in English, Chinese, Japanese, Korean, Spanish, Portuguese, Russian and French.</p>
      <a href="docs/images/feature-languages.png"><img src="docs/images/feature-languages.png" alt="Interface languages" width="420"></a>
    </td>
  </tr>
</table>

## Troubleshooting

<details>
<summary><strong>"Whisper isn't installed" (没有字幕可分析 … Whisper 还没安装)</strong></summary>

Install transcription support (step 2 of the quick start), or pass subtitles with `--srt`.

</details>

<details>
<summary><strong><code>TypeError: open() got an unexpected keyword argument 'metadata_errors'</code></strong></summary>

Your `av` library is too new for faster-whisper. Run `python -m pip install "av<15" --only-binary=:all:`.

</details>

<details>
<summary><strong><code>MemoryError: Unable to allocate … GiB</code> on long videos</strong></summary>

Whisper loads the whole audio track at once. Transcribe in pieces, then pass the result with `--srt`:

```bash
python scripts/transcribe_long.py "path/to/video.mp4"
autoclip run "path/to/video.mp4" --srt "path/to/video.srt" --provider gemini --model gemini-2.5-flash --api-key YOUR_KEY
```

Or trim the video first: `ffmpeg -ss 0 -t 720 -i video.mp4 -c copy first12min.mp4`. For YouTube videos, downloading the captions is fastest:
`yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs en --convert-subs srt -o video "YOUTUBE_LINK"`.

</details>

<details>
<summary><strong>Every clip has a score of 50</strong></summary>

50 is AutoClip's fallback when it can't read the model's scores. Make sure you're on the latest version of this fork, which fixed this for English videos. If it persists with your model, open an issue and include the lines containing `评分对齐` from the log.

</details>

<details>
<summary><strong><code>WinError 2 The system cannot find the file specified</code> in the log</strong></summary>

FFmpeg isn't installed or isn't on your PATH. Install it and open a new terminal; `ffmpeg -version` should work.

</details>

<details>
<summary><strong>Where are the logs?</strong></summary>

The run prints the log path at the end. On Windows it's `%APPDATA%\AutoClip\logs\cli.log`; read it with
`Get-Content "$env:APPDATA\AutoClip\logs\cli.log" -Encoding UTF8 -Tail 40`.

</details>

## Known limitations

- **Transcript-based.** Highlights are chosen from what is said, so talk-heavy videos work best; purely visual or music content does not.
- **Command-line messages are in Chinese.** The output content is in the video's language; the progress text is inherited from upstream.
- **Chinese category prompts are unchanged.** When Chinese videos use a category other than Default or Knowledge, several of those prompts ask for formats the code can't read (upstream behaviour). The English versions don't have this problem.
- **Collections need several clips.** The model's grouping is discarded when it suggests fewer than three collections, so short videos often get none.
- **The `shorts` preset stops at 60 seconds.** Use `douyin` for longer vertical clips.
- **Desktop installers don't include this fork's changes.** Use the CLI or Docker.

## Documentation

| Guide | Link |
| --- | --- |
| English videos, Windows setup and long videos | [docs/ENGLISH_CONTENT.md](docs/ENGLISH_CONTENT.md) |
| Installation (upstream) | [docs/USER_INSTALLATION_GUIDE.en.md](docs/USER_INSTALLATION_GUIDE.en.md) |
| Docker | [docs/DOCKER.en.md](docs/DOCKER.en.md) |
| Troubleshooting (upstream) | [docs/FAQ.en.md](docs/FAQ.en.md) |
| CLI / MCP, model providers (Chinese) | [docs/CLI_AND_MCP.md](docs/CLI_AND_MCP.md) · [docs/MULTI_LLM_PROVIDER_GUIDE.md](docs/MULTI_LLM_PROVIDER_GUIDE.md) |
| Privacy | [docs/PRIVACY.en.md](docs/PRIVACY.en.md) |

The original project's README is kept in [Chinese](README-ZH.md), [English](README-EN.md), [日本語](README-JA.md), [한국어](README-KO.md), [Español](README-ES.md), [Português](README-PT.md), [Русский](README-RU.md) and [Français](README-FR.md).

## Running the tests

```bash
cd backend
python -m pytest tests/test_content_language.py -q    # the English-support tests
python -m pytest tests -q                             # the full suite
```

## Credits and license

AutoClip Multilingual is a fork of **[AutoClip](https://github.com/zhouxiaoka/autoclip)** by **zhouxiaoka** and contributors. The clipping pipeline, desktop app, web interface, export and publishing features are their work. This fork adds the multilingual pipeline, the English prompt set, the fixes described above, and the Windows and long-video tooling.

Released under the [MIT License](LICENSE), the same license as the original; the original copyright notice is retained. Issues and pull requests about English support are welcome [here](https://github.com/mannas632006/autoclip-multilingual/issues). For anything else, the upstream project is the best place.
