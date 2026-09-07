"""Generate notebooks/*.ipynb deterministically. Run: python scripts/build_notebooks.py"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

BOOT = """import sys, pathlib
ROOT = pathlib.Path.cwd().resolve()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "python"))
import os; os.chdir(ROOT)
print("repo root:", ROOT)"""


def _nb(cells):
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
    }
    nb.cells = cells
    for i, c in enumerate(nb.cells):
        c["id"] = f"cell-{i:03d}"
    return nb


def setup_nb():
    return _nb(
        [
            nbf.v4.new_markdown_cell(
                "# 00 · Set up WSL2 for AlgoGauge\n\n"
                "Run this once on a fresh WSL2 Ubuntu 24.04. "
                "Step 1 needs `sudo`, so it is printed for you to run in a terminal; the rest runs here."
            ),
            nbf.v4.new_code_cell(BOOT),
            nbf.v4.new_markdown_cell(
                "## 1. System packages (run in a terminal, needs your password)"
            ),
            nbf.v4.new_code_cell(
                'print("wsl -d Ubuntu -e sudo bash", ROOT / "scripts" / "setup_wsl.sh")'
            ),
            nbf.v4.new_markdown_cell("## 2. Verify toolchain"),
            nbf.v4.new_code_cell(
                """import shutil, subprocess
for tool in ["g++", "cmake", "ninja", "perf", "uv", "git"]:
    print(f"{tool:<6}", shutil.which(tool) or "MISSING")
paranoid_path = pathlib.Path("/proc/sys/kernel/perf_event_paranoid")
print("perf_event_paranoid =", paranoid_path.read_text().strip() if paranoid_path.exists() else "n/a")"""
            ),
            nbf.v4.new_markdown_cell("## 3. Submodules + Python deps"),
            nbf.v4.new_code_cell(
                """subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
subprocess.run(["uv", "sync", "--extra", "dev"], check=True)"""
            ),
            nbf.v4.new_markdown_cell("## 4. Build benchmarks (Release)"),
            nbf.v4.new_code_cell(
                """subprocess.run(["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"], check=True)
subprocess.run(["cmake", "--build", "build", "--parallel"], check=True)"""
            ),
            nbf.v4.new_markdown_cell("## 5. Smoke run (no perf)"),
            nbf.v4.new_code_cell(
                """from algogauge import manifest, runner
m = manifest.load(ROOT / "algogauge.toml")
res = runner.run_suite(m.suites[0], m.defaults, ROOT, skip_perf=True)
print(res.run_id, len(res.records), "benchmarks recorded")"""
            ),
        ]
    )


def run_all_nb():
    return _nb(
        [
            nbf.v4.new_markdown_cell(
                "# 01 · Run all benchmark suites\n\n"
                "Runs every suite in `algogauge.toml`, appends to `history/`, and prints the headline "
                "numbers plus a Markdown table you can paste anywhere."
            ),
            nbf.v4.new_code_cell(BOOT),
            nbf.v4.new_code_cell(
                """SKIP_PERF = False   # set True to skip flamegraphs (faster; needed if perf is unavailable)
SUITES = None       # e.g. ["tick_to_trade"]; None = all"""
            ),
            nbf.v4.new_code_cell(
                """from algogauge import manifest, runner, cli
m = manifest.load(ROOT / "algogauge.toml")
results = {}
for s in m.suites:
    if SUITES and s.name not in SUITES:
        continue
    results[s.name] = runner.run_suite(s, m.defaults, ROOT, skip_perf=SKIP_PERF)"""
            ),
            nbf.v4.new_markdown_cell("## Summary"),
            nbf.v4.new_code_cell(
                """from IPython.display import Markdown, display
for name, res in results.items():
    display(Markdown(f"### {name}  (run `{res.run_id}`, perf={'on' if res.perf_ran else 'off'})\\n" + cli.summary_markdown(res.records)))"""
            ),
            nbf.v4.new_markdown_cell("## Regression check vs previous run"),
            nbf.v4.new_code_cell(
                """for name in results:
    print(f"\\n== {name} ==")
    cli.main(["compare", name, "--history-dir", str(ROOT / "history"), "--threshold", str(m.defaults.regression_threshold_pct)])"""
            ),
        ]
    )


def build(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for name, nb in (
        ("00_setup_wsl.ipynb", setup_nb()),
        ("01_run_all_benchmarks.ipynb", run_all_nb()),
    ):
        p = out_dir / name
        nbf.write(nb, str(p))
        out.append(p)
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for p in build(root / "notebooks"):
        print("wrote", p.relative_to(root))
    sys.exit(0)
