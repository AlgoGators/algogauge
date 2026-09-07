from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_wsl.sh"


def test_setup_script_exists_and_is_strict_bash():
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    for pkg in (
        "build-essential",
        "cmake",
        "libeigen3-dev",
        "nlohmann-json3-dev",
        "libpqxx-dev",
        "libnlopt-cxx-dev",
        "libgtest-dev",
        "libbenchmark-dev",
        "libcurl4-openssl-dev",
        "libarrow-dev",
    ):
        assert pkg in text, pkg
    assert "astral.sh/uv/install.sh" in text
    assert "perf_event_paranoid" in text
    assert "\r" not in text, "must use LF line endings for bash"
