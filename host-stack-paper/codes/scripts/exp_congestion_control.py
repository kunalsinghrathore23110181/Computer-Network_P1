"""Paper Section 3.10 - congestion control algorithms (Figure 13).

One flow (sender CPU 0 -> receiver CPU 2) with CUBIC, BBR and DCTCP.
Both namespaces get an fq queue that marks packets with ECN "Congestion
Experienced" when they wait longer than 1 ms (DCTCP needs ECN marks; BBR
needs pacing, which fq provides). ECN is enabled in both namespaces.

The script checks the algorithm actually running on the live data socket
(`ss -ti` on the client's fixed source port) instead of trusting the request,
and for DCTCP checks that ECN was negotiated: a DCTCP socket without ECN
falls back to "dctcp-reno" and ss reports "fallback_mode".
BBR and DCTCP are kernel modules: run `sudo modprobe tcp_bbr tcp_dctcp` first
(scripts/run_all.sh does this).
"""
import argparse
import random
import re
import time

from common import (VethPair, cpu_metrics, environment_record, give_back,
                    idle_baseline, inside, iperf_run, new_folder, preflight,
                    run, save_csv, save_json)

SENDER, RECEIVER = 0, 2


def configure_queue(pair):
    for namespace, device in pair.ends():
        # Delete and re-add so the queue counters start at zero.
        run(inside(namespace, "tc", "qdisc", "del", "dev", device, "root"), check=False)
        run(inside(namespace, "tc", "qdisc", "add", "dev", device, "root", "fq",
                   "limit", "10000", "flow_limit", "1000", "ce_threshold", "1ms"))


def queue_state(pair):
    return {namespace: run(inside(namespace, "tc", "-s", "-d", "qdisc",
                                  "show", "dev", device))
            for namespace, device in pair.ends()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--algorithms", default="cubic,bbr,dctcp")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    algorithms = args.algorithms.split(",")

    preflight("exp_congestion_control.py", ["ip", "tc", "ss", "iperf3", "mpstat", "taskset"])
    available = run(["sysctl", "-n", "net.ipv4.tcp_available_congestion_control"]).split()
    missing = sorted(set(algorithms) - set(available))
    if missing:
        raise SystemExit(f"Not loaded: {missing}. Run: sudo modprobe "
                         + " ".join(f"tcp_{name}" for name in missing))

    folder = new_folder("congestion-control")
    schedule = []
    rng = random.Random(42)
    for rep in range(1, args.reps + 1):
        order = algorithms.copy()
        rng.shuffle(order)
        schedule += [(algorithm, rep) for algorithm in order]

    rows = []
    try:
        with VethPair("cc", "10.231.5") as pair:
            pair.sysctl("net.ipv4.tcp_ecn", 1)
            configure_queue(pair)
            save_json(folder / "configuration.json", {
                "paper_section": "3.10 (Figure 13)",
                "algorithms": algorithms, "sender_cpu": SENDER,
                "receiver_cpu": RECEIVER, "mtu": 1500,
                "queue": "fq limit 10000 flow_limit 1000 ce_threshold 1ms (both ends)",
                "ecn": "net.ipv4.tcp_ecn=1 in both namespaces",
                "warmup_omitted_seconds": 3, "measurement_seconds": args.seconds,
                "repetitions": args.reps, "schedule": schedule,
                "setup": pair.describe(),
                "environment": environment_record(),
                "idle_baseline": idle_baseline(folder),
            })
            for index, (algorithm, rep) in enumerate(schedule):
                label = f"{algorithm}-r{rep}"
                cport = 41000 + index
                print(f"[{index + 1}/{len(schedule)}] {label}", flush=True)
                pair.sysctl("net.ipv4.tcp_congestion_control", algorithm)
                configure_queue(pair)
                samples = []

                def sample_socket(clients):
                    # Inspect only the data socket, found by its fixed source port,
                    # once just after the warm-up and once mid-measurement.
                    for number, delay in ((1, 4), (2, args.seconds / 2)):
                        time.sleep(delay)
                        snapshot = run(inside(pair.tx, "ss", "-tinH",
                                              f"sport = :{cport}"))
                        (folder / f"{label}-socket-{number}.txt").write_text(snapshot)
                        samples.append(snapshot)

                result = iperf_run(pair, [(SENDER, RECEIVER, 5301)], folder / label,
                                   seconds=args.seconds, cc=algorithm,
                                   cport_base=cport, during=sample_socket)
                queues = queue_state(pair)
                save_json(folder / f"{label}-queue-after.json", queues)

                if not samples or not all(
                        re.search(rf"(?m)^\s*{re.escape(algorithm)}(\s|$)", s)
                        for s in samples):
                    raise RuntimeError(f"{label}: live algorithm not verified; "
                                       "inspect the saved socket files.")
                ecn_flag = all(re.search(r"\becn\b", s) for s in samples)
                dctcp_active = algorithm == "dctcp" and all(
                    "dctcp:(ce_state:" in s for s in samples)
                evidence = ("ss_ecn_flag" if ecn_flag else
                            "dctcp_not_in_fallback" if dctcp_active else "none")
                if algorithm == "dctcp" and evidence == "none":
                    raise RuntimeError(f"{label}: ECN not negotiated (DCTCP fell back).")
                ce_marks = sum(int(m) for m in re.findall(r"ce_mark (\d+)",
                                                          queues[pair.tx]))
                delivered_ce = re.findall(r"delivered_ce:(\d+)", samples[-1])

                row = {"algorithm": algorithm, "repeat": rep,
                       "gbps": result["gbps"],
                       "retransmissions": result["retransmissions"],
                       "ecn_evidence": evidence,
                       "fq_ce_marks_sender": ce_marks,
                       "delivered_ce_at_sample2": int(delivered_ce[0]) if delivered_ce else 0}
                row.update(cpu_metrics(result["gbps"], result["cpu"],
                                       [SENDER], [RECEIVER]))
                rows.append(row)
                save_csv(folder / "runs.csv", rows)
                print(f"  {row['gbps']:.2f} Gbps; {row['retransmissions']} retrans; "
                      f"CE marks {ce_marks}; ECN evidence: {evidence}", flush=True)
                time.sleep(2)
        (folder / "COMPLETED.txt").write_text(
            f"{len(rows)} runs completed; live algorithm checked on every run.\n")
        print(f"\nCOMPLETE: {folder}", flush=True)
    finally:
        give_back(folder)


if __name__ == "__main__":
    main()
