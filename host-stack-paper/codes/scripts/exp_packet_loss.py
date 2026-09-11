"""Paper Section 3.6 - a single flow under random packet loss (Figure 9).

The paper puts a switch between the servers and makes it drop packets at
random with probability 0, 1.5e-4, 1.5e-3 and 1.5e-2. Here the receiver's
incoming traffic is redirected through an IFB device whose netem queue drops
packets at random with the same probabilities (0, 0.015%, 0.15%, 1.5%).

TSO, GSO and GRO are switched off on both veth ends. Otherwise a 64 KB
TSO/GSO "super-packet" would cross the veth whole and netem would drop 44
wire packets at once, which is not what a switch does.
The netem queue is deleted and re-created before every run so its packet and
drop counters start at zero; the measured loss rate is saved per run.
"""
import argparse
import json
import random
import time

from common import (VethPair, cpu_metrics, environment_record, give_back,
                    idle_baseline, inside, iperf_run, new_folder, preflight,
                    run, save_csv, save_json)

LOSSES = ["0", "0.015", "0.15", "1.5"]   # percent
SENDER, RECEIVER = 0, 2


def netem_counters(pair):
    stats = json.loads(run(inside(pair.rx, "tc", "-s", "-j", "qdisc",
                                  "show", "dev", "pl_ifb")))
    netem = next(q for q in stats if q.get("kind") == "netem")
    return netem["packets"], netem["drops"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()

    preflight("exp_packet_loss.py",
              ["ip", "tc", "ethtool", "iperf3", "mpstat", "taskset", "nstat"])
    folder = new_folder("packet-loss")
    schedule = [(loss, rep) for loss in LOSSES for rep in range(1, args.reps + 1)]
    random.Random(42).shuffle(schedule)

    rows = []
    try:
        with VethPair("pl", "10.231.3") as pair:
            pair.set_offloads(tso=False, gso=False, gro=False)
            run(["ip", "-n", pair.rx, "link", "add", "pl_ifb", "type", "ifb"])
            run(["ip", "-n", pair.rx, "link", "set", "pl_ifb", "up"])
            run(inside(pair.rx, "tc", "qdisc", "add", "dev", pair.dev_rx,
                       "handle", "ffff:", "ingress"))
            run(inside(pair.rx, "tc", "filter", "add", "dev", pair.dev_rx,
                       "parent", "ffff:", "protocol", "ip", "pref", "10",
                       "matchall", "action", "mirred", "egress", "redirect",
                       "dev", "pl_ifb"))
            save_json(folder / "configuration.json", {
                "paper_section": "3.6 (Figure 9)",
                "loss_percent": LOSSES, "sender_cpu": SENDER,
                "receiver_cpu": RECEIVER, "congestion_control": "cubic",
                "mtu": 1500, "offloads": "TSO/GSO/GRO off on both veth ends",
                "loss_placement": "receiver ingress -> IFB -> netem (data direction only)",
                "warmup_omitted_seconds": 3, "measurement_seconds": args.seconds,
                "repetitions": args.reps, "schedule": schedule,
                "qdisc_counters": "fresh for every run",
                "setup": pair.describe(),
                "environment": environment_record(),
                "idle_baseline": idle_baseline(folder),
            })
            for index, (loss, rep) in enumerate(schedule, 1):
                seed = 1000 + index
                label = f"loss-{loss}-r{rep}"
                print(f"[{index}/{len(schedule)}] loss {loss}% r{rep}", flush=True)
                run(inside(pair.rx, "tc", "qdisc", "del", "dev", "pl_ifb", "root"),
                    check=False)
                run(inside(pair.rx, "tc", "qdisc", "add", "dev", "pl_ifb", "root",
                           "netem", "limit", "10000",
                           "loss", "random", f"{loss}%", "seed", seed))
                for namespace in (pair.tx, pair.rx):
                    (folder / f"{label}-nstat-before-{namespace}.txt").write_text(
                        run(inside(namespace, "nstat", "-asz")))
                (folder / f"{label}-softnet-before.txt").write_text(
                    open("/proc/net/softnet_stat").read())

                result = iperf_run(pair, [(SENDER, RECEIVER, 5301)],
                                   folder / label, seconds=args.seconds)

                for namespace in (pair.tx, pair.rx):
                    (folder / f"{label}-nstat-after-{namespace}.txt").write_text(
                        run(inside(namespace, "nstat", "-asz")))
                (folder / f"{label}-softnet-after.txt").write_text(
                    open("/proc/net/softnet_stat").read())
                (folder / f"{label}-qdisc.json").write_text(run(inside(
                    pair.rx, "tc", "-s", "-j", "qdisc", "show", "dev", "pl_ifb")))
                packets, drops = netem_counters(pair)

                row = {"loss_percent": float(loss), "repeat": rep, "seed": seed,
                       "gbps": result["gbps"],
                       "retransmissions": result["retransmissions"],
                       "netem_packets": packets, "netem_drops": drops,
                       "measured_loss_percent": 100 * drops / max(1, packets + drops)}
                row.update(cpu_metrics(result["gbps"], result["cpu"],
                                       [SENDER], [RECEIVER]))
                rows.append(row)
                save_csv(folder / "runs.csv", rows)
                print(f"  {row['gbps']:.2f} Gbps; measured loss "
                      f"{row['measured_loss_percent']:.4f}%; "
                      f"{row['retransmissions']} retransmissions", flush=True)
                time.sleep(2)
        (folder / "COMPLETED.txt").write_text(f"{len(rows)} runs completed.\n")
        print(f"\nCOMPLETE: {folder}", flush=True)
    finally:
        give_back(folder)


if __name__ == "__main__":
    main()
