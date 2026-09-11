"""Shared helpers for the single-VM reproduction of
Cai et al., "Understanding Host Network Stack Overheads", SIGCOMM 2021.

Every experiment builds two fresh network namespaces - a "sender host" and a
"receiver host" - joined by a veth pair (the "cable"), pins every application
to a CPU with taskset, records per-CPU utilisation with mpstat and deletes the
namespaces again when it finishes.

CPU layout used by all experiments on the 4-vCPU VM:
    sender host   -> CPUs 0 and 1
    receiver host -> CPUs 2 and 3
"""
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
ENV = dict(os.environ, LC_ALL="C")

SENDER_CPUS = (0, 1)
RECEIVER_CPUS = (2, 3)
RFS_ENTRIES = Path("/proc/sys/net/core/rps_sock_flow_entries")


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------

def run(args, check=True, timeout=30):
    args = [str(arg) for arg in args]
    result = subprocess.run(
        args, text=True, capture_output=True, timeout=timeout, env=ENV
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(args)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


def inside(namespace, *args):
    return ["ip", "netns", "exec", namespace, *map(str, args)]


def preflight(script, tools, cpus=(0, 1, 2, 3)):
    if os.geteuid() != 0:
        raise SystemExit(f"Run: sudo python3 scripts/{script}")
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")
    if not set(cpus) <= os.sched_getaffinity(0):
        raise SystemExit(f"CPUs {sorted(cpus)} must be available.")


def new_folder(name):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = RESULTS / f"{name}-{stamp}"
    folder.mkdir(parents=True)
    print(f"Results: {folder}", flush=True)
    return folder


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def save_csv(path, rows):
    fields = []
    for row in rows:
        fields += [key for key in row if key not in fields]
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def give_back(folder):
    """Files written under sudo belong to root; return them to the user."""
    if "SUDO_UID" not in os.environ or not Path(folder).exists():
        return
    uid, gid = int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"])
    for path in [Path(folder), *Path(folder).rglob("*")]:
        os.chown(path, uid, gid)


def spawn(args, stdout, stderr=subprocess.STDOUT):
    # A new session lets stop() kill forked children too (netserver).
    return subprocess.Popen(
        [str(arg) for arg in args], stdout=stdout, stderr=stderr,
        env=ENV, start_new_session=True,
    )


def stop(process):
    if process is None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=3)
            break
        except subprocess.TimeoutExpired:
            continue
    process.wait()


def environment_record():
    record = {
        "kernel": os.uname().release,
        "machine": os.uname().machine,
        "cpus": os.cpu_count(),
        "iperf3": run(["iperf3", "--version"], check=False).splitlines()[0],
        "started": datetime.now().isoformat(timespec="seconds"),
    }
    for key in ("net.ipv4.tcp_rmem", "net.ipv4.tcp_wmem", "net.core.rmem_max",
                "net.core.wmem_max", "net.core.netdev_max_backlog"):
        # Global (non-namespaced) keys are invisible inside a user namespace.
        record[key] = run(["sysctl", "-n", key], check=False).strip() or "unavailable"
    return record


def idle_baseline(folder, seconds=5):
    """Record background CPU load before the experiment starts.

    Everything else running in the VM (editor, browser, Docker) competes
    with the experiment, so the report states how busy the CPUs were idle.
    """
    text = run(["mpstat", "-P", "ALL", "1", seconds], timeout=seconds + 10)
    (folder / "idle-baseline-cpu.txt").write_text(text)
    now = time.time()
    return cpu_usage(folder / "idle-baseline-cpu.txt", now - seconds - 2, now + 1)


# --------------------------------------------------------------------------
# The two "hosts"
# --------------------------------------------------------------------------

