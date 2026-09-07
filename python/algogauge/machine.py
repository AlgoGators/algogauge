"""Collect machine and git metadata so every benchmark record is attributable."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def git_sha(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "unknown"


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _paranoid() -> int | None:
    try:
        return int(Path("/proc/sys/kernel/perf_event_paranoid").read_text().strip())
    except (OSError, ValueError):
        return None


def collect(repo_root: Path) -> dict:
    return {
        "cpu_model": _cpu_model(),
        "cores": os.cpu_count() or 1,
        "os": platform.platform(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "perf_event_paranoid": _paranoid(),
        "algogauge_sha": git_sha(repo_root),
        "trade_ngin_sha": git_sha(repo_root / "external" / "trade-ngin"),
        "hostname": platform.node() or "unknown",
    }
