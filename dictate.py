#!/usr/bin/env python3
"""
Transcribe - Voice dictation tool using faster-whisper.
Hold the hotkey to record, release to transcribe and copy to clipboard.
"""

import argparse
import configparser
import queue
import subprocess
import tempfile
import threading
import signal
import sys
import os
import time
from pathlib import Path

from pynput import keyboard
from faster_whisper import WhisperModel

__version__ = "0.1.0"

# Load configuration
CONFIG_PATH = Path.home() / ".config" / "transcribe" / "config.ini"


def load_config():
    config = configparser.ConfigParser()

    # Defaults
    defaults = {
        "model": "base.en",
        "device": "cpu",
        "compute_type": "int8",
        "key": "cmd",
        "auto_type": "true",
        "notifications": "true",
    }

    if CONFIG_PATH.exists():
        config.read(CONFIG_PATH)

    return {
        "model": config.get("whisper", "model", fallback=defaults["model"]),
        "device": config.get("whisper", "device", fallback=defaults["device"]),
        "compute_type": config.get("whisper", "compute_type", fallback=defaults["compute_type"]),
        "key": config.get("hotkey", "key", fallback=defaults["key"]),
        "auto_type": config.getboolean("behavior", "auto_type", fallback=True),
        "notifications": config.getboolean("behavior", "notifications", fallback=True),
    }


CONFIG = load_config()


def get_hotkey(key_name):
    """Map key name to pynput key."""
    key_name = key_name.lower()
    if hasattr(keyboard.Key, key_name):
        return getattr(keyboard.Key, key_name)
    elif len(key_name) == 1:
        return keyboard.KeyCode.from_char(key_name)
    else:
        print(f"Unknown key: {key_name}, defaulting to cmd")
        return keyboard.Key.cmd


HOTKEY = get_hotkey(CONFIG["key"])
MODEL_SIZE = CONFIG["model"]
DEVICE = CONFIG["device"]
COMPUTE_TYPE = CONFIG["compute_type"]
AUTO_TYPE = CONFIG["auto_type"]
NOTIFICATIONS = CONFIG["notifications"]