class VethPair:
    """Two namespaces joined by one veth pair: sender (tx) and receiver (rx)."""

    def __init__(self, prefix, subnet):
        self.tx, self.rx = f"{prefix}_tx", f"{prefix}_rx"
        self.dev_tx, self.dev_rx = f"{prefix}_tx0", f"{prefix}_rx0"
        self.tx_ip, self.rx_ip = f"{subnet}.1", f"{subnet}.2"
        self.created = []
        self.rfs_original = None

    def ends(self):
        return ((self.tx, self.dev_tx), (self.rx, self.dev_rx))

    def __enter__(self):
        existing = {
            line.split()[0]
            for line in run(["ip", "netns", "list"]).splitlines() if line.strip()
        }
        if {self.tx, self.rx} & existing:
            raise SystemExit(
                f"Namespace {self.tx} or {self.rx} already exists. Another "
                "experiment may be running; delete it only if you know it is stale:\n"
                f"  sudo ip netns delete {self.tx}; sudo ip netns delete {self.rx}"
            )
        try:
            for namespace in (self.tx, self.rx):
                run(["ip", "netns", "add", namespace])
                self.created.append(namespace)
                run(["ip", "-n", namespace, "link", "set", "lo", "up"])
            run(["ip", "-n", self.tx, "link", "add", self.dev_tx, "type", "veth",
                 "peer", "name", self.dev_rx, "netns", self.rx])
            for (namespace, device), address in zip(
                    self.ends(), (self.tx_ip, self.rx_ip)):
                run(["ip", "-n", namespace, "address", "add",
                     f"{address}/24", "dev", device])
                run(["ip", "-n", namespace, "link", "set", device, "up"])
            run(inside(self.tx, "ping", "-c", "1", "-W", "2", self.rx_ip))
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self, *exc):
        if self.rfs_original is not None:
            RFS_ENTRIES.write_text(self.rfs_original + "\n")
            self.rfs_original = None
        for namespace in reversed(self.created):
            run(["ip", "netns", "delete", namespace], check=False)
        self.created = []

    # --- configuration ------------------------------------------------------

    def set_mtu(self, mtu):
        for namespace, device in self.ends():
            run(["ip", "-n", namespace, "link", "set", device, "mtu", mtu])

    def set_offloads(self, tso, gso, gro):
        wanted = {"tcp-segmentation-offload": tso,
                  "generic-segmentation-offload": gso,
                  "generic-receive-offload": gro}
        for namespace, device in self.ends():
            run(inside(namespace, "ethtool", "-K", device,
                       "tso", "on" if tso else "off",
                       "gso", "on" if gso else "off",
                       "gro", "on" if gro else "off"))
            text = run(inside(namespace, "ethtool", "-k", device))
            for feature, enabled in wanted.items():
                state = re.search(rf"(?m)^{feature}: (\w+)", text)
                if not state or state.group(1) != ("on" if enabled else "off"):
                    raise RuntimeError(f"Cannot verify {feature} on {device}")

    def set_rfs(self, enabled):
        """Receive Flow Steering, the software form of the paper's aRFS.

        With RFS the kernel processes an incoming packet on the CPU where the
        receiving application last ran. Without it, veth processes received
        packets on the CPU that transmitted them. Needs real root: the flow
        table size is a global (init-namespace) setting.
        """
        if not enabled and self.rfs_original is None:
            return          # never enabled: nothing to undo
        count = 32768 if enabled else 0
        if enabled and self.rfs_original is None:
            self.rfs_original = RFS_ENTRIES.read_text().strip()
        for namespace, device in self.ends():
            run(inside(namespace, "sh", "-c",
                       f"echo {count} > /sys/class/net/{device}/queues/rx-0/rps_flow_cnt"))
        if enabled:
            RFS_ENTRIES.write_text(f"{count}\n")
        elif self.rfs_original is not None:
            RFS_ENTRIES.write_text(self.rfs_original + "\n")
            self.rfs_original = None

    def sysctl(self, key, value):
        for namespace in (self.tx, self.rx):
            run(inside(namespace, "sysctl", "-qw", f"{key}={value}"))

    def describe(self):
        record = {}
        for namespace, device in self.ends():
            record[namespace] = {
                "link": run(["ip", "-n", namespace, "-d", "link", "show", device]),
                "offloads": run(inside(namespace, "ethtool", "-k", device)),
                "qdisc": run(inside(namespace, "tc", "qdisc", "show", "dev", device)),
                "congestion_control": run(inside(
                    namespace, "sysctl", "-n",
                    "net.ipv4.tcp_congestion_control")).strip(),
            }
        return record

    def listening(self, port):
        output = run(inside(self.rx, "ss", "-ltnH"))
        return any(
            len(line.split()) > 3 and line.split()[3].endswith(f":{port}")
            for line in output.splitlines()
        )

    def wait_listening(self, port, server, seconds=10):
        deadline = time.monotonic() + seconds
        while not self.listening(port):
            if server.poll() is not None:
                raise RuntimeError(f"Server on port {port} exited; read its log.")
            if time.monotonic() > deadline:
                raise RuntimeError(f"Server on port {port} did not start.")
            time.sleep(0.1)


