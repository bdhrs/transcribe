# Plan: Model test mode + hotwords file

## Architecture Decisions

- **Single file stays single file.** `dictate.py` is small enough that splitting into modules is not worth the friction. Test mode lives there as a separate `run_test_mode()` function alongside `main()`.
- **Reuse the existing hotkey listener for test-mode recording.** Don't invent a second recording UX. The same press/release flow gives a one-shot WAV.
- **`hotwords.example.txt` lives at repo root**, mirroring `config.example.ini`. No wheel-bundling or `importlib.resources` needed — the template is only used by the justfile, which runs from the repo checkout.
- **Seeding happens via `just install`, not at app startup.** The app does not auto-create `hotwords.txt`; it just loads it if present. This keeps the runtime simple and matches the existing pattern for `config.example.ini`.
- **Hotwords loaded once at startup, not per-call.** It's a small string and rereading on every transcription would only matter if the user edits during a session — they can restart.
- **Test mode releases models between iterations.** Sequential load/transcribe/release. Avoids holding multiple multi-GB models in RAM.
- **Test mode skips the daemon machinery entirely.** No PID file, no `--background`, no interaction with a running instance.
- **`hotwords` param with `initial_prompt` fallback.** If the installed `faster_whisper.WhisperModel.transcribe` signature lacks `hotwords`, fall back to passing the same string as `initial_prompt`. Decided at startup once via `inspect.signature`.

## Phase 1 — Hotwords support

- [ ] **P1.T1: Add hotwords loader and example file**
  - [ ] Create `hotwords.example.txt` at repo root with a short `#` header explaining the format (one term per line, blank lines and `#` comments allowed) and 2–3 placeholder lines.
  - [ ] Add `load_hotwords(path: Path) -> str` in `dictate.py`: returns a space-joined string of non-blank, non-comment lines, with each line trimmed. Returns `""` if the file doesn't exist or is empty.
  - → verify: write a small temp file with comments and blanks, call `load_hotwords()`, confirm only the real entries come back joined by spaces.

- [ ] **P1.T2: Wire hotwords into config and runtime**
  - [ ] Extend `load_config()` (`dictate.py:28`) to read `[behavior] hotwords_file` with default `~/.config/transcribe/hotwords.txt`.
  - [ ] At process start (after `load_config()`), call `load_hotwords()` once and stash on a module-level `HOTWORDS` string. Print `Hotwords: <N> entries loaded` (or `Hotwords: none` if empty) so the user can see it took effect.
  - [ ] Detect whether `WhisperModel.transcribe` accepts `hotwords` via `inspect.signature`. Stash a module-level flag, e.g. `HOTWORDS_KW = "hotwords"` or `"initial_prompt"`.
  - [ ] In `_transcribe()` (`dictate.py:208`), pass the hotwords string under whichever kwarg the installed version supports. When `HOTWORDS` is empty, do not pass the kwarg at all.
  - → verify: run `transcribe`, confirm the hotwords count line prints. Speak a known hotword, observe it transcribed correctly. Delete `hotwords.txt`, restart, confirm it still runs (prints `Hotwords: none`, no crash).

## Phase 2 — Test mode

- [ ] **P2.T1: Config support for the test model list**
  - [ ] In `load_config()`, parse `[test] models` as a comma-separated list. Strip whitespace and drop empty entries. Default to `["tiny.en", "base.en", "small.en", "distil-small.en", "large-v3-turbo"]` if absent.
  - [ ] Add the parsed list to the returned dict.
  - → verify: temporarily print the parsed list at startup, run with and without `[test]` in `config.ini`, confirm both shapes work.

