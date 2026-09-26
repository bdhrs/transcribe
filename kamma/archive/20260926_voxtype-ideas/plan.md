# Plan: Ideas from voxtype — three small features and three measurements

Spec: `kamma/threads/20260926_voxtype-ideas/spec.md`. Read it first. It holds the verified current behaviour, machine facts, the filler input/output table and the reasons behind each choice.

## Architecture Decisions

- **`dictate.py` stays one file.** The three features add one pure function (`remove_fillers`), one small method (`play_sound`) and a few config keys. No new modules.
- **Filler removal is a pure module-level function** so it can be unit-tested without a model or a mic. The rules are in the spec. The expected outputs in the spec's table come from a working prototype, so the tests and the code cannot drift apart by being written separately.
- **`mm` is not a filler here.** It also means millimetres. The rest of voxtype's default list is kept.
- **Tests run without an X display.** `tests/conftest.py` sets `PYNPUT_BACKEND=dummy` before `dictate` is imported. Without it the import fails with `ImportError: this platform is not supported`.
- **The trailing space is added only to the typed text**, not the clipboard, so a manual paste later stays clean. No setting — the user asked for the behaviour, not a switch.
- **Sounds go through `paplay` in a fire-and-forget `Popen`**, the same way `notify()` already calls `notify-send`. No audio library. Two path keys let the user swap sounds without code.
- **A missing `paplay` only warns.** `check_dependencies()` exits on anything in its `missing` list. A cosmetic sound must never stop dictation, so `paplay` gets a separate warning.
- **Sound calls sit after the existing early-return guards** in `start_recording()` / `stop_recording()`. Those guards already stop X11 key auto-repeat from starting a recording twice, so the sounds fire exactly once per press / release.
- **Measurements live outside the app**, as `uv run` scripts with inline dependencies in this thread's `artifacts/` folder. They never import `dictate` (its import sets `HF_HUB_OFFLINE=1`, which blocks model downloads). The app gains no dependencies.
- **Benchmarks compare like with like:** Whisper and Parakeet both at int8, each candidate in its own fresh process, a warm-up and the median of 3.
- **Paste speed is context, not a criterion.** `xdotool key` returns at once while `xdotool type` blocks, so a speed comparison always favours paste. The decision rests on "one key works everywhere, with diacritics correct".
- **No switch is built.** Paste mode, a modifier-key model and a new engine are follow-up threads, decided from `findings.md`.
- **The installed `transcribe` is an editable uv tool** (`_transcribe.pth` points at this repo), so `transcribe -r` runs the edited code. Never run a non-editable `uv tool install .` during this thread, or every live check tests stale code.
- **`erm` is deliberately not a filler**, matching voxtype's short list. "erm, wait" survives. This is known, not a bug.

## Phase 1 — Trailing space and filler removal

- [x] **P1.T1: Write the filler tests first**
  - [x] Create `tests/conftest.py` containing `import os` and `os.environ.setdefault("PYNPUT_BACKEND", "dummy")`, with a one-line comment saying why (importing `dictate` needs an X display otherwise).
  - [x] Create `tests/test_fillers.py`. It imports `remove_fillers` from `dictate` and checks every row of the filler table in the spec (section "2. Filler word removal"), copied exactly. Use one `pytest.mark.parametrize` table.
  - [x] In `pyproject.toml`, add `exclude = ["tests"]` under `[tool.hatch.build.targets.wheel]` so the new folder is not shipped in a built wheel.
  - → verify: run `uv run --with pytest pytest tests/test_fillers.py`. Expect a collection error, because `remove_fillers` does not exist yet: `ERROR tests/test_fillers.py` and `Interrupted: 1 error during collection`, exit code 2. Paste those two lines here.
    - Result (2026-09-26): `ERROR tests/test_fillers.py` / `Interrupted: 1 error during collection`, exit=2.

