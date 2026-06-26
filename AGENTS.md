# Agent notes for transcribe

## faster-whisper transcription kwargs
- Do not pass both `initial_prompt` and `hotwords` with the same long phrase list. The combination makes the model emit empty text on short clips. Pass only `hotwords` for biasing. Keep the two call sites (`_transcribe`, `run_test_mode`) in sync.
