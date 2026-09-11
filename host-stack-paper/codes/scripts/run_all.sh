#!/usr/bin/env bash
# Run every experiment with the corrected scripts (about 70 minutes), then
# rebuild all graphs and tables.   Usage:  sudo bash scripts/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ $EUID -ne 0 ]]; then
    echo "Run: sudo bash scripts/run_all.sh"
    exit 1
fi

echo "Close VS Code, the browser and Docker first: anything else running"
echo "competes with the experiment for the same 4 vCPUs."
sleep 5

# BBR and DCTCP are kernel modules that are not loaded by default.
modprobe tcp_bbr
modprobe tcp_dctcp

bash scripts/record_environment.sh > notes/environment.txt

python3 scripts/exp_single_flow.py          # Section 3.1, Figures 3a/3b/3e
python3 scripts/exp_traffic_patterns.py     # Sections 3.1-3.5, Figures 5-8
python3 scripts/exp_packet_loss.py          # Section 3.6, Figure 9
python3 scripts/exp_flow_sizes.py           # Section 3.7, Figures 10-11
python3 scripts/exp_congestion_control.py   # Section 3.10, Figure 13
python3 scripts/exp_cpu_profile.py          # Table 1, Figures 3c/3d

chown -R "${SUDO_UID:-0}:${SUDO_GID:-0}" notes results
sudo -u "${SUDO_USER:-root}" python3 scripts/analyze.py
