"""Paper Sections 3.1-3.5 - the five traffic patterns of Figure 2.

The paper uses up to 24 cores per server; the VM has 4 vCPUs, so each "host"
gets 2 CPUs (sender 0,1 and receiver 2,3) and the patterns are scaled down:
    single      0->2
    one-to-one  0->2, 1->3                (one unique receiver core per flow)
    incast      0->2, 1->2                (two flows share receiver core 2)
    outcast     0->2, 0->3                (two flows share sender core 0)
    all-to-all  0->2, 0->3, 1->2, 1->3    (every sender core to every receiver core)
Flow-count scaling (the x-axis of Figures 6 and 7):
    incast-4/8  4 or 8 flows into receiver core 2 (senders alternate 0,1)
    outcast-4/8 4 or 8 flows out of sender core 0 (receivers alternate 2,3)
Each flow is its own iperf3 client/server process pair, all started together.
Configuration: kernel defaults for veth (TSO/GSO on, GRO off, MTU 1500), CUBIC.
"""
import argparse
import random
import time

from common import (VethPair, cpu_metrics, environment_record, give_back,
                    idle_baseline, iperf_run, new_folder, preflight, save_csv,
                    save_json)

PATTERNS = {
    "single":     [(0, 2)],
    "one-to-one": [(0, 2), (1, 3)],
    "incast":     [(0, 2), (1, 2)],
    "outcast":    [(0, 2), (0, 3)],
    "all-to-all": [(0, 2), (0, 3), (1, 2), (1, 3)],
    "incast-4":   [(sender, 2) for sender in (0, 1) * 2],
    "incast-8":   [(sender, 2) for sender in (0, 1) * 4],
    "outcast-4":  [(0, receiver) for receiver in (2, 3) * 2],
    "outcast-8":  [(0, receiver) for receiver in (2, 3) * 4],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--patterns", default=",".join(PATTERNS))
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    patterns = args.patterns.split(",")
    if set(patterns) - set(PATTERNS):
        raise SystemExit(f"Unknown pattern; choose from {list(PATTERNS)}")

    preflight("exp_traffic_patterns.py", ["ip", "iperf3", "mpstat", "taskset"])
    folder = new_folder("traffic-patterns")

    # Interleave patterns in a random (seeded) order so slow drift in the
    # VM's background load does not favour whichever pattern ran first.
    schedule = [(name, rep) for rep in range(1, args.reps + 1) for name in patterns]
    random.Random(42).shuffle(schedule)

    rows = []
    try:
        with VethPair("tp", "10.231.2") as pair:
            save_json(folder / "configuration.json", {
                "paper_section": "3.1-3.5 (Figure 2 patterns; Figures 5-8)",
                "patterns": {name: PATTERNS[name] for name in patterns},
                "protocol": "TCP", "congestion_control": "cubic",
                "warmup_omitted_seconds": 3, "measurement_seconds": args.seconds,
                "repetitions": args.reps, "random_seed": 42,
                "schedule": schedule,
                "setup": pair.describe(),
                "environment": environment_record(),
                "idle_baseline": idle_baseline(folder),
            })
            for index, (name, rep) in enumerate(schedule, 1):
                flows = [(s, r, 5301 + i) for i, (s, r) in enumerate(PATTERNS[name])]
                print(f"[{index}/{len(schedule)}] {name} r{rep}: "
                      f"{len(flows)} flow(s)", flush=True)
                result = iperf_run(pair, flows, folder / f"{name}-r{rep}",
                                   seconds=args.seconds)
                senders = sorted({s for s, _, _ in flows})
                receivers = sorted({r for _, r, _ in flows})
                row = {"pattern": name, "flows": len(flows), "repeat": rep,
                       "gbps": result["gbps"],
                       "min_flow_gbps": min(result["flow_gbps"]),
                       "max_flow_gbps": max(result["flow_gbps"]),
                       "per_flow_gbps": " ".join(f"{g:.3f}" for g in result["flow_gbps"]),
                       "retransmissions": result["retransmissions"],
                       "launch_span_ms": result["launch_span_ms"],
                       "sender_cpus": " ".join(map(str, senders)),
                       "receiver_cpus": " ".join(map(str, receivers))}
                row.update(cpu_metrics(result["gbps"], result["cpu"],
                                       senders, receivers))
                rows.append(row)
                save_csv(folder / "runs.csv", rows)
                print(f"  {row['gbps']:.2f} Gbps total; "
                      f"{row['tpc_total_gbps']:.1f} Gbps per busy core; "
                      f"bottleneck side: {row['bottleneck_side']}", flush=True)
                time.sleep(2)
        (folder / "COMPLETED.txt").write_text(f"{len(rows)} runs completed.\n")
        print(f"\nCOMPLETE: {folder}", flush=True)
    finally:
        give_back(folder)


if __name__ == "__main__":
    main()
