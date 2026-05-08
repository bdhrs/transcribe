# Transcribe

Push-to-talk voice dictation for Linux using faster-whisper. Hold a key to record, release to transcribe.

## Install

```bash
# System dependencies (Ubuntu/Debian)
sudo apt install alsa-utils xclip xdotool libnotify-bin

# Fedora
sudo dnf install alsa-utils xclip xdotool libnotify

# Arch
sudo pacman -S alsa-utils xclip xdotool libnotify

# Install globally with uv
git clone https://github.com/bdhrs/transcribe.git
cd transcribe
just install
```

`just install` runs `uv tool install -e .` and copies `config.example.ini` and `hotwords.example.txt` to `~/.config/transcribe/` — only if those files don't already exist, so re-running after an upgrade never overwrites your changes.

If you don't have `just`, run these manually:

```bash
uv tool install -e .
mkdir -p ~/.config/transcribe
cp config.example.ini ~/.config/transcribe/config.ini
cp hotwords.example.txt ~/.config/transcribe/hotwords.txt
```

## Setup

```bash
# Enable autostart
mkdir -p ~/.config/autostart
cp transcribe.desktop ~/.config/autostart/
```

## Usage

```bash
transcribe              # Run in foreground (Ctrl+C to quit)
transcribe -b           # Run in background
transcribe -s           # Check if running
transcribe -k           # Stop background instance
transcribe -r           # Restart (kill and start in background)
```

- Hold **cmd** (or configured key) to record
- Release to transcribe → copies to clipboard and types
- **Ctrl+C** to quit (foreground mode)

## Autostart

Copy the desktop file to autostart:
```bash
cp transcribe.desktop ~/.config/autostart/
```

Transcribe starts automatically on login (in background mode).

## Configuration

Edit `~/.config/transcribe/config.ini`:

```ini
[whisper]
model = base.en
device = cpu
compute_type = int8

[hotkey]
key = cmd

[behavior]
auto_type = true
notifications = true
```

### Changing the Hotkey

1. Open the config file: `nano ~/.config/transcribe/config.ini`
2. Edit the `key` value under `[hotkey]`
3. Save and restart: `transcribe -r`

**Valid keys:**

| Type | Keys |
|------|------|
| Modifiers | `cmd`, `cmd_r`, `alt`, `alt_r`, `alt_gr`, `ctrl`, `ctrl_r`, `shift`, `shift_r` |
| Function | `f1` through `f20` |
| Navigation | `home`, `end`, `page_up`, `page_down`, `insert`, `delete`, `up`, `down`, `left`, `right` |
| Special | `scroll_lock`, `pause`, `print_screen`, `caps_lock`, `num_lock`, `space`, `tab`, `enter`, `esc`, `backspace` |
| Media | `media_play_pause`, `media_next`, `media_previous`, `media_volume_up`, `media_volume_down`, `media_volume_mute` |
| Single char | Any single letter or number: `a`, `b`, `1`, `2`, etc. |

### GPU Support

For NVIDIA GPU acceleration, install cuDNN 9 and set:
```ini
device = cuda
compute_type = float16
```

## Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny.en | ~75MB | Fastest | Basic |
| base.en | ~150MB | Fast | Good |
| small.en | ~500MB | Medium | Better |
| distil-small.en | ~330MB | Fast | Better (distilled) |
| medium.en | ~1.5GB | Slower | Great |
| large-v3-turbo | ~1.6GB | Fast | Near-best |
| large-v3 | ~3GB | Slowest | Best |

Use `transcribe --test` to compare models on your own voice and pick the best fit (see [Testing models](#testing-models) below).

## Testing models

`transcribe --test` records a sample using your configured hotkey, then runs it through every model in `[test] models` and prints transcription + timing for each. You pick the winner.

```bash
transcribe --test                 # record + test all configured models
transcribe --test --reuse-recording  # reuse last recording, re-run models
```

Configure the list in `~/.config/transcribe/config.ini`:

```ini
[test]
models = tiny.en, base.en, small.en, distil-small.en
```

The list is open-ended — any model name accepted by faster-whisper works.

## Hotwords

Add words or phrases the model frequently gets wrong to `~/.config/transcribe/hotwords.txt` — one entry per line. Lines starting with `#` and blank lines are ignored.

```
# ~/.config/transcribe/hotwords.txt
Zellij
Ghostty
uv
```

The file is seeded from `hotwords.example.txt` by `just install`. Hotwords are applied on every transcription (normal mode and test mode).

## Troubleshooting

**No audio:**
```bash
arecord -l          # List input devices
arecord -d 3 test.wav && aplay test.wav  # Test
```

**Keyboard permissions:**
```bash
sudo usermod -aG input $USER
# Log out and back in
```

**cuDNN errors:**
Install cuDNN 9 or use CPU mode (`device = cpu`).
