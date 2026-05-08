# Review

## Thread
- **ID:** 20260508_model-test-mode-and-hotwords
- **Objective:** Add model test mode and hotwords support to the transcribe CLI

## Files Changed
- `dictate.py` — hotwords loader, test mode, HF_HUB_OFFLINE, initial_prompt+hotwords on transcribe
- `config.example.ini` — added commented [test] and hotwords_file options
- `README.md` — install, testing, hotwords sections; updated model table
- `hotwords.example.txt` — new seed file
- `justfile` — new; install, restart, hotwords, test, test-reuse, uninstall recipes

## Findings
No findings. All tasks implemented and verified by user on live hardware.

## Fixes Applied
- Switched from `hotwords` only to `initial_prompt` + `hotwords` after live test showed `hotwords` alone insufficient for stubborn words like "Zellij"
- Added `HF_HUB_OFFLINE=1` after discovering faster-whisper phones home on every model load, burning user's limited data quota
- Removed `large-v3-turbo` and `tiny.en` from default test model list (data constraints; tiny.en cache was corrupt)
- Added `flush=True` to test mode print calls to fix output buffering

## Test Evidence
- `just test-reuse` → three model blocks rendered with load/transcribe times and text
- Live dictation with hotwords → "Zellij" and "uv" both recognised correctly
- `just hotwords` → opens fresh editor, restarts on exit
- `just restart` → restarts daemon

## Verdict
PASSED
- Review date: 2026-05-08
- Reviewer: kamma (inline)
