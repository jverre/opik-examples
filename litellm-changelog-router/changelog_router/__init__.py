"""Route changelog-writing requests to several LLM providers and compare them in Opik."""

PROJECT_NAME = "litellm-changelog-router"

# One LiteLLM model string per provider. Both ids are priced by Opik, so every
# llm span carries a non-null estimated cost.
MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-haiku-4-5-20251001",
]