- [x] **P1.T2: Add `remove_fillers` and wire both features into `_transcribe()`**
  - [x] In `dictate.py`, add `import re`, a module-level `FILLER_WORDS = ("uh", "um", "er", "ah", "eh", "hmm", "hm", "mhm")` and a compiled regex: `r"\b(?:" + "|".join(FILLER_WORDS) + r")\b[,;:]?\s*"` with `re.IGNORECASE`. The regex swallows one following separator and its spaces.
  - [x] Add `remove_fillers(text: str) -> str`. This is the prototype that produced the spec's table:
    ```python
    def remove_fillers(text):
        cleaned = _FILLER_RE.sub("", text)
        if cleaned == text:
            return text
        at_start = _FILLER_RE.match(text.lstrip(" .,;:!?…")) is not None
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        cleaned = re.sub(r",(\s*,)+", ",", cleaned)
        cleaned = re.sub(r"[,;:]+([.!?])", r"\1", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = cleaned.lstrip(" .,;:!?…").strip()
        cleaned = re.sub(r"[,;:]+$", "", cleaned)
        if not re.search(r"\w", cleaned):
            return ""
        if at_start and cleaned[:1].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned
    ```
    Match the file's style (type hints like `load_hotwords`). Comment only the non-obvious *why* lines, for example why `mm` is not in the list.
  - [x] In `_transcribe()`, right after `text = " ".join(...)`, add `text = remove_fillers(text)`. The existing `if text:` branch then handles an empty result as "No speech detected".
  - [x] Change only the `xdotool type` argument to `text + " "`. Leave the `xclip` input, the `print` and the notification using `text`.
  - [x] Do not touch `run_test_mode()` — test mode reports raw model output, and the transcribe kwargs do not change.
  - → verify: run `uv run --with pytest pytest tests/test_fillers.py`, expect all 14 cases pass. Then make `remove_fillers` return `text` at its first line, re-run, and record how many fail (expect 11 — every row except the 3 "unchanged" rows). Restore the function in the same step and re-run to green.
    - Result (2026-09-26): 14 passed. Reverted: `11 failed, 3 passed`. Restored (byte-identical, `cmp`): 14 passed.

- [x] **P1.T3: Phase 1 verification**
  - [x] Read the final `_transcribe()` and confirm the clipboard gets `text` and `xdotool` gets `text + " "`.
  - [x] Ask the user to run `transcribe -r`, dictate "um, this is a test" twice into a text box, and confirm the output reads `This is a test. This is a test. ` (two sentences, one space between, no "um").
  - → verify: pytest green, the user confirms the live output.
    - Result (2026-09-26): user confirmed "removes ums nicely and capitalized". (A first "nothing happens" report was a muted mic, not this change.)

## Phase 2 — Start and stop sounds

- [x] **P2.T1: Check the start sound**
  - [x] Run `paplay /usr/share/sounds/freedesktop/stereo/audio-volume-change.oga` and `paplay /usr/share/sounds/freedesktop/stereo/complete.oga`, and check both exit 0.
  - [x] The start sound is 0.067 s (measured in the spec). Only the start sound can bleed into a recording, so only its length matters. Keep it unless the user reports it in a transcript. The fallback is `message.oga` (0.311 s).
  - → verify: both commands exit 0. Ask the user whether they heard both sounds.
    - Result (2026-09-26): both `paplay` commands exit 0. User heard the sounds live and asked for the stop sound to match the start sound (see P2.T2).

