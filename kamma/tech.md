# Tech notes: transcribe

## Tools & Platforms
- Python ≥ 3.10, managed with uv. Installed as an editable uv tool (`uv tool install -e .`), so the
  live `transcribe` command runs the repo's code. `just` recipes: install, restart, test, hotwords, uninstall.
- Speech: faster-whisper (CTranslate2), CPU, int8. Live model: base.en, with the hotwords file.
- Keys: pynput listener. Audio: `arecord` (16 kHz mono WAV). Output: `xclip` (clipboard) and
  `xdotool type` (typing; the app locks layout group 0 around it, because xdotool switches group
  per character when another group is active and freezes Xorg). Not pynput's `Controller.type`: its XSendEvent
  events are ignored by Ghostty and xed. Optional: `paplay` (start/stop sounds), `notify-send` (notifications).
- Config: `~/.config/transcribe/config.ini` and `hotwords.txt`, seeded from the repo's example files.
- Tests: pytest (`uv run --with pytest pytest tests/`), run without an X display via `PYNPUT_BACKEND=dummy`.
  The dummy backend gives every named `Key` the same value, so tests cannot tell named keys apart.
- Hotkey: a key name, a single char, or a raw X keysym number. The live config uses `0x1008ffb1`,
  the keysym this laptop's layout gives the F23 its Copilot key sends (with Super_L and Shift_L).

## Who This Is For
The maintainer on Linux Mint (Cinnamon, X11). Others can install the fork on any X11 Linux desktop.

## Constraints
- X11 only (xdotool, xclip, pynput). Wayland is out of scope.
- CPU only: the machine has no NVIDIA GPU. Transcription must feel instant; base.en takes ~0.7 s per sentence.
- `dictate.py` stays a single file: module-level config constants, plain functions, `subprocess` for system tools.
- The app runs with `HF_HUB_OFFLINE=1`: it never downloads models, so a missing model fails.
- Pass only `hotwords` to faster-whisper, never `initial_prompt` too. Keep `_transcribe()` and
  `run_test_mode()` kwargs identical (AGENTS.md). Distilled models break with the long hotwords file.
- Never edit the user's live config; `.ini` edits need an explicit yes.
- Experiments live in a thread's `artifacts/` as `uv run` scripts with inline dependencies; they never
  add dependencies to `pyproject.toml` and never import `dictate`.

## Resources
- Intel Core Ultra 7 155H (22 threads), 30 GB RAM.
- Hugging Face downloads are slow and can hang when anonymous; fetch models in the background first.
- Freedesktop sounds in `/usr/share/sounds/freedesktop/stereo/`.

## What the output looks like
Text typed into the focused window with one trailing space, fillers removed, plus a clean clipboard
copy. Terminal log lines in foreground mode; background mode (`transcribe -b` / `-r`) discards all output.
