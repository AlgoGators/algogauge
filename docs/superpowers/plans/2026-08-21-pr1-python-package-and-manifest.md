# PR 1 — Python Package, Manifest, History & Runner — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn algogauge's two loose scripts into a manifest-driven `algogauge` Python package with a committed run history, regression comparison, and the two top-level notebooks — while the two existing C++ suites keep working unchanged.

**Architecture:** A small package under `python/algogauge/` with one module per responsibility (manifest → gbench parsing → machine info → history → compare → runner → cli). The runner replaces `benchmark_pipeline.py` (kept as a one-line shim), runs any Google Benchmark binary or script declared in `algogauge.toml`, writes raw artefacts to gitignored `results/`, and appends one compact JSON line per benchmark to tracked `history/<suite>.jsonl`. Notebooks only call the package.

**Tech Stack:** Python 3.12 (`tomllib` stdlib), `uv`, `pytest`, `nbformat`, Google Benchmark JSON, Linux `perf` + FlameGraph (optional via `--skip-perf`).

**Spec:** `docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md` — sections 2, 3.4, 4, 5, 7 (notebooks 00/01), 9, 10.

## Global Constraints

- Python `>=3.12` (already in `pyproject.toml`); use stdlib `tomllib`, no `toml`/`tomli` dependency.
- Google Benchmark defaults: `repetitions = 20`, `min_time = "2s"`; the runner passes `--benchmark_display_aggregates_only=true` (NOT `report_aggregates_only`) so per-repetition rows reach the JSON.
- Regression threshold default `10` (% on median). A run is `valid = false` if `cv_pct > 15`.
- `results/` stays gitignored; `history/` is tracked.
- All work on branch `feat/python-package-and-manifest`, based on `main`, in the algogauge clone at `C:/Users/johnp/AppData/Local/Temp/claude/C--Users-johnp--gemini-antigravity-scratch-AlgoGators-New-Algo-Xander-Sex-trade-ngin/05341f07-106d-4026-9c7d-a139eaf2cb86/scratchpad/algogauge`. Commits use `-c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com"` and end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Tests run on Windows (this machine) without WSL: run with `PYTHONPATH=python python -m pytest tests/ -q` (uv/WSL come later). Anything that shells out to `perf` or a binary is mocked or skipped on Windows.
- Existing behaviour preserved: `uv run python/benchmark_pipeline.py <binary>` still works (delegates to runner).

---

## File structure

| Path | Responsibility |
|---|---|
| `algogauge.toml` | Declares suites (spec §4). |
| `python/algogauge/__init__.py` | Version string only. |
| `python/algogauge/manifest.py` | Parse/validate `algogauge.toml` → `Manifest(defaults, suites)`. |
| `python/algogauge/gbench.py` | Parse a Google Benchmark JSON file → per-benchmark stats (median/p95/p99/mean/stddev/cv). |
| `python/algogauge/machine.py` | Collect machine + git metadata dict. |
| `python/algogauge/history.py` | `Record` dataclass; append/load `history/<suite>.jsonl`. |
| `python/algogauge/compare.py` | Compare two sets of records; regression detection; table rendering. |
| `python/algogauge/runner.py` | Run one suite (gbench binary or script) → results dir + history records; perf/flamegraph stages. |
| `python/algogauge/cli.py` | `algogauge list | run | compare` argparse entry point. |
| `python/benchmark_pipeline.py` | Backwards-compatible shim → `runner`. |
| `scripts/setup_wsl.sh` | Idempotent WSL2 Ubuntu toolchain install (spec §9). |
| `scripts/build_notebooks.py` | Generates `notebooks/00_setup_wsl.ipynb` and `01_run_all_benchmarks.ipynb` with `nbformat`. |
| `notebooks/*.ipynb` | Generated, committed. |
| `history/.gitkeep` | Tracked history dir. |
| `tests/test_*.py` | pytest per module. |

---

### Task 1: Package skeleton, pyproject, test harness

**Files:**
- Create: `python/algogauge/__init__.py`
- Modify: `pyproject.toml`
- Create: `tests/__init__.py` (empty), `tests/conftest.py`
- Create: `history/.gitkeep`

**Interfaces:**
- Produces: importable package `algogauge` (via `PYTHONPATH=python` locally; via hatchling wheel under `uv`), `algogauge.__version__`.

- [ ] **Step 1: Create branch**

```bash
cd "C:/Users/johnp/AppData/Local/Temp/claude/C--Users-johnp--gemini-antigravity-scratch-AlgoGators-New-Algo-Xander-Sex-trade-ngin/05341f07-106d-4026-9c7d-a139eaf2cb86/scratchpad/algogauge"
git checkout main && git pull -q && git checkout -b feat/python-package-and-manifest
```

- [ ] **Step 2: Write the failing test**

`tests/test_package.py`:
```python
def test_package_importable():
    import algogauge
    assert algogauge.__version__ == "0.3.0"
```

- [ ] **Step 3: Run it — expect ImportError**

Run: `PYTHONPATH=python python -m pytest tests/test_package.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'algogauge'`

- [ ] **Step 4: Create package + conftest**

`python/algogauge/__init__.py`:
```python
"""AlgoGauge - benchmarking and profiling suite for trade-ngin."""

__version__ = "0.3.0"
```

`tests/conftest.py`:
```python
import sys
from pathlib import Path

# Make `python/` importable without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
```

`tests/__init__.py`: empty file. `history/.gitkeep`: empty file.

- [ ] **Step 5: Update pyproject.toml**

Replace the `[project]` block and add build/packaging config so `uv run algogauge` works later:
```toml
[project]
name = "algogauge"
version = "0.3.0"
description = "Benchmarking and profiling suite for trade-ngin"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "dash>=4.1.0",
    "matplotlib>=3.10.8",
    "numpy>=2.4.3",
    "pandas>=3.0.2",
    "plotly>=6.6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "nbformat>=5.10", "jupyterlab>=4.0", "ipykernel>=6.29"]

[project.scripts]
algogauge = "algogauge.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["python/algogauge"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "$version"
version_scheme = "semver2"
version_provider = "uv"
update_changelog_on_bump = true
major_version_zero = true
```

- [ ] **Step 6: Run test — expect PASS**

Run: `python -m pytest tests/test_package.py -q`
Expected: `1 passed`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml python/algogauge/__init__.py tests/__init__.py tests/conftest.py tests/test_package.py history/.gitkeep
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "build: create algogauge python package skeleton and pytest harness

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Manifest loader

**Files:**
- Create: `python/algogauge/manifest.py`, `algogauge.toml`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True) class Defaults: repetitions:int=20; min_time:str="2s"; perf:bool=True; regression_threshold_pct:float=10.0
  @dataclass(frozen=True) class Suite: name:str; kind:str  # "gbench"|"script"
                                       binary:str|None; script:str|None; args:tuple[str,...]; repetitions:int; min_time:str; perf:bool
  @dataclass(frozen=True) class Manifest: defaults:Defaults; suites:tuple[Suite,...]; def get(self,name)->Suite
  def load(path: Path) -> Manifest
  class ManifestError(ValueError)
  ```

- [ ] **Step 1: Write failing tests**

`tests/test_manifest.py`:
```python
from pathlib import Path
import pytest
from algogauge import manifest


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "algogauge.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_applies_defaults_and_overrides(tmp_path):
    p = write(tmp_path, """
[defaults]
repetitions = 7
min_time = "1s"

[[benchmark]]
name = "a"
kind = "gbench"
binary = "build/a"

[[benchmark]]
name = "b"
kind = "script"
script = "python/b.py"
args = ["--x", "1"]
perf = false
repetitions = 3
""")
    m = manifest.load(p)
    assert m.defaults.repetitions == 7
    assert m.defaults.regression_threshold_pct == 10.0
    a, b = m.suites
    assert (a.name, a.kind, a.binary, a.repetitions, a.min_time, a.perf) == ("a", "gbench", "build/a", 7, "1s", True)
    assert (b.kind, b.script, b.args, b.perf, b.repetitions) == ("script", "python/b.py", ("--x", "1"), False, 3)
    assert m.get("b") is b


