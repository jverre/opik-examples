<div align="center">

# Whisper Vet Voicemail Triage

**`whisper-vet-voicemail-triage`**

*Press play on the voicemail behind every triage note, and keep a flaky judge from crying wolf.*

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around)**

</div>

---

A triage note is only as good as the sound it came from. When a clinic's voicemail pipeline files "rabbit stopped eating" as routine, or writes down a callback number with a digit wrong, nothing errors: the nurse just calls the wrong person late. By the time you read the note, the evidence (the caller's voice) is gone, and the transcript in between may have misheard a name. This example is a voicemail triage pipeline for a fictional clinic that keeps the evidence: every voicemail is a trace with the original audio attached and playable, the Whisper transcript, and the note built from it. A test suite then checks each note against its transcript, with an `execution_policy` so a flaky small-model judge does not decide the verdict alone.

## What you'll build

A three-step pipeline on the OpenAI Python SDK, one trace per voicemail: synthesize, transcribe, triage. The five voicemails are fictional scripts in `voicemails.py` (a beagle that ate chocolate, cat vaccines, a limping Labrador, a rabbit that stopped eating, a refill request with a self-corrected phone number), spoken by `gpt-4o-mini-tts` at run time into an ignored `out/` folder. `whisper-1` turns each MP3 back into text and `gpt-4o-mini` writes a JSON triage note: urgency (`emergency`, `same_day`, `routine`), pet, owner, callback number, request. The pipeline is traced with `@opik.track`, the OpenAI calls with `track_openai`, and the MP3 is attached to the trace with Opik's `Attachment` type. `evaluate.py` is an Opik test suite with three judge-checked assertions and `runs_per_item=3`, `pass_threshold=2`.

## See it in Opik

Open the `whisper-vet-voicemail-triage` project, Traces tab. The final run left 20 traces: 5 named `triage-voicemail` (the pipeline) and 15 named `evaluation_task` (the suite, 5 items x 3 runs).

Open any `triage-voicemail` trace. The span tree has six spans: `synthesize-voicemail` containing `audio.speech.create` (type llm, with a small TTS cost, about $0.00014 to $0.00021 per voicemail), then `transcribe` (the Whisper output is the span's output; `track_openai` does not trace the transcription call itself, so this span has no token count), then `triage` containing `chat_completion_create` (type llm, roughly 400 to 430 prompt tokens, about $0.00012 per voicemail). On the trace itself, the Attachments area holds the MP3 (for example `refill-number-correction.mp3`, `audio/mpeg`, 248 KB), and it plays in the browser. Every one of the 5 pipeline traces has exactly one attachment.

That attachment is the point. The `transcribe` span is what the pipeline believes was said. The attachment is what was said. In the final run Whisper turned "my beagle Biscuit" into "my Beavel Biscuit" in `chocolate-beagle`, and "Sam Reyes" into "Sam Ray" in `refill-number-correction`. Open the trace, press play, and you settle in seconds whether the caller or the transcript is wrong. The same trace shows the self-correction: the caller says "0131, actually sorry, that's 0138", while Whisper wrote "555-0138. 0138." and dropped the false start, so the note still got the right number, by luck of the transcription.

Then open Test suites, `whisper-vet-voicemail-triage-suite`, and the latest run (experiment `incredible_cucumber_1481`). The final run **failed 4/5 items** (pass rate 80%), and the failure is real rather than flaky: `chocolate-beagle` failed the third assertion in all three runs. The transcript says "Beavel Biscuit", so the triage model wrote species `Beagle` (it guessed the breed from the mangled word and from nothing else in the transcript) and the judge flagged it each time: "the transcript does not specify the pet species". Per-assertion totals across the 15 runs: urgency 15/15, callback number 15/15, pet and owner details 12/15 (the three misses are all this one item).

Why the execution policy matters: both the triage model and the judge are LLMs, so a single run can flip. In an earlier development run of the same suite, one of the 15 judge verdicts failed (14/15 on the pet-details assertion) and every item still passed, because an item only needs 2 of its 3 runs. A failure that happens 3 times out of 3, like `Beavel`, is not noise, and the policy does not hide it. We used `runs_per_item=3` with `pass_threshold=2` because the judge's per-run flip rate looked like roughly one in fifteen, so a majority of three makes a false alarm rare while a regression that breaks every run still fails the item. The numbers above are from one run, so expect yours to differ.

## Run it yourself

1. `cp .env.example .env` and add your keys (`OPENAI_API_KEY`, `OPIK_API_KEY`, `OPIK_WORKSPACE`).
2. `uv sync`
3. `uv run main.py` generates five MP3s into `out/`, transcribes them, and prints a triage note for each. About 40 seconds.
4. `uv run evaluate.py` runs the test suite against the cached transcripts. About 20 seconds.
5. Open the `whisper-vet-voicemail-triage` project in Opik, click a `triage-voicemail` trace, and press play on the attachment. Then open the test suite and read the failed item.

A full run (both commands) costs a few cents, well under $0.10. Everything audible is synthetic: the callers, the pets, the clinic, and the phone numbers (all 555-01xx) are fictional, and the voices are OpenAI TTS. No real voicemail is involved. Whisper is not deterministic across runs, so which words it mishears will vary from the run described above.

## Poke around

- Set `runs_per_item` to 1 in `evaluate.py` and run it a few times. Watch the suite flip between passed and failed on items that did not change, then restore 3 and 2.
- Open the `transcribe` span of `chocolate-beagle` and play the attachment next to it. Then add "if the species is unclear, use `unknown`" to the triage prompt in `main.py` and see whether the suite recovers on the item Whisper garbles.
- Lower the stakes of the rabbit call: edit the script in `voicemails.py` so Clementine "has been eating a bit less". Does the urgency drop to `same_day`, and does the judge agree?
- Add a sixth voicemail with a callback number spoken as words ("five five five, oh one six five"). Check which step, Whisper or the triage model, rewrites it.

## How it's put together

- `main.py`: the pipeline (TTS, Whisper, triage), one `triage-voicemail` trace per voicemail with the MP3 attached; caches transcripts and notes in `out/`.
- `voicemails.py`: five fictional voicemail scripts, each with the TTS voice that speaks it.
- `evaluate.py`: the Opik test suite, three judge-checked assertions, `runs_per_item=3`, `pass_threshold=2`.
- `pyproject.toml`: pins `opik==2.2.96`; Python 3.12 or 3.13.
- `.env.example`: the keys the example needs.
