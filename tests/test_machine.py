from pathlib import Path

from algogauge import machine

ROOT = Path(__file__).resolve().parents[1]


def test_collect_has_all_keys_and_types():
    m = machine.collect(ROOT)
    assert set(m) == {
        "cpu_model",
        "cores",
        "os",
        "kernel",
        "python",
        "perf_event_paranoid",
        "algogauge_sha",
        "trade_ngin_sha",
        "hostname",
    }
    assert isinstance(m["cores"], int) and m["cores"] >= 1
    assert m["algogauge_sha"] != "unknown" and len(m["algogauge_sha"]) >= 7
    assert m["perf_event_paranoid"] is None or isinstance(m["perf_event_paranoid"], int)


def test_git_sha_unknown_for_non_repo(tmp_path):
    assert machine.git_sha(tmp_path) == "unknown"
