"""One traced extraction: label image in, typed NutritionFacts out."""

import base64
from pathlib import Path

import opik
from openai import OpenAI
from opik import Attachment, opik_context
from opik.integrations.openai import track_openai

from nutrition_labels import MODEL, PROJECT_NAME
from nutrition_labels.models import NutritionFacts, json_schema

# track_openai wraps the regular client: every chat.completions call made
# through it becomes an `llm` span with token usage and cost.
client = track_openai(OpenAI(), project_name=PROJECT_NAME)

SYSTEM_PROMPT = """\
You read photos of food nutrition labels and return the values for ONE serving.
Read only what is printed on the image. Never guess a number.

- product_name: the product name as printed.
- serving_size_g: grams in one serving. If the label only gives a per-100 g
  column, the serving is 100 g.
- calories: kilocalories (kcal) per serving. If energy is also given in kJ,
  use the kcal number.
- total_fat_g, total_carbs_g, protein_g: grams per serving.
- sodium_mg: milligrams per serving.
- allergens: lowercase allergen names from the "Contains" statement only.
  A "may contain traces of ..." line is not part of the list.

If a label shows a per-100 g column and a per-serving column, report the
per-serving column."""


@opik.track(name="extract_label", project_name=PROJECT_NAME, ignore_arguments=["image_path", "tags"])
def extract_label(image_path: str | Path, tags: list[str] | None = None) -> NutritionFacts:
    """Attach the label image to the trace, ask gpt-4o-mini for typed fields."""
    path = Path(image_path)
    image_b64 = base64.b64encode(path.read_bytes()).decode()

    # The attachment is the point: the exact pixels the model saw, next to its answer.
    opik_context.update_current_trace(
        input={"image": path.name},
        tags=tags or [],
        attachments=[Attachment(data=str(path), content_type="image/png")],
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract the nutrition facts from this label."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "high"},
                    },
                ],
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "nutrition_facts", "strict": True, "schema": json_schema()},
        },
    )
    return NutritionFacts.model_validate_json(response.choices[0].message.content)