- [x] **P2.T2: Add config keys, `play_sound`, and the two calls**
  - [x] In `load_config()`, read `[behavior] sounds` (`getboolean`, fallback `True`), `start_sound` and `stop_sound` (fallbacks: the two default paths, passed through `Path(...).expanduser()`). Add module-level `SOUNDS`, `START_SOUND`, `STOP_SOUND` next to the existing constants.
  - [x] Add `Dictation.play_sound(self, path)` next to `notify()`: return if `not SOUNDS`; otherwise `subprocess.Popen(["paplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)`. Follow `notify()`'s shape.
    - Drift (2026-09-26): the `Popen` is wrapped in `try/except FileNotFoundError: pass`. Without it, a missing `paplay` raises inside `start_recording()` after `self.recording = True` and before `arecord` starts, so the event worker logs an error and the app is stuck "recording" with no recorder. The warning in `check_dependencies()` alone does not prevent that.
  - [x] In `start_recording()`, call `self.play_sound(START_SOUND)` after the early-return guard, just before `arecord` starts. In `stop_recording()`, call `self.play_sound(STOP_SOUND)` after `arecord` has been stopped, before the transcribe thread starts.
  - [x] In `check_dependencies()`, when `SOUNDS` is true and `paplay` is missing, print `Warning: paplay not found, sounds disabled - install with: sudo apt install pulseaudio-utils`. Do **not** add it to `missing`, because `missing` triggers `sys.exit(1)`. Do not change the existing checks.
  - [x] Trace every path that reaches `start_recording()` / `stop_recording()` (only `_event_worker`; `run_test_mode` has its own recorder and must not play sounds) and confirm each sound fires once per press / release. Write the trace result here.
    - Trace (2026-09-26, `rg`): `start_recording()` and `stop_recording()` are called only from `_event_worker`, each behind a `self.recording` check, and each method re-checks `self.recording` in its own guard before `play_sound`. `play_sound` has no other callers. `run_test_mode` uses its own inline `arecord` and never calls either method, so test mode stays silent.
  - → verify: run `env -u DISPLAY PYNPUT_BACKEND=dummy uv run python -c "import dictate; print(dictate.SOUNDS, dictate.START_SOUND, dictate.STOP_SOUND)"`. Expect `True` and the two default paths, because the user's current config has no `sounds` key. Then ask the user to run `transcribe -r`, hold and release the hotkey three times, and confirm exactly three start and three stop sounds, with nothing from the start sound in the transcribed text.
    - Result (2026-09-26): import check printed `True /usr/share/sounds/freedesktop/stereo/audio-volume-change.oga /usr/share/sounds/freedesktop/stereo/complete.oga`. (Historical: the stop default changed to `audio-volume-change.oga` in the next note; current code, README, config.example.ini and spec all use it for both.) Live check: user confirmed "perfect" after the stop-sound change.
    - Change (2026-09-26, user request): `stop_sound` now defaults to the same `audio-volume-change.oga` as `start_sound` (no pitched variant exists in the system sounds).

- [x] **P2.T3: Document the new keys**
  - [x] `README.md`: add `sounds`, `start_sound`, `stop_sound` to the `[behavior]` example under Configuration, with one line explaining each. Add `pulseaudio-utils` (optional, for sounds) to the install section.
  - [x] `config.example.ini`: ask the user once before editing it. (User said "sure" on 2026-09-26; three commented lines added under `[behavior]`, matching the `load_config()` fallbacks.) If they agree, add commented lines for the three keys under `[behavior]`.
  - → verify: read both files and confirm the key names and defaults match `load_config()` exactly.

- [x] **P2.T4: Phase 2 verification**
  - [x] Ask the user to add `sounds = false` to their own config (the agent must not edit it), run `transcribe -r`, and confirm no sounds play. Then ask them to remove the line again.
  - [x] Run `uv run --with pytest pytest tests/` to confirm the Phase 1 tests still pass.
  - → verify: the user confirms silence with `sounds = false`, and pytest is green.
    - Result (2026-09-26): the user keeps sounds on and said "do whatever you need to do". Checked instead with a throwaway `HOME` whose config has `sounds = false`: `SOUNDS False`, 0 `Popen` calls from `play_sound`. With the live config: `SOUNDS True`, one `paplay` call. pytest 14 passed.

## Phase 3 — Paste test (measurement only)

