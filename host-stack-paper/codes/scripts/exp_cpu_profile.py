"""Paper Table 1 and Figures 3(c)/3(d) - where do the CPU cycles go?

For each single-flow optimisation level (see exp_single_flow.py) this runs a
flow, samples the sender core (CPU 0) and receiver core (CPU 2) with
`perf record -e cpu-clock` for 10 s of the steady state, and sorts every
kernel function into the paper's eight categories (Table 1).
Idle samples are removed before computing fractions, as in the paper.

perf needs real root; it does not work inside an unprivileged namespace.
The VM exposes no hardware PMU, so cpu-clock (timer) sampling is used;
cache-miss counters (Figures 3e, 4, 6c) are not available at all.
"""
import argparse
from collections import Counter
import re
import subprocess
import time

from common import (VethPair, environment_record, give_back, iperf_run,
                    new_folder, preflight, run, save_csv, save_json)
from exp_single_flow import LEVELS, configure

SENDER, RECEIVER = 0, 2
CATEGORIES = ["data copy", "tcp/ip processing", "netdevice subsystem",
              "skb mgmt", "memory alloc/dealloc", "lock/unlock",
              "scheduling", "etc."]

# First matching rule wins, so specific rules come before generic ones
# (e.g. tcp_gro_receive is GRO, i.e. netdevice, not tcp/ip).
RULES = [
    ("idle", r"default_idle_call|cpu_idle_poll|arch_cpu_idle|^do_idle|"
             r"cpuidle_|cpu_do_idle|^psci_|^wfi"),
    ("data copy", r"copy_(to|from)_user|__arch_copy|copy_user|_copy_(to|from)_iter|"
                  r"skb_copy_datagram|simple_copy_to_iter|__skb_datagram_iter|"
                  r"csum_partial_copy|^__?memcpy|^copy_page"),
    ("lock/unlock", r"spin_lock|spin_unlock|_raw_\w*lock|lock_sock|release_sock|"
                    r"mutex|rwsem|queued_\w*lock"),
    ("scheduling", r"schedule|sched_|__switch_to|context_switch|finish_task_switch|"
                   r"try_to_wake_up|wake_up|ttwu|enqueue_task|dequeue_task|"
                   r"pick_next|update_curr|update_load|select_task_rq|"
                   r"sk_wait_data|wait_woken|woken_wake|set_next_entity|put_prev"),
    ("memory alloc/dealloc", r"alloc_skb|kmem_cache|kmalloc|^kfree$|^kvfree|slab|slub|"
                             r"alloc_pages|free_pages|free_unref|__free_page|"
                             r"get_page_from_freelist|rmqueue|page_frag|folio|"
                             r"page_pool|mem_cgroup|memcg|lruvec|refill_stock|"
                             r"sk_mem_|__sk_mem|put_page|free_pcppages"),
    ("netdevice subsystem", r"^dev_|^__dev_|netif_|napi|net_rx_action|process_backlog|"
                            r"gro|gso|qdisc|^sch_|^fq_|veth|netdev|validate_xmit|"
                            r"skb_segment|ifb|netem|mirred|tcf_|enqueue_to_backlog|"
                            r"rps_|flow_dissect|^eth_"),
    ("tcp/ip processing", r"tcp|^ip_|^__ip|ipv4|inet|^raw_|udp|icmp|^nf_|netfilter|"
                          r"sock_|^sk_|^__sk_|^rt_|dst_|fib|neigh|csum|checksum"),
    ("skb mgmt", r"skb"),
]
RULES = [(name, re.compile(pattern)) for name, pattern in RULES]
LINE = re.compile(r"^\s*(?P<comm>.*?)\s+\[(?P<cpu>\d+)\]\s+(?P<ip>[0-9a-f]+)\s+"
                  r"(?P<sym>.+?)\s+\((?P<dso>[^()]*)\)\s*$")


