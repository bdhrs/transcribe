## Thread
- **ID:** 20260926_voxtype-ideas
- **Objective:** Ideas from voxtype — three small features (trailing space, filler removal, start/stop sounds) and three measurements (paste, bigger Whisper, Parakeet).

## Files Changed
- `dictate.py` — `remove_fillers` (+ filler and quoted-filler regexes), trailing space on typed text only, `sounds`/`start_sound`/`stop_sound` config, `play_sound`, two sound calls, missing-`paplay` warning.
- `tests/conftest.py`, `tests/test_fillers.py` — first tests in the repo; 27 filler cases, run without an X display.
- `pyproject.toml` — `exclude = ["tests"]` for the wheel.
- `README.md`, `config.example.ini` — document the three sound keys and `pulseaudio-utils`.
- `kamma/lessons.md` — three lessons (corrupt test.wav, slow HF downloads, distil + hotwords collapse).
- Thread folder — spec, plan, findings, `artifacts/paste_test.py`, `artifacts/bench.py`, samples, `results.jsonl`, `report.md`.

## Findings
| # | Severity | Location | What | Why | Fix |
|---|----------|----------|------|-----|-----|
| 1 | major | `dictate.py` `_FILLER_RE` | `\b` treated hyphens/apostrophes as boundaries: "uh-huh" → "-huh", "mm-hmm" → "mm-" | Corrupts common spoken affirmations | Lookarounds exclude `\w ' ’ -` (CodeRabbit + independent review) |
| 2 | minor | `dictate.py` `remove_fillers` | Quoted/bracketed lone filler left an empty pair: `"" she said`, `hello () world`, `‘’` | Garbled output | `_QUOTED_FILLER_RE` for `"" “” ‘’ () []` |
| 3 | major | `findings.md` distil bullet | Blamed the AGENTS.md initial_prompt problem; bench passes hotwords only | Wrong lesson for future threads | `:nohotwords` control run (25.4 % WER); bullet and lessons rewritten (external review) |
| 4 | major | `artifacts/bench.py` `report()` | Candidates with no rows vanished from the table | Report and findings disagreed | Start from `CANDIDATES`; print NOT RUN (external review) |
| 5 | nit | `dictate.py` `check_dependencies` | Warning said "sounds disabled" though `SOUNDS` stays true | Overstated behaviour | Reworded |
| 6 | minor | `plan.md` | Stale turbo notes after turbo was dropped | Plan contradicted reality | Updated (CodeRabbit) |

## Fixes Applied
- All six findings above fixed. Plan "Review fixes" R1–R6 record each with its verify result.

## Test Evidence
- `uv run --with pytest pytest tests/` (scope: all 27 filler cases, the whole suite) → 27 passed; same with `env -u DISPLAY` → 27 passed.
- Revert checks: no-op `remove_fillers` → 11 of the first 14 fail; old `\b` pattern → 8 of 9 hyphen/quote cases fail; double-quote pairs only → 3 of 4 bracket/curly cases fail. Each restored byte-identical (`cmp`).
- `bench.py report` re-run by the independent reviewer → byte-identical to `artifacts/report.md`; every figure in `findings.md` matches.
- Live, by the user: filler removal + capitalisation, sounds on press/release, stop sound = start sound.
- Sounds off: throwaway `HOME` with `sounds = false` → 0 `Popen` calls; live config → one `paplay` call.
- CodeRabbit (`--agent --uncommitted --include-untracked`, 19 files) → 1 finding (#6), fixed.

## Not Verified
- Trailing space not confirmed by eye as a separate check; the user confirmed the live output only in general terms.
- Sounds once per real key press: verified by reading the guards and a call trace, not by counting live presses.
- Paste test covers Ghostty only; the user dropped paste before the browser and editor runs.
- Benchmark: n = 6 samples, only 2 Pāḷi; run started with a 1-minute load of 8.29; large-v3-turbo and Parakeet full precision not measured.
- Pre-existing, not touched: `packages = ["."]` ships the whole repo (including thread audio) in a wheel.

## Verdict
PASSED
- Review date: 2026-09-26
- Reviewer: independent Sonnet subagent + CodeRabbit + two user-supplied external reviews; fixes by Claude Opus 5.5
