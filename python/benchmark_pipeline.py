"""Backwards-compatible entry point. Prefer: uv run algogauge run <suite>."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from algogauge.manifest import Defaults, Suite  # noqa: E402
from algogauge.runner import run_suite  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: benchmark_pipeline.py <benchmark_binary> [--skip-perf]")
        sys.exit(1)
    binary = Path(sys.argv[1])
    if not binary.exists():
        print(f"Error: binary not found: {binary}")
        sys.exit(1)
    root = Path.cwd()
    suite = Suite(
        name=binary.name,
        kind="gbench",
        binary=str(binary.relative_to(root) if binary.is_absolute() else binary),
        script=None,
        args=(),
        repetitions=30,
        min_time="5s",
        perf=True,
    )
    run_suite(suite, Defaults(), root, skip_perf="--skip-perf" in sys.argv[2:])


if __name__ == "__main__":
    main()
