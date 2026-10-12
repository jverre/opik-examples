<div align="center">

# Board-Game Card Art with Managed Briefs

**`openai-image-boardgame-cards`**

*Two versions of an art brief, four generated card illustrations, every PNG attached to its Opik trace.*

</div>

---

Image pipelines have a version-control problem text pipelines don't: the output is a picture, so you can't grep it. A designer writes "Board game creature card: Lantern Fox" and gets back a whole mocked-up card, with a parchment border and a banner of fake lettering that collides with the real frame and title bar the layout tool adds later. Someone rewrites the brief, assets pile up in a folder, and weeks later nobody can say which wording produced which file. This example is a small card-art generator for a fictional cooperative game, Emberwick Hollow, written in TypeScript on the OpenAI SDK. The brief lives in the Opik prompt library with two versions, every image is one trace with the PNG attached, and a vision check scores each picture so the v1 to v2 improvement shows up as numbers, not an argument.

## What you'll build

A generator for two cards of Emberwick Hollow: a creature card, "Lantern Fox", and a location card, "Moss Bridge". The art brief is registered in the Opik prompt library as `openai-image-boardgame-cards-art-brief`, twice. v1 is what a designer types on day one: the card, the subject, the mood. v2 keeps that and adds art direction: flat gouache style, artwork only (no frame, banner or title bar), no text of any kind, a centered subject with empty space at the top. The demo fetches each version from the library, renders it with Mustache variables, and calls `images.generate` with `gpt-image-1-mini` (low quality, 1024x1024) on an OpenAI client wrapped with `trackOpenAI` from `opik-openai`. That is four images, two cards times two versions.

Each image gets one `generate-card-art` trace. The PNG goes into the trace output as a base64 data URI and the Opik SDK uploads it as a real attachment, with no extra code. Then a `guardrail` span, `art-only-check`, sends the image to `gpt-4o-mini` with a short instruction ("any lettering? any drawn card frame?") and the result is logged as an `art-only` feedback score on the trace: 1 for clean artwork, 0 for stray text or a drawn frame. PNGs are also saved to `out/` (git-ignored).

## See it in Opik

Open the `openai-image-boardgame-cards` project in Opik.

**Traces tab.** Four traces named `generate-card-art`, each tagged with its brief version (`v1` or `v2`) and the card id. Add the `art-only` column. In the verified run both v1 traces scored `0.0` and both v2 traces scored `1.0`. Filter by tag `v1` and you get exactly the images that came back wrong.

**One trace, open.** The input holds the card name, type and the fully rendered brief. The metadata pins `prompt_name`, `prompt_version` (`v1` or `v2`) and `prompt_id`. In the attachments area there is one PNG, between 1.2 MB and 1.9 MB, and clicking it shows the actual card art. Compare the two Lantern Fox traces: the v1 image is a full card mock-up with a cream parchment border and a scroll banner across the top filled with garbled lettering; the v2 image is clean, flat gouache artwork of the fox with its lantern and no frame. The `art-only` score on the v1 trace carries its reason text, `has_text=true, has_card_frame=true`.

**Span shape.** Each trace has three spans: `images.generate` (model `gpt-image-1-mini`, around 50 to 150 input tokens depending on the brief version, 272 output image tokens), `art-only-check` of type `guardrail` holding the verdict as its output, and a `vision-check` span under it for the `gpt-4o-mini-2024-07-18` call (about 2,900 tokens, mostly the image, roughly $0.00046 each). The v2 `images.generate` spans show about 146 input tokens against 53 for v1, because the art direction is longer. Note that the estimated cost on image spans (about $0.0001 to $0.0003) only counts the tokens the Images API reports; actual image billing is higher, on the order of a cent or less per low-quality image.

**Another v1 image.** The v1 Moss Bridge came back with "MOSS BRIDGE" in large letters across the top and a parchment margin on both sides. The v2 Moss Bridge is a lantern-lit stone bridge over a stream with no lettering. Image models are nondeterministic, so your v1 images will fail in different ways, and sometimes a v1 image comes back clean. In earlier runs while building this example, the v1 Lantern Fox once came back with no text or frame and scored `1.0`. That is the point of scoring every image instead of eyeballing one.

**Prompt library.** Open the Prompt library and find `openai-image-boardgame-cards-art-brief`. It has two versions with change descriptions. Compare v1 to v2: the diff shows six added lines (a blank line, the "Art direction" heading and its four bullets) and nothing removed. The demo also prints the same diff in the terminal using `compareTo`. Versions are immutable and timestamped, so the diff doubles as the campaign's change log, and the trace metadata tells you which version produced which image.

**The checker is a model too.** `gpt-4o-mini` at low image detail is a cheap, mostly reliable judge of "is there lettering", but it can miss small glyphs and its `note` text is sometimes bland. Treat the score as a triage signal and look at the attachment when it matters.

## Run it yourself

1. Install dependencies (Node 20+): `npm install`. The `.npmrc` sets `legacy-peer-deps=true` because `opik-openai@2.2.96` still declares a peer range of `opik@^1.8.61`, which excludes `opik@2.x`.
2. Copy the env file and fill it in: `cp .env.example .env`, then export the variables in your shell (for example `set -a; source .env; set +a`). Opik Cloud needs `OPIK_API_KEY`, `OPIK_WORKSPACE` and `OPIK_URL_OVERRIDE`; the OpenAI key goes in `OPENAI_API_KEY`. The demo also reads `.env` itself if present.
3. Make sure traces go to the right project: `export OPIK_PROJECT_NAME=openai-image-boardgame-cards`. If you have a default project in `~/.opik.config`, this overrides it.
4. Run the demo: `npm run demo`. It takes about 45 seconds and costs a few cents (four low-quality images and four vision checks).
5. Open the `openai-image-boardgame-cards` project in Opik and check the Traces tab, then the Prompt library.

The first run registers the prompt. Later runs reuse it, so you will not get a spurious v3.

## Poke around

- Add a v3 in `src/prompts.ts`, for example "limited palette of three colors" or a rule about the empty top fifth, delete the prompt in the library, re-run, and compare the `art-only` column and the attachments across three versions.
- Add a third card to `CARDS` (say an item card, "Brass Compass") and see whether v1 invents a frame again. Does the verdict change from run to run for the same brief?
- Tighten the checker in `checkArt`: ask it to also flag "photorealistic" images, log a second score, and see whether the v2 style rule holds across cards.
- Open one `images.generate` span and read the usage. Image output is billed in tokens, and the trace records them per generation, so you can chart image cost per brief version.

## How it's put together

- `src/main.ts`: registers the two brief versions, prints the diff, generates the four images with `trackOpenAI`, attaches each PNG to its trace, runs the vision guardrail and logs the `art-only` score.
- `src/prompts.ts`: the two brief templates, the change description for v2, the fictional game and the two cards.
- `.npmrc`: `legacy-peer-deps=true` for the stale `opik-openai` peer range.
- `.env.example`: the keys the demo reads. Generated images land in `out/`, which is git-ignored.
