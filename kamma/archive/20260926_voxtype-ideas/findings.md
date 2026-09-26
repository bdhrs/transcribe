# Findings: voxtype ideas 4, 5 and 6

## Idea 4 — paste instead of type

Script: `artifacts/paste_test.py`, sample of 307 characters with Pāḷi diacritics. Default `--wait 0.5`.
Times are the whole send sequence. `type` blocks until typing ends; paste times are a lower bound (`xdotool key` returns before the app pastes). Speed is context only.

| App | type | ctrl+v | ctrl+shift+v | shift+Insert |
|---|---|---|---|---|
| Ghostty + bash (2026-09-26) | Complete, diacritics correct. 2.08 s | **Fail**: a literal `^` arrived (bash quoted-insert), not the text. 0.55 s. Clipboard restored OK | Complete, diacritics correct. 0.57 s. Clipboard restored OK | **Wrong text**: pasted the X PRIMARY selection (the previous command line), not the clipboard. 0.56 s. Clipboard restored OK |
| Browser text box | not run | not run | not run | not run |
| Main editor | not run | not run | not run | not run |

Notes:
- The browser and editor rows were not run. After the Ghostty results the user decided on 2026-09-26: "i dont want paste. i just want automatic typing to appear."
- In Ghostty, `shift+Insert` reads PRIMARY, not CLIPBOARD, so it can only work if paste mode also sets PRIMARY.
- The Ghostty run was in the same shell that ran the script, so the pasted text landed on the next prompt. bash then tried to run the `ctrl+shift+v` text and printed `bash: syntax error near unexpected token '('`. That is expected here and says nothing about paste.

**Recommendation (idea 4): do not build paste mode.** The user rejected it after seeing the Ghostty results. The data points the same way: in Ghostty only `ctrl+shift+v` worked, while browsers and most editors expect `ctrl+v`, so one paste key cannot serve every app without per-window key detection, which the user already judged not worth it. Paste mode would also lose non-text clipboard contents (images) on every dictation. Typing already delivers the Pāḷi diacritics correctly.

## Ideas 5 and 6 — bigger Whisper model, Parakeet

Script: `artifacts/bench.py`. Raw rows: `artifacts/results.jsonl`. Report copy: `artifacts/report.md`.

**Setup.** n = 6 samples of the user's voice (6.9–12.8 s each): 2 plain English, 2 coding, 2 Pāḷi. CPU only (Core Ultra 7 155H), int8 for every model. Whisper uses the production settings (`beam_size=5`, `vad_filter=True`, hotwords from the user's file). Parakeet has no hotwords. Each candidate ran in a fresh process; per sample one warm-up, then the median of 3 runs.

**System load.** `uptime` at the start of the run printed `load average: 8.29, 2.94, 1.92`. The 1-minute figure came from the Parakeet v3 smoke test that had just ended; the busiest other processes were herdr (12 %) and Chrome (9 %). The turbo download ran in the background throughout (network, little CPU).

**Not measured.** `whisper:large-v3-turbo` (shown as NOT RUN) — its download ran at about 0.4 MB/s, stalled at 264 MB, and a restart sat at 0 bytes for over 20 minutes (anonymous Hugging Face downloads throttled). The user dropped it on 2026-09-26: "i dnt care, drop it". Parakeet at full precision — its download hung; int8 was already word-perfect on the JFK clip.

**Filler check.** No filler word appears in any of the 36 outputs (30 production-setting runs plus 6 control runs), so no benchmark strings were added to the filler tests.

n = 6 samples

| Candidate | Status | Load s | Median transcribe s (mean over samples) | WER | Hotword terms exact |
|---|---|---|---|---|---|
| whisper:base.en | OK | 1.64 | 0.68 | 11.0% | 17/23 |
| whisper:small.en | OK | 1.63 | 1.85 | 11.0% | 19/23 |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | OK | 1.91 | 1.12 | 17.8% | 7/23 |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | OK | 2.04 | 1.17 | 19.5% | 6/23 |
| whisper:distil-small.en | OK | 4.11 | 6.38 | 95.8% | 0/23 |
| whisper:large-v3-turbo | NOT RUN | | | | |
| whisper:distil-small.en:nohotwords | OK | 3.93 | 1.15 | 25.4% | 3/23 |

