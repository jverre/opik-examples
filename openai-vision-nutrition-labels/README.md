<div align="center">

# Nutrition Label Reader

**`openai-vision-nutrition-labels`**

*The model read the image, and the trace keeps the image next to what it said.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/openai-gpt--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Pillow](https://img.shields.io/badge/pillow-11%2B-3B77A8?style=flat)
[![Opik](https://img.shields.io/badge/Opik-2.2.96-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around) · [How it's put together](#how-its-put-together)**

</div>

---

When a vision model returns `"serving_size_g": 39` for a label that says 38 g, you cannot grep the input to find out why. The input is pixels. You need the exact image the model saw, sitting next to the fields it claimed to read, and you need a test that tells you on every change whether the hard labels still work. This example is a nutrition-label reader on `gpt-4o-mini`: a small Python package draws six fictional labels with Pillow, reads each one into a typed record (serving size, calories, macros, sodium, allergens), attaches the label image to its Opik trace, and runs an Opik test suite over all six, three runs each. One of the six fails, and the failure is real.

## What you'll build

A package, `nutrition_labels/`, with a three-command CLI. `render` draws six labels into `out/labels/` (git-ignored, nothing is committed): three clean ones, and three deliberately hard ones. The hard ones are a granola label with a loud per-100 g column next to a quiet per-serving column, a peanut-cup panel photographed at a 23 degree tilt, and a trail-mix panel in grey ink on grey paper with a blur. `extract <image>` sends one image to `gpt-4o-mini` and prints a validated `NutritionFacts` record: product name, serving size in grams, kcal, fat, carbs, protein, sodium, and the allergens from the "Contains" line (a "may contain traces of peanuts" line must not count). `suite` builds an Opik test suite from the same truth that drew the images, so the pixels and the assertions cannot drift apart, and runs it with `runs_per_item` 3 and a pass threshold of 2.

Tracing is the official OpenAI integration: `track_openai` wraps the client, `@opik.track` wraps `extract_label`, and `opik_context.update_current_trace(attachments=[Attachment(...)])` puts the PNG on the trace. The Opik project is `openai-vision-nutrition-labels`.

## See it in Opik

Open the `openai-vision-nutrition-labels` project and look at the Traces tab. One full run leaves 19 traces: one `extract_label` trace from the `extract` command (tagged `cli`), and 18 `evaluation_task` traces from the suite, three per label, each tagged `suite` and the label name (`05_rotated`, and so on). Open any of them and look at the attachments: the PNG the model received is there, for example `04_dual_column.png` (45 KB, `image/png`), previewable in place. Next to it is the typed output. The attachment is on all 19 traces.

Expand a suite trace and you see the span tree: `task`, then `extract_label` (general), then `chat_completion_create` (llm, model `gpt-4o-mini-2024-07-18`) with token usage and estimated cost. Next to it are the judge's own spans (`llm_judge` and a `completion` llm span), because the suite's assertions are graded by an LLM. Vision is where cost surprises you. Five of the six labels cost 25,893 prompt tokens per call, about $0.0024 each. The smaller grey label (500 by 680 px) costs 14,559 tokens, about $0.0011, because the image is smaller. Image size is a cost knob, and the span shows it per call. The whole run, extractions and judging, comes to about $0.05.

Then open Test Suites, the `openai-vision-nutrition-labels` suite, and its experiment `openai-vision-nutrition-labels-gpt-4o-mini`. It has 6 items and 18 runs, and the pass rate is 83% (5 of 6). Five of the six labels pass 3 of 3 runs, and two of the three hard ones are among them:

- `01_oat_clusters`, `02_lentil_soup` (it correctly leaves peanuts out of the allergens), and `03_seed_crackers` (it takes 250 kcal, not 1046 kJ): 3 of 3.
- `04_dual_column`: 3 of 3. The model reports 30 g, 141 kcal, 5.4 g fat, the per-serving column, even though the 470 and 18 in the per-100 g column are in bigger type. I also removed the prompt sentence about per-serving columns and it still got it right three times out of three, so this trap does not fool `gpt-4o-mini`.
- `06_low_contrast`: 3 of 3. Grey on grey with a blur was readable.
- `05_rotated`: 0 of 3. This is the honest failure. In all three runs the model read the serving size as 39 g, the label says 2 cups (38 g). Everything else on that tilted label (210 kcal, 13 g fat, 21 g carbs, 5 g protein, 115 mg sodium, peanuts, milk, soy) was right. The judge's reason, per run: serving size is 39 in the output, not 38. Because the same wrong digit came back three times, this is a stable misread of one rotated number, not noise, and that is exactly what `runs_per_item` 3 is for.

Opik is not asked to guess whether 39 is close enough. The assertion says 38, so 39 fails. Judged runs vary, so your pass rate may differ.

## Run it yourself

1. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY`, and `OPIK_WORKSPACE` (or run `opik configure`).
2. `uv sync`
3. `uv run nutrition-labels render` (writes six PNGs into `out/labels/`).
4. `uv run nutrition-labels extract out/labels/04_dual_column.png` (prints the typed fields and whether they match the generated truth).
5. `uv run nutrition-labels suite` (about 1 minute and about 5 cents; it renders the labels itself if you skipped step 3).
6. Open the `openai-vision-nutrition-labels` project in Opik, open a trace and its attachment, then open the experiment link printed at the end.

## Poke around

- Open `out/labels/05_rotated.png` next to its trace. Find the "2 cups (38 g)" line at a tilt, and in `render.py` change the rotation in `draw_rotated` from 23 to 10 or 35 to see where the 39 flips to 38 or gets worse.
- In `extract.py` change `"detail": "high"` to `"low"` and re-run `suite`. Prompt tokens fall a lot, and the suite tells you which labels paid for it.
- Make `06_low_contrast` meaner: darken the paper toward the ink in `draw_low_contrast`, or raise the blur radius, and find where grey-on-grey finally breaks.
- Add a seventh label to `LABELS` in `render.py` with its truth dict, for example a label whose serving is "2 tbsp (30 g)". The assertions come from the truth automatically, and suite inserts deduplicate, so re-running only adds the new item.

## How it's put together

- `nutrition_labels/__init__.py`: the project name, the model, and the guard that pins `OPIK_PROJECT_NAME`.
- `nutrition_labels/models.py`: the `NutritionFacts` pydantic model and its strict JSON schema.
- `nutrition_labels/render.py`: Pillow drawing of the six labels, plus the per-serving truth and generated assertions for each.
- `nutrition_labels/extract.py`: the system prompt and the traced `extract_label` call with the image attachment.
- `nutrition_labels/suite.py`: the test suite, its global assertions, and the 3-runs, 2-must-pass execution policy.
- `nutrition_labels/cli.py`: the `render`, `extract`, and `suite` subcommands.
- `.env.example`: the keys the example needs.

---

Part of [Opik Integration Examples](../README.md) · built with [Opik](https://github.com/comet-ml/opik) · ⭐ [star Opik](https://github.com/comet-ml/opik) if this example helped
