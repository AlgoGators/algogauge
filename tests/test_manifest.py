from pathlib import Path

import pytest

from algogauge import manifest


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "algogauge.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_applies_defaults_and_overrides(tmp_path):
    p = write(
        tmp_path,
        """
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
""",
    )
    m = manifest.load(p)
    assert m.defaults.repetitions == 7
    assert m.defaults.regression_threshold_pct == 10.0
    a, b = m.suites
    assert (a.name, a.kind, a.binary, a.repetitions, a.min_time, a.perf) == (
        "a",
        "gbench",
        "build/a",
        7,
        "1s",
        True,
    )
    assert (b.kind, b.script, b.args, b.perf, b.repetitions) == (
        "script",
        "python/b.py",
        ("--x", "1"),
        False,
        3,
    )
    assert m.get("b") is b


def test_get_unknown_raises(tmp_path):
    m = manifest.load(write(tmp_path, '[[benchmark]]\nname="a"\nkind="gbench"\nbinary="x"\n'))
    with pytest.raises(manifest.ManifestError, match="unknown suite 'zzz'"):
        m.get("zzz")


@pytest.mark.parametrize(
    "body,msg",
    [
        ('[[benchmark]]\nname="a"\nkind="gbench"\n', "requires 'binary'"),
        ('[[benchmark]]\nname="a"\nkind="script"\n', "requires 'script'"),
        ('[[benchmark]]\nname="a"\nkind="weird"\nbinary="x"\n', "kind must be"),
        ('[[benchmark]]\nkind="gbench"\nbinary="x"\n', "requires 'name'"),
        (
            '[[benchmark]]\nname="a"\nkind="gbench"\nbinary="x"\n[[benchmark]]\nname="a"\nkind="gbench"\nbinary="y"\n',
            "duplicate suite name",
        ),
    ],
)
def test_validation_errors(tmp_path, body, msg):
    with pytest.raises(manifest.ManifestError, match=msg):
        manifest.load(write(tmp_path, body))


def test_repo_manifest_loads_and_lists_existing_suites():
    m = manifest.load(Path(__file__).resolve().parents[1] / "algogauge.toml")
    names = {s.name for s in m.suites}
    assert {"base_strategy", "trend_following"} <= names