| Candidate | Sample | Median s | WER | Terms | Output |
|---|---|---|---|---|---|
| whisper:base.en | 01 | 0.59 | 0.0% | 0/0 | The weather turned cold last night, so we lit the fire early and read by the window until the rain stopped. |
| whisper:base.en | 02 | 0.73 | 5.6% | 0/0 | Please send me the reports by Friday afternoon and remember to include the figures from the second quarter. |
| whisper:base.en | 03 | 0.73 | 4.8% | 6/6 | Open Ghostty, start a Zellij session and then run pytest with uv and check the JSON output against the README.md file |
| whisper:base.en | 04 | 0.61 | 18.2% | 4/6 | Oskloat to write a reject that passes the TSV export then commit the YAML config and update the gitignore on GitHub |
| whisper:base.en | 05 | 0.68 | 33.3% | 2/5 | Yvesuddhimagga explains the jhāna in detail and the aṭakatān tikā add layers of commentary on each sutta. |
| whisper:base.en | 06 | 0.71 | 5.6% | 5/6 | mettā karuṇāna muditā and upekkhā are the four brahmavihāra taught in the Dīgha Nikāya and the Saṃyutta Nikāya |
| whisper:small.en | 01 | 1.63 | 0.0% | 0/0 | The weather turned cold last night, so we lit the fire early and read by the window until the rain stopped. |
| whisper:small.en | 02 | 1.53 | 5.6% | 0/0 | Please send me the reports by Friday afternoon and remember to include the figures from the second quarter. |
| whisper:small.en | 03 | 1.79 | 9.5% | 5/6 | Open Ghosty, start a Zellij session and then run pytest with uv and check the JSON output against the README.md file. |
| whisper:small.en | 04 | 1.87 | 4.5% | 6/6 | Ask Claude to write a regex that passes the TSV export, then commit the YAML config and update the gitignore on GitHub. |
| whisper:small.en | 05 | 2.08 | 33.3% | 3/5 | Visuddhimagga explains the jhāna in detail and ātakatān tīkā add layers of commentary on each sutta |
| whisper:small.en | 06 | 2.20 | 16.7% | 5/6 | mettā karuṇā muditā upekkhā or the four brahmavihāra taught in the Dīgha Nikāya and the Samyutta Nikāya |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | 01 | 1.25 | 0.0% | 0/0 | The weather turned cold last night, so we lit the fire early and read by the window until the rain stopped. |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | 02 | 0.95 | 5.6% | 0/0 | Please send me the reports by Friday afternoon and remember to include the figures from the second quarter. |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | 03 | 1.15 | 14.3% | 1/6 | Open Ghosty, start a Zillage session, and then run Pytest with UV and check the JSON output against the readme.md file. |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | 04 | 1.08 | 13.6% | 4/6 | Ask Claude to write a regek that passes the TSV export, then commit the YAL config and update the gitignore on GitHub. |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | 05 | 1.12 | 22.2% | 2/5 | The Visuddhimagga explains the Jhana in detail and the Atakata and Tika add layers of commentary on each sutta. |
| parakeet:nemo-parakeet-tdt-0.6b-v2 | 06 | 1.17 | 55.6% | 0/6 | Metta, Karuna, Modita and Upeka are the four Brahma Vihara, taught in the Diga Nikaya and the Samyutta Nikaya. |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | 01 | 1.36 | 4.8% | 0/0 | The weather cold last night, so we lit the fire early and read by the window until the rain stopped. |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | 02 | 1.03 | 5.6% | 0/0 | Please send me the reports by Friday afternoon and remember to include the figures from the second quarter. |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | 03 | 1.27 | 14.3% | 1/6 | Open Ghosty, start a Zelage session, and then run PyTest with UV and check the JSON output against the readme.md file. |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | 04 | 1.13 | 9.1% | 4/6 | Ask Claude to write a reject that passes the TSV export, then commit the YAML config and update the Gitignore on GitHub. |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | 05 | 1.09 | 33.3% | 1/5 | Vivisuddhi Magga explains the jhana in detail and the Atakata and Tika add layers of commentary on each sutta. |
| parakeet:nemo-parakeet-tdt-0.6b-v3 | 06 | 1.12 | 55.6% | 0/6 | Metta, Karuna, Mudita, and Upeka are the four Brahma Vihara taught in the Dig Nikaya and the Samyutta Nikaya. |
| whisper:distil-small.en | 01 | 2.69 | 90.5% | 0/0 | The weather |
| whisper:distil-small.en | 02 | 4.45 | 94.4% | 0/0 | Please |
| whisper:distil-small.en | 03 | 16.69 | 95.2% | 0/6 | G, Stā, St stop, S and CH |
| whisper:distil-small.en | 04 | 8.94 | 95.5% | 0/6 | Oscl and |
| whisper:distil-small.en | 05 | 2.19 | 100.0% | 0/5 |  |
| whisper:distil-small.en | 06 | 3.32 | 100.0% | 0/6 |  |
| whisper:distil-small.en:nohotwords | 01 | 1.00 | 0.0% | 0/0 | The weather turned cold last night so we lit the fire early and read by the window until the rain stopped. |
| whisper:distil-small.en:nohotwords | 02 | 1.00 | 5.6% | 0/0 | Please send me the reports by Friday afternoon and remember to include the figures from the second quarter. |
| whisper:distil-small.en:nohotwords | 03 | 1.12 | 28.6% | 0/6 | Open Ghosty, start a zellage session and then run pie test with UV and check the Jason output against the readme.MD file. |
| whisper:distil-small.en:nohotwords | 04 | 1.08 | 22.7% | 3/6 | Ask Claude to write a reject that passes the TSV export, then commit the ammo config and update the Git Ignore on GitHub. |
| whisper:distil-small.en:nohotwords | 05 | 1.34 | 44.4% | 0/5 | Ivisudi Magga explains the Jana in detail and the Atakatan Tika add layers of commentary on each Suta. |
| whisper:distil-small.en:nohotwords | 06 | 1.38 | 55.6% | 0/6 | Meta, Karuna, Mudita and Upeka are the four Brahma Vihara, taught in the Deganicaya and the Samutaniutanikaya. |