- [ ] **P2.T2: Add `--test` flag and a one-shot recording helper**
  - [ ] Add `--test` and `--reuse-recording` flags in `main()`'s argparse (`dictate.py:370`). `--test` is mutually exclusive with `--background`, `--kill`, `--status`, `--restart`.
  - [ ] When `--test` is set, route to a new `run_test_mode(args)` function and skip the daemon flow entirely. Do **not** call `write_pid()` or `get_running_pid()`.
  - [ ] Inside `run_test_mode`: define `TEST_WAV = Path.home() / ".cache" / "transcribe" / "test.wav"`. Ensure parent dir exists.
  - [ ] If `--reuse-recording` and `TEST_WAV` exists, skip recording. If `--reuse-recording` and `TEST_WAV` missing, print a clear error and exit non-zero.
  - [ ] Otherwise, record one sample by reusing the existing arecord invocation pattern from `start_recording`/`stop_recording`. Drive it via the same `keyboard.Listener` so the user holds/releases the configured key. On release, terminate `arecord`, leave the WAV at `TEST_WAV` (overwriting any prior file), and proceed.
  - → verify: `transcribe --test`, hold key, say "test recording one two three", release. Confirm `~/.cache/transcribe/test.wav` exists and is non-empty. Then run `transcribe --test --reuse-recording` and confirm it does not record again.

- [ ] **P2.T3: Run all configured models against the recording and print results**
  - [ ] After the WAV is ready, iterate over the parsed `[test] models` list.
  - [ ] For each name: print a header line, time `WhisperModel(name, device=DEVICE, compute_type=COMPUTE_TYPE)` construction, time `model.transcribe(TEST_WAV, beam_size=5, vad_filter=True, **hotwords_kw)`, collect text via the same `" ".join(seg.text.strip() for seg in segments)` pattern.
  - [ ] Print, per model: `name`, `load X.XXs`, `transcribe X.XXs`, blank line, then the text indented one level. On exception, print the exception message and continue to the next model.
  - [ ] After the loop, `del model` and call `gc.collect()` between iterations to release RAM.
  - [ ] Exit 0 on completion (even if some models errored).
  - → verify: run `transcribe --test` with three models in config, observe three result blocks, each with the same text shape. Run with one bogus model name and confirm it errors gracefully and continues.

- [ ] **P2.T4: Phase 2 verification**
  - [ ] Set `[test] models = tiny.en, base.en` in a scratch config, run `transcribe --test`, record one sample, confirm both blocks render with sensible numbers.
  - [ ] Run `transcribe --test --reuse-recording` and confirm identical-shape output without re-recording.
  - [ ] Run plain `transcribe`, confirm normal dictation still works (no regression from hotwords integration).
  - → verify: all three checks above pass on the developer machine.

## Phase 3 — Justfile

- [ ] **P3.T1: Add `justfile` with install + update recipes**
  - [ ] Create `justfile` at repo root with at minimum:
    - `install` — runs `uv tool install -e .`, then for each of `config.example.ini` and `hotwords.example.txt`, copies it to `~/.config/transcribe/<name without .example>` only if the target does not already exist (use `cp -n` or a small shell `if` guard). Creates `~/.config/transcribe/` first.
    - `update` — alias for `install` (same behaviour: re-install the tool, ensure config files exist, never overwrite).
    - `uninstall` — `uv tool uninstall transcribe`. Does not delete user config (clearly safer default).
  - [ ] Add a `default` recipe that prints `just --list` so a bare `just` is helpful.
  - → verify: from a clean state (`rm -rf ~/.config/transcribe`), run `just install`. Confirm both `config.ini` and `hotwords.txt` appear in `~/.config/transcribe/`. Edit `hotwords.txt`, re-run `just install`, confirm the edit is preserved.

## Phase 4 — Documentation

- [ ] **P4.T1: Update README**
  - [ ] Replace the manual `mkdir`/`cp` install steps with `just install` as the primary path; keep the manual steps as a fallback for users without `just`.
  - [ ] Add a "Testing models" subsection under Configuration showing `transcribe --test`, `--reuse-recording`, and the `[test] models = ...` config block.
  - [ ] Add a "Hotwords" subsection: where the file lives, format (one entry per line, `#` comments), how `just install` seeds it.
  - [ ] Update the Models table to mention `distil-small.en` and `large-v3-turbo` as worth trying.
  - → verify: read the rendered README, confirm both new sections are present, accurate, and the install flow reads sensibly end-to-end.

- [ ] **P4.T2: Update `config.example.ini`**
  - [ ] Add a commented `[test]` section with the default model list.
  - [ ] Add a commented `[behavior] hotwords_file` line documenting the override.
  - → verify: diff `config.example.ini`, confirm the new lines are commented out so existing user configs remain valid after a manual diff/merge.
