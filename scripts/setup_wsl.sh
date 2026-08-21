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