# --------------------------------------------------------------------------
# iperf3 flows
# --------------------------------------------------------------------------

def iperf_run(pair, flows, prefix, seconds=15, omit=3, cc="cubic",
              window=None, cport_base=None, during=None):
    """Run one iperf3 client/server process pair per flow, all at once.

    flows: list of (sender_cpu, receiver_cpu, port).
    Writes <prefix>-flow-<port>.json, <prefix>-cpu.txt and <prefix>-meta.json
    and returns a per-run record with throughput and per-CPU utilisation.
    """
    prefix = Path(prefix)
    processes, handles, clients, launches = [], [], [], []
    try:
        for _, receiver_cpu, port in flows:
            log = open(f"{prefix}-server-{port}.txt", "w")
            handles.append(log)
            server = spawn(inside(pair.rx, "taskset", "-c", receiver_cpu,
                                  "iperf3", "-s", "-1", "-B", pair.rx_ip,
                                  "-p", port), log)
            processes.append(server)
            pair.wait_listening(port, server)

        cpu_log = open(f"{prefix}-cpu.txt", "w")
        handles.append(cpu_log)
        processes.append(spawn(["mpstat", "-P", "ALL", "1"], cpu_log))

        for index, (sender_cpu, _, port) in enumerate(flows):
            args = inside(pair.tx, "taskset", "-c", sender_cpu, "iperf3",
                          "-c", pair.rx_ip, "-B", pair.tx_ip, "-p", port,
                          "-P", 1, "-C", cc, "-O", omit, "-t", seconds,
                          "-J", "--get-server-output")
            if window:
                args += ["-w", window]
            if cport_base:
                args += ["--cport", cport_base + index]
            output = open(f"{prefix}-flow-{port}.json", "w")
            errors = open(f"{prefix}-flow-{port}-errors.txt", "w")
            handles += [output, errors]
            launches.append(time.time())
            client = spawn(args, output, errors)
            processes.append(client)
            clients.append(client)

        if during:
            during(clients)

        deadline = time.monotonic() + omit + seconds + 30
        for client in clients:
            client.wait(timeout=max(1, deadline - time.monotonic()))
            if client.returncode != 0:
                raise RuntimeError(f"iperf3 failed: inspect {prefix.name}-flow-*")
    finally:
        for process in reversed(processes):
            stop(process)
        for handle in handles:
            handle.close()

    starts, rates, retransmits = [], [], []
    for _, _, port in flows:
        data = json.loads(Path(f"{prefix}-flow-{port}.json").read_text())
        if "error" in data:
            raise RuntimeError(f"{prefix.name} port {port}: {data['error']}")
        starts.append(data["start"]["timestamp"]["timemillisecs"] / 1000)
        rates.append(data["end"]["sum_received"]["bits_per_second"] / 1e9)
        retransmits.append(data["end"]["sum_sent"].get("retransmits", 0))

    # Measure CPU only while every flow is inside its measured 15 s.
    window_start = max(starts) + omit
    window_end = min(starts) + omit + seconds
    meta = {
        "flows": flows, "cc": cc, "seconds": seconds, "omit": omit,
        "window": window, "launch_span_ms": 1000 * (launches[-1] - launches[0]),
        "cpu_window_epoch": [window_start, window_end],
    }
    save_json(f"{prefix}-meta.json", meta)

    return {
        "flow_gbps": rates,
        "gbps": sum(rates),
        "retransmissions": sum(retransmits),
        "launch_span_ms": meta["launch_span_ms"],
        "cpu": cpu_usage(f"{prefix}-cpu.txt", window_start, window_end),
    }


