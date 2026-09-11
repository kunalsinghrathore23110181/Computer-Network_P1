"""Paper Section 3.1 - a single long flow (Figures 3a, 3b and 3e).

Phase A ("levels") repeats Figure 3(a): optimisations are enabled one at a time
    no-opt   TSO, GSO and GRO off, MTU 1500 (every skb is one 1500-byte packet)
    tso-gro  + TSO/GSO at the sender and GRO at the receiver
    jumbo    + MTU 9000
    rfs      + Receive Flow Steering (software stand-in for aRFS; needs root)
Phase B ("buffers") repeats the throughput half of Figure 3(e): the TCP
buffer is fixed with iperf3 -w instead of Linux auto-tuning.

Sender application: CPU 0. Receiver application: CPU 2.
"""
import argparse
import random
import time

from common import (VethPair, cpu_metrics, environment_record, give_back,
                    idle_baseline, iperf_run, new_folder, preflight, save_csv,
                    save_json)

LEVELS = {
    "no-opt":  dict(tso=False, gro=False, mtu=1500, rfs=False),
    "tso-gro": dict(tso=True,  gro=True,  mtu=1500, rfs=False),
    "jumbo":   dict(tso=True,  gro=True,  mtu=9000, rfs=False),
    "rfs":     dict(tso=True,  gro=True,  mtu=9000, rfs=True),
}
BUFFER_LEVEL = "jumbo"
BUFFERS_KB = [100, 200, 400, 800, 1600, 3200]
SENDER, RECEIVER = 0, 2


def configure(pair, level):
    settings = LEVELS[level]
    pair.set_mtu(settings["mtu"])
    pair.set_offloads(settings["tso"], settings["tso"], settings["gro"])
    pair.set_rfs(settings["rfs"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--levels", default=",".join(LEVELS))
    parser.add_argument("--no-buffers", action="store_true")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    levels = args.levels.split(",")
    if set(levels) - set(LEVELS):
        raise SystemExit(f"Unknown level; choose from {list(LEVELS)}")

    preflight("exp_single_flow.py", ["ip", "ethtool", "iperf3", "mpstat", "taskset"])
    folder = new_folder("single-flow")
    rng = random.Random(42)

    schedule = [("levels", level, None, rep)
                for rep in range(1, args.reps + 1) for level in levels]
    rng.shuffle(schedule)
    if not args.no_buffers:
        buffers = [("buffers", BUFFER_LEVEL, kb, rep)
                   for rep in range(1, args.reps + 1) for kb in BUFFERS_KB]
        rng.shuffle(buffers)
        schedule += buffers

    rows, described = [], set()
    try:
        with VethPair("sf", "10.231.1") as pair:
            save_json(folder / "configuration.json", {
                "paper_section": "3.1 (Figures 3a, 3b, 3e)",
                "levels": {name: LEVELS[name] for name in levels},
                "buffer_phase_level": BUFFER_LEVEL,
                "buffers_kb": [] if args.no_buffers else BUFFERS_KB,
                "sender_cpu": SENDER, "receiver_cpu": RECEIVER,
                "warmup_omitted_seconds": 3, "measurement_seconds": args.seconds,
                "repetitions": args.reps, "random_seed": 42,
                "schedule": schedule,
                "environment": environment_record(),
                "idle_baseline": idle_baseline(folder),
            })
            for index, (phase, level, kb, rep) in enumerate(schedule, 1):
                label = f"{level}-r{rep}" if kb is None else f"buf{kb}k-r{rep}"
                print(f"[{index}/{len(schedule)}] {phase}: {label}", flush=True)
                configure(pair, level)
                if level not in described:
                    save_json(folder / f"setup-{level}.json", pair.describe())
                    described.add(level)
                result = iperf_run(pair, [(SENDER, RECEIVER, 5301)],
                                   folder / label, seconds=args.seconds,
                                   window=f"{kb}K" if kb else None)
                row = {"phase": phase, "level": level, "buffer_kb": kb or "",
                       "repeat": rep, "gbps": result["gbps"],
                       "retransmissions": result["retransmissions"]}
                row.update(cpu_metrics(result["gbps"], result["cpu"],
                                       [SENDER], [RECEIVER]))
                rows.append(row)
                save_csv(folder / "runs.csv", rows)
                print(f"  {row['gbps']:.2f} Gbps; CPU0 {row['cpu0_busy']:.0f}% "
                      f"CPU2 {row['cpu2_busy']:.0f}% busy; "
                      f"{row['tpc_total_gbps']:.1f} Gbps per busy core", flush=True)
                time.sleep(2)
        (folder / "COMPLETED.txt").write_text(f"{len(rows)} runs completed.\n")
        print(f"\nCOMPLETE: {folder}", flush=True)
    finally:
        give_back(folder)


if __name__ == "__main__":
    main()
