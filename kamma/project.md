# Project: transcribe

## What it is and why
A push-to-talk voice dictation tool for Linux. Hold a hotkey to record, release it, and the speech is
transcribed on the local CPU with faster-whisper, copied to the clipboard and typed into the focused
window. It exists so dictation is fast, private (no cloud) and accurate for a vocabulary most tools get
wrong: Pāḷi terms with diacritics, coding names and AI tool names, steered by a hotwords file.

## Who it's for
The maintainer first: tuned to one voice, one X11 Cinnamon desktop and one vocabulary. Others are
welcome: the fork (bdhrs/transcribe, originally ksred/transcribe) stays installable with `just install`
and documented in the README, but personal needs win when they conflict.

## One-off or ongoing
Ongoing. It runs in the background all day and gets small improvements as needs come up.

## What it produces
- Typed text in whatever window has focus (terminals, browsers, editors), plus a clipboard copy.
- Mixed dictation: English prose, prompts for AI coding agents, and Pāḷi terms for dictionary and research work.

## How you'll know it worked
- Text appears almost at once after the key is released.
- Pāḷi and coding terms come out spelled right, diacritics included, with no fixing by hand.
- It runs in the background for months without crashes, stuck recordings or missed key presses.