- [x] **P3.T1: Write the paste test script**
  - [x] Create `kamma/threads/20260926_voxtype-ideas/artifacts/paste_test.py` with an inline `# /// script` block (standard library only). It must not import `dictate`.
  - [x] Sample text: about 300 characters, mixing English, punctuation and Pāḷi diacritics (for example "Pāḷi", "aṭṭhakathā", "Saṃyutta Nikāya", "mettā").
  - [x] Modes, chosen by argument: `type` runs `xdotool type --delay 3 <text>`. `paste <key>` saves `xclip -o -selection clipboard` output (if that exits non-zero because the clipboard is empty, print that and treat it as empty), sets the sample with `xclip -selection clipboard`, sends `xdotool key --clearmodifiers <key>`, waits `--wait` seconds (default 0.5), then restores the saved text.
  - [x] After a paste run, print a reminder: if nothing or the old clipboard text arrived, the app may read the clipboard late, so re-run with a longer `--wait` (for example 1.5) before calling that key a failure.
  - [x] Each mode prints a 3-second countdown (so the user can focus the target window), then the time for the **whole** send sequence. For paste that includes save, set, key, the wait and restore. Print a note that `xdotool key` returns before the target app has finished pasting, so paste time is a lower bound.
  - [x] Handle a missing tool or a failed subprocess by printing the command and its error — never a message that looks like success.
  - → verify: `uv run kamma/threads/20260926_voxtype-ideas/artifacts/paste_test.py --help` prints the usage. Read the script and confirm the `type` mode uses exactly `xdotool type --delay 3`, the same as `dictate.py`.
    - Result (2026-09-26): `--help` and `paste --help` print usage; sample is 307 characters; `type` mode runs `["xdotool", "type", "--delay", "3", SAMPLE]`, matching `dictate.py` except the app's trailing space.
    - Drift: the clipboard write does not capture stderr. `xclip` forks a helper that holds inherited pipes open, so `subprocess.run(..., stderr=PIPE)` would hang. `dictate.py` also captures nothing from `xclip`.

- [x] **P3.T2: The user runs the paste test** (cut short: user dropped paste on 2026-09-26)
  - [x] Ask the user to list the apps they dictate into (at least Ghostty with Zellij, a browser text box and their main editor).
  - [x] Give them the commands: `uv run kamma/threads/20260926_voxtype-ideas/artifacts/paste_test.py type`, then `... paste ctrl+v`, `... paste ctrl+shift+v`, `... paste shift+Insert`, one run per app.
  - [x] Record in `findings.md` a table: rows = apps, columns = type / ctrl+v / ctrl+shift+v / shift+Insert. Each cell: complete and correct (yes/no, and what went wrong), and the time. Also note whether the clipboard was restored.
  - → verify: the table has a cell filled for every app × method.
    - Result (2026-09-26): Ghostty row filled (type OK 2.08 s, ctrl+v fail, ctrl+shift+v OK 0.57 s, shift+Insert pasted PRIMARY). User then said "i dont want paste. i just want automatic typing to appear." Browser and editor rows marked "not run"; recommendation written in `findings.md`. P5.T1's paste recommendation is therefore already done.

## Phase 4 — Model and engine benchmark (measurement only)

