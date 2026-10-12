"""Opik tracing setup: LiteLLM's OpikLogger callback plus a flush helper."""

import logging
import os
import warnings

import opik

from changelog_router import PROJECT_NAME


def setup_tracing() -> None:
    """Pin the Opik project, then register LiteLLM's Opik callback.

    The project must be set before OpikLogger is created, because the callback
    reads OPIK_PROJECT_NAME once at construction time.
    """
    os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

    import litellm
    from litellm.integrations.opik.opik import OpikLogger

    # In a plain script (no event loop) OpikLogger logs a harmless "no running
    # event loop" error while it falls back to synchronous sending. Hide it.
    litellm_logger = logging.getLogger("LiteLLM")
    previous_level = litellm_logger.level
    litellm_logger.setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore", message=".*periodic_flush.*", category=RuntimeWarning)
    litellm.callbacks = [OpikLogger()]
    litellm_logger.setLevel(previous_level)


def flush() -> None:
    """Wait until every trace and span has been sent to Opik."""
    opik.flush_tracker()
