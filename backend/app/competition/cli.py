import argparse
import json
import sys
import time
from pathlib import Path


def main(started_at=None):
    started_at = time.monotonic() if started_at is None else started_at
    parser = argparse.ArgumentParser(description="Mlution AutoResearch: organizer task.md interface")
    parser.add_argument("task", nargs="?", default="task.md", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--time-budget", type=int, default=10800)
    parser.add_argument("--max-experiments", type=int, default=24)
    parser.add_argument("--trial-timeout", type=int, default=1200)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-llm-calls", type=int, default=16)
    parser.add_argument("--max-llm-tokens", type=int, default=24000)
    parser.add_argument(
        "--offline", action="store_true", help="Local heuristic smoke tests; not an LLM agent run"
    )
    args = parser.parse_args()
    from .engine import research

    def emit(stage, message, data=None):
        print(json.dumps({"stage": stage, "message": message, "data": data}, ensure_ascii=False), flush=True)

    try:
        state = research(
            args.task,
            output=args.output,
            seconds=args.time_budget,
            max_experiments=args.max_experiments,
            trial_seconds=args.trial_timeout,
            threads=args.threads,
            seed=args.seed,
            offline=args.offline,
            max_llm_calls=args.max_llm_calls,
            max_llm_tokens=args.max_llm_tokens,
            emit=emit,
            started_at=started_at,
        )
        print(json.dumps({"output": state["output"], "status": state["status"]}), flush=True)
    except Exception as error:
        print(
            f"Mlution: {type(error).__name__}. Check task files, provider configuration and local experiment logs.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