- [x] **P4.T1: Smoke-test both engines on known-good speech**
  - [x] Do not use `~/.cache/transcribe/test.wav`. It is a clipped tone, not speech (see the spec).
  - [x] Download `https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/tests/data/jfk.flac` into `kamma/threads/20260926_voxtype-ideas/artifacts/smoke/`, and convert it with `ffmpeg -i jfk.flac -ar 16000 -ac 1 jfk.wav`.
  - [x] Run `uv run --with 'onnx-asr[cpu,hub]' python -c "import onnx_asr; m = onnx_asr.load_model('nemo-parakeet-tdt-0.6b-v2', quantization='int8'); print(m.recognize('<path>/jfk.wav'))"`, then the same with `-v3`. Run each model a second time with no `quantization` argument (full precision). This downloads each model variant once.
  - [x] `base.en` on this file returns `And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.` (verified by the reviewer). Use it as the reference when comparing.
  - → verify: all four commands print a non-empty English transcript. Paste all four outputs here. If int8 is clearly worse than full precision, note the gap — it goes into `findings.md` and the benchmark then runs both precisions for Parakeet.
    - Result (2026-09-26): v2 int8 printed `'And so, my fellow Americans, ask not what your country can do for you, ask what you can do for your country.'` — word-perfect against the base.en reference.
    - Drift: the v2 full-precision download hung (encoder at 2.4 GB still creeping, two other parts frozen for 2 h on unauthenticated HF downloads) and was killed at 20:19. Full-precision runs are dropped: int8 is what the benchmark tests, and v2 int8 was already word-perfect, so there is no gap to explain. v3 int8 is smoke-tested after `bench.py fetch` downloads it.
    - Result (2026-09-26): v3 int8 via `bench.py run` printed the same word-perfect line (load 1.90 s, median 1.13 s).

- [x] **P4.T2: Write the benchmark script**
  - [x] Create `kamma/threads/20260926_voxtype-ideas/artifacts/bench.py` with inline dependencies: `faster-whisper`, `onnx-asr[cpu,hub]`, `jiwer`.
  - [x] **Do not import `dictate`.** Its import sets `HF_HUB_OFFLINE=1` and would stop `large-v3-turbo` from downloading. Copy the 8-line `load_hotwords` body from `dictate.py` into the script, with a one-line comment saying why it is copied.
  - [x] `record` mode: for each of 6 prepared sentences (write them in the script: 2 plain English, 2 with coding terms, 2 with Pāḷi terms taken from `~/.config/transcribe/hotwords.txt`), show the sentence, press Enter to start `arecord -f S16_LE -r 16000 -c 1 -t wav`, press Enter to stop. Save `artifacts/samples/NN.wav` and `NN.txt` (the reference sentence). After each take:
    - compare the header's data size with the file size minus the header; if they differ, rewrite the file with the `wave` module from its raw frames;
    - reject the take and ask to re-record if more than 1% of samples are at ±32767/−32768, or if the RMS is below a near-silence threshold. Print the peak, RMS and clipped fraction either way.
  - [x] `run <candidate>` mode: one candidate in this process. Whisper candidates use `WhisperModel(name, device="cpu", compute_type="int8")` and `transcribe(wav, beam_size=5, vad_filter=True, hotwords=<the loaded hotwords>)` — never `initial_prompt`. Parakeet candidates use `onnx_asr.load_model(name, quantization="int8").recognize(wav)`. Measure load time; per sample, one warm-up, then the median of 3 timed runs. Print one JSON line per sample: candidate, sample, load_s, median_s, text.
  - [x] `run` accepts `--samples <wav>...` to override the sample set, for smoke tests.
  - [x] `fetch` mode: download every candidate model (load each once, transcribe nothing), so downloads happen outside the timed run.
  - [x] `all` mode: print `uptime`, then run `run <candidate>` in a fresh `subprocess` for each candidate, in this order so a cut-short run still yields the rows that matter most: `whisper:base.en`, `whisper:small.en`, `parakeet:nemo-parakeet-tdt-0.6b-v2`, `parakeet:nemo-parakeet-tdt-0.6b-v3`, `whisper:distil-small.en`, `whisper:large-v3-turbo`. Parakeet runs at int8 (plus full precision too, if P4.T1 found a clear gap). `--extra whisper:medium.en` adds medium.en (already cached). Append the JSON lines to `artifacts/results.jsonl`.
  - [x] `report` mode: read `results.jsonl` and the references. Aggregate only candidates with a result for every sample. Mark any candidate with fewer as PARTIAL (showing how many samples it has) and leave it out of the aggregate WER, so a cut-short run cannot look better than it is. Compute WER (lowercased, punctuation stripped, via `jiwer`), and count reference hotword terms found exactly (case- and diacritic-sensitive) in the output. Print two Markdown tables: aggregate per candidate, and per candidate × sample.
  - [x] Catch only specific exceptions around model load and transcribe, and print the error with the candidate name. A failed candidate shows as FAILED in the report, never as an empty result.
  - → verify: `uv run .../bench.py --help` shows all five modes. Feed `report` a hand-made `results.jsonl` where one candidate has 5 of 6 samples, and confirm it prints PARTIAL for that candidate. Run `uv run .../bench.py run whisper:base.en --samples .../smoke/jfk.wav` and `... run parakeet:nemo-parakeet-tdt-0.6b-v2 --samples .../smoke/jfk.wav`. Both print a JSON line whose text matches the JFK line from P4.T1.
    - Result (2026-09-26): `--help` lists record, run, fetch, all, report. Report test on a scratch copy with hand-made results printed `whisper:full6 | OK`, `whisper:part5 | PARTIAL (5/6)`, `parakeet:broken | FAILED: load failed: OSError: test`. JFK: base.en `And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country.` (load 1.71 s, median 0.61 s); Parakeet v2 int8 the same with a comma after "so" (load 1.70 s, median 1.14 s).
    - Additions not in the task text: `record` also rejects takes outside 5–15 s; a candidate suffix `:full` runs Parakeet at full precision (use with `--extra` if P4.T1 finds an int8 gap); `report` keeps the latest result per candidate × sample.

