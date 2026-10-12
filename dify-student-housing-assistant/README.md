# Student Housing Assistant in Dify

**`dify-student-housing-assistant`**

*A housing-office chatbot nobody wrote code for, fully traced in Opik.*

---

Some of the most-used LLM apps are never written in Python or TypeScript. A housing coordinator assembles a resident assistant in Dify's studio, pastes in the handbook, and the bot starts answering students about broken heaters and guest rules. There is no application code, so there is nowhere to add an SDK call, and that is usually where observability stops. This example shows it doesn't have to. It builds a front-desk assistant for Larkspur University Housing (a fictional university with four residence halls) in Dify and turns on Opik tracing with one platform setting, written here through Dify's own console API so the whole thing is headless and repeatable.

## What you'll build

A self-hosted Dify stack (release 1.17.1, config vendored in `dify-docker/`) running a chat app imported from a committed DSL file, so the app is reproducible rather than click-built. The app's whole "source" is a system prompt that carries a condensed housing handbook: room assignments, maintenance response times, move-in and move-out rules, and the guest policy. gpt-4o-mini answers from it, and anything off-handbook is redirected to the housing office. `setup.sh` does what the Dify UI would do through the console API: creates the admin account, installs the OpenAI provider plugin, stores your key, imports the app, then writes the Opik tracing config and enables it. `demo.sh` asks three resident questions through Dify's service API in one conversation, the way a housing portal widget would.

```
resident question ──► Dify service API ──► gpt-4o-mini ──► answer
                           │
                           └──► Opik: trace + llm span + token usage, grouped by conversation
```

## See it in Opik

Open the `dify-student-housing-assistant` project in the workspace you configured. After one `./demo.sh` it holds 4 traces and 1 thread.

- **Traces tab.** Three traces named `message`, one per resident question, each with a single span named `llm` (type `llm`). The trace input is the full prompt Dify assembled: the system prompt with the whole handbook, then the conversation history and the new question. The output is the answer, for example "For no heat in winter, someone will respond within 2 hours. Please call the 24-hour maintenance line at 555-0142". You configured nothing in code, yet you can open any answer and see exactly what context the model had.
- **Usage columns.** The `llm` span carries token usage. In the verified run the three turns used 983, 1049 and 1136 prompt tokens (and 34, 45 and 36 completion tokens). The prompt grows by roughly 60 to 90 tokens a turn because Dify attaches the history: the quiet cost driver of every chat app, visible per turn with no instrumentation work.
- **Threads tab.** Dify forwards its conversation id as the Opik thread id, so all four traces sit in one thread (the id printed at the end of `./demo.sh`) and read as a single transcript.
- **The fourth trace, `generate_conversation_name`.** A small trace with one `general` span: Dify's own housekeeping call that asks the model to title the chat ("Alder Hall Heating: Who to Call and How Soon?"). Platform-level tracing catches LLM calls you didn't know your platform was making.
- **Metadata.** Each trace carries Dify's `conversation_id`, `message_id`, `app_id`, `ls_provider` (`langgenius/openai/openai`) and `ls_model_name` (`gpt-4o-mini`), so you can jump from a bad trace back to the exact conversation in Dify.

Honest limits. Dify puts the model name in metadata rather than on the span's `model` field, so Opik does not compute a dollar cost for these spans; you get token counts, not cost. The `demo.sh` output also prints the token counts Dify reports, which match what Opik shows.

## Run it yourself

1. Install Docker and have Python 3 on the path (the scripts use only the standard library). `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (or export them; `~/.opik.config` from `opik configure` also works for the Opik ones). Do not commit `.env`.
2. `./setup.sh` starts the stack on `http://localhost:4290` and configures it end to end. The first run pulls images, so allow a few minutes.
3. `./demo.sh` asks the assistant three questions.
4. Open the `dify-student-housing-assistant` project in Opik and click the newest trace.

Stop and restart: `docker compose -p dify-student-housing-assistant stop` keeps the data, `docker compose -p dify-student-housing-assistant start` brings it back. To delete the stack and its databases: `docker compose -f dify-docker/docker-compose.yaml --project-directory dify-docker down -v`, then remove the local data folders under `dify-docker/volumes/` (except `sandbox/`); `./setup.sh` rebuilds everything from scratch in about a minute once the images are pulled. The Dify login is `admin@larkspur.example` / `LarkspurHousing2026`, local defaults you can override in `.env`.

Ports used: 4290 (Dify web and API), 4291 (HTTPS, unused), 4292 and 4293 (plugin daemon). Override `DIFY_PORT` and `DIFY_SSL_PORT` before the first `./setup.sh` if they collide.

Note for self-hosted Opik: Dify runs inside Docker, so point `OPIK_URL_OVERRIDE` at an address the containers can reach (for example `http://host.docker.internal:5173/api/`). Dify requires the URL to end in `/api/`; `configure_dify.py` adds the trailing slash if it is missing.

## Poke around

- Ask something the handbook doesn't cover in the Dify chat preview at `http://localhost:4290` ("can I get my deposit back early because I hate my roommate?") and check in the trace that the bot redirects to housing@larkspur.example instead of inventing a policy.
- Edit the handbook in the Dify studio (it is just the system prompt), change the overnight-guest limit from 3 nights to 2, ask the guest question again, and compare the two traces side by side in Opik.
- Open `app/larkspur-housing-assistant.yml`: that one file is the entire app. Change the model to `gpt-4.1-mini` and re-run `./setup.sh` on a fresh stack to compare token counts and latency per answer.
- Ask a long conversation of ten questions in the chat preview and watch the prompt-token count climb turn by turn in the thread.

## How it's put together

- `setup.sh` is the idempotent entry point: writes the Docker env overrides, starts compose, then hands off to the configurator.
- `configure_dify.py` does everything the Dify UI would, through the console API (admin account, OpenAI plugin, credential, app import, Opik tracing config, service API key). Standard library only.
- `demo.sh` asks three resident questions through Dify's service API, in one conversation.
- `app/larkspur-housing-assistant.yml` is the app as Dify DSL: prompt, handbook, model, settings.
- `dify-docker/` holds Dify 1.17.1's official compose file and config, vendored so the stack is pinned. `setup.sh` creates its `.env` from `env.example` on first run.
- `.env.example` lists the keys the setup needs.
