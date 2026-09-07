import importlib.util
import json
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
ROOT = Path(__file__).resolve().parents[1]


def _load_build_notebooks():
    spec = importlib.util.spec_from_file_location("bn", ROOT / "scripts" / "build_notebooks.py")
    bn = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bn)
    return bn


def test_build_notebooks_roundtrip(tmp_path):
    bn = _load_build_notebooks()
    paths = bn.build(tmp_path)
    assert [p.name for p in paths] == ["00_setup_wsl.ipynb", "01_run_all_benchmarks.ipynb"]
    for p in paths:
        nb = nbformat.read(p, as_version=4)
        nbformat.validate(nb)
        src = "\n".join(c.source for c in nb.cells)
        assert "sys.path.insert" in src


def test_committed_notebooks_match_generator(tmp_path):
    bn = _load_build_notebooks()
    for p in bn.build(tmp_path):
        committed = json.loads((ROOT / "notebooks" / p.name).read_text(encoding="utf-8"))
        generated = json.loads(p.read_text(encoding="utf-8"))
        assert committed == generated, f"{p.name} is stale: run python scripts/build_notebooks.py"
