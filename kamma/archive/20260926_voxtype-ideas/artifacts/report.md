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