### What the numbers say

With n = 6, a difference of one or two hotword terms, or a few points of WER, is within noise. Only large gaps count.

- **base.en (current):** 11.0 % WER, 17/23 hotword terms, 0.68 s mean per sample. It was the fastest by a wide margin.
- **small.en:** the same 11.0 % WER, 19/23 terms, and 1.85 s mean, 2.7× slower. It fixed sample 04 ("Oskloat ... reject" → "Ask Claude ... regex") but lost "Ghostty" and "Saṃyutta". Its gain is two terms out of 23.
- **Parakeet v2 / v3:** 17.8 % / 19.5 % WER, 7/23 and 6/23 terms, 1.12 s / 1.17 s. The plain English was as good as Whisper. But Parakeet wrote every Pāḷi word without diacritics ("Metta, Karuna ... Diga Nikaya"), so sample 06 scored 55.6 % WER and 0/6 terms for both. It also missed coding names that the hotwords fix for Whisper ("Zillage", "UV", "readme.md"). v3 (multilingual) was no better than v2 on Pāḷi.
- **distil-small.en:** with the hotwords file it collapsed: it stopped after one or two words or returned nothing (95.8 % WER, 0/23 terms) and was the slowest (6.38 s). This is **not** the `AGENTS.md` problem — that one needs `initial_prompt` and `hotwords` together, and `bench.py` passes hotwords only. A control run with the same model and no hotwords (`whisper:distil-small.en:nohotwords`, added after an external review) transcribed normally: 25.4 % WER, 3/23 terms, 1.15 s. So the user's 76-entry hotwords file breaks this distilled model, with the same silent empty-output symptom. It is a model-dependent failure, not a broken model. Even without hotwords it trails base.en and small.en (11.0 %), so it stays out.

### Recommendations

**Idea 5 (second, bigger model on a modifier key): not worth building on this evidence.** small.en gives no clear accuracy gain (same WER, +2 terms of 23) for 2.7× the time. The only bigger candidate left untested is large-v3-turbo. The user dropped it. If it is ever wanted, one `bench.py run whisper:large-v3-turbo` settles it (set a Hugging Face token first; anonymous downloads crawled). It would need a clear jump on the Pāḷi and coding samples (for example 21+/23 terms), with a time the user can accept for a deliberate "careful" key.

**Idea 6 (switch to Parakeet): no.** It is slower than base.en (about 1.1 s against 0.68 s) and clearly worse on what the user dictates most: it drops all Pāḷi diacritics and cannot take hotwords. Its plain-English quality is equal, not better.

**Keep base.en with hotwords.** Its weak spots are aṭṭhakathā ("aṭakatān") and the first word of a sentence ("Oskloat", "Yvesuddhimagga"). aṭṭhakathā and Visuddhimagga are already in the hotwords file, so adding hotwords will not fix these. No tested model fixed them reliably either: small.en got Visuddhimagga right but still wrote "ātakatān".