def test_get_unknown_raises(tmp_path):
    m = manifest.load(write(tmp_path, '[[benchmark]]\nname="a"\nkind="gbench"\nbinary="x"\n'))
    with pytest.raises(manifest.ManifestError, match="unknown suite 'zzz'"):
        m.get("zzz")


@pytest.mark.parametrize("body,msg", [
    ('[[benchmark]]\nname="a"\nkind="gbench"\n', "requires 'binary'"),
    ('[[benchmark]]\nname="a"\nkind="script"\n', "requires 'script'"),
    ('[[benchmark]]\nname="a"\nkind="weird"\nbinary="x"\n', "kind must be"),
    ('[[benchmark]]\nkind="gbench"\nbinary="x"\n', "requires 'name'"),
    ('[[benchmark]]\nname="a"\nkind="gbench"\nbinary="x"\n[[benchmark]]\nname="a"\nkind="gbench"\nbinary="y"\n', "duplicate suite name"),
])
def test_validation_errors(tmp_path, body, msg):
    with pytest.raises(manifest.ManifestError, match=msg):
        manifest.load(write(tmp_path, body))


def test_repo_manifest_loads_and_lists_existing_suites():
    m = manifest.load(Path(__file__).resolve().parents[1] / "algogauge.toml")
    names = {s.name for s in m.suites}
    assert {"base_strategy", "trend_following"} <= names
```

- [ ] **Step 2: Run — expect failure**

Run: `python -m pytest tests/test_manifest.py -q`
Expected: FAIL, `ImportError: cannot import name 'manifest'`

- [ ] **Step 3: Implement manifest.py**

```python
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
```

- [ ] **Step 4: Write algogauge.toml (existing suites only; Tier-1 suites are added by PRs 2–4)**

```toml
# AlgoGauge benchmark manifest. See docs/superpowers/specs/2026-08-21-tier1-benchmarking-design.md §4.

[defaults]
repetitions = 20
min_time = "2s"
perf = true
regression_threshold_pct = 10

[[benchmark]]
name   = "base_strategy"
kind   = "gbench"
binary = "build/benchmarks/base_strategy_benchmarks"

[[benchmark]]
name   = "trend_following"
kind   = "gbench"
binary = "build/benchmarks/trend_following_benchmarks"
```

- [ ] **Step 5: Run — expect PASS**

Run: `python -m pytest tests/test_manifest.py -q` → `8 passed`

- [ ] **Step 6: Commit**

```bash
git add python/algogauge/manifest.py algogauge.toml tests/test_manifest.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: add algogauge.toml manifest loader

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Google Benchmark JSON parser with percentiles

**Files:**
- Create: `python/algogauge/gbench.py`
- Test: `tests/test_gbench.py`, `tests/fixtures/gbench_sample.json`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True) class BenchStat: name:str; family:str; param:str|None; unit:str; samples:int
                                          median:float; p95:float; p99:float; mean:float; stddev:float; cv_pct:float
                                          iterations:int; counters:dict[str,float]
  def parse(path: Path) -> list[BenchStat]
  def percentile(values: list[float], q: float) -> float   # nearest-rank, q in [0,100]
  ```
- Notes: with `--benchmark_display_aggregates_only=true`, the JSON `benchmarks` array holds one entry per repetition with `"run_type": "iteration"` and `"run_name"` = benchmark name, plus aggregate rows (`"run_type": "aggregate"`) which are ignored. Family/param are split on the first `/` (`"OnDataScaling/256"` → `("OnDataScaling","256")`; no `/` → param `None`). Counters are any numeric key not in the standard set.

- [ ] **Step 1: Create fixture JSON**

`tests/fixtures/gbench_sample.json` — 3 repetitions × 2 benchmarks, plus aggregate rows to be ignored:
```json
{
  "context": {"date": "2026-08-21T10:00:00+00:00", "host_name": "box", "executable": "x", "num_cpus": 16,
              "mhz_per_cpu": 3000, "cpu_scaling_enabled": false, "library_version": "v1.8.3", "build_type": "release"},
  "benchmarks": [
    {"name": "OnDataScaling/256", "run_name": "OnDataScaling/256", "run_type": "iteration", "repetitions": 3, "repetition_index": 0, "iterations": 1000, "real_time": 100.0, "cpu_time": 99.0, "time_unit": "ns", "bars": 256.0},
    {"name": "OnDataScaling/256", "run_name": "OnDataScaling/256", "run_type": "iteration", "repetitions": 3, "repetition_index": 1, "iterations": 1000, "real_time": 120.0, "cpu_time": 119.0, "time_unit": "ns", "bars": 256.0},
    {"name": "OnDataScaling/256", "run_name": "OnDataScaling/256", "run_type": "iteration", "repetitions": 3, "repetition_index": 2, "iterations": 1000, "real_time": 110.0, "cpu_time": 109.0, "time_unit": "ns", "bars": 256.0},
    {"name": "OnDataScaling/256_mean", "run_name": "OnDataScaling/256", "run_type": "aggregate", "aggregate_name": "mean", "iterations": 3, "real_time": 110.0, "cpu_time": 109.0, "time_unit": "ns"},
    {"name": "PauseStrategy", "run_name": "PauseStrategy", "run_type": "iteration", "repetitions": 3, "repetition_index": 0, "iterations": 50, "real_time": 5000.0, "cpu_time": 5000.0, "time_unit": "ns"},
    {"name": "PauseStrategy", "run_name": "PauseStrategy", "run_type": "iteration", "repetitions": 3, "repetition_index": 1, "iterations": 50, "real_time": 5000.0, "cpu_time": 5000.0, "time_unit": "ns"},
    {"name": "PauseStrategy", "run_name": "PauseStrategy", "run_type": "iteration", "repetitions": 3, "repetition_index": 2, "iterations": 50, "real_time": 5000.0, "cpu_time": 5000.0, "time_unit": "ns"}
  ]
}
```

- [ ] **Step 2: Write failing tests**

`tests/test_gbench.py`:
```python
from pathlib import Path
import pytest
from algogauge import gbench

FIX = Path(__file__).parent / "fixtures" / "gbench_sample.json"


def test_percentile_nearest_rank():
    v = [10.0, 20.0, 30.0, 40.0]
    assert gbench.percentile(v, 50) == 20.0
    assert gbench.percentile(v, 95) == 40.0
    assert gbench.percentile(v, 0) == 10.0
    assert gbench.percentile([7.0], 99) == 7.0


def test_percentile_empty_raises():
    with pytest.raises(ValueError):
        gbench.percentile([], 50)


def test_parse_groups_repetitions_and_ignores_aggregates():
    stats = {s.name: s for s in gbench.parse(FIX)}
    assert set(stats) == {"OnDataScaling/256", "PauseStrategy"}
    s = stats["OnDataScaling/256"]
    assert (s.family, s.param, s.unit, s.samples, s.iterations) == ("OnDataScaling", "256", "ns", 3, 1000)
    assert s.median == 110.0 and s.p95 == 120.0 and s.p99 == 120.0
    assert s.mean == pytest.approx(110.0)
    assert s.stddev == pytest.approx(10.0)          # sample stddev of 100,120,110
    assert s.cv_pct == pytest.approx(100 * 10.0 / 110.0)
    assert s.counters == {"bars": 256.0}
    p = stats["PauseStrategy"]
    assert p.param is None and p.stddev == 0.0 and p.cv_pct == 0.0 and p.counters == {}
```

- [ ] **Step 3: Run — expect failure** (`ImportError`)

- [ ] **Step 4: Implement gbench.py**

```python
"""Parse Google Benchmark JSON output into per-benchmark statistics."""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_STANDARD_KEYS = {
    "name", "run_name", "run_type", "repetitions", "repetition_index", "threads",
    "iterations", "real_time", "cpu_time", "time_unit", "aggregate_name", "aggregate_unit",
    "family_index", "per_family_instance_index", "label", "error_occurred", "error_message",
}


