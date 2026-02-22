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
uv tool install -e .
```

## Setup

```bash
# Create config
mkdir -p ~/.config/transcribe
cp config.example.ini ~/.config/transcribe/config.ini

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

- Hold **F12** (or configured key) to record
- Release to transcribe → copies to clipboard and types
- **Ctrl+C** to quit

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
key = f12

[behavior]
auto_type = true
notifications = true
```

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
| medium.en | ~1.5GB | Slower | Great |
| large-v3 | ~3GB | Slowest | Best |

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
