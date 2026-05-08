# Spec: Model test mode + hotwords file

## Overview

Two related additions to the `transcribe` CLI:

1. **Test mode** (`transcribe --test`): record one short sample, then run that same WAV through every model listed in config and print each transcription with timing, so the user can pick a winner by reading the outputs.
2. **Hotwords file**: a newline-separated text file of frequently-used vocabulary (names, jargon) loaded into faster-whisper's `hotwords` parameter on every transcription, in normal mode and test mode.

## Repo context (current state)

- Single-file CLI at `dictate.py`, entry point `transcribe = "dictate:main"` (`pyproject.toml:27`).
- Uses `faster_whisper.WhisperModel` directly (`dictate.py:20`, `dictate.py:98`).
- Records via `arecord` to a temp `.wav` (`dictate.py:154-165`), transcribes with `model.transcribe(wav, beam_size=5, vad_filter=True)` (`dictate.py:208-212`), then deletes the WAV (`dictate.py:250-251`).
- Config lives at `~/.config/transcribe/config.ini`, loaded by `load_config()` (`dictate.py:28-51`); template ships as `config.example.ini` and is **manually copied** by the user (per `README.md:25-28`).
- Installed via `uv tool install -e .` (`README.md:20`); no post-install hooks available in `uv tool`.
- `argparse` already wires several flags: `-b`, `-k`, `-s`, `-r`, `-v` (`dictate.py:370-399`).

## What it should do

### Test mode

- New flag: `transcribe --test` (no short form to avoid conflict; `-t` is fine if free).
- On invocation:
  1. Print which models will be tested.
  2. Record one sample using the same `arecord` command and the same hotkey UX as normal mode (hold key, release to stop).
  3. Save the WAV to a stable, non-temp path so it survives the run (e.g. `~/.cache/transcribe/test.wav`) and can be reused if the user re-runs `--test` without re-recording (see `--reuse-recording` below).
  4. For each model in the configured list:
     - Print model name.
     - Load it (timing this load).
     - Transcribe the saved WAV using the **same `transcribe()` call shape** as normal mode (same `beam_size`, `vad_filter`, and `hotwords` if set).
     - Print: load time (s), transcribe time (s), and the transcription text.
     - Release the model object before loading the next.
  5. Exit cleanly (no daemonisation, no PID file, no key listener after recording).
- Optional flag `--reuse-recording`: skip recording, run directly on the existing `~/.cache/transcribe/test.wav`. Errors clearly if the file is missing.
- Test mode must not interfere with a running daemon (it should not write the PID file, and should be allowed to run while the daemon runs).

### Test models config

- New config section `[test]` with key `models` — comma-separated list of model names accepted by `WhisperModel(...)`. Whitespace tolerated.
- Default (when `[test]` missing): `tiny.en, base.en, small.en, distil-small.en, large-v3-turbo` — a sensible spread the user can edit.
- Open-ended: any new whisper model (or distilled / turbo variant) faster-whisper accepts can be added by editing one config line, no code change.

### Hotwords

- New file: `~/.config/transcribe/hotwords.txt`. Newline-separated. Blank lines and lines starting with `#` are ignored. Trailing whitespace is trimmed.
- Loaded once at process start into a single space-joined string and passed via `hotwords=` to every `model.transcribe(...)` call (normal mode and test mode).
- If the file is missing, the app loads zero hotwords and runs normally — no error, no auto-creation in code.
- New config key `[behavior] hotwords_file` lets the user override the default path. If unset, default is used.
- The repo ships a `hotwords.example.txt` at the repo root next to `config.example.ini`, with a short comment header and a couple of placeholder lines.
- **Install via justfile**: a new `justfile` provides `just install`, which runs `uv tool install -e .` and then copies `config.example.ini` and `hotwords.example.txt` into `~/.config/transcribe/` only if those targets do not already exist. Re-running `just install` after an edit never clobbers the user's files.

## Assumptions & uncertainties

- **`hotwords` param exists in faster-whisper >= 1.0.0**: research suggests yes, added in the 1.x line. If the installed version doesn't support it we will fall through to `initial_prompt=` with the same string. Will verify by inspecting the installed `faster_whisper` package's `transcribe()` signature during implementation; fix at that point if needed.
- **`just` is available on the user's machine**: the justfile only runs when invoked, so users without `just` can still `uv tool install -e .` and copy files manually. README will document both paths.
- **Memory between models in test mode**: assumes each `WhisperModel` is GC'd when its variable goes out of scope between iterations. Adequate for 3–5 models on CPU. Not loading them all in parallel.
- **Recording UX in test mode**: reuses normal hotkey listener so the user can hold/release the same key. We will not background or fork in test mode.

## Constraints

- No new third-party Python deps.
- No regression in normal `transcribe` runtime path: the `hotwords=` kwarg is the only change to `model.transcribe(...)`.
- The `hotwords` argument must always be a string (faster-whisper rejects `None` for some param shapes); pass `""` when no hotwords are loaded.
- Must keep working for users who upgrade and have no `hotwords.txt` and no `[test]` section — defaults handle both.
- Don't break `--background`, `--kill`, `--status`, `--restart`.

## How we'll know it's done

- Manual: edit `config.ini` to set `[test] models = tiny.en, base.en, distil-small.en`, run `transcribe --test`, hold the hotkey, say "schedule a meeting at three", release. Output shows three blocks, each with model name, load+transcribe times, and the transcription.
- Manual: add a custom hotword to `hotwords.txt` (e.g. a name the model gets wrong), re-run `transcribe --test --reuse-recording`, observe whether outputs change.
- Manual: delete `~/.config/transcribe/hotwords.txt`, run `transcribe`, confirm it starts cleanly with zero hotwords loaded (no crash, no auto-create). Then run `just install` and confirm the file is restored.
- Manual: rename `config.ini` to `config.ini.bak` (no config at all), run `transcribe --test`, confirm it falls back to defaults and works.
- Manual: `transcribe --kill`, `transcribe -s`, `transcribe -r` still behave correctly.

## What's not included

- No automatic "winner" picking — quality is judged by the user reading outputs.
- No new transcription engines (Moonshine, Parakeet) — faster-whisper only.
- No tuning of `initial_prompt`. Hotwords-only this round.
- No GUI / TUI for selecting models.
- No persistent log of past test results.
