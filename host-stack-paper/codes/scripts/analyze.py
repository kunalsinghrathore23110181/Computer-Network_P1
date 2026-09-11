"""Build every graph and table from the newest COMPLETE result of each experiment.

    python3 scripts/analyze.py        (no sudo needed)

Output: analysis/*.png, analysis/*.csv and analysis/summary.json.
Throughput-per-core (the paper's metric, Section 2.2) is computed from the
per-CPU mpstat logs recorded during each run's 15-second measurement window.
"""
import csv
import json
import math
from pathlib import Path
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, ROOT, cpu_metrics, cpu_usage  # noqa: E402

OUT = ROOT / "analysis"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": False,
    "savefig.dpi": 200, "savefig.bbox": "tight",
})


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def latest(name):
    folders = sorted(p for p in RESULTS.glob(f"{name}-2*")
                     if (p / "COMPLETED.txt").exists() and (p / "runs.csv").exists())
    return folders[-1] if folders else None


def load_rows(folder):
    with (folder / "runs.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key, value in row.items():
            try:
                row[key] = float(value)
            except (TypeError, ValueError):
                pass
        add_side_metrics(row)
    return rows


def add_side_metrics(row):
    # Throughput per busy core of one side: the paper's Figure 6 uses the
    # receiver core (incast), Figure 7 the sender core (outcast).
    if "sender_cores" in row:
        gbps = row.get("gbps", row.get("goodput_gbps"))
        row["tpc_sender_gbps"] = gbps / row["sender_cores"]
        row["tpc_receiver_gbps"] = gbps / row["receiver_cores"]


def baseline(folder):
    """Background CPU load measured before the experiment (busy % per CPU)."""
    try:
        data = json.loads((folder / "configuration.json").read_text())["idle_baseline"]
    except (OSError, KeyError, ValueError):
        return None
    return {cpu: round(values["busy"], 1) for cpu, values in data.items()}


def legacy_cpu(folder, rows):
    """Older congestion-control results have no CPU columns: compute them."""
    for row in rows:
        if "tpc_total_gbps" in row:
            continue
        label = f"{row['algorithm']}-r{int(row['repeat'])}"
        data = json.loads((folder / f"{label}.json").read_text())
        start = data["start"]["timestamp"]["timemillisecs"] / 1000 + 3
        cpu = cpu_usage(folder / f"{label}-cpu.txt", start, start + 15)
        row["gbps"] = row.get("gbps", row.get("receiver_gbps"))
        row.update(cpu_metrics(row["gbps"], cpu, [0], [2]))
        add_side_metrics(row)
    return rows


def mean_sd(values):
    values = [v for v in values if isinstance(v, float) and math.isfinite(v)]
    if not values:
        return float("nan"), float("nan")
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def summarize(rows, key, order, metrics):
    table = []
    for name in order:
        selected = [row for row in rows if row[key] == name]
        if not selected:
            continue
        record = {key: name, "runs": len(selected)}
        for metric in metrics:
            record[f"{metric}_mean"], record[f"{metric}_sd"] = mean_sd(
                [row[metric] for row in selected])
        table.append(record)
    return table


def write_table(name, table):
    if not table:
        return
    with (OUT / f"{name}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------

def bars(ax, labels, table, metric, color, title, ylabel, fmt="{:.1f}"):
    x = range(len(labels))
    means = [row[f"{metric}_mean"] for row in table]
    sds = [row[f"{metric}_sd"] for row in table]
    ax.bar(x, means, yerr=sds, width=0.6, color=color, capsize=3,
           error_kw={"elinewidth": 1, "ecolor": INK})
    top = max(m + s for m, s in zip(means, sds)) if means else 1
    for i, (m, s) in enumerate(zip(means, sds)):
        ax.text(i, m + s + top * 0.02, fmt.format(m), ha="center", va="bottom",
                fontsize=8, color=INK)
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, top * 1.15)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)


