"""Backwards-compatible entry point. Prefer: uv run algogauge dashboard

The old single-run-folder dashboard (`python dashboard.py results/<suite>/<run-id>/`)
is superseded by the multi-suite, multi-run dashboard that reads history/ + results/
directly. This shim ignores the legacy folder argument (if given) and launches the
new dashboard against the current directory's history/ and results/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from algogauge.dashboard.app import build_app  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        print(
            f"Note: the single-run-folder argument ({sys.argv[1]}) is no longer used -- "
            "the dashboard now reads every run from history/ and results/ directly."
        )
    root = Path.cwd()
    app = build_app(root / "history", root / "results")
    app.run(debug=True)


if __name__ == "__main__":
    main()
