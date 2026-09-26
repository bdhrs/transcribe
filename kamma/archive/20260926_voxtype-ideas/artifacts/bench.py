# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "faster-whisper>=1.0.0",
#     "onnx-asr[cpu,hub]",
#     "jiwer",
# ]
# ///
"""
Benchmark Whisper sizes and Parakeet on the user's own voice.

  uv run bench.py record              # record the 6 samples
  uv run bench.py fetch               # download every candidate model
  uv run bench.py all [--extra C]...  # run every candidate, each in a fresh process
  uv run bench.py run CANDIDATE [--samples WAV...]
  uv run bench.py report

A candidate is "whisper:<name>" or "parakeet:<name>", with ":full" on a
Parakeet name for full precision instead of int8, or ":nohotwords" on a
Whisper name as a control run without the hotwords file.
"""

import argparse
import array
import json
import re
import statistics
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLES_DIR = HERE / "samples"
RESULTS = HERE / "results.jsonl"
HOTWORDS_PATH = Path.home() / ".config" / "transcribe" / "hotwords.txt"

SENTENCES = [
    "The weather turned cold last night, so we lit the fire early and read by the window until the rain stopped.",
    "Please send me the report by Friday afternoon, and remember to include the figures from the second quarter.",
    "Open Ghostty, start a Zellij session, then run pytest with uv and check the JSON output against the README.md file.",
    "Ask Claude to write a regex that parses the TSV export, then commit the YAML config and update the gitignore on GitHub.",
    "The Visuddhimagga explains jhāna in detail, and the aṭṭhakathā and ṭīkā add layers of commentary on each sutta.",
    "Mettā, karuṇā, muditā and upekkhā are the four brahmavihāra, taught in the Dīgha Nikāya and the Saṃyutta Nikāya.",
]

CANDIDATES = [
    "whisper:base.en",
    "whisper:small.en",
    "parakeet:nemo-parakeet-tdt-0.6b-v2",
    "parakeet:nemo-parakeet-tdt-0.6b-v3",
    "whisper:distil-small.en",
    "whisper:large-v3-turbo",
]

CLIP_LIMIT = 0.01
SILENCE_RMS = 100


# Copied from dictate.py rather than imported: importing dictate sets HF_HUB_OFFLINE=1,
# which would stop large-v3-turbo from downloading.
def load_hotwords(path: Path) -> str:
    if not path.exists():
        return ""
    lines = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return " ".join(lines)


def hotword_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    terms = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in terms:
            terms.append(line)
    return terms


# ---------- record ----------

def data_chunk(path: Path):
    """Return (offset of sample data, size the header claims) for a WAV file."""
    raw = path.read_bytes()
    pos = 12
    while pos + 8 <= len(raw):
        chunk_id, size = struct.unpack("<4sI", raw[pos:pos + 8])
        if chunk_id == b"data":
            return pos + 8, size
        pos += 8 + size + (size & 1)
    raise ValueError(f"{path}: no data chunk")


def fix_header(path: Path) -> bool:
    offset, claimed = data_chunk(path)
    actual = path.stat().st_size - offset
    if claimed == actual:
        return False
    frames = path.read_bytes()[offset:offset + actual - (actual % 2)]
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(frames)
    return True


def check_levels(path: Path):
    with wave.open(str(path), "rb") as w:
        frames = w.readframes(w.getnframes())
        rate = w.getframerate()
    samples = array.array("h", frames)
    if not samples:
        return 0.0, 0, 0.0, 0.0
    peak = max(abs(s) for s in samples)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    clipped = sum(1 for s in samples if s >= 32767 or s <= -32768) / len(samples)
    return len(samples) / rate, peak, rms, clipped


