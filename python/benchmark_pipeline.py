import sys
import subprocess
import datetime
from pathlib import Path


def run_command(cmd, stdout_file=None):
    """Run a shell command with optional stdout teeing."""
    print(f"Running: {' '.join(cmd)}")

    if stdout_file:
        with open(stdout_file, "w") as f:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            if process.stdout is None:
                raise RuntimeError("Failed to capture stdout")
            for line in process.stdout:
                print(line, end="")
                f.write(line)
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
    else:
        subprocess.run(cmd, check=True)


def check_perf_permissions():
    try:
        paranoid = Path("/proc/sys/kernel/perf_event_paranoid").read_text().strip()
        if paranoid != "0":
            raise RuntimeError(
                "perf_event_paranoid must be 0. Run:\n"
                "sudo sysctl -w kernel.perf_event_paranoid=1"
            )
    except FileNotFoundError:
        raise RuntimeError("Cannot read perf_event_paranoid")

    try:
        kptr = Path("/proc/sys/kernel/kptr_restrict").read_text().strip()
        if kptr != "0":
            raise RuntimeError(
                "kptr_restrict must be 0. Run:\n"
                "sudo sysctl -w kernel.kptr_restrict=0"
            )
    except FileNotFoundError:
        raise RuntimeError("Cannot read kptr_restrict")


def main():
    if len(sys.argv) < 2:
        print("usage: run_benchmark_pipeline.py <benchmark_binary>")
        sys.exit(1)

    bin_path = Path(sys.argv[1])
    name = bin_path.name

    if not bin_path.exists():
        print(f"Error: binary not found: {bin_path}")
        sys.exit(1)

    check_perf_permissions()

    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_dir = Path("results") / name / run_id
    result_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running benchmark: {name}")
    print(f"Results directory: {result_dir}")

    # --- Google Benchmark ---
    run_command(
        [
            str(bin_path),
            f"--benchmark_out={result_dir}/benchmark.json",
            "--benchmark_out_format=json",
            "--benchmark_min_time=5s",
            "--benchmark_repetitions=30",
            "--benchmark_report_aggregates_only=true",
        ],
        stdout_file=result_dir / "benchmark.txt",
    )

    # --- perf record ---
    run_command(
        [
            "perf",
            "record",
            "-F",
            "999",
            "-g",
            "-o",
            str(result_dir / "perf.data"),
            "--",
            str(bin_path),
            "--benchmark_min_time=5s",
        ]
    )

    # --- perf script ---
    run_command(
        [
            "perf",
            "script",
            "-i",
            str(result_dir / "perf.data"),
        ],
        stdout_file=result_dir / "perf.script",
    )

    # --- stack collapse ---
    run_command(
        [
            "tools/FlameGraph/stackcollapse-perf.pl",
            str(result_dir / "perf.script"),
        ],
        stdout_file=result_dir / "perf.folded",
    )

    # --- flamegraph ---
    run_command(
        [
            "tools/FlameGraph/flamegraph.pl",
            str(result_dir / "perf.folded"),
        ],
        stdout_file=result_dir / "flamegraph.svg",
    )

    print("\nBenchmark complete")
    print(f"Results stored in:\n{result_dir}")


if __name__ == "__main__":
    main()
