<div align="center">

# Podcast Titles, Versioned

**`prompt-library-podcast-titles`**

*Keep the title prompt in the Opik prompt library and test every version: v1 passes 0% of the suite, v2 passes 100%.*

![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenAI SDK](https://img.shields.io/badge/openai-1.0%2B-412991?style=flat&logo=openai&logoColor=white)
[![Opik SDK](https://img.shields.io/badge/Opik%20SDK-2.2%2B-2f54eb?style=flat)](https://github.com/comet-ml/opik)
[![uv](https://img.shields.io/badge/setup-uv-DE5FE9?style=flat&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

**[What you'll build](#what-youll-build) · [See it in Opik](#see-it-in-opik) · [Run it](#run-it-yourself) · [Poke around](#poke-around)**

</div>

---

A prompt is the part of an LLM app that changes most and is tested least. It gets edited in place, and when the output gets worse nobody can say which wording was live. This example takes one small job, writing episode titles for a fictional podcast called Second Draft, and moves its system prompt out of the code and into the Opik prompt library. Every edit becomes an immutable version, Opik shows the diff between versions, and a test suite of plain-language assertions runs against each version so the pass rate tells you whether an edit helped. Here the result is stark: version 1 passes 0% of the suite, version 2 passes 100%.

## What you'll build

A Python package, `podcast_titles`, with a command line called `podcast-titles`. It writes a title for each of six episodes of Second Draft (a podcast about people who left one career for another) using `gpt-4o-mini` and the plain Opik SDK. There are four commands:

- `push --version v1|v2` publishes a prompt version to the library. v1 is "write a catchy, attention-grabbing title". v2 adds explicit rules: a `Guest full name: short phrase` format, 55 characters at most, plain wording with no emoji, exclamation marks, ALL CAPS or clickbait.
- `versions` lists the versions in the library and prints the diff between the last two.
- `title` titles the first three episodes with a given version, so you can see the output without running the whole suite.
- `test` builds a test suite from the episodes and runs it once per version. Each run is an experiment linked to the prompt version it tested.

At run time the app fetches the prompt from the library on every call, so publishing a new version changes its behaviour without a deploy. The version and commit that produced each title are written to the trace metadata.

The suite has three assertions that every title must pass: it is 60 characters or fewer, it contains the guest's full name exactly as written, and it is plain and specific (no emoji, exclamation marks, ALL CAPS or clickbait). Models are flaky and so are judges, so each episode runs three times and counts as passed when at least two runs pass. LLM judges cannot count characters reliably, so the task hands the judge the title's `length_in_characters` alongside the title.

## See it in Opik

Open the `prompt-library-podcast-titles` project in Opik Cloud and start in the prompt library. The prompt `prompt-library-podcast-titles-episode-title` has two versions, v1 (commit `a43e6af6`) and v2 (commit `f2dfbc87`), and the commit diff shows v1's three lines replaced by v2's three bullet rules. Each version is immutable and timestamped, which is the audit trail a prompt string in a Python file never gives you.

Next, open the test suite `prompt-library-podcast-titles-suite` and its experiments, `prompt-library-podcast-titles-v1` and `prompt-library-podcast-titles-v2`. Select both and open the compare view. Each row is one episode (Marguerite Okafor, Tobias Lindqvist, Priya Raghunathan, Dmitri Valcourt, Aoife Brennan, Kwame Asante-Reyes) checked against the same three assertions. v1 passed 0 of 6 episodes and v2 passed 6 of 6. Each experiment also records the prompt version it ran, so the result stays meaningful long after everyone forgets what "the old prompt" said.

The reason for the 0% is visible in the data. Across v1's 18 runs, 16 titles ran past 60 characters (average 71, longest 88: "From Headlines to Harnesses: Kwame's Journey from Sports Journalist to Guide Dog Trainer") and 16 left out the guest's full name, usually writing "Marguerite's Bold Leap into Ceramics" with the first name only. v2's 18 runs averaged 47 characters (longest 57), and every one carried the full name: "Marguerite Okafor: from air traffic to ceramics".

Finally, open the project's Traces tab. The run produced 36 `evaluation_task` traces: 6 episodes, 3 runs each, 2 versions. Each trace contains a `task` span, a `write_title` span, and an `llm` span `chat_completion_create` from `gpt-4o-mini` with token usage and cost, plus the judge's own spans (`llm_judge`, and an `llm` span `completion` for the default judge model). Open any trace's metadata and the `prompt_version` and `prompt_commit` fields tell you which prompt produced that title: 18 traces carry `v1` and 18 carry `v2`.

## Run it yourself

1. `cp .env.example .env` and fill in `OPENAI_API_KEY`, `OPIK_API_KEY` and `OPIK_WORKSPACE` (or run `opik configure` once).
2. `uv sync`
3. `uv run podcast-titles push --version v1`
4. `uv run podcast-titles push --version v2`
5. `uv run podcast-titles versions`
6. `uv run podcast-titles test`

Steps 3 to 6 took about a minute and cost under a cent in LLM calls. The last command prints `v1: 0% pass rate (0/6 episodes passed)` and `v2: 100% pass rate (6/6 episodes passed)`, plus a link to the experiment. The project name is pinned in code to `prompt-library-podcast-titles`, so nothing lands in your default project.

## Poke around

- Edit `V2` in `podcast_titles/prompts.py`, raise the limit to 70 characters and run `push --version v2` again. The library gains a v3 because the text changed, and `test --versions v1 v3` compares it against v1. Identical text never creates a duplicate version.
- Push v1 again while v2 is the latest version. Opik creates a new version with v1's text rather than moving a pointer, which is what a rollback looks like in an immutable history.
- Run `uv run podcast-titles title --version v1`, then `--version v2`, to see the difference without the suite.
- Drop the "never possessive" rule from v2 and watch the full-name assertion start to fail on titles like "Tobias Lindqvist's journey".
- Add an episode to `data/episodes.json` and re-run `test`. The suite inserts only items it does not already hold.

## How it's put together

- `podcast_titles/config.py`: project, prompt and suite names; pins the Opik project before anything else loads.
- `podcast_titles/prompts.py`: the v1 and v2 prompt text that `push` publishes, with change descriptions.
- `podcast_titles/writer.py`: `write_title`, which fetches a prompt version from the library, calls `gpt-4o-mini` through `track_openai`, and tags the trace with the version and commit.
- `podcast_titles/suite.py`: the test suite, its three assertions, the three-runs execution policy, and the per-version `run_tests` call.
- `podcast_titles/cli.py`: the `push`, `versions`, `title` and `test` commands.
- `data/episodes.json`: six fictional episodes of Second Draft.