def record():
    SAMPLES_DIR.mkdir(exist_ok=True)
    for n, sentence in enumerate(SENTENCES, 1):
        wav = SAMPLES_DIR / f"{n:02d}.wav"
        while True:
            print(f"\nSample {n}/{len(SENTENCES)}. Read this aloud at your normal pace:\n\n  {sentence}\n")
            input("Press Enter to start recording...")
            proc = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "wav", str(wav)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            input("Recording. Press Enter to stop...")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

            if fix_header(wav):
                print("Header size did not match the file; rewrote it.")
            seconds, peak, rms, clipped = check_levels(wav)
            print(f"Length {seconds:.1f}s, peak {peak}, RMS {rms:.0f}, clipped {clipped:.2%}")
            problems = []
            if clipped > CLIP_LIMIT:
                problems.append("too many samples at full scale (mic input broken or far too loud)")
            if rms < SILENCE_RMS:
                problems.append("near silence (mic muted or wrong input?)")
            if not 5 <= seconds <= 15:
                problems.append("length outside 5-15 s")
            if problems:
                print("Rejected: " + "; ".join(problems) + ". Record it again.")
                continue
            (SAMPLES_DIR / f"{n:02d}.txt").write_text(sentence + "\n")
            break
    print(f"\nDone. Samples are in {SAMPLES_DIR}")


# ---------- run ----------

def load_candidate(candidate: str):
    """Return a function wav_path -> text."""
    engine, _, name = candidate.partition(":")
    if engine == "whisper":
        from faster_whisper import WhisperModel

        name, _, variant = name.partition(":")
        model = WhisperModel(name, device="cpu", compute_type="int8")
        kwargs = {"beam_size": 5, "vad_filter": True}
        hotwords = "" if variant == "nohotwords" else load_hotwords(HOTWORDS_PATH)
        if hotwords:
            # hotwords only, never initial_prompt too: see AGENTS.md.
            kwargs["hotwords"] = hotwords

        def transcribe(wav):
            segments, _ = model.transcribe(str(wav), **kwargs)
            return " ".join(s.text.strip() for s in segments)

        return transcribe
    if engine == "parakeet":
        import onnx_asr

        name, _, precision = name.partition(":")
        if precision == "full":
            model = onnx_asr.load_model(name)
        else:
            model = onnx_asr.load_model(name, quantization="int8")
        return lambda wav: model.recognize(str(wav))
    raise ValueError(f"unknown engine in {candidate!r}; use whisper:<name> or parakeet:<name>")


def sample_wavs():
    return sorted(SAMPLES_DIR.glob("*.wav"))


def run(candidate: str, wavs: list[Path]):
    if not wavs:
        print(json.dumps({"candidate": candidate, "error": "no samples; run record first"}))
        return 1
    t0 = time.perf_counter()
    try:
        transcribe = load_candidate(candidate)
    except (ValueError, RuntimeError, OSError, ImportError) as e:
        print(json.dumps({"candidate": candidate, "error": f"load failed: {type(e).__name__}: {e}"}), flush=True)
        return 1
    load_s = time.perf_counter() - t0

    for wav in wavs:
        try:
            transcribe(wav)  # warm-up
            times = []
            for _ in range(3):
                t1 = time.perf_counter()
                text = transcribe(wav)
                times.append(time.perf_counter() - t1)
        except (RuntimeError, OSError, ValueError) as e:
            print(json.dumps({"candidate": candidate, "sample": wav.stem,
                              "error": f"transcribe failed: {type(e).__name__}: {e}"}), flush=True)
            continue
        print(json.dumps({
            "candidate": candidate,
            "sample": wav.stem,
            "load_s": round(load_s, 3),
            "median_s": round(statistics.median(times), 3),
            "text": text,
        }, ensure_ascii=False), flush=True)
    return 0


def fetch(candidates):
    for candidate in candidates:
        print(f"Fetching {candidate}...", flush=True)
        try:
            load_candidate(candidate)
            print("  OK", flush=True)
        except (ValueError, RuntimeError, OSError, ImportError) as e:
            print(f"  FAILED: {type(e).__name__}: {e}", flush=True)


def run_all(candidates):
    print(subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip(), flush=True)
    with RESULTS.open("a", encoding="utf-8") as out:
        for candidate in candidates:
            print(f"\n== {candidate}", flush=True)
            t0 = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "run", candidate],
                capture_output=True, text=True,
            )
            got_line = False
            for line in proc.stdout.splitlines():
                if line.startswith("{"):
                    out.write(line + "\n")
                    out.flush()
                    got_line = True
                    print(line, flush=True)
            if proc.returncode != 0 or not got_line:
                err = proc.stderr.strip().splitlines()[-1:] or ["no output"]
                record_line = json.dumps({"candidate": candidate,
                                          "error": f"exit {proc.returncode}: {err[0]}"})
                out.write(record_line + "\n")
                print(record_line, flush=True)
            print(f"   ({time.perf_counter() - t0:.0f}s)", flush=True)


