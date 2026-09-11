#!/usr/bin/env bash
# Print the facts about this machine that the results depend on.
# Usage: bash scripts/record_environment.sh > notes/environment.txt

section() { printf '\n%s\n' "$1"; }

echo "Recorded: $(date --iso-8601=seconds)"
section "OPERATING SYSTEM";  uname -a; grep -E '^(PRETTY_NAME|VERSION)=' /etc/os-release
section "VIRTUALISATION";    systemd-detect-virt 2>/dev/null || echo unknown
section "CPU";               lscpu | grep -E '^(Architecture|CPU\(s\)|Vendor ID|Model name|Thread|Core|Socket|NUMA node|L[123])'
section "MEMORY";            free -h
section "PERFORMANCE COUNTERS"
ls /sys/bus/event_source/devices/
echo "(no cpu/armv8 PMU entry = no hardware cache-miss counters in this VM)"
section "TCP SETTINGS"
sysctl net.ipv4.tcp_available_congestion_control net.ipv4.tcp_congestion_control \
       net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.core.rmem_max net.core.wmem_max \
       net.core.netdev_max_backlog net.core.default_qdisc
section "TOOLS"
for tool in iperf3 netperf mpstat perf ethtool tc; do
    printf '%-8s ' "$tool"; command -v "$tool" || echo MISSING
done
iperf3 --version | head -1
netperf -V
mpstat -V 2>&1 | head -1
