"""Load and validate algogauge.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

KINDS = ("gbench", "script")


class ManifestError(ValueError):
    """Raised when algogauge.toml is malformed."""


@dataclass(frozen=True)
class Defaults:
    repetitions: int = 20
    min_time: str = "2s"
    perf: bool = True
    regression_threshold_pct: float = 10.0


@dataclass(frozen=True)
class Suite:
    name: str
    kind: str
    binary: str | None
    script: str | None
    args: tuple[str, ...]
    repetitions: int
    min_time: str
    perf: bool


@dataclass(frozen=True)
class Manifest:
    defaults: Defaults
    suites: tuple[Suite, ...]

    def get(self, name: str) -> Suite:
        for s in self.suites:
            if s.name == name:
                return s
        raise ManifestError(f"unknown suite '{name}'")


def _suite(raw: dict, d: Defaults) -> Suite:
    if "name" not in raw:
        raise ManifestError("[[benchmark]] requires 'name'")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise ManifestError(f"suite '{raw['name']}': kind must be one of {KINDS}")
    if kind == "gbench" and "binary" not in raw:
        raise ManifestError(f"suite '{raw['name']}': kind=gbench requires 'binary'")
    if kind == "script" and "script" not in raw:
        raise ManifestError(f"suite '{raw['name']}': kind=script requires 'script'")
    return Suite(
        name=raw["name"],
        kind=kind,
        binary=raw.get("binary"),
        script=raw.get("script"),
        args=tuple(str(a) for a in raw.get("args", [])),
        repetitions=int(raw.get("repetitions", d.repetitions)),
        min_time=str(raw.get("min_time", d.min_time)),
        perf=bool(raw.get("perf", d.perf)),
    )


def load(path: Path) -> Manifest:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    d = Defaults(**data.get("defaults", {}))
    suites = tuple(_suite(r, d) for r in data.get("benchmark", []))
    names = [s.name for s in suites]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise ManifestError(f"duplicate suite name(s): {sorted(dupes)}")
    return Manifest(defaults=d, suites=suites)