- [x] **P4.T3: The user records the samples**
  - [x] Give the user the command `uv run kamma/threads/20260926_voxtype-ideas/artifacts/bench.py record`.
  - → verify: `artifacts/samples/` holds 6 `.wav` files and 6 matching `.txt` files. For each WAV, `soxi -D` gives 5–15 s and agrees with the file size ÷ 32000 (to within 0.1 s), which proves the header is sound.
    - Result (2026-09-26): 6 WAV + 6 TXT. `soxi -D` / (size − 44) ÷ 32000: 01 12.75/12.75, 02 6.88/6.88, 03 9.62/9.62, 04 9.38/9.38, 05 7.75/7.75, 06 8.50/8.50.

- [x] **P4.T4: Run the benchmark** (turbo not run; see below)
  - [x] Check `uptime` and `ps --sort=-%cpu | head` first. If load is high, wait or note it.
  - [x] Run `uv run .../bench.py fetch` as a background command first, and wait for it to finish. It downloads about 1.6 GB for `large-v3-turbo` plus the Parakeet models.
  - [x] Run `uv run .../bench.py all` as a background command.
    - Change (2026-09-26, user said "start"): the turbo download was crawling (~0.4 MB/s), so `all` runs now with `--skip whisper:large-v3-turbo` (new flag on `fetch` and `all`). The fetch keeps downloading turbo; it is added later as a single `run` if the user still wants it. Budget: 45 minutes, with downloads already done. If turbo has not finished in the budget, stop it, note that in `findings.md`, and run `--extra whisper:medium.en` instead.
  - [x] Run `uv run .../bench.py report`.
  - [x] Scan the outputs for real fillers ("um", "uh", ...). If any, copy those exact strings into `tests/test_fillers.py` as extra cases, with expected outputs taken from running `remove_fillers`, and check each by eye. Re-run the tests.
  - → verify: the report has a row for every candidate and no FAILED rows, or each FAILED row has its error written in `findings.md`.
    - Result (2026-09-26): 5 candidates, all OK, no FAILED rows, 30 result lines. `uptime` at start: `load average: 8.29, 2.94, 1.92` (1-min from the v3 smoke test just before). distil-small.en returned cut-off or empty text (95.8 % WER) — written up in `findings.md`. Filler scan of `results.jsonl`: 0 matches, so no test cases added. Report saved to `artifacts/report.md`. large-v3-turbo still downloading; not run.