def cpu_stack(ax, labels, table, cpus, title):
    """Stacked user/system/softirq busy % for each CPU of each condition."""
    width = 0.8 / len(cpus)
    parts = [("usr", "user space", BLUE), ("sys", "kernel (process context)", ORANGE),
             ("soft", "softirq / irq", AQUA)]
    for j, cpu in enumerate(cpus):
        x = [i - 0.4 + width * (j + 0.5) for i in range(len(labels))]
        bottom = [0.0] * len(labels)
        for key, name, color in parts:
            values = [row.get(f"cpu{cpu}_{key}_mean", 0) for row in table]
            ax.bar(x, values, width * 0.9, bottom=bottom, color=color,
                   edgecolor="white", linewidth=1, label=name if j == 0 else None)
            bottom = [b + v for b, v in zip(bottom, values)]
        for xi, total in zip(x, bottom):
            ax.text(xi, total + 1.5, f"CPU{cpu}", ha="center", fontsize=7, color=MUTED)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylim(0, 115)
    ax.set_ylabel("CPU busy (%)")
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", fontsize=8, ncol=3)


CPU_KEYS = [f"cpu{c}_{k}" for c in range(4) for k in ("busy", "usr", "sys", "soft")]
BASE_METRICS = ["gbps", "retransmissions", "tpc_total_gbps", "tpc_bottleneck_gbps",
                "tpc_sender_gbps", "tpc_receiver_gbps",
                "cores_used", "sender_cores", "receiver_cores"] + CPU_KEYS


# --------------------------------------------------------------------------
# Experiments
# --------------------------------------------------------------------------

def single_flow(summary):
    folder = latest("single-flow")
    if not folder:
        return
    rows = load_rows(folder)
    levels = [lv for lv in ("no-opt", "tso-gro", "jumbo", "rfs")
              if any(r["phase"] == "levels" and r["level"] == lv for r in rows)]
    level_rows = [r for r in rows if r["phase"] == "levels"]
    table = summarize(level_rows, "level", levels, BASE_METRICS)
    write_table("single_flow_levels", table)
    names = {"no-opt": "No opt.", "tso-gro": "+TSO/GRO", "jumbo": "+Jumbo", "rfs": "+RFS"}
    labels = [names[lv] for lv in levels]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    bars(axes[0], labels, table, "gbps", BLUE, "Throughput", "Gbps")
    bars(axes[1], labels, table, "tpc_total_gbps", ORANGE,
         "Throughput per busy core (CPU0 + CPU2)", "Gbps per core")
    cpu_stack(axes[2], labels, table, [0, 2], "Where the CPU time goes")
    fig.suptitle("Single flow, optimisations enabled one at a time "
                 "(sender app on CPU0, receiver app on CPU2)", x=0.01, ha="left")
    fig.savefig(OUT / "fig_single_flow_levels.png")
    plt.close(fig)

    buffer_rows = [r for r in rows if r["phase"] == "buffers"]
    buffer_table = []
    if buffer_rows:
        sizes = sorted({int(r["buffer_kb"]) for r in buffer_rows})
        for r in buffer_rows:
            r["buffer_kb"] = int(r["buffer_kb"])
        buffer_table = summarize(buffer_rows, "buffer_kb", sizes, BASE_METRICS)
        write_table("single_flow_buffers", buffer_table)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        labels = [str(s) for s in sizes]
        bars(axes[0], labels, buffer_table, "gbps", BLUE, "Throughput", "Gbps")
        bars(axes[1], labels, buffer_table, "tpc_total_gbps", ORANGE,
             "Throughput per busy core", "Gbps per core")
        for ax in axes:
            ax.set_xlabel("TCP buffer set with iperf3 -w (KB)")
        fig.savefig(OUT / "fig_single_flow_buffers.png")
        plt.close(fig)
    summary["single_flow"] = {"source": folder.name, "idle": baseline(folder), "levels": table,
                              "buffers": buffer_table}