def categorize(symbol, dso):
    if "kernel" not in dso and not dso.startswith("["):
        return "etc."          # user-space code of iperf3 / libc
    for name, pattern in RULES:
        if pattern.search(symbol):
            return name
    return "etc."


def breakdown(perf_script_text):
    """Return {cpu: Counter(category)} and {cpu: Counter(symbol)}."""
    categories, symbols = {}, {}
    for line in perf_script_text.splitlines():
        match = LINE.match(line)
        if not match:
            continue
        cpu = int(match["cpu"])
        symbol = match["sym"].split("+0x")[0]
        category = categorize(symbol, match["dso"])
        categories.setdefault(cpu, Counter())[category] += 1
        symbols.setdefault(cpu, Counter())[(symbol, category)] += 1
    return categories, symbols


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--levels", default=",".join(LEVELS))
    parser.add_argument("--seconds", type=int, default=15)
    args = parser.parse_args()
    levels = args.levels.split(",")

    preflight("exp_cpu_profile.py", ["ip", "ethtool", "iperf3", "mpstat", "perf"])
    folder = new_folder("cpu-profile")
    probe = subprocess.run(["perf", "record", "-e", "cpu-clock", "-a", "-o",
                            str(folder / "probe.data"), "--", "sleep", "0.2"],
                           capture_output=True, text=True)
    (folder / "probe.data").unlink(missing_ok=True)
    if probe.returncode != 0:
        raise SystemExit("perf cannot sample this system:\n" + probe.stderr)

    rows, top = [], []
    try:
        with VethPair("pf", "10.231.6") as pair:
            save_json(folder / "configuration.json", {
                "paper_section": "Table 1; Figures 3(c) and 3(d)",
                "levels": {name: LEVELS[name] for name in levels},
                "event": "cpu-clock at 999 Hz on CPUs 0 and 2, 10 s of steady state",
                "categories": CATEGORIES,
                "rules": [(name, pattern.pattern) for name, pattern in RULES],
                "environment": environment_record(),
            })
            for level in levels:
                print(f"Profiling level {level}", flush=True)
                configure(pair, level)
                data = folder / f"{level}.perf.data"

                def record(clients):
                    time.sleep(4)   # skip slow start and iperf3's 3 s warm-up
                    run(["perf", "record", "-e", "cpu-clock", "-F", 999,
                         "-C", f"{SENDER},{RECEIVER}", "-o", data, "--",
                         "sleep", 10], timeout=60)

                result = iperf_run(pair, [(SENDER, RECEIVER, 5301)], folder / level,
                                   seconds=args.seconds, during=record)
                text = run(["perf", "script", "-i", data, "-F", "comm,cpu,ip,sym,dso"],
                           timeout=600)
                (folder / f"{level}.perf-script.txt").write_text(text)
                categories, symbols = breakdown(text)
                for cpu, role in ((SENDER, "sender"), (RECEIVER, "receiver")):
                    counts = categories.get(cpu, Counter())
                    busy = sum(counts.values()) - counts["idle"]
                    row = {"level": level, "cpu": cpu, "role": role,
                           "gbps_during_profile": result["gbps"],
                           "samples": sum(counts.values()),
                           "idle_fraction": counts["idle"] / max(1, sum(counts.values()))}
                    row.update({name: counts[name] / max(1, busy) for name in CATEGORIES})
                    rows.append(row)
                    for (symbol, category), count in symbols.get(cpu, Counter()).most_common(30):
                        top.append({"level": level, "cpu": cpu, "role": role,
                                    "symbol": symbol, "category": category,
                                    "fraction_of_all_samples": count / max(1, sum(counts.values()))})
                save_csv(folder / "breakdown.csv", rows)
                save_csv(folder / "top-symbols.csv", top)
                data.unlink()   # large; the text export is kept
                time.sleep(2)
        (folder / "COMPLETED.txt").write_text(f"{len(levels)} levels profiled.\n")
        print(f"\nCOMPLETE: {folder}", flush=True)
    finally:
        give_back(folder)


if __name__ == "__main__":
    main()