- [x] **P4.T5: Run large-v3-turbo when its download lands** (added 2026-09-26; user: "let's try a run when it lands")
  - [x] The fetch stalled at 264 MB and was restarted at 20:58; the restart began a fresh copy from 0 (no resume). A background job runs `bench.py fetch` for turbo only, then `bench.py run whisper:large-v3-turbo`, appending to `artifacts/results.jsonl`.
  - [x] Re-run `bench.py report`, save it to `artifacts/report.md`, add the turbo row and a verdict on idea 5 to `findings.md`. (Superseded: turbo was dropped, so there is no turbo row; `report.md` shows it as NOT RUN and `findings.md` records why.)
  - [x] If the download crawls again (under ~100 KB/s), tell the user and drop turbo, recording why in `findings.md`.
  - → verify: `report` shows `whisper:large-v3-turbo | OK` with 6/6 samples, or `findings.md` says why it was dropped.
    - Result (2026-09-26): the restarted download sat at 0 bytes for 20+ minutes. The user said "i dnt care, drop it". Job killed; `findings.md` records why, and the report shows `whisper:large-v3-turbo | NOT RUN`.

## Review fixes (2026-09-26)

- [x] **R1: Filler boundaries** (CodeRabbit, independent review, external review nit 4). `_FILLER_RE` now uses `(?<![\w'’-])` / `(?![\w'’-])` instead of `\b`, and a new `_QUOTED_FILLER_RE` removes a filler quoted on its own. 9 cases added to `tests/test_fillers.py`, with expected outputs taken from running the fixed function and checked by eye.
  - → verify: 23 passed. With the old `\b` pattern and no quoted-filler step put back: `8 failed, 15 passed` (the 9th new row, Pāḷi, passes either way). Restored byte-identical (`cmp`), 23 passed.
- [x] **R2: distil-small.en cause** (external review major 1). The findings wrongly blamed the `AGENTS.md` initial_prompt+hotwords problem; `bench.py` passes hotwords only. Added a `:nohotwords` Whisper candidate suffix and ran `whisper:distil-small.en:nohotwords`: 25.4 % WER, 3/23 terms, 1.15 s (the reviewer measured 26.3 % / 1.52 s). Rewrote the findings bullet and added a `[DATA]` line to `kamma/lessons.md`.
  - → verify: the findings bullet and lessons line quote the numbers in `artifacts/report.md`.
- [x] **R3: NOT RUN rows** (external review major 2). `report()` now starts from `CANDIDATES`, so a candidate with no rows prints `NOT RUN` instead of vanishing. `report.md` and the table in `findings.md` regenerated.
  - → verify: the report prints `whisper:large-v3-turbo | NOT RUN`.
- [x] **R4: stale plan line** (external review nit 3). Annotated the P2.T2 import-check note.
- [x] **R6: Second review round** (independent Sonnet review; CodeRabbit re-run). `_QUOTED_FILLER_RE` now matches a filler inside `"…"`, `“…”`, `‘…’`, `(…)` or `[…]`, and the start check skips `‘ ( [` too. The missing-`paplay` warning now says "start/stop sounds will not play" instead of "sounds disabled" (`SOUNDS` stays true; nothing is switched off). CodeRabbit's one finding: stale "Still open: turbo" note in P5.T3 — fixed, and P4.T5's superseded turbo-row step annotated. 4 filler cases added.
  - → verify: 27 passed (also with `env -u DISPLAY`). With only the two double-quote pairs: `3 failed, 24 passed` (the 4th new row is a no-filler guard). Restored byte-identical (`cmp`).