# --------------------------------------------------------------------------
# CPU accounting (the paper's denominator)
# --------------------------------------------------------------------------

def read_mpstat(path):
    """Return [(epoch, cpu, {column: value})] from an `mpstat -P ALL 1` log."""
    lines = Path(path).read_text().splitlines()
    if not lines:
        return []
    found = re.search(r"(\d\d)/(\d\d)/(\d\d)", lines[0])
    month, day, year = map(int, found.groups()) if found else (1, 1, 70)
    day_start = datetime(2000 + year, month, day).timestamp()
    columns, samples, previous, rollover = None, [], None, 0
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 3 or not re.fullmatch(r"\d\d:\d\d:\d\d", parts[0]):
            continue
        if parts[1] == "CPU":
            columns = [name.lstrip("%") for name in parts[2:]]
            continue
        if columns is None or parts[1] == "all":
            continue
        hours, minutes, secs = map(int, parts[0].split(":"))
        clock = 3600 * hours + 60 * minutes + secs
        if previous is not None and clock < previous:
            rollover += 86400
        previous = clock
        values = dict(zip(columns, map(float, parts[2:])))
        samples.append((day_start + rollover + clock, int(parts[1]), values))
    return samples


def cpu_usage(path, start, end):
    """Average per-CPU utilisation over the intervals inside [start, end].

    mpstat stamps each 1-second interval with its end time, so an interval
    stamped T covers (T-1, T]. "busy" is 100 - idle and includes user,
    system, softirq and irq time: everything the CPU did.
    """
    chosen = [
        (cpu, values) for stamp, cpu, values in read_mpstat(path)
        if stamp - 1 >= start - 0.5 and stamp <= end + 0.5
    ]
    usage = {}
    for cpu in sorted({cpu for cpu, _ in chosen}):
        rows = [values for c, values in chosen if c == cpu]
        mean = lambda key: sum(row.get(key, 0.0) for row in rows) / len(rows)
        usage[cpu] = {
            "busy": 100 - mean("idle"),
            "usr": mean("usr") + mean("nice"),
            "sys": mean("sys"),
            "soft": mean("soft") + mean("irq"),
            "samples": len(rows),
        }
    return usage


def cpu_metrics(gbps, cpu, sender_cpus, receiver_cpus):
    """Throughput-per-core, adapted from the paper's definition (Section 2.2).

    Paper: throughput / CPU utilisation of the bottleneck host.
    Here both "hosts" share one kernel, so we report both
      - per side: throughput / cores busy on that side's CPUs, the bottleneck
        side being the one whose busiest CPU is most loaded, and
      - total: throughput / cores busy on every CPU the experiment used.
    """
    if not cpu:
        raise RuntimeError("No mpstat samples inside the measurement window.")
    cores = lambda cpus: sum(cpu[c]["busy"] for c in cpus) / 100
    peak = lambda cpus: max(cpu[c]["busy"] for c in cpus)
    sender, receiver = cores(sender_cpus), cores(receiver_cpus)
    side = "sender" if peak(sender_cpus) >= peak(receiver_cpus) else "receiver"
    record = {
        "sender_cores": sender,
        "receiver_cores": receiver,
        "cores_used": sender + receiver,
        "bottleneck_side": side,
        "tpc_bottleneck_gbps": gbps / (sender if side == "sender" else receiver),
        "tpc_total_gbps": gbps / (sender + receiver),
        "cpu_samples": min(cpu[c]["samples"] for c in cpu),
    }
    for c in sorted(cpu):
        for key in ("busy", "usr", "sys", "soft"):
            record[f"cpu{c}_{key}"] = cpu[c][key]
    return record
