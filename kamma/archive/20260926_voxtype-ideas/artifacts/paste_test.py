# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Compare typing against pasting into the focused window.

  uv run paste_test.py type
  uv run paste_test.py paste ctrl+v [--wait 0.5]

Focus the target window during the 3-second countdown.
Does not import dictate: this is a measurement, not part of the app.
"""

import argparse
import subprocess
import sys
import time

SAMPLE = (
    "Testing dictation into this window. The Pāḷi word mettā means loving-kindness; "
    "the aṭṭhakathā are the old commentaries, and the Saṃyutta Nikāya groups suttas by theme. "
    "Punctuation check: commas, full stops. Quotes \"like this\" and (brackets) too! "
    "Numbers 1, 2, 3 and a path ~/MyFiles/notes.md end the sample."
)


def run(cmd, **kwargs):
    """Run a command; on failure print the command and its error, then exit non-zero."""
    try:
        return subprocess.run(cmd, check=True, **kwargs)
    except FileNotFoundError as e:
        print(f"FAILED: {' '.join(cmd[:3])} ... - {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace").strip() if e.stderr else ""
        print(f"FAILED: {' '.join(cmd[:3])} ... exited {e.returncode} {stderr}", file=sys.stderr)
        sys.exit(1)


def countdown():
    for n in (3, 2, 1):
        print(f"Focus the target window... {n}", flush=True)
        time.sleep(1)


def do_type():
    t0 = time.perf_counter()
    # Same command dictate.py uses.
    run(["xdotool", "type", "--delay", "3", SAMPLE])
    return time.perf_counter() - t0


def read_clipboard():
    try:
        result = subprocess.run(
            ["xclip", "-o", "-selection", "clipboard"], capture_output=True
        )
    except FileNotFoundError as e:
        print(f"FAILED: xclip -o - {e}", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print("Note: clipboard was empty or held no text; treating it as empty.")
        return None
    return result.stdout


def write_clipboard(data: bytes):
    # No stderr capture: xclip forks a helper that keeps the pipe open, which would hang run().
    run(["xclip", "-selection", "clipboard"], input=data)


def do_paste(key, wait):
    t0 = time.perf_counter()
    saved = read_clipboard()
    write_clipboard(SAMPLE.encode())
    run(["xdotool", "key", "--clearmodifiers", key], stderr=subprocess.PIPE)
    time.sleep(wait)
    write_clipboard(saved if saved is not None else b"")
    elapsed = time.perf_counter() - t0
    restored = read_clipboard()
    return elapsed, saved, restored


def main():
    parser = argparse.ArgumentParser(description="Compare typing and pasting into the focused window.")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("type", help="type the sample with xdotool type --delay 3")
    p = sub.add_parser("paste", help="paste the sample with one key, then restore the clipboard")
    p.add_argument("key", help="xdotool key name, e.g. ctrl+v, ctrl+shift+v, shift+Insert")
    p.add_argument("--wait", type=float, default=0.5, help="seconds to wait before restoring the clipboard (default 0.5)")
    args = parser.parse_args()

    print(f"Sample: {len(SAMPLE)} characters.")
    countdown()

    if args.mode == "type":
        elapsed = do_type()
        print(f"\ntype: {elapsed:.2f}s (xdotool type blocks until typing ends)")
    else:
        elapsed, saved, restored = do_paste(args.key, args.wait)
        print(f"\npaste {args.key}: {elapsed:.2f}s for save + set + key + {args.wait}s wait + restore")
        print("Note: xdotool key returns before the app has finished pasting, so this time is a lower bound.")
        if saved is None:
            print("Clipboard restore: clipboard was empty before, so it was set back to empty.")
        elif restored == saved:
            print("Clipboard restore: OK (clipboard holds the old text again).")
        else:
            print("Clipboard restore: MISMATCH - the clipboard does not hold the old text.")
        print(
            "If nothing, or the old clipboard text, arrived: the app may read the clipboard late. "
            "Re-run with a longer --wait (e.g. 1.5) before calling this key a failure."
        )

    print("\nCheck the window: did the full sample arrive, with Pāḷi diacritics correct?")


if __name__ == "__main__":
    main()