# ---------- report ----------

def normalise(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def term_hits(reference: str, output: str, terms: list[str]):
    present = [t for t in terms if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", reference)]
    found = [t for t in present if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", output)]
    return len(found), len(present)


def report():
    import jiwer

    refs = {p.stem: p.read_text().strip() for p in sorted(SAMPLES_DIR.glob("*.txt"))}
    if not refs:
        print("No reference files in samples/. Run record first.")
        return 1
    if not RESULTS.exists():
        print(f"No {RESULTS.name}. Run all first.")
        return 1
    terms = hotword_terms(HOTWORDS_PATH)

    # Start from the full candidate list so a skipped candidate shows as NOT RUN instead of vanishing.
    rows, errors, order = {}, {}, list(CANDIDATES)
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        c = r["candidate"]
        if c not in order:
            order.append(c)
        if "error" in r:
            errors.setdefault(c, []).append(r["error"])
            continue
        if r["sample"] in refs:
            rows.setdefault(c, {})[r["sample"]] = r  # a later run replaces an earlier one

    print(f"n = {len(refs)} samples\n")
    print("| Candidate | Status | Load s | Median transcribe s (mean over samples) | WER | Hotword terms exact |")
    print("|---|---|---|---|---|---|")
    for c in order:
        got = rows.get(c, {})
        if not got and c not in errors:
            print(f"| {c} | NOT RUN | | | | |")
            continue
        if not got:
            print(f"| {c} | FAILED: {'; '.join(errors.get(c, ['no results']))} | | | | |")
            continue
        if len(got) < len(refs):
            print(f"| {c} | PARTIAL ({len(got)}/{len(refs)}) | | | | |")
            continue
        samples = sorted(got)
        wer = jiwer.wer([normalise(refs[s]) for s in samples], [normalise(got[s]["text"]) for s in samples])
        hits = [term_hits(refs[s], got[s]["text"], terms) for s in samples]
        found, present = sum(h[0] for h in hits), sum(h[1] for h in hits)
        load = got[samples[0]]["load_s"]
        mean_t = statistics.mean(got[s]["median_s"] for s in samples)
        print(f"| {c} | OK | {load:.2f} | {mean_t:.2f} | {wer:.1%} | {found}/{present} |")

    print("\n| Candidate | Sample | Median s | WER | Terms | Output |")
    print("|---|---|---|---|---|---|")
    for c in order:
        for s, r in sorted(rows.get(c, {}).items()):
            wer = jiwer.wer(normalise(refs[s]), normalise(r["text"]))
            found, present = term_hits(refs[s], r["text"], terms)
            text = r["text"].replace("|", "\\|")
            print(f"| {c} | {s} | {r['median_s']:.2f} | {wer:.1%} | {found}/{present} | {text} |")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Benchmark speech models on the user's voice.")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("record", help="record the 6 samples with their reference texts")
    p_run = sub.add_parser("run", help="run one candidate in this process, print JSON lines")
    p_run.add_argument("candidate")
    p_run.add_argument("--samples", nargs="+", type=Path, help="WAV files to use instead of samples/")
    p_fetch = sub.add_parser("fetch", help="download every candidate model")
    p_all = sub.add_parser("all", help="run every candidate in a fresh process, append to results.jsonl")
    for p in (p_fetch, p_all):
        p.add_argument("--extra", action="append", default=[], help="extra candidate, e.g. whisper:medium.en")
        p.add_argument("--skip", action="append", default=[], help="leave out a candidate, e.g. whisper:large-v3-turbo")
    sub.add_parser("report", help="print Markdown tables from results.jsonl")
    args = parser.parse_args()

    if args.mode == "record":
        record()
    elif args.mode == "run":
        sys.exit(run(args.candidate, args.samples or sample_wavs()))
    elif args.mode == "fetch":
        fetch([c for c in CANDIDATES + args.extra if c not in args.skip])
    elif args.mode == "all":
        run_all([c for c in CANDIDATES + args.extra if c not in args.skip])
    else:
        sys.exit(report())


if __name__ == "__main__":
    main()
