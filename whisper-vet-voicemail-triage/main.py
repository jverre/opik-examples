"""Voicemail triage pipeline for a fictional vet clinic, traced with Opik.

Each voicemail becomes one trace in the "whisper-vet-voicemail-triage" project:

    triage-voicemail                  <- the whole pipeline, MP3 attached
    |- synthesize-voicemail           <- TTS: the caller's script -> MP3
    |  '- audio.speech.create         <- logged by track_openai
    |- transcribe                     <- whisper-1 speech-to-text
    '- triage                         <- gpt-4o-mini -> urgency, pet, callback
       '- chat_completion_create      <- logged by track_openai (tokens, cost)

The audio is synthetic: each script in voicemails.py is spoken by OpenAI TTS
and written to out/ (git-ignored). The MP3 is attached to the trace, so you can
press play on exactly what the pipeline heard.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

EXAMPLE_DIR = Path(__file__).resolve().parent
OUT_DIR = EXAMPLE_DIR / "out"
PROJECT_NAME = "whisper-vet-voicemail-triage"

# Pin the Opik project before opik is imported, and drop any proxy base URL
# the shell may set so the example always talks to the public OpenAI API.
load_dotenv(EXAMPLE_DIR / ".env")
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME
os.environ.pop("OPENAI_BASE_URL", None)

import opik
from openai import OpenAI
from opik import Attachment, opik_context
from opik.integrations.openai import track_openai

from voicemails import VOICEMAILS

TTS_MODEL = "gpt-4o-mini-tts"
TRANSCRIBE_MODEL = "whisper-1"
TRIAGE_MODEL = "gpt-4o-mini"

TRIAGE_SYSTEM_PROMPT = """\
You are the front-desk triage assistant at a small-animal veterinary clinic.
You read a transcript of a voicemail (speech-to-text output) and write a short
triage note for the nurse who will call the owner back. Reply with JSON only,
in exactly this shape:

{
  "urgency": "emergency | same_day | routine",
  "urgency_reason": "one sentence tying the urgency to what the caller said",
  "pet": {"name": "the pet's name", "species": "dog, cat, rabbit, ..."},
  "owner": "the caller's name",
  "callback_number": "the number to call back, written like 555-0123",
  "request": "what the caller wants, in one sentence"
}

Urgency rules:
- emergency: possible poisoning, trouble breathing, collapse, seizures,
  heavy bleeding, bloat, or a rabbit or other small mammal that has stopped
  eating. The nurse calls back immediately.
- same_day: the animal is in pain or has a new problem but is stable
  (limping, vomiting once, minor wounds). The nurse calls back today.
- routine: bookings, vaccines, refills, questions. The nurse calls back within
  two working days.
- Judge urgency by what happened to the animal, not by how worried the caller
  sounds. A calm, polite caller can still be describing an emergency.

Rules for the other fields:
- Use the callback number exactly as the caller gave it. If they correct
  themselves, use the corrected number.
- Only write what the caller said. Never invent symptoms, times, or names.
"""

openai_client = track_openai(OpenAI())


@opik.track(name="synthesize-voicemail")
def synthesize_voicemail(voicemail: dict, audio_path: Path) -> dict:
    """Speak the caller's script with OpenAI TTS and write the MP3."""
    response = openai_client.audio.speech.create(
        model=TTS_MODEL,
        voice=voicemail["voice"],
        input=voicemail["script"],
        response_format="mp3",
    )
    audio_path.write_bytes(response.content)
    return {
        "audio_path": str(audio_path.relative_to(EXAMPLE_DIR)),
        "voice": voicemail["voice"],
        "size_bytes": len(response.content),
    }


@opik.track(name="transcribe")
def transcribe(audio_path: Path) -> str:
    """Speech-to-text with Whisper. The transcript is the span's output."""
    with audio_path.open("rb") as audio_file:
        return openai_client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=audio_file,
            response_format="text",
        )


@opik.track(name="triage")
def triage(transcript: str) -> dict:
    """Transcript -> triage note (urgency, pet, callback) with gpt-4o-mini."""
    response = openai_client.chat.completions.create(
        model=TRIAGE_MODEL,
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


@opik.track(name="triage-voicemail")
def triage_voicemail(voicemail: dict) -> dict:
    """The full pipeline for one voicemail. One call, one trace."""
    audio_path = OUT_DIR / f"{voicemail['id']}.mp3"
    synthesize_voicemail(voicemail, audio_path)

    transcript = transcribe(audio_path)
    note = triage(transcript)

    # Attach the exact audio the pipeline heard, playable from the trace.
    opik_context.update_current_trace(
        attachments=[Attachment(data=str(audio_path), content_type="audio/mpeg")]
    )

    result = {"voicemail": voicemail["id"], "transcript": transcript, "note": note}
    # Cache transcript + note so evaluate.py can build its test suite.
    (OUT_DIR / f"{voicemail['id']}.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    for voicemail in VOICEMAILS:
        print(f"\n=== {voicemail['id']} (caller: {voicemail['caller']}) ===")
        result = triage_voicemail(voicemail)
        note = result["note"]
        print(f"Heard:    {result['transcript'].strip()}")
        print(f"Urgency:  {note['urgency']} - {note['urgency_reason']}")
        print(f"Pet:      {note['pet']['name']} ({note['pet']['species']})")
        print(f"Callback: {note['owner']} at {note['callback_number']}")
        print(f"Request:  {note['request']}")
    opik.flush_tracker()
    print(f"\nDone. Open the {PROJECT_NAME} project in Opik.")
