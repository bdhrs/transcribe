# Agent notes for transcribe

## faster-whisper transcription kwargs
- Do not pass both `initial_prompt` and `hotwords` with the same long phrase list. The combination makes the model emit empty text on short clips. Pass only `hotwords` for biasing. Keep the two call sites (`_transcribe`, `run_test_mode`) in sync.
- Distilled models (e.g. `distil-small.en`) collapse to cut-off or empty text with the long hotwords file even when only `hotwords` is passed (95.8 % WER vs 25.4 % without hotwords, 2026-09-26). Do not switch to a distil model without testing it on the real hotwords file.

## filler removal
- `remove_fillers` must leave words joined by a hyphen or apostrophe whole ("uh-huh", "mm-hmm", "um's"). Any change to its regex needs test cases next to `- ' ’ " “ ‘ ( [`, not just spaces.