PATTERN_ORDER = ["single", "one-to-one", "incast", "outcast", "all-to-all"]
PATTERN_LABELS = {"single": "Single\n0→2", "one-to-one": "One-to-one\n0→2, 1→3",
                  "incast": "Incast\n0→2, 1→2", "outcast": "Outcast\n0→2, 0→3",
                  "all-to-all": "All-to-all\n2×2 flows"}


def traffic_patterns(summary):
    folder = latest("traffic-patterns")
    if not folder:
        return
    rows = load_rows(folder)
    metrics = BASE_METRICS + ["min_flow_gbps", "max_flow_gbps"]
    present = [p for p in PATTERN_ORDER if any(r["pattern"] == p for r in rows)]
    table = summarize(rows, "pattern", present, metrics)
    write_table("traffic_patterns", table)

    fig = plt.figure(figsize=(13, 8.6), layout="constrained")
    grid = fig.add_gridspec(2, 2)
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]),
            fig.add_subplot(grid[1, :])]
    labels = [PATTERN_LABELS[p] for p in present]
    bars(axes[0], labels, table, "gbps", BLUE, "Total throughput", "Gbps")
    bars(axes[1], labels, table, "tpc_total_gbps", ORANGE,
         "Throughput per busy core (all used CPUs)", "Gbps per core")
    heat = [[row[f"cpu{c}_busy_mean"] for c in range(4)] for row in table]
    image = axes[2].imshow(list(zip(*heat)), cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i, column in enumerate(heat):
        for c, value in enumerate(column):
            axes[2].text(i, c, f"{value:.0f}", ha="center", va="center", fontsize=8,
                         color="white" if value > 60 else INK)
    axes[2].set_xticks(range(len(present)), [p.replace("-", "-\n") if p == "all-to-all"
                                             else p for p in present], fontsize=8)
    axes[2].set_yticks(range(4), ["CPU0 (sender)", "CPU1 (sender)",
                                  "CPU2 (receiver)", "CPU3 (receiver)"])
    axes[2].grid(False)
    axes[2].set_title("CPU busy % per core")
    for ax in axes[:2]:
        ax.tick_params(axis="x", labelsize=8)
    fig.colorbar(image, ax=axes[2], fraction=0.04)
    fig.savefig(OUT / "fig_traffic_patterns.png")
    plt.close(fig)

    scaling = {}
    for kind in ("incast", "outcast"):
        names = [n for n in ("single", kind, f"{kind}-4", f"{kind}-8")
                 if any(r["pattern"] == n for r in rows)]
        scaling[kind] = summarize(rows, "pattern", names, metrics)
        for record, name in zip(scaling[kind], names):
            fixed = {"single": 1, kind: 2}
            record["flows"] = fixed[name] if name in fixed else int(name.split("-")[-1])
        write_table(f"scaling_{kind}", scaling[kind])
    if any(len(t) > 2 for t in scaling.values()):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for kind, color, marker in (("incast", BLUE, "o"), ("outcast", ORANGE, "s")):
            table_k = scaling[kind]
            flows = [r["flows"] for r in table_k]
            shared = "tpc_receiver_gbps" if kind == "incast" else "tpc_sender_gbps"
            for ax, metric in zip(axes, ("gbps", shared)):
                ax.errorbar(flows, [r[f"{metric}_mean"] for r in table_k],
                            yerr=[r[f"{metric}_sd"] for r in table_k], color=color,
                            marker=marker, markersize=6, linewidth=2, capsize=3,
                            label=f"{kind}: all flows share {'receiver CPU2' if kind == 'incast' else 'sender CPU0'}")
        axes[0].set_title("Total throughput")
        axes[0].set_ylabel("Gbps")
        axes[1].set_title("Throughput per busy core of the shared CPU")
        axes[1].set_ylabel("Gbps per core")
        for ax in axes:
            ax.set_xscale("log", base=2)
            ax.set_xticks([1, 2, 4, 8], ["1", "2", "4", "8"])
            ax.set_xlabel("Number of flows")
            ax.set_ylim(bottom=0)
        axes[0].legend(fontsize=8, loc="lower left")
        fig.savefig(OUT / "fig_flow_scaling.png")
        plt.close(fig)
    summary["traffic_patterns"] = {"source": folder.name, "idle": baseline(folder), "patterns": table,
                                   "scaling": scaling}


def packet_loss(summary):
    folder = latest("packet-loss")
    if not folder:
        return
    rows = load_rows(folder)
    losses = sorted({r["loss_percent"] for r in rows})
    table = summarize(rows, "loss_percent", losses,
                      BASE_METRICS + ["measured_loss_percent"])
    write_table("packet_loss", table)
    labels = [f"{loss:g}%" for loss in losses]
    fig, grid = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    axes = grid.flatten()
    bars(axes[0], labels, table, "gbps", BLUE, "Throughput", "Gbps")
    bars(axes[1], labels, table, "tpc_total_gbps", ORANGE,
         "Throughput per busy core", "Gbps per core")
    bars(axes[2], labels, table, "retransmissions", AQUA,
         "TCP retransmissions", "Segments per 15 s", fmt="{:,.0f}")
    width = 0.36
    for offset, cpu, name, color in ((-width / 2, 0, "CPU0 (sender app)", BLUE),
                                     (width / 2, 2, "CPU2 (receiver app)", ORANGE)):
        axes[3].bar([i + offset for i in range(len(losses))],
                    [r[f"cpu{cpu}_busy_mean"] for r in table], width * 0.92,
                    yerr=[r[f"cpu{cpu}_busy_sd"] for r in table], capsize=3,
                    color=color, label=name, error_kw={"elinewidth": 1})
    axes[3].set_xticks(range(len(losses)), labels)
    axes[3].set_ylim(0, 115)
    axes[3].set_ylabel("CPU busy (%)")
    axes[3].set_title("CPU utilisation")
    axes[3].legend(fontsize=8, loc="upper right", ncol=2)
    for ax in axes:
        ax.set_xlabel("Random loss probability")
    fig.savefig(OUT / "fig_packet_loss.png")
    plt.close(fig)
    summary["packet_loss"] = {"source": folder.name, "idle": baseline(folder), "table": table}


def flow_sizes(summary):
    folder = latest("flow-sizes")
    if not folder:
        return
    rows = load_rows(folder)
    metrics = ["rpc_tps", "rpc_bidirectional_gbps", "bulk_gbps", "goodput_gbps",
               "tpc_receiver_gbps", "cpu2_busy", "cpu0_busy", "cpu1_busy",
               "cpu2_usr", "cpu2_sys", "cpu2_soft"]
    sizes = summarize([r for r in rows if r["phase"] == "sizes"], "condition",
                      ["rpc-4KiB", "rpc-16KiB", "rpc-32KiB", "rpc-64KiB"], metrics)
    mixed = summarize([r for r in rows if r["phase"] == "mixed"], "condition",
                      ["bulk-plus-0", "bulk-plus-1", "bulk-plus-4", "bulk-plus-16",
                       "rpc-only-16"], metrics)
    write_table("flow_sizes_rpc", sizes)
    write_table("flow_sizes_mixed", mixed)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.2))
    labels = ["4", "16", "32", "64"][:len(sizes)]
    bars(axes[0], labels, sizes, "rpc_tps", BLUE, "16:1 RPC incast: transactions/s",
         "Transactions per second", fmt="{:,.0f}")
    bars(axes[1], labels, sizes, "tpc_receiver_gbps", ORANGE,
         "Goodput per busy receiver core", "Gbps per core (request + response)")
    for ax in axes[:2]:
        ax.set_xlabel("Request = response size (KiB)")
    mix_labels = ["bulk\nalone", "bulk +\n1 RPC", "bulk +\n4 RPC", "bulk +\n16 RPC",
                  "16 RPC\nalone"][:len(mixed)]
    x = range(len(mixed))
    axes[2].bar([i - 0.19 for i in x], [r["bulk_gbps_mean"] for r in mixed], 0.36,
                yerr=[r["bulk_gbps_sd"] for r in mixed], capsize=3, color=BLUE,
                label="long flow", error_kw={"elinewidth": 1})
    axes[2].bar([i + 0.19 for i in x], [r["rpc_bidirectional_gbps_mean"] for r in mixed],
                0.36, yerr=[r["rpc_bidirectional_gbps_sd"] for r in mixed], capsize=3,
                color=ORANGE, label="short flows (request + response)",
                error_kw={"elinewidth": 1})
    axes[2].set_xticks(list(x), mix_labels, fontsize=8)
    axes[2].set_ylabel("Goodput (Gbps)")
    axes[2].set_title("Long + 4 KiB short flows on one core per side")
    axes[2].legend(fontsize=8)
    axes[2].grid(axis="x", visible=False)
    fig.savefig(OUT / "fig_flow_sizes.png")
    plt.close(fig)
    summary["flow_sizes"] = {"source": folder.name, "idle": baseline(folder), "rpc": sizes, "mixed": mixed}


