#!/usr/bin/env bash
# Live demo for the presentation (about 3 minutes including talking).
# Two "hosts" in one VM joined by a veth cable; one TCP flow with offloads
# OFF then ON; then two flows into one receiver core (incast).
# After each flow it prints the throughput and how busy CPU0/CPU1/CPU2 were.
#
#   sudo bash scripts/demo.sh            # pauses before every step
#   sudo DEMO_AUTO=1 bash scripts/demo.sh   # no pauses
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run: sudo bash scripts/demo.sh"; exit 1; }
export LC_ALL=C

TX=demo_tx RX=demo_rx
if ip netns list | grep -qE "^($TX|$RX)( |$)"; then
    echo "$TX or $RX already exists (an earlier demo?). Remove it first:"
    echo "  sudo ip netns del $TX; sudo ip netns del $RX"
    exit 1
fi
LOG=$(mktemp -d)
cleanup() {
    ip netns del "$TX" 2>/dev/null || true
    ip netns del "$RX" 2>/dev/null || true
    rm -rf "$LOG"
}
trap cleanup EXIT

step() {
    printf '\n\033[1;34m== %s\033[0m\n' "$1"
    [[ -n "${DEMO_AUTO:-}" ]] || read -rp "   (press Enter) "
}
show() {   # print the command, then run it
    printf '\033[2m$ %s\033[0m\n' "$*" >&2
    "$@"
}
cpu_report() {   # average busy % and softirq % of the given CPUs
    awk -v cpus="$1" 'BEGIN { split(cpus, c, ","); for (i in c) want[c[i]] = 1 }
        $1 == "Average:" && ($2 in want) {
            printf "   CPU%s: %5.1f %% busy (softirq %4.1f %%)\n", $2, 100 - $NF, $8 }' "$LOG/mpstat.txt"
}
gbps() { awk '/receiver/ { print "   " $(NF-2), $(NF-1), "received" }' "$1"; }

step "1. Create two hosts (network namespaces) and a virtual cable (veth)"
show ip netns add $TX
show ip netns add $RX
show ip -n $TX link add demo_tx0 type veth peer name demo_rx0 netns $RX
show ip -n $TX address add 10.99.0.1/24 dev demo_tx0
show ip -n $RX address add 10.99.0.2/24 dev demo_rx0
show ip -n $TX link set demo_tx0 up
show ip -n $RX link set demo_rx0 up
show ip netns exec $TX ping -c 2 -q 10.99.0.2 | tail -n 2

one_flow() {
    ip netns exec $RX taskset -c 2 iperf3 -s -1 -B 10.99.0.2 >/dev/null &
    sleep 0.5
    mpstat -P 0,2 1 8 > "$LOG/mpstat.txt" &
    show ip netns exec $TX taskset -c 0 iperf3 -c 10.99.0.2 -t 8 -f g > "$LOG/flow.txt"
    wait
    gbps "$LOG/flow.txt"
    cpu_report 0,2
}

step "2. One TCP flow (sender CPU0 -> receiver CPU2) with TSO/GSO/GRO OFF: every 1500-byte packet is processed on its own"
for side in tx rx; do
    show ip netns exec demo_$side ethtool -K demo_${side}0 tso off gso off gro off
done
one_flow

step "3. The same flow with TSO/GSO/GRO ON: the stack works with 64 KB packets"
for side in tx rx; do
    show ip netns exec demo_$side ethtool -K demo_${side}0 tso on gso on gro on
done
one_flow

step "4. Incast: two flows (from CPU0 and CPU1) into ONE receiver core, CPU2"
for port in 5201 5202; do
    ip netns exec $RX taskset -c 2 iperf3 -s -1 -B 10.99.0.2 -p $port >/dev/null &
done
sleep 0.5
mpstat -P 0,1,2 1 8 > "$LOG/mpstat.txt" &
show ip netns exec $TX taskset -c 0 iperf3 -c 10.99.0.2 -p 5201 -t 8 -f g > "$LOG/a.txt" &
show ip netns exec $TX taskset -c 1 iperf3 -c 10.99.0.2 -p 5202 -t 8 -f g > "$LOG/b.txt" &
wait
gbps "$LOG/a.txt"
gbps "$LOG/b.txt"
cpu_report 0,1,2

step "Done. The namespaces are deleted automatically."