@dataclass(frozen=True)
class BenchStat:
    name: str
    family: str
    param: str | None
    unit: str
    samples: int
    median: float
    p95: float
    p99: float
    mean: float
    stddev: float
    cv_pct: float
    iterations: int
    counters: dict[str, float] = field(default_factory=dict)


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile; q in [0, 100]."""
    if not values:
        raise ValueError("percentile of empty list")
    s = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(s)))
    return s[rank - 1]


def _split(name: str) -> tuple[str, str | None]:
    fam, sep, param = name.partition("/")
    return (fam, param if sep else None)


def parse(path: Path) -> list[BenchStat]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = defaultdict(list)
    for b in data.get("benchmarks", []):
        if b.get("run_type", "iteration") != "iteration" or b.get("error_occurred"):
            continue
        rows[b.get("run_name", b["name"])].append(b)

    out: list[BenchStat] = []
    for name, reps in rows.items():
        times = [float(r["real_time"]) for r in reps]
        mean = statistics.fmean(times)
        sd = statistics.stdev(times) if len(times) > 1 else 0.0
        fam, param = _split(name)
        last = reps[-1]
        counters = {k: float(v) for k, v in last.items()
                    if k not in _STANDARD_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool)}
        out.append(BenchStat(
            name=name, family=fam, param=param, unit=last.get("time_unit", "ns"),
            samples=len(times), median=percentile(times, 50), p95=percentile(times, 95),
            p99=percentile(times, 99), mean=mean, stddev=sd,
            cv_pct=(100.0 * sd / mean) if mean else 0.0,
            iterations=int(last.get("iterations", 0)), counters=counters,
        ))
    return out
```

- [ ] **Step 5: Run — expect PASS** (`3 passed`)

- [ ] **Step 6: Commit**

```bash
git add python/algogauge/gbench.py tests/test_gbench.py tests/fixtures/gbench_sample.json
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: parse Google Benchmark JSON with median/p95/p99 from repetitions

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Machine & git metadata

**Files:**
- Create: `python/algogauge/machine.py`
- Test: `tests/test_machine.py`

**Interfaces:**
- Produces: `def collect(repo_root: Path) -> dict` with keys `cpu_model:str, cores:int, os:str, kernel:str, python:str, perf_event_paranoid:int|None, algogauge_sha:str, trade_ngin_sha:str, hostname:str`. Missing info → `"unknown"` / `None`, never raises. `def git_sha(path: Path) -> str` returns short SHA or `"unknown"`.

- [ ] **Step 1: Write failing tests**

`tests/test_machine.py`:
```python
from pathlib import Path
from algogauge import machine

ROOT = Path(__file__).resolve().parents[1]


def test_collect_has_all_keys_and_types():
    m = machine.collect(ROOT)
    assert set(m) == {"cpu_model", "cores", "os", "kernel", "python", "perf_event_paranoid",
                      "algogauge_sha", "trade_ngin_sha", "hostname"}
    assert isinstance(m["cores"], int) and m["cores"] >= 1
    assert m["algogauge_sha"] != "unknown" and len(m["algogauge_sha"]) >= 7
    assert m["perf_event_paranoid"] is None or isinstance(m["perf_event_paranoid"], int)


def test_git_sha_unknown_for_non_repo(tmp_path):
    assert machine.git_sha(tmp_path) == "unknown"
```

- [ ] **Step 2: Run — expect failure** (`ImportError`)

- [ ] **Step 3: Implement machine.py**

```python
"""Collect machine and git metadata so every benchmark record is attributable."""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def git_sha(path: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short=12", "HEAD"],
                              capture_output=True, text=True, check=True, timeout=10).stdout.strip() or "unknown"
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
```

- [ ] **Step 4: Run — expect PASS** (`2 passed`)

- [ ] **Step 5: Commit**

```bash
git add python/algogauge/machine.py tests/test_machine.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: collect machine and git metadata for benchmark records

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: History store

**Files:**
- Create: `python/algogauge/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: `gbench.BenchStat`.
- Produces:
  ```python
  CV_INVALID_PCT = 15.0
  @dataclass class Record: run_id:str; suite:str; benchmark:str; family:str; param:str|None; unit:str
                           median:float; p95:float; p99:float; mean:float; stddev:float; cv_pct:float
                           samples:int; iterations:int; counters:dict[str,float]; valid:bool; invalid_reason:str|None
                           machine:dict; trade_ngin_sha:str; algogauge_sha:str; ts:str; perf:bool
                           def to_json(self)->str; @classmethod from_json(cls, line:str)->Record
  def from_stats(run_id, suite, stats:list[BenchStat], machine:dict, ts:str, perf:bool) -> list[Record]
  def history_path(history_dir: Path, suite: str) -> Path         # history/<suite>.jsonl
  def append(history_dir: Path, records: list[Record]) -> Path
  def load(history_dir: Path, suite: str) -> list[Record]          # [] if file missing
  def load_all(history_dir: Path) -> dict[str, list[Record]]
  def latest_run(records: list[Record], valid_only=True) -> str|None   # run_id with max ts
  ```
- Validity: `valid = cv_pct <= 15.0`; `invalid_reason = "cv_pct > 15"` otherwise.

- [ ] **Step 1: Write failing tests**

`tests/test_history.py`:
```python
from pathlib import Path
from algogauge import history
from algogauge.gbench import BenchStat

MACHINE = {"cpu_model": "x", "cores": 4, "trade_ngin_sha": "abc", "algogauge_sha": "def"}


def stat(name="A/1", cv=1.0):
    return BenchStat(name=name, family=name.split("/")[0], param="1" if "/" in name else None, unit="ns",
                     samples=20, median=100.0, p95=110.0, p99=115.0, mean=101.0, stddev=1.0, cv_pct=cv,
                     iterations=10, counters={"k": 2.0})


def test_from_stats_marks_validity():
    recs = history.from_stats("r1", "s", [stat(cv=1.0), stat("B", cv=20.0)], MACHINE, "2026-08-21T00:00:00Z", True)
    assert [r.valid for r in recs] == [True, False]
    assert recs[1].invalid_reason == "cv_pct > 15"
    assert recs[0].trade_ngin_sha == "abc" and recs[0].suite == "s" and recs[0].run_id == "r1"


def test_round_trip_json():
    r = history.from_stats("r1", "s", [stat()], MACHINE, "t", False)[0]
    assert history.Record.from_json(r.to_json()) == r


def test_append_and_load(tmp_path: Path):
    recs = history.from_stats("r1", "s", [stat(), stat("B")], MACHINE, "2026-01-01T00:00:00Z", True)
    p = history.append(tmp_path, recs)
    assert p == tmp_path / "s.jsonl" and p.read_text().count("\n") == 2
    history.append(tmp_path, history.from_stats("r2", "s", [stat()], MACHINE, "2026-01-02T00:00:00Z", True))
    loaded = history.load(tmp_path, "s")
    assert [r.run_id for r in loaded] == ["r1", "r1", "r2"]
    assert history.load(tmp_path, "missing") == []
    assert set(history.load_all(tmp_path)) == {"s"}


def test_latest_run_prefers_valid():
    recs = history.from_stats("r1", "s", [stat()], MACHINE, "2026-01-01T00:00:00Z", True) + \
           history.from_stats("r2", "s", [stat(cv=50)], MACHINE, "2026-01-02T00:00:00Z", True)
    assert history.latest_run(recs) == "r1"
    assert history.latest_run(recs, valid_only=False) == "r2"
    assert history.latest_run([]) is None
```

- [ ] **Step 2: Run — expect failure** (`ImportError`)

- [ ] **Step 3: Implement history.py**

```python
"""Compact, committed run history: one JSONL file per suite, one line per benchmark per run."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .gbench import BenchStat

CV_INVALID_PCT = 15.0


