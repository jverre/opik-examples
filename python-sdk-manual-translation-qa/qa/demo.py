"""Run the Tidepool strings through the translation QA pipeline and flush."""

from __future__ import annotations

import time

from qa.pipeline import MODEL, PROJECT, SHIP_THRESHOLD, check_string, client
from qa.strings import STRINGS


def main() -> None:
    print(f"Checking {len(STRINGS)} strings with {MODEL} (ship threshold {SHIP_THRESHOLD})...\n")
    started = time.time()

    for item in STRINGS:
        r = check_string(item)
        print(f"[{r['verdict'].upper():6}] {r['id']} {r['source']} -> {r['target']}  meaning={r['score']:.2f} lexical={r['lexical']:.2f}")
        print(f"         {r['text']}")
        print(f"         {r['translation']}")
        print(f"         back: {r['back_translation']}")
        if r["verdict"] == "review":
            print(f"         drift: {r['drift']}")

    # The SDK batches traces, spans and scores in memory and sends them from a
    # background thread. flush() blocks until everything is delivered. Call it
    # before exit in any short-lived process (scripts, cron jobs, serverless
    # handlers): see flush_demo.py for what happens when you don't.
    client.flush()

    print(f"\nDone in {time.time() - started:.0f}s. Open the \"{PROJECT}\" project in Opik: one trace per string.")


if __name__ == "__main__":
    main()
