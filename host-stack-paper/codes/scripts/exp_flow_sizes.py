"""Paper Section 3.7 - short flows and mixed long/short workloads (Figs 10, 11).

Part A ("sizes", Figure 10): 16 ping-pong RPC connections (netperf TCP_RR,
request = response size, 4/16/32/64 KiB) from the sender host into ONE
receiver core (16:1 incast). Senders alternate over CPUs 0 and 1.
Part B ("mixed", Figure 11): one long flow (netperf TCP_STREAM) plus 0, 1, 4
or 16 4-KiB RPC flows, all on a single sender core (0) and a single
receiver core (2); plus 16 RPC flows alone for comparison.

netserver forks one worker per connection; every worker inherits CPU 2.
The bulk flow writes 128 KiB per call, the same as iperf3, so it is directly
comparable with the other experiments.
"""
import argparse
import random
import time

from common import (VethPair, cpu_metrics, environment_record, give_back,
                    idle_baseline, inside, new_folder, preflight, run,
                    save_csv, save_json, spawn, stop, cpu_usage)

PORT = 12867
RECEIVER = 2
CASES = (
    [("sizes", f"rpc-{size // 1024}KiB", 16, size, 0)
     for size in (4096, 16384, 32768, 65536)]
    + [("mixed", f"bulk-plus-{count}", count, 4096, 1) for count in (0, 1, 4, 16)]
    + [("mixed", "rpc-only-16", 16, 4096, 0)]
)


def scalar(path):
    value = float(path.read_text().split()[0])
    if not value > 0:
        raise RuntimeError(f"Invalid netperf result in {path}")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args()
    seconds = args.seconds

    preflight("exp_flow_sizes.py", ["ip", "netperf", "netserver", "mpstat", "taskset"])
    folder = new_folder("flow-sizes")
    rng = random.Random(42)
    rows, server = [], None
    try:
        with VethPair("fs", "10.231.4") as pair:
            save_json(folder / "configuration.json", {
                "paper_section": "3.7 (Figures 10 and 11)",
                "cases": CASES, "duration_seconds": seconds,
                "cpu_window": "seconds 2 .. duration-1 after launch",
                "repetitions": args.reps, "random_seed": 42,
                "sizes_sender_cpus": [0, 1], "mixed_sender_cpus": [0],
                "receiver_cpu": RECEIVER,
                "rpc": "netperf TCP_RR, one outstanding request per connection",
                "bulk": "netperf TCP_STREAM, 128 KiB writes",
                "netperf_version": run(["netperf", "-V"]).strip(),
                "setup": pair.describe(),
                "environment": environment_record(),
                "idle_baseline": idle_baseline(folder),
            })
            server_log = open(folder / "netserver.txt", "w")
            server = spawn(inside(pair.rx, "taskset", "-c", RECEIVER, "netserver",
                                  "-D", "-4", "-L", pair.rx_ip, "-p", PORT),
                           server_log)
            pair.wait_listening(PORT, server)

            schedule = []
            for phase in ("sizes", "mixed"):
                phase_cases = [case for case in CASES if case[0] == phase]
                for rep in range(1, args.reps + 1):
                    order = phase_cases.copy()
                    rng.shuffle(order)
                    schedule += [(case, rep) for case in order]

            for index, ((phase, label, count, size, bulk), rep) in enumerate(schedule, 1):
                prefix = f"{phase}-{label}-r{rep}"
                print(f"[{index}/{len(schedule)}] {prefix}", flush=True)
                jobs = [("bulk", 0, "TCP_STREAM")] if bulk else []
                jobs += [(f"rpc-{i:02d}", i % 2 if phase == "sizes" else 0, "TCP_RR")
                         for i in range(count)]
                senders = sorted({cpu for _, cpu, _ in jobs})

                processes, handles, outputs = [], [], []
                cpu_log = open(folder / f"{prefix}-cpu.txt", "w")
                handles.append(cpu_log)
                monitor = spawn(["mpstat", "-P", "ALL", "1"], cpu_log)
                try:
                    launch = time.time()
                    for name, cpu, test in jobs:
                        output = folder / f"{prefix}-{name}.txt"
                        out = open(output, "w")
                        err = open(folder / f"{prefix}-{name}-errors.txt", "w")
                        handles += [out, err]
                        command = inside(pair.tx, "taskset", "-c", cpu, "netperf",
                                         "-4", "-H", pair.rx_ip, "-p", PORT,
                                         "-l", seconds, "-t", test, "-P", 0, "-v", 0,
                                         "-f", "x" if test == "TCP_RR" else "m", "--")
                        command += (["-r", f"{size},{size}"] if test == "TCP_RR"
                                    else ["-m", 131072])
                        processes.append(spawn(command, out, err))
                        outputs.append((test, output))
                    save_json(folder / f"{prefix}-meta.json", {
                        "jobs": jobs, "launch_epoch": launch,
                        "cpu_window_epoch": [launch + 2, launch + seconds - 1]})
                    deadline = time.monotonic() + seconds + 30
                    for process, (_, output) in zip(processes, outputs):
                        process.wait(timeout=max(1, deadline - time.monotonic()))
                        if process.returncode != 0:
                            raise RuntimeError(f"netperf failed: {output.name}")
                finally:
                    for process in processes:
                        stop(process)
                    stop(monitor)
                    for handle in handles:
                        handle.close()

                rpc_tps = sum(scalar(o) for t, o in outputs if t == "TCP_RR")
                bulk_gbps = sum(scalar(o) for t, o in outputs if t == "TCP_STREAM") / 1000
                rpc_one_way = rpc_tps * size * 8 / 1e9
                # Application bytes the receiver core handles: bulk data in,
                # RPC requests in and RPC responses out.
                goodput = bulk_gbps + 2 * rpc_one_way
                row = {"phase": phase, "condition": label, "repeat": rep,
                       "rpc_flows": count, "message_bytes": size, "bulk_flows": bulk,
                       "rpc_tps": rpc_tps, "rpc_request_gbps": rpc_one_way,
                       "rpc_bidirectional_gbps": 2 * rpc_one_way,
                       "bulk_gbps": bulk_gbps, "goodput_gbps": goodput}
                cpu = cpu_usage(folder / f"{prefix}-cpu.txt",
                                launch + 2, launch + seconds - 1)
                row.update(cpu_metrics(goodput, cpu, senders, [RECEIVER]))
                rows.append(row)
                save_csv(folder / "runs.csv", rows)
                print(f"  RPC {rpc_tps:,.0f} trans/s; bulk {bulk_gbps:.2f} Gbps; "
                      f"receiver CPU2 {row['cpu2_busy']:.0f}% busy", flush=True)
                time.sleep(2)

        (folder / "COMPLETED.txt").write_text(f"{len(rows)} runs completed.\n")
        print(f"\nCOMPLETE: {folder}", flush=True)
    finally:
        stop(server)
        give_back(folder)


if __name__ == "__main__":
    main()