@dataclass
class Record:
    run_id: str
    suite: str
    benchmark: str
    family: str
    param: str | None
    unit: str
    median: float
    p95: float
    p99: float
    mean: float
    stddev: float
    cv_pct: float
    samples: int
    iterations: int
    counters: dict[str, float]
    valid: bool
    invalid_reason: str | None
    machine: dict
    trade_ngin_sha: str
    algogauge_sha: str
    ts: str
    perf: bool = field(default=False)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, line: str) -> "Record":
        return cls(**json.loads(line))


def from_stats(run_id: str, suite: str, stats: list[BenchStat], machine: dict, ts: str, perf: bool) -> list[Record]:
    out = []
    for s in stats:
        valid = s.cv_pct <= CV_INVALID_PCT
        out.append(Record(
            run_id=run_id, suite=suite, benchmark=s.name, family=s.family, param=s.param, unit=s.unit,
            median=s.median, p95=s.p95, p99=s.p99, mean=s.mean, stddev=s.stddev, cv_pct=s.cv_pct,
            samples=s.samples, iterations=s.iterations, counters=dict(s.counters),
            valid=valid, invalid_reason=None if valid else f"cv_pct > {CV_INVALID_PCT:g}",
            machine=dict(machine), trade_ngin_sha=str(machine.get("trade_ngin_sha", "unknown")),
            algogauge_sha=str(machine.get("algogauge_sha", "unknown")), ts=ts, perf=perf,
        ))
    return out


def history_path(history_dir: Path, suite: str) -> Path:
    return Path(history_dir) / f"{suite}.jsonl"


def append(history_dir: Path, records: list[Record]) -> Path:
    if not records:
        raise ValueError("no records to append")
    suites = {r.suite for r in records}
    if len(suites) != 1:
        raise ValueError(f"records span multiple suites: {sorted(suites)}")
    p = history_path(history_dir, records[0].suite)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for r in records:
            f.write(r.to_json() + "\n")
    return p


