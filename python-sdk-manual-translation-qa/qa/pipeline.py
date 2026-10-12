"""Translation QA, hand-instrumented with the low-level Opik Python client.

No @opik.track, no track_openai. Every trace, span and every field on the LLM
spans (model, provider, token usage) is created by an explicit call in this
file, which is what the decorators and wrappers do for you behind the scenes.

Pipeline, per UI string:
  detect          LLM: which language is the source text in?
  translate       LLM: source language -> target language
  back_translate  LLM: target language -> source language, blind to the original
  compare         tool: lexical similarity (difflib) + LLM judge: did the meaning survive?
  verdict         guardrail: threshold the judge's score into ship / review
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Any

import opik
from opik.datetime_helpers import local_timestamp
from opik.id_helpers import generate_id
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the example folder (existing environment values win).
load_dotenv()

# Dev machines sometimes point the OpenAI SDK at a local proxy. This example
# talks to the public API, so drop it.
os.environ.pop("OPENAI_BASE_URL", None)

PROJECT = "python-sdk-manual-translation-qa"
MODEL = "gpt-4o-mini"

# The judge's meaning-preservation score must reach this to ship the translation.
SHIP_THRESHOLD = 0.85

# The low-level client. Credentials come from the environment or ~/.opik.config.
# The project name is pinned here so every trace lands in the same project.
client = opik.Opik(project_name=PROJECT)
openai_client = OpenAI()


class Step:
    """One span, written ONCE, when the step is finished.

    The low-level client batches creates in memory. `Span.update()` and
    `Span.end()` right after creation are separate PATCH calls that can race
    the batched create and lose data (the SDK even logs a warning). The safe
    pattern: remember `start_time`, do the work, then send the complete span
    (input, output, start_time, end_time, usage) in a single `client.span()`
    call. Parent/child links work because we pick the span ids ourselves.
    """

    def __init__(self, trace_id: str, name: str, type: str, input: dict[str, Any], parent: "Step | None" = None):
        self.trace_id = trace_id
        self.id = generate_id()
        self.parent_id = parent.id if parent else None
        self.name, self.type, self.input = name, type, input
        self.start = local_timestamp()

    def finish(self, output: dict[str, Any], **extra: Any) -> None:
        client.span(
            trace_id=self.trace_id,
            id=self.id,
            parent_span_id=self.parent_id,
            name=self.name,
            type=self.type,
            start_time=self.start,
            end_time=local_timestamp(),
            input=self.input,
            output=output,
            **extra,
        )


def chat_json(trace_id: str, parent: Step, name: str, system: str, user: str) -> dict[str, Any]:
    """One OpenAI call recorded as an "llm" span under `parent`, by hand.

    This function IS the integration. `track_openai` does the same thing:
    an "llm" span with the exact messages as input, the provider call, then
    model, provider and token usage copied from the response onto the span.
    Opik multiplies model + provider + usage by its price table to compute the
    span cost (pass `total_cost=` instead for custom pricing).
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    step = Step(trace_id, name, "llm", {"messages": messages}, parent=parent)
    try:
        response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
    except Exception as exc:
        # A failed call still deserves a span: record the error and re-raise.
        step.finish(
            output={},
            error_info={"exception_type": type(exc).__name__, "message": str(exc), "traceback": repr(exc)},
        )
        raise
    result = json.loads(response.choices[0].message.content or "{}")
    usage = response.usage
    step.finish(
        output={"result": result},
        model=response.model,  # the resolved snapshot, e.g. gpt-4o-mini-2024-07-18
        provider="openai",
        usage={
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    )
    return result


DETECT_SYSTEM = (
    "You identify the language of a short piece of app UI text. "
    'Respond with JSON only: {"language": "English name of the language", "confidence": 0.0-1.0}'
)

TRANSLATE_SYSTEM = (
    "You are a localization translator for a mobile app. Translate the text from "
    "{source} into {target}, keeping the tone and length suitable for a UI string. "
    'Respond with JSON only: {{"translation": "..."}}'
)

BACK_TRANSLATE_SYSTEM = (
    "Translate the text into {source}, as literally and faithfully as you can. "
    "Do not try to guess an original phrasing; translate what the text actually says. "
    'Respond with JSON only: {{"translation": "..."}}'
)

JUDGE_SYSTEM = (
    "You are a localization QA reviewer. You get an original UI string and a "
    "back-translation of its translation. Score how well the MEANING of the original "
    "survived the round trip, from 0.0 (meaning lost or changed) to 1.0 (identical meaning). "
    "Wording differences that keep the meaning and tone are fine. Penalize literal readings of "
    "idioms, lost tone, and added or dropped information. "
    'Respond with JSON only: {"score": 0.0-1.0, "drift": "one sentence on what changed, or \\"none\\""}'
)


def check_string(item: dict[str, str]) -> dict[str, Any]:
    """Run one UI string through the pipeline, building its Opik trace by hand."""
    # The root trace: one per UI string. We pick its id so we can send the
    # trace twice: now with just the input (it shows up in Opik straight
    # away), and again at the end with the full payload and the same id, which
    # overwrites the first version. That is the SDK's recommended alternative
    # to Trace.update()/end() right after creation.
    trace_id = generate_id()
    trace_start = local_timestamp()
    trace_input = {"id": item["id"], "text": item["text"], "target_language": item["target"]}
    trace_metadata = {"pipeline_version": "1.0", "ship_threshold": SHIP_THRESHOLD, "model": MODEL}
    client.trace(
        id=trace_id,
        name="translation-qa",
        start_time=trace_start,
        input=trace_input,
        metadata=trace_metadata,
    )

    # ---- Step 1: detect the source language ------------------------------
    detect = Step(trace_id, "detect", "general", {"text": item["text"]})
    detected = chat_json(trace_id, detect, "chat detect-language", DETECT_SYSTEM, item["text"])
    source = detected.get("language", "unknown")
    detect.finish({"language": source, "confidence": detected.get("confidence")})

    # ---- Step 2: translate ------------------------------------------------
    translate = Step(trace_id, "translate", "general", {"text": item["text"], "from": source, "to": item["target"]})
    translated = chat_json(
        trace_id,
        translate,
        "chat translate",
        TRANSLATE_SYSTEM.format(source=source, target=item["target"]),
        item["text"],
    )["translation"]
    translate.finish({"translation": translated})

    # ---- Step 3: back-translate, without showing the original -------------
    back_step = Step(trace_id, "back_translate", "general", {"text": translated, "from": item["target"], "to": source})
    back = chat_json(
        trace_id,
        back_step,
        "chat back-translate",
        BACK_TRANSLATE_SYSTEM.format(source=source),
        translated,
    )["translation"]
    back_step.finish({"back_translation": back})

    # ---- Step 4: compare ---------------------------------------------------
    compare = Step(trace_id, "compare", "general", {"original": item["text"], "back_translation": back})
    # 4a. A cheap lexical check, as a "tool" span: no LLM, no cost.
    lexical_step = Step(trace_id, "lexical-similarity", "tool", {"a": item["text"], "b": back}, parent=compare)
    lexical = round(difflib.SequenceMatcher(None, item["text"].lower(), back.lower()).ratio(), 3)
    lexical_step.finish({"ratio": lexical})
    # 4b. An LLM judge for meaning, as an "llm" span.
    judged = chat_json(
        trace_id,
        compare,
        "chat judge-meaning",
        JUDGE_SYSTEM,
        json.dumps({"original": item["text"], "back_translation": back}, ensure_ascii=False),
    )
    score = float(judged.get("score", 0.0))
    drift = judged.get("drift", "")
    compare.finish({"lexical_similarity": lexical, "meaning_score": score, "drift": drift})

    # ---- Step 5: verdict ---------------------------------------------------
    # type="guardrail": the span that decides whether a translation may ship.
    verdict_step = Step(trace_id, "verdict", "guardrail", {"meaning_score": score, "ship_threshold": SHIP_THRESHOLD})
    verdict = "ship" if score >= SHIP_THRESHOLD else "review"
    rule = f"meaning_score {score} {'>=' if verdict == 'ship' else '<'} {SHIP_THRESHOLD}"
    verdict_step.finish({"verdict": verdict, "rule": rule})

    # ---- Close the trace: re-send it complete, same id ---------------------
    # Feedback scores ride along. They show up as columns in the trace table
    # and are filterable. Both are 0..1, so they chart on one axis.
    feedback_scores = [
        {"name": "back_translation_similarity", "value": score, "reason": drift or "no drift reported"},
        {"name": "lexical_similarity", "value": lexical},
    ]
    client.trace(
        id=trace_id,
        name="translation-qa",
        start_time=trace_start,
        end_time=local_timestamp(),
        input=trace_input,
        output={"verdict": verdict, "translation": translated, "back_translation": back, "rule": rule},
        metadata=trace_metadata,
        tags=[item["target"].lower(), verdict],
        feedback_scores=feedback_scores,
    )

    return {
        "id": item["id"],
        "source": source,
        "target": item["target"],
        "text": item["text"],
        "translation": translated,
        "back_translation": back,
        "score": score,
        "lexical": lexical,
        "drift": drift,
        "verdict": verdict,
    }
