# Spec: Ideas from voxtype — three small features and three measurements

## Overview

This thread comes from a research pass over [voxtype](https://github.com/peteonrails/voxtype), a large Rust dictation tool for Linux (about 92,000 lines). The user went through each voxtype idea one by one on 2026-09-26 and chose:

**Build now:**
1. A trailing space after each result.
2. Filler word removal ("um", "uh", ...).
3. Start and stop sounds.

**Measure first, decide in a later thread:**
4. Paste instead of type (with the old clipboard restored afterwards).
5. A bigger Whisper model, as a possible second model on a modifier key.
6. A different speech engine (NVIDIA Parakeet) instead of Whisper.

**Dropped by the user:** replacements table (hotwords already do this job well), cancel key (press-to-start / release-to-stop makes it unnecessary), retry on repeating output, cleanup command through an LLM (too slow), and all Wayland, packaging, GPU, setup-screen, panel, meeting and file-transcription features (not relevant on this X11 machine, or already covered elsewhere).

**Update 2026-09-26:** after the Ghostty paste results the user dropped idea 4: "i dont want paste. i just want automatic typing to appear." The browser and editor paste runs were not done. `findings.md` records the partial table and the decision.

The measurements produce numbers and a written recommendation only. They do not change how dictation behaves. Any switch (paste mode, modifier model, new engine) is a follow-up thread that the user starts after reading the findings.

A pre-flight review (2026-09-26) found two blocking and five major problems in the first draft. This version fixes them. Each fix was checked on the machine; see "Assumptions & uncertainties".

## Current behaviour (verified by reading `dictate.py` on `main` at 23242a0)

- `dictate.py` is the whole app (575 lines). `transcribe` is the entry point `dictate:main`.
- `dictate.py:20` runs `os.environ.setdefault("HF_HUB_OFFLINE", "1")` at import time, so anything that imports `dictate` cannot download models.
- `dictate.py` imports `pynput.keyboard` at module level. Importing `dictate` with no X display fails: `ImportError: this platform is not supported: ('failed to acquire X connection: Bad display name ""')`. With `PYNPUT_BACKEND=dummy` set, the import works (verified both ways).
- Holding the hotkey (`[hotkey] key`, the user's value is `cmd`) sends `"start"` to a queue; releasing sends `"stop"`. A worker thread calls `start_recording()` / `stop_recording()`.
- `start_recording()` starts `arecord` (16 kHz mono WAV to a temp file). It returns early if `self.recording` is already true, so X11 key auto-repeat cannot start it twice: `on_press` also checks `self.recording`, and the worker re-checks before calling.
- `stop_recording()` stops `arecord`, then starts `_transcribe()` in a new thread.
- `_transcribe()` calls `model.transcribe(file, beam_size=5, vad_filter=True, hotwords=HOTWORDS)`. It joins segment texts with `" "`. Then it:
  - pipes `text` into `xclip -selection clipboard` (this overwrites the user's clipboard every time),
  - if `auto_type`, stops the pynput listener and runs `xdotool type --delay 3 text`,
  - prints `Copied: <text>` and sends a notification (the user has notifications off).
- There is no feedback at all while recording when notifications are off. There is no trailing space, so results dictated one after another run together.
- `check_dependencies()` collects missing tools into a list and calls `sys.exit(1)` if any are missing. It checks `arecord` and `xclip`, and `xdotool` only when `auto_type` is on.
- Config is `~/.config/transcribe/config.ini`, read by `load_config()` with fallbacks. The `[behavior]` section holds `auto_type`, `notifications`, `hotwords_file`.
- Test mode (`transcribe --test [--reuse-recording]`) records one sample to `~/.cache/transcribe/test.wav` and runs it through every model in `[test] models`. It uses the same kwargs as `_transcribe()`. `AGENTS.md` requires these two call sites to stay in sync.
- The repo has no tests and declares no dev dependencies or pre-commit config. `pyproject.toml` has `packages = ["."]` under `[tool.hatch.build.targets.wheel]`, so a new top-level `tests/` folder could end up in a built wheel.

## Machine facts (verified 2026-09-26)

- X11 session, Cinnamon desktop (`XDG_SESSION_TYPE=x11`, `XDG_CURRENT_DESKTOP=X-Cinnamon`).
- Intel Core Ultra 7 155H, 22 threads, 30 GB RAM, no NVIDIA GPU.
- Live config: `model = base.en`, `device = cpu`, `compute_type = int8`, `key = cmd`, `auto_type = true`, `notifications = false`.
- `~/.config/transcribe/hotwords.txt` has 76 lines, many of them Pāḷi terms with diacritics (for example Pāḷi, aṭṭhakathā, Saṃyutta Nikāya, mettā).
- `paplay`, `pactl`, `xdotool`, `xclip`, `notify-send`, `ffmpeg`, `ffprobe`, `soxi` are installed. `playerctl` is not.
- Freedesktop sounds in `/usr/share/sounds/freedesktop/stereo/` (lengths measured with `ffprobe`): `audio-volume-change.oga` 0.067 s, `message.oga` 0.311 s, `complete.oga` 1.089 s.
- Cached faster-whisper models: tiny.en, base.en, base, small.en, distil-small.en, medium.en. `large-v3-turbo` is **not** cached and would download (about 1.6 GB).
- **`~/.cache/transcribe/test.wav` is not speech. Do not use it.** Its data is a full-scale clipped square wave (bytes `ff7f` / `0080` repeated). Its RIFF header claims a data chunk of about 2^31 bytes for a 692 KB file. faster-whisper ignores the header, but VAD finds no speech in it.
- A known-good English speech sample for smoke tests: `https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/tests/data/jfk.flac` (returns HTTP 200).

## What it should do

### 1. Trailing space

- The text that `xdotool` types ends with one space.
- The clipboard copy stays exactly as now (no trailing space), so a later manual paste is clean.
- No setting. It is always on.

### 2. Filler word removal

- A pure module-level function `remove_fillers(text)` removes these whole words, case-insensitive: `uh`, `um`, `er`, `ah`, `eh`, `hmm`, `hm`, `mhm`. This is voxtype's default list (from voxtype `src/config/text.rs`) **minus `mm`**, which is dropped on purpose because it also means millimetres ("5 mm").
- The filler regex also swallows one directly following separator (`,` `;` `:`) and the spaces after it. Then the result is tidied: space before punctuation removed, repeated commas collapsed, a `,;:` right before `.!?` dropped, double spaces collapsed, leading punctuation and trailing `,;:` stripped.
- If a filler was removed at the start of the text (ignoring leading punctuation such as "..."), the new first letter is capitalised. If nothing but punctuation is left, the result is `""`. Capitals elsewhere are left exactly as Whisper wrote them. The user confirmed this rule on 2026-09-26, knowing that "uh hello world" → "Hello world" while "hello world, uh." stays lower case.
- Word boundaries matter: "umbrella", "summer", "herb" and "ahead" stay untouched. Text with no filler is returned unchanged.
- **Added after review (2026-09-26):** a hyphen or apostrophe next to a filler does not count as a word boundary, so "uh-huh", "mm-hmm", "Uh-oh", "um's" and "5'er" stay whole. A filler quoted on its own is removed with its quotes: `"Um," she said.` → `She said.`, and `He said "um" loudly` → `He said loudly`. Leading quote marks are skipped when deciding whether the filler was at the start. A second review round extended this to curly single quotes and round and square brackets: `hello (um) world` → `hello world`, `‘Um,’ she said.` → `She said.`, while `(see above) okay` stays unchanged. CodeRabbit, an independent review and an external review each found part of this; the old `\b` boundary produced `-huh, sure`, `He said mm-.` and `"" she said.`.
- These input → output pairs were produced by a working prototype on 2026-09-26 (not written by hand):

  | Input | Output |
  |---|---|
  | `Well, um, I think` | `Well, I think` |
  | `uh hello world` | `Hello world` |
  | `hello world, uh.` | `hello world.` |
  | `Um, so we go.` | `So we go.` |
  | `Uh, um.` | `` (empty) |
  | `The umbrella and summer herb, ahead.` | unchanged |
  | `UM okay` | `Okay` |
  | `The vim, uh, the editor, um, is fast.` | `The vim, the editor, is fast.` |
  | `I said 5 mm of cloth.` | unchanged |
  | `...um... okay` | `Okay` |
  | `I think, um.` | `I think.` |
  | `So, uh, you know, er, it works` | `So, you know, it works` |
  | `Hmm? What?` | `What?` |
  | `hello world` | unchanged |

- It runs in `_transcribe()` before the clipboard copy and before typing. If the result is empty, the existing "No speech detected" branch handles it.
- No setting. It is always on.

### 3. Start and stop sounds

- A short sound plays when recording starts and another when it stops.
- Sounds play through `paplay` in a non-blocking `subprocess.Popen` with output sent to `/dev/null`. They must never delay recording or transcription.
- New config keys in `[behavior]`:
  - `sounds = true` (default true when the key is missing, so the user gets it without editing their config)
  - `start_sound` (default `/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga`, 0.067 s)
  - `stop_sound` (default `/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga`, the same blip as the start sound. Changed on 2026-09-26 at the user's request: "make the end sound the same or variant of the start". The system has no pitched variant of that blip, so the same file is used.)
- Only the start sound can bleed into a recording, because `paplay` runs async and overlaps `arecord`. The default is 0.067 s. If it proves audible in the transcript, `message.oga` (0.311 s) is the fallback to try, and `vad_filter=True` should drop a short blip either way.
- The start sound fires in `start_recording()`, after its early-return guard. The stop sound fires in `stop_recording()`, after its early-return guard. Each fires exactly once per press and once per release (see the auto-repeat note in "Current behaviour").
- Test mode does not play sounds.
- If `sounds` is on and `paplay` is missing, `check_dependencies()` prints a **warning** with the package hint `pulseaudio-utils` and dictation still starts. A missing sound player must never stop dictation, so `paplay` is not added to the list that triggers `sys.exit(1)`.
- `config.example.ini` and `README.md` document the three keys.

### 4. Paste test (measurement only)

Question to answer: can paste work in every window the user types into, with diacritics correct and the clipboard restored?

- A standalone script in this thread's `artifacts/` folder (not in `dictate.py`). For a sample text of about 300 characters that includes Pāḷi diacritics, it compares:
  - **Type:** `xdotool type --delay 3 <text>` (the exact current command).
  - **Paste:** save the current clipboard text with `xclip -o`, put the sample on the clipboard, send one paste key with `xdotool key`, wait 0.3 s, restore the old clipboard.
  - Paste keys tried: `ctrl+v`, `ctrl+shift+v`, `shift+Insert`.
- Timing covers the **whole** sequence for each method: for paste, the clipboard save, set, key and restore (including the 0.3 s wait), because production paste mode would pay all of that on every dictation. Even so, `xdotool key` returns as soon as the key event is sent, while `xdotool type` blocks until typing ends, so the two numbers are not equal measures. Speed is reported as context only. It is **not** a deciding criterion.
- The user focuses each target app during a countdown and notes whether the text arrived complete and correct, and whether the clipboard was restored.
- Target apps: the ones the user really dictates into. At least Ghostty (with Zellij), a web browser text box, and the editor they use most. The user confirms the list when they run it.
- The deciding questions: does one paste key work in all target apps, with diacritics correct? If none does, paste needs per-window key detection, which the user already judged not worth it.
- A known cost of paste mode itself (not just the test): clipboard restore saves text only. If the clipboard held an image or other non-text data, paste mode would lose it on every dictation. This counts against shipping paste mode.

### 5 and 6. Model and engine benchmark (measurement only)

Question to answer: does a bigger Whisper model, or Parakeet, give clearly better results on the user's own voice, at a speed that still feels instant?

- **Samples:** 6 short recordings (5–15 s each) of the user reading prepared sentences. Each has a reference text file. The sentences mix plain English, coding terms and Pāḷi terms from the hotwords file. A `record` mode in the benchmark script shows each sentence and records it with the same `arecord` flags as `dictate.py`. After each take it:
  - checks that the WAV header's data size matches the file size, and rewrites the header with Python's `wave` module if it does not;
  - rejects the take (and asks for a re-record) if more than 1% of samples are at full scale, or if the RMS level is near silence — so a broken mic input like the one in `test.wav` is caught at once.
- **Candidates:**
  - faster-whisper `base.en` (current), `small.en`, `distil-small.en`, `large-v3-turbo`, and optionally `medium.en` (already cached, a free extra if turbo is slow). Same settings as production: CPU, int8, `beam_size=5`, `vad_filter=True`, `hotwords` from the user's file (and never `initial_prompt` — see `AGENTS.md`).
  - Parakeet through the `onnx-asr` Python package (`onnx-asr[cpu,hub]`, version 0.12.0 resolves cleanly per the review): `nemo-parakeet-tdt-0.6b-v2` (English) and `nemo-parakeet-tdt-0.6b-v3` (multilingual). Both names are confirmed in the onnx-asr docs. Both run with `quantization="int8"` so they are compared against int8 Whisper on equal terms. (`load_model` defaults to full precision.) No hotwords, because onnx-asr does not document hotword support.
- **The benchmark script must not import `dictate`.** Importing it sets `HF_HUB_OFFLINE=1`, which would stop `large-v3-turbo` from downloading. The script carries its own copy of the 8-line hotwords loader.
- **Method:** each candidate runs in its own fresh process. Load time is measured separately. Per sample: one warm-up run, then the median of 3 timed runs. Check system load with `uptime` first, and note it in the findings. The full run is long (a 1.6 GB download plus `large-v3-turbo` on CPU), so it runs as a background command.
- **Metrics per candidate:** load time, median transcribe time per sample, word error rate against the reference (lowercased, punctuation stripped), and how many Pāḷi / coding hotword terms from the reference appear exactly (diacritics included, case-sensitive) in the output.
- **Output:** `findings.md` in this thread folder with an aggregate table, a per-sample table (so one bad take is visible next to n = 6), the paste results, and a plain recommendation for each of ideas 4, 5 and 6.

## Assumptions & uncertainties

- **Verified:** everything under "Current behaviour" and "Machine facts" was read from the code or checked on the machine on 2026-09-26. This includes: the corrupt `test.wav` (hex dump), the display-less import failure and the `PYNPUT_BACKEND=dummy` fix, the three sound lengths, the `HF_HUB_OFFLINE` line, and `sys.exit(1)` in `check_dependencies()`. The onnx-asr model names and the `quantization="int8"` parameter come from the onnx-asr usage docs. The filler table comes from running a prototype of the rules above.
- **Assumption:** Whisper models often leave out fillers on their own, so filler removal may rarely change anything. The user asked for it as cheap insurance. If the benchmark outputs contain real fillers, copy them into the tests.
- **Assumption:** `paplay` plays `.oga` files on the user's default sound output. Not yet heard on the machine.
- **Uncertain:** the default sound choice. The user may prefer others. The two path keys let them change it without code.
- **Uncertain:** whether Parakeet handles the Pāḷi diacritics at all (v3 is multilingual, v2 is English-only). The benchmark answers this.
- **Uncertain:** whether onnx-asr reads FLAC. The smoke test converts `jfk.flac` to 16 kHz mono WAV with `ffmpeg` first to avoid the question.
- **Uncertain:** Cohere Transcribe (which voxtype rates highly) has no documented Python route in onnx-asr. It is left out. If a simple Python route turns up during the benchmark, note it in the findings but do not build it.
- The Kamma setup files (`kamma/project.md`, `kamma/tech.md`, `kamma/workflow.md`) are missing. The plan follows the structure of the archived thread `kamma/archive/20260508_model-test-mode-and-hotwords/plan.md`.

## Constraints

- Keep `dictate.py` a single file. Match its style: module-level config constants, plain functions, `subprocess` for system tools.
- Never modify the user's live config, `~/.config/transcribe/config.ini`. New config keys are read with fallbacks. `config.example.ini` is a repo template; editing it needs a one-time yes from the user (their global rule covers `.ini` files).
- Keep the `_transcribe()` and `run_test_mode()` transcription kwargs identical (`AGENTS.md`). This thread does not change them.
- Tests import `dictate` with `PYNPUT_BACKEND=dummy` set (via `tests/conftest.py`), so they run without an X display.
- Benchmark and paste scripts live in `kamma/threads/20260926_voxtype-ideas/artifacts/`, run with `uv run <script>` using inline script dependencies. They must not add dependencies to `pyproject.toml`, and must not import `dictate`.
- No git commands unless the user asks.
- Do not run the app or scripts that need the user's voice or window focus. Hand those steps to the user with exact commands.

## How we'll know it's done

- A dictated result is typed with one trailing space. The clipboard copy has none.
- A dictated sentence containing "um" or "uh" comes out without them, with tidy punctuation. The unit tests for the filler function pass, and most fail when the function is reverted to return its input unchanged.
- A sound plays once on press and once on release. No sound plays in test mode. Setting `sounds = false` silences both. With `paplay` missing, dictation still starts and a warning prints.
- `findings.md` exists with the paste table, the aggregate and per-sample benchmark tables, and a recommendation for ideas 4, 5 and 6.

## What's not included

- Switching to paste mode, adding a modifier-key second model, or adding a new engine. Each is a follow-up thread, decided from `findings.md`.
- Per-window paste key detection.
- Intel NPU / OpenVINO acceleration.
- Settings to turn the trailing space or filler removal off.
- Sounds in test mode, or an error sound.
- Fixing the header of files that `arecord` writes in the app or in test mode. The benchmark's `record` mode fixes its own files only. (faster-whisper ignores the header, so the app is not affected.)
- Everything the user dropped (see Overview).