def load(history_dir: Path, suite: str) -> list[Record]:
    p = history_path(history_dir, suite)
    if not p.exists():
        return []
    return [Record.from_json(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_all(history_dir: Path) -> dict[str, list[Record]]:
    d = Path(history_dir)
    return {p.stem: load(d, p.stem) for p in sorted(d.glob("*.jsonl"))}


def latest_run(records: list[Record], valid_only: bool = True) -> str | None:
    pool = [r for r in records if r.valid] if valid_only else list(records)
    if not pool:
        return None
    return max(pool, key=lambda r: (r.ts, r.run_id)).run_id
```

- [ ] **Step 4: Run — expect PASS** (`4 passed`)

- [ ] **Step 5: Commit**

```bash
git add python/algogauge/history.py tests/test_history.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: add committed JSONL run history with validity flags

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Compare / regression detection

**Files:**
- Create: `python/algogauge/compare.py`
- Test: `tests/test_compare.py`

**Interfaces:**
- Consumes: `history.Record`, `history.load`, `history.latest_run`.
- Produces:
  ```python
  @dataclass(frozen=True) class Delta: benchmark:str; unit:str; baseline_median:float; current_median:float; delta_pct:float; regressed:bool
  def compare(baseline: list[Record], current: list[Record], threshold_pct: float) -> list[Delta]   # only benchmarks in both; sorted by name
  def select_run(records: list[Record], run_id: str) -> list[Record]   # "latest" → latest valid run
  def render_table(deltas: list[Delta], threshold_pct: float) -> str    # ASCII only
  def has_regression(deltas) -> bool
  ```

- [ ] **Step 1: Write failing tests**

`tests/test_compare.py`:
```python
from algogauge import compare, history
from algogauge.gbench import BenchStat

M = {"trade_ngin_sha": "a", "algogauge_sha": "b"}


def rec(run, name, median, ts):
    s = BenchStat(name=name, family=name, param=None, unit="ns", samples=5, median=median, p95=median, p99=median,
                  mean=median, stddev=0.0, cv_pct=0.0, iterations=1, counters={})
    return history.from_stats(run, "s", [s], M, ts, False)[0]


def test_compare_flags_regressions_only_above_threshold():
    base = [rec("r1", "A", 100.0, "t1"), rec("r1", "B", 100.0, "t1"), rec("r1", "OnlyBase", 1.0, "t1")]
    cur = [rec("r2", "A", 115.0, "t2"), rec("r2", "B", 105.0, "t2"), rec("r2", "OnlyCur", 1.0, "t2")]
    d = compare.compare(base, cur, threshold_pct=10.0)
    assert [x.benchmark for x in d] == ["A", "B"]
    assert d[0].delta_pct == 15.0 and d[0].regressed is True
    assert d[1].delta_pct == 5.0 and d[1].regressed is False
    assert compare.has_regression(d) is True
    assert compare.has_regression(d[1:]) is False


def test_select_run_latest_and_explicit():
    recs = [rec("r1", "A", 1, "t1"), rec("r2", "A", 2, "t2")]
    assert [r.run_id for r in compare.select_run(recs, "latest")] == ["r2"]
    assert [r.median for r in compare.select_run(recs, "r1")] == [1]
    assert compare.select_run(recs, "nope") == []


def test_render_table_is_ascii_and_marks_regressions():
    d = compare.compare([rec("r1", "A", 100.0, "t1")], [rec("r2", "A", 130.0, "t2")], 10.0)
    out = compare.render_table(d, 10.0)
    assert out.isascii() and "A" in out and "+30.0%" in out and "[REGRESSION]" in out
```

- [ ] **Step 2: Run — expect failure** (`ImportError`)

- [ ] **Step 3: Implement compare.py**

```python
"""Compare two runs and flag median regressions beyond a threshold."""
from __future__ import annotations

from dataclasses import dataclass

from .history import Record, latest_run


@dataclass(frozen=True)
class Delta:
    benchmark: str
    unit: str
    baseline_median: float
    current_median: float
    delta_pct: float
    regressed: bool


def select_run(records: list[Record], run_id: str) -> list[Record]:
    target = latest_run(records) if run_id == "latest" else run_id
    return [r for r in records if r.run_id == target]


def compare(baseline: list[Record], current: list[Record], threshold_pct: float) -> list[Delta]:
    base = {r.benchmark: r for r in baseline}
    out = []
    for name in sorted(set(base) & {r.benchmark for r in current}):
        b = base[name]
        c = next(r for r in current if r.benchmark == name)
        pct = ((c.median - b.median) / b.median * 100.0) if b.median else 0.0
        out.append(Delta(name, c.unit, b.median, c.median, round(pct, 2), pct > threshold_pct))
    return out


def has_regression(deltas: list[Delta]) -> bool:
    return any(d.regressed for d in deltas)


def render_table(deltas: list[Delta], threshold_pct: float) -> str:
    lines = [f"{'Benchmark':<40} {'Baseline':>14} {'Current':>14} {'Delta':>9}", "-" * 80]
    for d in deltas:
        tag = "  [REGRESSION]" if d.regressed else ""
        lines.append(f"{d.benchmark:<40} {d.baseline_median:>11.1f} {d.unit:<2} {d.current_median:>11.1f} {d.unit:<2} "
                     f"{d.delta_pct:>+8.1f}%{tag}")
    n = sum(d.regressed for d in deltas)
    lines.append("-" * 80)
    lines.append(f"[FAIL] {n} regression(s) beyond {threshold_pct:g}%" if n else
                 f"[PASS] no regressions beyond {threshold_pct:g}%")
    return "\n".join(lines)
```

- [ ] **Step 4: Run — expect PASS** (`3 passed`)

- [ ] **Step 5: Commit**

```bash
git add python/algogauge/compare.py tests/test_compare.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: add run comparison with median regression detection

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Runner (generalised pipeline) + backwards-compatible shim

**Files:**
- Create: `python/algogauge/runner.py`
- Modify: `python/benchmark_pipeline.py` (replace body with shim)
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `manifest.Suite`, `manifest.Defaults`, `gbench.parse`, `machine.collect`, `history.from_stats/append`.
- Produces:
  ```python
  @dataclass class RunResult: suite:str; run_id:str; result_dir:Path; records:list[Record]; perf_ran:bool
  def new_run_id(now: datetime|None=None) -> str                         # "%Y%m%d_%H%M%S"
  def gbench_command(binary: Path, suite: Suite, out_json: Path) -> list[str]
  def check_perf_permissions() -> None                                    # raises RuntimeError with fix hint
  def run_suite(suite: Suite, defaults: Defaults, repo_root: Path, *, skip_perf=False,
                results_dir: Path|None=None, history_dir: Path|None=None,
                run_id: str|None=None, executor=subprocess.run) -> RunResult
  ```
- Behaviour:
  - `kind == "gbench"`: run binary with `--benchmark_out=<dir>/benchmark.json --benchmark_out_format=json --benchmark_min_time=<min_time> --benchmark_repetitions=<n> --benchmark_display_aggregates_only=true`, tee stdout to `benchmark.txt`; then parse JSON → records → append to history.
  - `kind == "script"`: run `python <script> <args...> --out <dir>/benchmark.json` (scripts must write the same Google-Benchmark-shaped JSON — PR 4's harness will); same parse/append path.
  - perf stages (`perf record -F 999 -g -o perf.data -- <binary> --benchmark_min_time=<min_time>`, `perf script`, `stackcollapse-perf.pl`, `flamegraph.pl`) run only when `suite.perf and not skip_perf` and kind is gbench; if `check_perf_permissions()` fails, print a warning and skip perf instead of aborting (old behaviour aborted — the spec §9 requires timing numbers even without perf).
  - `executor` is injectable so tests never spawn real processes.

- [ ] **Step 1: Write failing tests**

`tests/test_runner.py`:
```python
import json
import shutil
from datetime import datetime
from pathlib import Path

from algogauge import runner
from algogauge.manifest import Defaults, Suite

FIX = Path(__file__).parent / "fixtures" / "gbench_sample.json"


def suite(kind="gbench", perf=True):
    return Suite(name="demo", kind=kind, binary="build/demo" if kind == "gbench" else None,
                 script="python/demo.py" if kind == "script" else None, args=("--n", "2"),
                 repetitions=3, min_time="1s", perf=perf)


def test_new_run_id_format():
    assert runner.new_run_id(datetime(2026, 8, 21, 13, 5, 9)) == "20260821_130509"


def test_gbench_command_uses_display_aggregates_only():
    cmd = runner.gbench_command(Path("build/demo"), suite(), Path("out/benchmark.json"))
    assert cmd[0] == "build/demo"
    assert "--benchmark_display_aggregates_only=true" in cmd
    assert "--benchmark_report_aggregates_only=true" not in cmd
    assert "--benchmark_repetitions=3" in cmd and "--benchmark_min_time=1s" in cmd


def fake_executor(calls):
    """Records commands; fakes the benchmark binary by copying the fixture JSON to --benchmark_out."""
    def run(cmd, **kw):
        calls.append(list(cmd))
        for a in cmd:
            if isinstance(a, str) and a.startswith("--benchmark_out="):
                shutil.copy(FIX, a.split("=", 1)[1])
            if isinstance(a, str) and a == "--out":
                shutil.copy(FIX, cmd[cmd.index(a) + 1])
        class R: returncode = 0; stdout = ""
        return R()
    return run


def test_run_suite_gbench_skip_perf_writes_results_and_history(tmp_path):
    calls = []
    res = runner.run_suite(suite(), Defaults(), tmp_path, skip_perf=True, results_dir=tmp_path / "results",
                           history_dir=tmp_path / "history", run_id="r1", executor=fake_executor(calls))
    assert res.run_id == "r1" and res.perf_ran is False
    assert (res.result_dir / "benchmark.json").exists()
    assert res.result_dir == tmp_path / "results" / "demo" / "r1"
    assert len(calls) == 1 and not any("perf" in c[0] for c in calls)
    lines = (tmp_path / "history" / "demo.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["suite"] == "demo"
    assert {r.benchmark for r in res.records} == {"OnDataScaling/256", "PauseStrategy"}


def test_run_suite_runs_perf_stages_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "check_perf_permissions", lambda: None)
    calls = []
    res = runner.run_suite(suite(), Defaults(), tmp_path, results_dir=tmp_path / "r", history_dir=tmp_path / "h",
                           run_id="r1", executor=fake_executor(calls))
    assert res.perf_ran is True
    heads = [c[0] for c in calls]
    assert heads[1:3] == ["perf", "perf"] and heads[3].endswith("stackcollapse-perf.pl") and heads[4].endswith("flamegraph.pl")


def test_run_suite_skips_perf_when_permissions_fail(tmp_path, monkeypatch, capsys):
    def boom():
        raise RuntimeError("perf_event_paranoid must be 0")
    monkeypatch.setattr(runner, "check_perf_permissions", boom)
    calls = []
    res = runner.run_suite(suite(), Defaults(), tmp_path, results_dir=tmp_path / "r", history_dir=tmp_path / "h",
                           run_id="r1", executor=fake_executor(calls))
    assert res.perf_ran is False and len(calls) == 1
    assert "skipping perf" in capsys.readouterr().out


def test_run_suite_script_kind(tmp_path):
    calls = []
    res = runner.run_suite(suite(kind="script", perf=False), Defaults(), tmp_path, results_dir=tmp_path / "r",
                           history_dir=tmp_path / "h", run_id="r1", executor=fake_executor(calls))
    cmd = calls[0]
    assert cmd[1].endswith("demo.py") and cmd[2:4] == ["--n", "2"] and "--out" in cmd
    assert len(res.records) == 2
```

- [ ] **Step 2: Run — expect failure** (`ImportError`)

- [ ] **Step 3: Implement runner.py**

```python
"""Run one benchmark suite: Google Benchmark (or a script), optional perf + flamegraph, history append."""
from __future__ import annotations

import datetime as _dt
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from . import gbench, history, machine
from .history import Record
from .manifest import Defaults, Suite


@dataclass
class RunResult:
    suite: str
    run_id: str
    result_dir: Path
    records: list[Record]
    perf_ran: bool


def new_run_id(now: _dt.datetime | None = None) -> str:
    return (now or _dt.datetime.now()).strftime("%Y%m%d_%H%M%S")


def gbench_command(binary: Path, suite: Suite, out_json: Path) -> list[str]:
    return [
        str(binary),
        f"--benchmark_out={out_json}",
        "--benchmark_out_format=json",
        f"--benchmark_min_time={suite.min_time}",
        f"--benchmark_repetitions={suite.repetitions}",
        "--benchmark_display_aggregates_only=true",
    ]


def check_perf_permissions() -> None:
    for knob, want in (("perf_event_paranoid", "0"), ("kptr_restrict", "0")):
        try:
            val = Path(f"/proc/sys/kernel/{knob}").read_text().strip()
        except OSError as e:
            raise RuntimeError(f"cannot read {knob}: {e}") from e
        if val != want:
            raise RuntimeError(f"{knob} must be {want} (is {val}). Run: sudo sysctl -w kernel.{knob}={want}")


def _tee(executor, cmd: list[str], stdout_file: Path | None, cwd: Path) -> None:
    print(f"Running: {' '.join(map(str, cmd))}")
    if stdout_file is None:
        r = executor(cmd, cwd=str(cwd), check=False)
        rc = getattr(r, "returncode", 0)
    else:
        r = executor(cmd, cwd=str(cwd), check=False, capture_output=True, text=True)
        rc = getattr(r, "returncode", 0)
        out = getattr(r, "stdout", "") or ""
        stdout_file.write_text(out, encoding="utf-8")
        if out:
            print(out, end="")
    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)


def _perf_stages(executor, binary: Path, suite: Suite, rd: Path, repo_root: Path) -> None:
    fg = repo_root / "tools" / "FlameGraph"
    _tee(executor, ["perf", "record", "-F", "999", "-g", "-o", str(rd / "perf.data"), "--", str(binary),
                    f"--benchmark_min_time={suite.min_time}"], None, repo_root)
    _tee(executor, ["perf", "script", "-i", str(rd / "perf.data")], rd / "perf.script", repo_root)
    _tee(executor, [str(fg / "stackcollapse-perf.pl"), str(rd / "perf.script")], rd / "perf.folded", repo_root)
    _tee(executor, [str(fg / "flamegraph.pl"), str(rd / "perf.folded")], rd / "flamegraph.svg", repo_root)


def run_suite(suite: Suite, defaults: Defaults, repo_root: Path, *, skip_perf: bool = False,
              results_dir: Path | None = None, history_dir: Path | None = None,
              run_id: str | None = None, executor=subprocess.run) -> RunResult:
    repo_root = Path(repo_root)
    run_id = run_id or new_run_id()
    rd = (results_dir or repo_root / "results") / suite.name / run_id
    rd.mkdir(parents=True, exist_ok=True)
    out_json = rd / "benchmark.json"
    print(f"Suite: {suite.name}\nResults: {rd}")

    if suite.kind == "gbench":
        binary = repo_root / suite.binary
        _tee(executor, gbench_command(binary, suite, out_json), rd / "benchmark.txt", repo_root)
    else:
        script = repo_root / suite.script
        _tee(executor, [sys.executable, str(script), *suite.args, "--out", str(out_json)], rd / "benchmark.txt", repo_root)

    perf_ran = False
    if suite.kind == "gbench" and suite.perf and not skip_perf:
        try:
            check_perf_permissions()
            _perf_stages(executor, repo_root / suite.binary, suite, rd, repo_root)
            perf_ran = True
        except RuntimeError as e:
            print(f"WARNING: {e}\nskipping perf/flamegraph stages (timing results are unaffected)")

    stats = gbench.parse(out_json)
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    records = history.from_stats(run_id, suite.name, stats, machine.collect(repo_root), ts, perf_ran)
    history.append(history_dir or repo_root / "history", records)
    print(f"Recorded {len(records)} benchmark(s) to history; {sum(not r.valid for r in records)} invalid")
    return RunResult(suite.name, run_id, rd, records, perf_ran)
```

- [ ] **Step 4: Replace `python/benchmark_pipeline.py` with a shim**

```python
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
    suite = Suite(name=binary.name, kind="gbench", binary=str(binary.relative_to(root) if binary.is_absolute() else binary),
                  script=None, args=(), repetitions=30, min_time="5s", perf=True)
    run_suite(suite, Defaults(), root, skip_perf="--skip-perf" in sys.argv[2:])


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run — expect PASS** (`6 passed`), then full suite `python -m pytest -q` all green.

- [ ] **Step 6: Commit**

```bash
git add python/algogauge/runner.py python/benchmark_pipeline.py tests/test_runner.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: manifest-driven runner with optional perf stages; keep pipeline shim

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: CLI

**Files:**
- Create: `python/algogauge/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `def main(argv: list[str]|None=None) -> int` with subcommands:
  - `algogauge list` — prints `name  kind  binary|script  perf` per suite.
  - `algogauge run [SUITE ...] [--skip-perf] [--manifest PATH]` — runs named suites (all if none); prints a Markdown summary table (`benchmark | median | p95 | unit | valid`) per suite; returns 1 if any suite raised.
  - `algogauge compare SUITE [--baseline RUN|latest] [--current RUN|latest] [--threshold PCT]` — prints `compare.render_table`; returns 1 on regression. `--baseline` defaults to the latest valid run *before* current; `--current` defaults to latest valid.
  - `def summary_markdown(records: list[Record]) -> str`.

- [ ] **Step 1: Write failing tests**

`tests/test_cli.py`:
```python
from pathlib import Path
from algogauge import cli, history
from algogauge.gbench import BenchStat

M = {"trade_ngin_sha": "a", "algogauge_sha": "b"}
ROOT = Path(__file__).resolve().parents[1]


def rec(run, name, median, ts, cv=0.0):
    s = BenchStat(name=name, family=name, param=None, unit="ns", samples=5, median=median, p95=median + 1, p99=median + 2,
                  mean=median, stddev=0.0, cv_pct=cv, iterations=1, counters={})
    return history.from_stats(run, "s", [s], M, ts, False)[0]


def test_list_prints_suites(capsys):
    assert cli.main(["list", "--manifest", str(ROOT / "algogauge.toml")]) == 0
    out = capsys.readouterr().out
    assert "base_strategy" in out and "trend_following" in out and "gbench" in out


def test_summary_markdown():
    md = cli.summary_markdown([rec("r1", "A", 100.0, "t", cv=20.0)])
    assert md.splitlines()[0].startswith("| benchmark") and "| A |" in md and "no" in md


def test_compare_defaults_and_exit_code(tmp_path, capsys):
    history.append(tmp_path, [rec("r1", "A", 100.0, "2026-01-01T00:00:00Z")])
    history.append(tmp_path, [rec("r2", "A", 150.0, "2026-01-02T00:00:00Z")])
    rc = cli.main(["compare", "s", "--history-dir", str(tmp_path)])
    assert rc == 1 and "[REGRESSION]" in capsys.readouterr().out
    rc = cli.main(["compare", "s", "--history-dir", str(tmp_path), "--threshold", "60"])
    assert rc == 0


def test_compare_needs_two_runs(tmp_path, capsys):
    history.append(tmp_path, [rec("r1", "A", 100.0, "2026-01-01T00:00:00Z")])
    assert cli.main(["compare", "s", "--history-dir", str(tmp_path)]) == 2
    assert "need at least two" in capsys.readouterr().out


def test_run_unknown_suite_returns_1(capsys):
    assert cli.main(["run", "nope", "--manifest", str(ROOT / "algogauge.toml")]) == 1
    assert "unknown suite" in capsys.readouterr().out
```

- [ ] **Step 2: Run — expect failure** (`ImportError`)

- [ ] **Step 3: Implement cli.py**

```python
"""Command-line interface: algogauge list | run | compare."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import compare as cmp, history, manifest, runner
from .history import Record


def _root(manifest_path: Path) -> Path:
    return manifest_path.resolve().parent


def summary_markdown(records: list[Record]) -> str:
    lines = ["| benchmark | median | p95 | unit | valid |", "|---|---:|---:|---|---|"]
    for r in sorted(records, key=lambda r: r.benchmark):
        lines.append(f"| {r.benchmark} | {r.median:.1f} | {r.p95:.1f} | {r.unit} | {'yes' if r.valid else 'no'} |")
    return "\n".join(lines)


def _cmd_list(a) -> int:
    m = manifest.load(a.manifest)
    for s in m.suites:
        print(f"{s.name:<28} {s.kind:<7} {s.binary or s.script:<48} perf={'on' if s.perf else 'off'}")
    return 0


def _cmd_run(a) -> int:
    m = manifest.load(a.manifest)
    root = _root(a.manifest)
    names = a.suites or [s.name for s in m.suites]
    failed = 0
    for n in names:
        try:
            s = m.get(n)
            res = runner.run_suite(s, m.defaults, root, skip_perf=a.skip_perf)
            print(f"\n### {s.name}  (run {res.run_id})\n{summary_markdown(res.records)}\n")
        except Exception as e:  # noqa: BLE001 - report and continue with the next suite
            failed += 1
            print(f"ERROR running suite '{n}': {e}")
    return 1 if failed else 0


def _cmd_compare(a) -> int:
    recs = history.load(a.history_dir, a.suite)
    runs = sorted({(r.ts, r.run_id) for r in recs if r.valid})
    if len(runs) < 2 and (a.baseline == "auto" or a.current == "latest"):
        print(f"need at least two valid runs of '{a.suite}' in {a.history_dir} (have {len(runs)})")
        return 2
    current_id = runs[-1][1] if a.current == "latest" else a.current
    baseline_id = next((rid for ts, rid in reversed(runs) if rid != current_id), None) if a.baseline == "auto" else a.baseline
    base = cmp.select_run(recs, baseline_id)
    cur = cmp.select_run(recs, current_id)
    deltas = cmp.compare(base, cur, a.threshold)
    print(f"baseline={baseline_id}  current={current_id}")
    print(cmp.render_table(deltas, a.threshold))
    return 1 if cmp.has_regression(deltas) else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="algogauge")
    sub = p.add_subparsers(dest="cmd", required=True)
    default_manifest = Path.cwd() / "algogauge.toml"

    l = sub.add_parser("list", help="list suites in the manifest")
    l.add_argument("--manifest", type=Path, default=default_manifest)
    l.set_defaults(fn=_cmd_list)

    r = sub.add_parser("run", help="run one or more suites")
    r.add_argument("suites", nargs="*")
    r.add_argument("--manifest", type=Path, default=default_manifest)
    r.add_argument("--skip-perf", action="store_true")
    r.set_defaults(fn=_cmd_run)

    c = sub.add_parser("compare", help="compare two runs of a suite")
    c.add_argument("suite")
    c.add_argument("--history-dir", type=Path, default=Path.cwd() / "history")
    c.add_argument("--baseline", default="auto", help="run id; default: latest valid run before --current")
    c.add_argument("--current", default="latest")
    c.add_argument("--threshold", type=float, default=10.0)
    c.set_defaults(fn=_cmd_compare)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run — expect PASS** (`5 passed`); full suite green.

- [ ] **Step 5: Commit**

```bash
git add python/algogauge/cli.py tests/test_cli.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: add algogauge CLI (list, run, compare)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: WSL2 setup script

**Files:**
- Create: `scripts/setup_wsl.sh`
- Test: `tests/test_setup_script.py` (static checks only — it cannot run on Windows)

- [ ] **Step 1: Write failing test**

`tests/test_setup_script.py`:
```python
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_wsl.sh"


def test_setup_script_exists_and_is_strict_bash():
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    for pkg in ("build-essential", "cmake", "libeigen3-dev", "nlohmann-json3-dev", "libpqxx-dev",
                "libnlopt-cxx-dev", "libgtest-dev", "libbenchmark-dev", "libcurl4-openssl-dev", "libarrow-dev"):
        assert pkg in text, pkg
    assert "astral.sh/uv/install.sh" in text
    assert "perf_event_paranoid" in text
    assert "\r" not in text, "must use LF line endings for bash"
```

- [ ] **Step 2: Run — expect FAIL** (`FileNotFoundError`)

- [ ] **Step 3: Write scripts/setup_wsl.sh** (LF endings!)

```bash
#!/usr/bin/env bash
# Idempotent toolchain setup for AlgoGauge on WSL2 Ubuntu 24.04.
# Usage (from Windows):  wsl -d Ubuntu -e sudo bash scripts/setup_wsl.sh
# Re-run any time; every step is safe to repeat.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then echo "run with sudo"; exit 1; fi
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"

echo "==> apt packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential cmake ninja-build pkg-config git curl ca-certificates lsb-release wget \
  libeigen3-dev nlohmann-json3-dev libpqxx-dev libnlopt-cxx-dev libnlopt-dev libgtest-dev libbenchmark-dev \
  libcurl4-openssl-dev libpq-dev linux-tools-common "linux-tools-$(uname -r)" linux-tools-generic || true

echo "==> Apache Arrow (official apt repo)"
if ! dpkg -s libarrow-dev >/dev/null 2>&1; then
  wget -q "https://packages.apache.org/artifactory/arrow/$(lsb_release --id --short | tr 'A-Z' 'a-z')/apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb" -O /tmp/arrow.deb
  apt-get install -y -qq /tmp/arrow.deb
  apt-get update -qq
  apt-get install -y -qq libarrow-dev
fi

echo "==> perf sysctl (session + persistent)"
sysctl -w kernel.perf_event_paranoid=0 kernel.kptr_restrict=0 >/dev/null
printf 'kernel.perf_event_paranoid=0\nkernel.kptr_restrict=0\n' > /etc/sysctl.d/99-algogauge-perf.conf
command -v perf >/dev/null || echo "NOTE: 'perf' not found for this WSL kernel; timing still works, flamegraphs will be skipped (--skip-perf)."

echo "==> uv for $REAL_USER"
if ! sudo -u "$REAL_USER" bash -lc 'command -v uv' >/dev/null 2>&1; then
  sudo -u "$REAL_USER" bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi

echo "==> done. Next (as $REAL_USER, in the algogauge repo):"
echo "    git submodule update --init --recursive"
echo "    uv sync --extra dev"
echo "    cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --parallel"
echo "    uv run algogauge run --skip-perf"
```

- [ ] **Step 4: Run — expect PASS**; ensure LF: `git config core.autocrlf` is unset or use `git add --renormalize`. Verify with `python -c "assert b'\r' not in open('scripts/setup_wsl.sh','rb').read()"`.

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_wsl.sh tests/test_setup_script.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "build: add idempotent WSL2 toolchain setup script

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Notebooks 00 and 01 (generated with nbformat)

**Files:**
- Create: `scripts/build_notebooks.py`, `notebooks/00_setup_wsl.ipynb`, `notebooks/01_run_all_benchmarks.ipynb`
- Test: `tests/test_notebooks.py`

**Interfaces:**
- Produces: `build_notebooks.build(out_dir: Path) -> list[Path]`. Notebooks import the package via a first cell that inserts `../python` into `sys.path` so they work under `uv run jupyter lab` without install.

- [ ] **Step 1: Write failing test**

`tests/test_notebooks.py`:
```python
import json
from pathlib import Path
import pytest

nbformat = pytest.importorskip("nbformat")
ROOT = Path(__file__).resolve().parents[1]


def test_build_notebooks_roundtrip(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bn", ROOT / "scripts" / "build_notebooks.py")
    bn = importlib.util.module_from_spec(spec); spec.loader.exec_module(bn)
    paths = bn.build(tmp_path)
    assert [p.name for p in paths] == ["00_setup_wsl.ipynb", "01_run_all_benchmarks.ipynb"]
    for p in paths:
        nb = nbformat.read(p, as_version=4)
        nbformat.validate(nb)
        src = "\n".join(c.source for c in nb.cells)
        assert "sys.path.insert" in src


def test_committed_notebooks_match_generator(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bn", ROOT / "scripts" / "build_notebooks.py")
    bn = importlib.util.module_from_spec(spec); spec.loader.exec_module(bn)
    for p in bn.build(tmp_path):
        committed = json.loads((ROOT / "notebooks" / p.name).read_text(encoding="utf-8"))
        generated = json.loads(p.read_text(encoding="utf-8"))
        assert committed == generated, f"{p.name} is stale: run python scripts/build_notebooks.py"
```

- [ ] **Step 2: Run — expect FAIL** (`FileNotFoundError`)

- [ ] **Step 3: Write scripts/build_notebooks.py**

```python
"""Generate notebooks/*.ipynb deterministically. Run: python scripts/build_notebooks.py"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

BOOT = '''import sys, pathlib
ROOT = pathlib.Path.cwd().resolve()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "python"))
import os; os.chdir(ROOT)
print("repo root:", ROOT)'''


def _nb(cells):
    nb = nbf.v4.new_notebook()
    nb.metadata = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                   "language_info": {"name": "python"}}
    nb.cells = cells
    for c in nb.cells:
        c.pop("id", None)
    return nb


def setup_nb():
    return _nb([
        nbf.v4.new_markdown_cell("# 00 · Set up WSL2 for AlgoGauge\n\nRun this once on a fresh WSL2 Ubuntu 24.04. "
                                 "Step 1 needs `sudo`, so it is printed for you to run in a terminal; the rest runs here."),
        nbf.v4.new_code_cell(BOOT),
        nbf.v4.new_markdown_cell("## 1. System packages (run in a terminal, needs your password)"),
        nbf.v4.new_code_cell('print("wsl -d Ubuntu -e sudo bash", ROOT / "scripts" / "setup_wsl.sh")'),
        nbf.v4.new_markdown_cell("## 2. Verify toolchain"),
        nbf.v4.new_code_cell('''import shutil, subprocess
for tool in ["g++", "cmake", "ninja", "perf", "uv", "git"]:
    print(f"{tool:<6}", shutil.which(tool) or "MISSING")
print("perf_event_paranoid =", open("/proc/sys/kernel/perf_event_paranoid").read().strip() if pathlib.Path("/proc/sys/kernel/perf_event_paranoid").exists() else "n/a")'''),
        nbf.v4.new_markdown_cell("## 3. Submodules + Python deps"),
        nbf.v4.new_code_cell('''subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
subprocess.run(["uv", "sync", "--extra", "dev"], check=True)'''),
        nbf.v4.new_markdown_cell("## 4. Build benchmarks (Release)"),
        nbf.v4.new_code_cell('''subprocess.run(["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"], check=True)
subprocess.run(["cmake", "--build", "build", "--parallel"], check=True)'''),
        nbf.v4.new_markdown_cell("## 5. Smoke run (no perf)"),
        nbf.v4.new_code_cell('''from algogauge import manifest, runner
m = manifest.load(ROOT / "algogauge.toml")
res = runner.run_suite(m.suites[0], m.defaults, ROOT, skip_perf=True)
print(res.run_id, len(res.records), "benchmarks recorded")'''),
    ])


def run_all_nb():
    return _nb([
        nbf.v4.new_markdown_cell("# 01 · Run all benchmark suites\n\nRuns every suite in `algogauge.toml`, appends to "
                                 "`history/`, and prints the headline numbers plus a Markdown table you can paste anywhere."),
        nbf.v4.new_code_cell(BOOT),
        nbf.v4.new_code_cell('''SKIP_PERF = False   # set True to skip flamegraphs (faster; needed if perf is unavailable)
SUITES = None       # e.g. ["tick_to_trade"]; None = all'''),
        nbf.v4.new_code_cell('''from algogauge import manifest, runner, cli
m = manifest.load(ROOT / "algogauge.toml")
results = {}
for s in m.suites:
    if SUITES and s.name not in SUITES:
        continue
    results[s.name] = runner.run_suite(s, m.defaults, ROOT, skip_perf=SKIP_PERF)'''),
        nbf.v4.new_markdown_cell("## Summary"),
        nbf.v4.new_code_cell('''from IPython.display import Markdown, display
for name, res in results.items():
    display(Markdown(f"### {name}  (run `{res.run_id}`, perf={'on' if res.perf_ran else 'off'})\\n" + cli.summary_markdown(res.records)))'''),
        nbf.v4.new_markdown_cell("## Regression check vs previous run"),
        nbf.v4.new_code_cell('''for name in results:
    print(f"\\n== {name} ==")
    cli.main(["compare", name, "--history-dir", str(ROOT / "history"), "--threshold", str(m.defaults.regression_threshold_pct)])'''),
    ])


def build(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for name, nb in (("00_setup_wsl.ipynb", setup_nb()), ("01_run_all_benchmarks.ipynb", run_all_nb())):
        p = out_dir / name
        nbf.write(nb, str(p))
        out.append(p)
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for p in build(root / "notebooks"):
        print("wrote", p.relative_to(root))
    sys.exit(0)
```

- [ ] **Step 4: Generate + run tests**

Run: `pip install nbformat` (if missing) then `python scripts/build_notebooks.py && python -m pytest tests/test_notebooks.py -q` → `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_notebooks.py notebooks/00_setup_wsl.ipynb notebooks/01_run_all_benchmarks.ipynb tests/test_notebooks.py
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "feat: add generated setup and run-all notebooks

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 11: Docs update, full test pass, PR

**Files:**
- Modify: `README.md` (Quick Start + structure), `docs/pipeline.md`, `docs/configuration.md`, `.gitignore` (ensure `results/` stays, add `.ipynb_checkpoints/`), `CHANGELOG.md` (Unreleased entry)

- [ ] **Step 1: README Quick Start** — replace steps 4–5 with:

```markdown
# 4. Run every suite declared in algogauge.toml (add --skip-perf if perf is unavailable)
uv run algogauge run

# 5. Compare the last two runs of a suite (exit 1 on >10% median regression)
uv run algogauge compare base_strategy

# 6. Or do it all from Jupyter
uv run jupyter lab notebooks/
```
Add to Repository Structure: `algogauge.toml`, `python/algogauge/`, `notebooks/`, `history/`, `scripts/`. Add a line: "WSL2 users: `wsl -d Ubuntu -e sudo bash scripts/setup_wsl.sh`."

- [ ] **Step 2: docs/pipeline.md** — add a "Manifest-driven runner" section at the top describing `algogauge run`, the `--benchmark_display_aggregates_only` change and why (percentiles), the `history/<suite>.jsonl` record fields (copy the `Record` field list), validity rule (`cv_pct > 15` ⇒ invalid), and that perf failure now warns instead of aborting. Keep the existing stage table.

- [ ] **Step 3: docs/configuration.md** — add the `algogauge.toml` schema: `[defaults]` keys and `[[benchmark]]` keys with types and defaults (copy from Task 2 interface).

- [ ] **Step 4: .gitignore** — append:
```
.ipynb_checkpoints/
.pytest_cache/
__pycache__/
```

- [ ] **Step 5: CHANGELOG.md** — under a new `## Unreleased` heading:
```
### Feat
- `algogauge` Python package: manifest (`algogauge.toml`), runner, committed `history/`, `compare` regression check, CLI
- Notebooks 00 (WSL setup) and 01 (run all)
### Refactor
- `benchmark_pipeline.py` is now a shim over `algogauge.runner`; perf permission failure warns and skips instead of aborting
```

- [ ] **Step 6: Full test run**

Run: `python -m pytest -q` → all passed. Run `python scripts/build_notebooks.py` and confirm `git status` shows no notebook diff.

- [ ] **Step 7: Commit + push + PR**

```bash
git add README.md docs/pipeline.md docs/configuration.md .gitignore CHANGELOG.md
git -c user.name="John Riley" -c user.email="mr.jorge.fabio@gmail.com" commit -m "docs: document manifest runner, history and notebooks

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push -u origin feat/python-package-and-manifest
gh pr create --repo AlgoGators/algogauge --head feat/python-package-and-manifest --base main \
  --title "feat: algogauge Python package — manifest, runner, history, compare, notebooks (PR 1/6)" \
  --body "Implements spec §2, §3.4, §4, §5, §7 (notebooks 00/01), §9. Existing suites unchanged and still runnable via the manifest or the old shim. Tests: \`python -m pytest\` (all mocked, no WSL needed). Depends on #2 (spec). Next: PR 2 tick-to-trade suite.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

---

## Self-review

- **Spec coverage:** §2 layout (Tasks 1–10) ✓; §3.4 machine metadata + validity (Tasks 4–5) ✓; §4 manifest (Task 2 — Tier-1 entries deliberately added by PRs 2–4 when their binaries exist) ✓; §5 history + compare (Tasks 5–6, 8) ✓; §7 notebooks 00/01 (Task 10) ✓; §9 setup (Task 9) ✓; §10 Python tests ✓. Dashboard (§6) and notebooks 02–05 are PRs 5 and 2–4 — out of scope here by design.
- **Placeholders:** none; every file has full content.
- **Type consistency:** `Suite`/`Defaults` fields used identically in Tasks 2, 7, 8, 10; `Record` fields match between Task 5 and Task 8's `summary_markdown`; `run_suite` signature identical in Tasks 7, 8, 10; `gbench.BenchStat` constructor args identical in Tasks 3, 5, 6, 8 tests.