- [x] **R5: Model cache cleanup** (user request: "clean up what is not used. if we just using a model for a test, that counts as not used."). Deleted from `~/.cache/huggingface/hub/`: Parakeet v2 and v3, the partial large-v3-turbo, medium.en, small.en, distil-small.en, base, tiny.en (about 5 GB). Kept: base.en (live model) and microsoft/trocr-base-handwritten (not this project's). Consequence: `transcribe --test` with no `[test] models` in the config defaults to `base.en, distil-small.en`, and distil-small.en now errors offline (printed per model, the run continues). `bench.py` would re-download on next use.
- NOTICED — NOT TOUCHING: `pyproject.toml` `packages = ["."]` (pre-existing) ships the whole repo in a wheel, now including this thread's `artifacts/` (a 1.1 MB `jfk.flac`, results, samples text). `exclude = ["tests"]` works. Found by the independent review.

## Phase 5 — Findings

- [x] **P5.T1: Write `findings.md`**
  - [x] Create `kamma/threads/20260926_voxtype-ideas/findings.md` with: the system load at run time; the paste table from P3.T2; the aggregate and per-sample benchmark tables from P4.T4; the sample count (n = 6) next to every rate.
  - [x] One recommendation per idea, in plain English:
    - **Paste (idea 4):** recommend it only if one paste key worked in every app with diacritics correct and the clipboard restored. Speed is context, not a reason. State the non-text clipboard loss as a cost that counts against it.
    - **Second model (idea 5):** recommend a modifier-key model only if a bigger Whisper has clearly fewer errors on the Pāḷi and coding samples, and its median time stays short enough to feel instant. State the numbers.
    - **Engine (idea 6):** compare Parakeet v2 and v3 speed and WER against `base.en`, and state how many Pāḷi terms each got right without hotwords.
  - → verify: every number in `findings.md` is copied from `results.jsonl`, the report output or the paste table. Re-read each one against its source.
    - Result (2026-09-26): every table row is pasted from `bench.py report` (saved as `artifacts/report.md`); prose figures re-checked against it (11.0/17/0.68, 11.0/19/1.85, 17.8/7/1.12, 19.5/6/1.17, 95.8/0/6.38; 1.85 ÷ 0.68 = 2.7). One wrong claim caught and fixed: "add hotwords" for aṭṭhakathā — it is already a hotword. Turbo row absent (not downloaded in time); findings say how to add it.

- [x] **P5.T2: Record the lesson**
  - [x] Append a line to `kamma/lessons.md` in its existing format (`- YYYY-MM-DD [TAG] ...`), for example `- 2026-09-26 [DATA] ~/.cache/transcribe/test.wav` from 2026-05-08 is a clipped tone with a corrupt header, not speech — do not reuse it for model tests; `transcribe --test` overwrites it on the next recording.
  - → verify: read `kamma/lessons.md` and confirm the new line follows the format of the existing one.
    - Result: two lines added (`[DATA]` test.wav, `[WORKFLOW]` slow/hanging HF downloads), same `- YYYY-MM-DD [TAG] ...` format.

- [x] **P5.T3: Final verification**
  - [x] Run `uv run --with pytest pytest tests/`, expect all pass. Run it once more with `env -u DISPLAY` to prove the tests do not need a display.
  - [x] Read the full diff of `dictate.py` and confirm: only `import re`, `FILLER_WORDS`, the regex, `remove_fillers`, its call, the trailing space, the sound config, `play_sound`, its two calls and the `paplay` warning changed. `_transcribe()` and `run_test_mode()` still pass identical transcribe kwargs.
  - [x] Confirm `pyproject.toml` changed only by the `exclude` line, and that no file under `~/.config/transcribe/` was edited by the agent.
  - → verify: pytest green both ways, the diff matches the list above, and `findings.md` answers ideas 4, 5 and 6.
    - Result (2026-09-26): pytest 14 passed, and 14 passed with `env -u DISPLAY`. `git diff dictate.py` holds only the listed changes; both `transcribe_kwargs` lines are `{"beam_size": 5, "vad_filter": True}`. `pyproject.toml` diff is only `exclude = ["tests"]`. `~/.config/transcribe/` files dated 2026-05-08 and 2026-06-26 (untouched).
    - Turbo: dropped by the user after the restarted download stalled (see P4.T5). Nothing is left open.