def congestion_control(summary):
    folder = latest("congestion-control")
    if not folder:
        return
    rows = legacy_cpu(folder, load_rows(folder))
    order = [a for a in ("cubic", "bbr", "dctcp", "reno")
             if any(r["algorithm"] == a for r in rows)]
    table = summarize(rows, "algorithm", order, BASE_METRICS)
    write_table("congestion_control", table)
    labels = [a.upper() for a in order]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    bars(axes[0], labels, table, "gbps", BLUE, "Throughput", "Gbps")
    bars(axes[1], labels, table, "tpc_total_gbps", ORANGE,
         "Throughput per busy core", "Gbps per core")
    cpu_stack(axes[2], labels, table, [0, 2], "Sender (CPU0) and receiver (CPU2) CPU")
    fig.savefig(OUT / "fig_congestion_control.png")
    plt.close(fig)
    summary["congestion_control"] = {"source": folder.name, "idle": baseline(folder), "table": table,
                                     "ecn_evidence": sorted({str(r.get("ecn_evidence"))
                                                             for r in rows
                                                             if r["algorithm"] == "dctcp"})}


def cpu_profile(summary):
    folders = sorted(p for p in RESULTS.glob("cpu-profile-2*")
                     if (p / "COMPLETED.txt").exists())
    if not folders:
        return
    folder = folders[-1]
    with (folder / "breakdown.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    categories = ["data copy", "tcp/ip processing", "netdevice subsystem", "skb mgmt",
                  "memory alloc/dealloc", "lock/unlock", "scheduling", "etc."]
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.2), sharey=True)
    colors = [BLUE, ORANGE, AQUA, YELLOW, "#e87ba4", "#008300", "#4a3aa7", "#9a9994"]
    for ax, role in zip(axes, ("sender", "receiver")):
        selected = [r for r in rows if r["role"] == role]
        width = 0.8 / max(1, len(selected))
        for j, row in enumerate(selected):
            ax.bar([i - 0.4 + width * (j + 0.5) for i in range(len(categories))],
                   [float(row[c]) for c in categories], width * 0.9,
                   color=colors[j], label=row["level"])
        ax.set_xticks(range(len(categories)), categories, rotation=30, ha="right")
        ax.set_title(f"{role.capitalize()} core (CPU{0 if role == 'sender' else 2})")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Fraction of busy CPU samples")
    axes[0].legend(fontsize=8)
    fig.savefig(OUT / "fig_cpu_breakdown.png")
    plt.close(fig)
    summary["cpu_profile"] = {"source": folder.name, "idle": baseline(folder), "rows": rows}


def main():
    OUT.mkdir(exist_ok=True)
    summary = {}
    for step in (single_flow, traffic_patterns, packet_loss, flow_sizes,
                 congestion_control, cpu_profile):
        step(summary)
        if step.__name__ in summary:
            print(f"{step.__name__:20s} <- {summary[step.__name__]['source']}")
        else:
            print(f"{step.__name__:20s}    no completed result yet")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"Graphs and tables: {OUT}")


if __name__ == "__main__":
    main()
