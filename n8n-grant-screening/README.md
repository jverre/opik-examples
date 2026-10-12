<div align="center">

# Grant Screening in n8n

**`n8n-grant-screening`**

*A no-code LLM workflow that decides fund, review, or decline, traced in Opik without a line of instrumentation.*

[![n8n](https://img.shields.io/badge/n8n-2.42.7-ea4b71?style=flat)](https://n8n.io)
![model](https://img.shields.io/badge/model-gpt--4o--mini-10a37f?style=flat)
[![n8n-observability](https://img.shields.io/badge/n8n--observability-1.0.3-2f54eb?style=flat)](https://github.com/comet-ml/n8n-observability)
[![setup](https://img.shields.io/badge/setup-docker-blue?style=flat)](https://docs.docker.com/compose/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around) · [How it's put together](#how-its-put-together)**

</div>

---

A program officer at a small arts foundation opens the inbox on Monday and finds forty grant applications. Someone on the team builds an n8n workflow so a language model can do the first pass: read the application, check it against the foundation's criteria, and answer fund, review, or decline. It ships in an afternoon, and nobody wrote any code. Three weeks later an applicant asks why they were declined, and nobody can say what the model was asked, what it answered, or whether a rule on the canvas overrode it. This example is that workflow, for a fictional funder called the Lantern Arts Foundation. Every application becomes one trace in Opik, and the workflow itself was never changed to make that happen.

## What you'll build

A self-hosted n8n instance in Docker with a four-node workflow: **Application webhook, Screen application (gpt-4o-mini), Apply funding cap, Respond**. You POST an application (`applicant`, `project_title`, `amount_requested`, `summary`, `budget_notes`) to the webhook. The model scores it against the foundation's eligibility rules and priorities and returns a JSON verdict with `decision`, `reason`, and `criteria_met`. A Set node then applies one business rule the model is not trusted with: any `fund` verdict above the 15,000 USD single-grant cap is downgraded to `review`. The caller gets back both the model's verdict (`model_decision`) and the final one (`decision`).

The Opik side needs no nodes and no code. The Dockerfile installs the [`n8n-observability`](https://github.com/comet-ml/n8n-observability) package and points n8n's `EXTERNAL_HOOK_FILES` at its OpenTelemetry hooks. From then on every execution is a trace and every node is a span, exported over OTLP to Opik. The `projectName` header in `docker-compose.yml` routes them into the `n8n-grant-screening` project. The workflow is not clicked together by hand either: `setup.sh` creates the owner account, mints an n8n API key, creates the OpenAI credential from your environment, and imports and activates `workflow/grant-screening.json` through the n8n API. A fresh clone goes from nothing to a live, traced workflow with no browser.

## See it in Opik

Open the `n8n-grant-screening` project in Opik Cloud. After `./demo.sh` it holds exactly four traces, all named `Grant application screening`, each 1.2 to 1.6 seconds long and each with five spans: the root workflow span `Grant application screening` plus one span per node (`Application webhook`, `Screen application (gpt-4o-mini)`, `Apply funding cap`, `Respond`).

Open any trace and then the `Screen application (gpt-4o-mini)` span. Its input holds the whole system prompt (all 1,444 characters of eligibility rules, priorities, and decision rules) under `n8n.node.parameters.messages.values.0.content`. It also holds the application as the model received it under `n8n.node.input`, and the model's JSON answer under `n8n.node.output`. For the Saturday Mural Lab application that answer is `fund`, with the reason "strong on community access and support for emerging artists" and three entries in `criteria_met`. This is what the canvas normally swallows. When an applicant asks why they were declined, the answer is on this span.

The four runs are chosen so the traces differ in ways you can read:

- **Saturday Mural Lab** (9,000 USD): the model says `fund`, the final decision is `fund`.
- **Harbour Street Players** (22,000 USD): the model says `fund`, but open the `Apply funding cap` span and its output shows `model_decision: fund` next to `decision: review`, with a reason that starts "Over the 15,000 USD single-grant cap". A rule on the canvas changed the outcome, and the trace is the only place both values sit side by side.
- **Tidepool Collective** (12,000 USD): `review` from the model, because the plan is "a big art thing" with a budget of "materials, some fees, and a bit for marketing".
- **Fennick Brand Studio** (7,500 USD): `decline`, because it asks the foundation to reimburse a printing bill that was already paid.

Three things Opik does not show for this example, and they are worth knowing before you go looking. First, every span has type `general` except one, and the one is `Respond`. The hooks put `gen_ai.request.model` on whichever node receives an item that has a `model` field, which here is the last node (the Set node's output carries `"model": "gpt-4o-mini"`). So Opik shows the model name `gpt-4o-mini` and type `llm` on `Respond`, not on the `Screen application` span that actually called the model. This is a known quirk of the upstream package, not something this workflow does wrong. Second, there are no token counts and no cost: n8n's OpenAI node does not hand its usage numbers to the hooks, so the usage and cost columns stay empty. Third, the trace-level Output column in the traces table is empty too, because the hooks put each node's result on its own span, not on the trace; open the `Apply funding cap` or `Respond` span to see the verdict. What you get is the prompt, the input, the verdict, and the timing of every step.

## Run it yourself

Requires Docker, `curl`, and `python3`. An Opik API key, your Opik workspace name, and an OpenAI key.

1. `cp .env.example .env` and fill in `OPIK_API_KEY`, `OPIK_WORKSPACE`, and `OPENAI_API_KEY`. Or export those three in your shell. For self-hosted Opik also set `OPIK_URL_OVERRIDE` to its API URL, reachable from inside the container (untested here; the verified run used Opik Cloud).
2. `./setup.sh` builds the image, starts n8n on `localhost:4280`, creates the owner account and the OpenAI credential, and imports and activates the workflow. It takes about 1.5 minutes the first time (the image build) and is safe to run again.
3. `./demo.sh` sends the four applications, prints each verdict, and waits until four new traces appear in Opik.
4. Open the `n8n-grant-screening` project in Opik and click the newest trace.

The one-liner is `./setup.sh && ./demo.sh`. In the verified run it took about 29 seconds with a warm image cache, and the four model calls cost well under one cent.

Stop the container with `docker compose stop` and start it again with `docker compose up -d` (the workflow stays active). `docker compose down -v` removes the container and the n8n data volume.

The n8n UI is at `http://localhost:4280`, login `demo@example.com` / `GrantScreen-demo-1`. That account exists only inside your local container.

## Poke around

- **Send your own application.** `curl -X POST localhost:4280/webhook/grant-screening -H 'Content-Type: application/json' -d '{"applicant":"...","project_title":"...","amount_requested":5000,"summary":"...","budget_notes":"..."}'`, then find it in Opik and check whether you agree with the reason.
- **Move the cap.** In the n8n UI, open `Apply funding cap` and change `15000` in the `decision` and `reason` expressions (the two assignments that contain it) to `25000`. Re-send the Harbour Street Players application and compare the two traces: the model's answer is identical, only the final decision differs.
- **Try to fool the screener.** Send a commercial brand dressed up as a community project ("a free public festival that happens to feature our new product line") and read the `reason` on the `Screen application` span to see which criterion it keyed on.
- **Keep applicant data out of Opik.** Applications are personal data. Add `N8N_OTEL_CAPTURE_INPUT: "false"` and `N8N_OTEL_CAPTURE_OUTPUT: "false"` to the `environment` block in `docker-compose.yml`, run `docker compose up -d`, and send one more application. The trace still shows the span tree and timings, but the payloads are gone. `N8N_OTEL_NODE_EXCLUDE=Respond` drops a noisy node instead.

## How it's put together

- `setup.sh`: headless bootstrap. Compose up, owner setup, n8n API key, OpenAI credential from the environment, import and activate the workflow through the n8n API.
- `demo.sh`: sends four fictional applications to the live webhook, then polls Opik until their traces arrive.
- `workflow/grant-screening.json`: the exported workflow, with the credential ID left as a placeholder that `setup.sh` fills in at import time.
- `Dockerfile`: the official `n8nio/n8n` image plus `npm install -g n8n-observability`, with `EXTERNAL_HOOK_FILES` pointing at its hooks.
- `docker-compose.yml`: compose project `n8n-grant-screening`, host port 4280 mapped to 5678, its own volume, and the OTLP endpoint, auth header, and Opik project name.
- `.env.example`: the three keys the scripts read. `.env` is git-ignored.