class Dictation:
    def __init__(self):
        self.recording = False
        self.record_process = None
        self.temp_file = None
        self.model = None
        self.model_loaded = threading.Event()
        self.model_error = None
        self.running = True
        self.is_transcribing = False
        self.listener = None
        self._event_queue = queue.Queue()
        self._worker_stop = threading.Event()
        threading.Thread(target=self._event_worker, daemon=True).start()

        # Load model in background
        print(f"Loading Whisper model ({MODEL_SIZE})...")
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        try:
            self.model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
            self.model_loaded.set()
            hotkey_name = HOTKEY.name if hasattr(HOTKEY, 'name') else HOTKEY.char
            print(f"Model loaded. Ready for dictation!")
            print(f"Hold [{hotkey_name}] to record, release to transcribe.")
            print("Press Ctrl+C to quit.")
        except Exception as e:
            self.model_error = str(e)
            self.model_loaded.set()
            print(f"Failed to load model: {e}")
            if "cudnn" in str(e).lower() or "cuda" in str(e).lower():
                print("Hint: Try setting device = cpu in your config, or install cuDNN.")

    def _event_worker(self):
        while not self._worker_stop.is_set():
            try:
                event = self._event_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if event is None:
                break
            try:
                if event == "start" and not self.recording:
                    self.start_recording()
                elif event == "stop" and self.recording:
                    self.stop_recording()
            except Exception as e:
                print(f"Event worker error: {e}")

    def notify(self, title, message, icon="dialog-information", timeout=2000):
        """Send a desktop notification."""
        if not NOTIFICATIONS:
            return
        subprocess.Popen(
            [
                "notify-send",
                "-a", "Transcribe",
                "-i", icon,
                "-t", str(timeout),
                "-h", "string:x-canonical-private-synchronous:transcribe",
                title,
                message
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def start_recording(self):
        if self.recording or self.model_error:
            return

        self.recording = True
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_file.close()

        # Record using arecord (ALSA) - works on most Linux systems
        self.record_process = subprocess.Popen(
            [
                "arecord",
                "-f", "S16_LE",  # Format: 16-bit little-endian
                "-r", "16000",   # Sample rate: 16kHz (what Whisper expects)
                "-c", "1",       # Mono
                "-t", "wav",
                self.temp_file.name
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("Recording...")
        hotkey_name = HOTKEY.name if hasattr(HOTKEY, 'name') else HOTKEY.char
        self.notify("Recording...", f"Release {hotkey_name.upper()} when done", "audio-input-microphone", 30000)

    def stop_recording(self):
        if not self.recording:
            return

        self.recording = False

        if self.record_process:
            self.record_process.terminate()
            try:
                self.record_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.record_process.kill()
            self.record_process = None

        threading.Thread(target=self._transcribe, daemon=True).start()

    def _transcribe(self):
        if self.is_transcribing:
            return
        self.is_transcribing = True

        # Lower CPU priority for transcription
        os.nice(10)

        print("Transcribing...")
        self.notify("Transcribing...", "Processing your speech", "emblem-synchronizing", 30000)

        try:
            self.model_loaded.wait()

            if self.model_error:
                print(f"Cannot transcribe: model failed to load")
                self.notify("Error", "Model failed to load", "dialog-error", 3000)
                return

            if not self.temp_file or not os.path.exists(self.temp_file.name):
                return

            segments, info = self.model.transcribe(
                self.temp_file.name,
                beam_size=5,
                vad_filter=True,
            )

            text = " ".join(segment.text.strip() for segment in segments)

            if text:
                process = None
                try:
                    process = subprocess.Popen(
                        ["xclip", "-selection", "clipboard"],
                        stdin=subprocess.PIPE
                    )
                    process.communicate(input=text.encode(), timeout=5)
                except subprocess.TimeoutExpired:
                    if process:
                        process.kill()

                if AUTO_TYPE:
                    if self.listener:
                        self.listener.stop()
                    try:
                        subprocess.run(
                            ["xdotool", "type", "--delay", "3", text],
                            timeout=30
                        )
                    except subprocess.TimeoutExpired:
                        print("xdotool timed out")

                print(f"Copied: {text}")
                self.notify("Copied!", text[:100] + ("..." if len(text) > 100 else ""), "emblem-ok-symbolic", 3000)
            else:
                print("No speech detected")
                self.notify("No speech detected", "Try speaking louder", "dialog-warning", 2000)

        except Exception as e:
            print(f"Error: {e}")
            self.notify("Error", str(e)[:50], "dialog-error", 3000)
        finally:
            self.is_transcribing = False
            if self.temp_file and os.path.exists(self.temp_file.name):
                os.unlink(self.temp_file.name)

    def on_press(self, key):
        if key == HOTKEY and not self.recording:
            self._event_queue.put("start")

    def on_release(self, key):
        if key == HOTKEY and self.recording:
            self._event_queue.put("stop")

    def stop(self):
        print("\nExiting...")
        self.running = False
        self._worker_stop.set()
        self._event_queue.put(None)
        if self.listener:
            self.listener.stop()
        if self.record_process:
            self.record_process.terminate()
            try:
                self.record_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.record_process.kill()

    def run(self):
        while self.running:
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            self.listener.start()
            self.listener.join()


def check_dependencies():
    """Check that required system commands are available."""
    missing = []

    for cmd in ["arecord", "xclip"]:
        if subprocess.run(["which", cmd], capture_output=True).returncode != 0:
            pkg = "alsa-utils" if cmd == "arecord" else cmd
            missing.append((cmd, pkg))

    if AUTO_TYPE:
        if subprocess.run(["which", "xdotool"], capture_output=True).returncode != 0:
            missing.append(("xdotool", "xdotool"))

    if missing:
        print("Missing dependencies:")
        for cmd, pkg in missing:
            print(f"  {cmd} - install with: sudo apt install {pkg}")
        sys.exit(1)


def daemonize():
    """Fork process to background."""
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    os.setsid()
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    with open("/dev/null", "r") as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())
    with open("/dev/null", "a+") as devnull:
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())


def get_pid_file():
    return Path.home() / ".cache" / "transcribe.pid"


def write_pid():
    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))


def remove_pid():
    pid_file = get_pid_file()
    if pid_file.exists():
        pid_file.unlink()


def get_running_pid():
    pid_file = get_pid_file()
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError):
        pid_file.unlink(missing_ok=True)
        return None


def kill_running():
    pid = get_running_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped transcribe (PID {pid})")
        remove_pid()
    else:
        print("No running instance found")


def show_status():
    pid = get_running_pid()
    if pid:
        print(f"transcribe is running (PID {pid})")
    else:
        print("transcribe is not running")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe - Push-to-talk voice dictation"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"Transcribe {__version__}"
    )
    parser.add_argument(
        "-b", "--background",
        action="store_true",
        help="Run as background daemon"
    )
    parser.add_argument(
        "-k", "--kill",
        action="store_true",
        help="Stop running instance"
    )
    parser.add_argument(
        "-s", "--status",
        action="store_true",
        help="Show running status"
    )
    parser.add_argument(
        "-r", "--restart",
        action="store_true",
        help="Kill and restart in background"
    )
    args = parser.parse_args()

    if args.kill:
        kill_running()
        return

    if args.status:
        show_status()
        return

    if args.restart:
        kill_running()
        time.sleep(0.5)
        print("Starting transcribe in background...")
        args.background = True

    if get_running_pid():
        print("transcribe is already running")
        print("Use --kill to stop it first")
        return

    if args.background and not args.restart:
        print("Starting transcribe in background...")

    if args.background:
        daemonize()
        write_pid()

    print(f"Transcribe v{__version__}")
    print(f"Config: {CONFIG_PATH}")

    check_dependencies()

    dictation = Dictation()

    def handle_sigint(sig, frame):
        dictation.stop()
        remove_pid()

    def handle_sigterm(sig, frame):
        dictation.stop()
        remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigterm)

    if not args.background:
        write_pid()

    try:
        dictation.run()
    finally:
        remove_pid()


if __name__ == "__main__":
    main()
