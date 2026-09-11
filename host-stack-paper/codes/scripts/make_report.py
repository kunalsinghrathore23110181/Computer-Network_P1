"""Build the project report (report/*.html and *.pdf) from the analysis output.

    python3 scripts/analyze.py && python3 scripts/make_report.py

Every number in the results sections is read from analysis/summary.json,
so re-running the experiments and these two commands keeps the report
consistent with the data. The PDF needs WeasyPrint (sudo apt install
weasyprint); without it the HTML is written and can be printed from a browser.
"""
import html
import json
import math
from datetime import date
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
REPORT = ROOT / "report"
NAME = "Host_Stack_Project_Report"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def num(value, digits=1):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    return f"{value:,.{digits}f}"


def pm(record, key, digits=1):
    return f"{num(record.get(key + '_mean'), digits)} ± {num(record.get(key + '_sd'), digits)}"


def m(record, key):
    return record[key + "_mean"]


def pick(records, key, value):
    return next((r for r in records if r.get(key) == value), None)


def change(new, old):
    return 100 * (new / old - 1)


def signed(value, digits=0):
    return f"{value:+.{digits}f}%"


def table(head, rows, cls=""):
    parts = [f'<table class="{cls}"><thead><tr>']
    parts += [f"<th>{h}</th>" for h in head]
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def figure(name, caption):
    if not (ANALYSIS / name).exists():
        return (f'<p class="missing">Figure {name} is not available yet: run the '
                "experiment, then scripts/analyze.py and this script.</p>")
    return (f'<figure><img src="../analysis/{name}"/>'
            f"<figcaption>{caption}</figcaption></figure>")


def safe(section):
    """Render a results section; show a clear notice if its data is missing."""
    def wrapper(summary):
        try:
            return section(summary)
        except (KeyError, TypeError, StopIteration, ZeroDivisionError, IndexError) as error:
            return (f'<p class="missing">Results for this section are not available '
                    f"yet ({type(error).__name__}: {error}). Run the experiment and "
                    "scripts/analyze.py.</p>")
    return wrapper


# One explanation box per experiment: question, setup, steps, measurement.
GLANCE = {
    "single": [
        ("Question", "How much CPU does one long TCP flow cost, and how much does each kernel "
                     "optimisation save?"),
        ("Setup", "One iperf3 flow: sender application pinned to CPU0, receiver application "
                  "pinned to CPU2; CUBIC; 128 KB writes. Script <code>exp_single_flow.py</code>."),
        ("Steps", "1. Create the two namespaces and the veth. 2. Set the level: <b>No opt.</b> = "
                  "<code>ethtool -K … tso off gso off gro off</code>, MTU 1500 → <b>+TSO/GSO/GRO</b> "
                  "= all three on → <b>+Jumbo</b> = MTU 9000 → <b>+RFS</b> = receive processing "
                  "steered to the receiver's core (sudo only). 3. Run iperf3: 3 s warm-up discarded, "
                  "15 s measured, mpstat logging every CPU each second. 4. Three runs per level, "
                  "levels in random order."),
        ("Measured", "Throughput; busy % of CPU0 and CPU2 split into user / kernel / softirq; "
                     "throughput per busy core; retransmissions."),
        ("Reading the figure", "Left: speed. Middle: efficiency (Gbps per busy core). Right: what "
                               "each core spent its time on; softirq on CPU0 is receive work done "
                               "on the sender's core."),
    ],
    "buffers": [
        ("Question", "Does the size of the TCP buffer change speed and CPU efficiency?"),
        ("Setup", "Same flow as 6.1 at the +Jumbo level. <code>iperf3 -w SIZE</code> fixes the send "
                  "and receive socket buffers and so turns Linux auto-tuning off, as the paper does. "
                  "Above 4 MB the kernel caps the value (<code>net.core.rmem_max</code>), so we stop "
                  "at 3200 KB, the paper's first six sizes."),
        ("Steps", "Sizes 100, 200, 400, 800, 1600, 3200 KB; three runs each in random order; "
                  "3 s warm-up + 15 s."),
        ("Measured", "Throughput and throughput per busy core for each size."),
        ("Reading the figure", "A low bar means the buffer limits the flow; flat bars mean the "
                               "buffer no longer matters."),
    ],
    "patterns": [
        ("Question", "What happens to efficiency when flows share sender or receiver cores?"),
        ("Setup", "Each host has two cores. Single: 0→2. One-to-one: 0→2, 1→3. Incast: 0→2, 1→2 "
                  "(receiver core shared). Outcast: 0→2, 0→3 (sender core shared). All-to-all: "
                  "0→2, 0→3, 1→2, 1→3. Kernel-default veth settings (TSO/GSO on, GRO off, "
                  "MTU 1500), CUBIC. Script <code>exp_traffic_patterns.py</code>."),
        ("Steps", "For every flow one iperf3 server pinned to its receiver core and one client "
                  "pinned to its sender core, all started together; 3 s warm-up + 15 s. All "
                  "patterns interleaved in one random order, three runs each."),
        ("Measured", "Total throughput (sum of the flows), slowest and fastest flow (fairness), "
                     "busy % of all four CPUs, throughput per busy core."),
        ("Reading the figure", "The heat map shows which core is full (dark) in each pattern: "
                               "that core limits the pattern."),
    ],
    "scaling": [
        ("Question", "What happens when more and more flows share one core?"),
        ("Setup", "Incast-N: N flows into receiver CPU2 (senders alternate CPU0/CPU1). "
                  "Outcast-N: N flows out of sender CPU0 (receivers alternate CPU2/CPU3). "
                  "N = 1, 2, 4, 8 (the paper goes to 24)."),
        ("Steps", "Run in the same session and random order as 6.3, three runs each."),
        ("Measured", "Total throughput, and throughput per busy core of the shared CPU (CPU2 for "
                     "incast, CPU0 for outcast), the paper's metric in Figs. 6 and 7."),
        ("Reading the figure", "A falling line means each extra flow makes the shared core less "
                               "efficient."),
    ],
    "loss": [
        ("Question", "How does random packet loss change throughput and CPU efficiency?"),
        ("Setup", "One flow CPU0 → CPU2, CUBIC, TSO/GSO/GRO off, MTU 1500. Packets arriving at the "
                  "receiver are redirected to an IFB device where <code>netem</code> drops them at "
                  "random (the paper uses a switch); ACKs are not dropped. "
                  "Script <code>exp_packet_loss.py</code>."),
        ("Steps", "For each run: delete and re-create the netem queue with the loss rate (0, 0.015, "
                  "0.15 or 1.5 %) and a new seed; save nstat and softnet counters; run 3 s + 15 s; "
                  "save the counters again and netem's packet and drop counts. Three runs per rate, "
                  "random order."),
        ("Measured", "Throughput, retransmissions, measured loss rate (drops ÷ packets), CPU0 and "
                     "CPU2 busy, throughput per busy core."),
        ("Reading the figure", "Compare each loss rate with 0 %: what the drops cost in speed and "
                               "efficiency, and how the work moves between the cores."),
    ],
    "sizes": [
        ("Question", "Do short request/response flows cost the CPU differently from long flows, and "
                     "what happens when both share a core?"),
        ("Setup", "(a) 16 netperf TCP_RR connections (one request outstanding each; request = "
                  "response = 4, 16, 32 or 64 KiB) from CPUs 0/1 into one receiver core, CPU2 "
                  "(16:1 incast). (b) One netperf TCP_STREAM long flow (128 KB writes) plus 0, 1, 4 "
                  "or 16 short 4 KiB RPC flows, all clients on CPU0 and all servers on CPU2; plus "
                  "16 RPC flows alone. Script <code>exp_flow_sizes.py</code>."),
        ("Steps", "netserver, pinned to CPU2, forks one worker per connection; all netperf clients "
                  "start together and run 20 s; CPU is averaged over seconds 2–19. Three runs per "
                  "case, random order within each part."),
        ("Measured", "Transactions per second, application goodput (request + response bytes), "
                     "long-flow throughput, receiver-core busy %, goodput per busy receiver core."),
        ("Reading the figure", "Left and middle: how message size changes rate and efficiency. "
                               "Right: long-flow and short-flow goodput as short flows join the "
                               "same cores."),
    ],
    "cc": [
        ("Question", "Does the congestion-control algorithm change CPU efficiency?"),
        ("Setup", "One flow CPU0 → CPU2, MTU 1500, <code>fq</code> qdisc on both ends (pacing for "
                  "BBR; ECN CE mark after 1 ms of queueing for DCTCP), ECN on. CUBIC, BBR, DCTCP. "
                  "Script <code>exp_congestion_control.py</code>."),
        ("Steps", "Set the algorithm in both namespaces and with <code>iperf3 -C</code>; re-create "
                  "the queues; run 3 s + 15 s; read the live socket twice with <code>ss -ti</code> "
                  "to prove which algorithm ran (and that DCTCP had ECN); three runs each, random "
                  "order."),
        ("Measured", "Throughput, retransmissions, CPU0/CPU2 busy and their split, throughput per "
                     "busy core, ECN marks."),
        ("Reading the figure", "Equal bars mean the algorithm does not matter; the CPU panel shows "
                               "where any extra cost appears."),
    ],
    "profile": [
        ("Question", "Which parts of the kernel use the CPU time (the paper's Table 1 categories)?"),
        ("Setup", "Same flow and levels as 6.1. <code>perf record -e cpu-clock -F 999 -C 0,2</code> "
                  "samples CPU0 and CPU2 about 1000 times per second. Script "
                  "<code>exp_cpu_profile.py</code> (needs sudo)."),
        ("Steps", "Start the flow; after the 4 s warm-up record 10 s; export with "
                  "<code>perf script</code>; map every function name to a category by fixed rules "
                  "(e.g. <code>__arch_copy_to_user</code> → data copy, <code>tcp_*</code> → tcp/ip, "
                  "<code>*gro*</code> → netdevice); drop idle samples."),
        ("Measured", "Fraction of each core's busy time per category; the top 30 functions per core "
                     "with their category."),
        ("Reading the figure", "The tallest bars are the biggest costs; comparing levels shows what "
                               "each optimisation removes."),
    ],
}



# What the paper did in each experiment, and how to run ours.
PAPER_SETUP = {
    "single": "Two servers, 100 Gbps cable. One iperf flow between NIC-local cores. Optimisations "
              "switched on one at a time: none → TSO/GRO → jumbo frames (MTU 9000) → aRFS. "
              "Without aRFS the interrupts are pinned to a core on another NUMA node (worst case).",
    "buffers": "The same single flow with all optimisations. TCP receive buffer fixed between 100 KB "
               "and 12.8 MB (auto-tuning overridden) and NIC receive descriptors 128–8192; L3 cache "
               "miss rate measured with hardware counters.",
    "patterns": "1 to 24 cores per server, all optimisations on. One-to-one: sender core i → receiver "
                "core i. Incast: n sender cores → 1 receiver core. Outcast: 1 sender core → n receiver "
                "cores. All-to-all: every sender core to every receiver core (up to 24 × 24 = 576 flows).",
    "scaling": "Incast with 1, 8, 16, 24 flows into one receiver core (Fig. 6); outcast with 1, 8, 16, "
               "24 flows from one sender core (Fig. 7), reported as throughput per sender core.",
    "loss": "Single flow with all optimisations. A programmable switch between the servers drops "
            "packets at random with rate 0, 1.5·10⁻⁴, 1.5·10⁻³ and 1.5·10⁻²; CPU breakdown at both ends.",
    "sizes": "(a) 16 applications on separate sender cores, each with one long-lived TCP connection "
             "doing ping-pong RPCs of 4, 16, 32 or 64 KB with one receiver application on one core "
             "(netperf). (b) One core at each end: one long iperf flow plus 0, 1, 4 or 16 short 4 KB "
             "RPC flows.",
    "cc": "Single flow with all optimisations; CUBIC (the default), BBR (paced by the qdisc) and "
          "DCTCP; sender and receiver CPU breakdown.",
    "profile": "perf sampling on sender and receiver; the functions covering about 95 % of CPU time "
               "classified into the 8 categories of Table 1; shown for every configuration "
               "(Figs. 3c/d, 5b/c, 6b, 7b, 8b, 9c/d, 10b, 11b, 12b/c, 13b/c).",
}

RUN = {
    "single": ("<code>sudo python3 scripts/exp_single_flow.py</code> (all four levels and the buffer "
               "sizes, ≈ 12 min). Options: <code>--levels no-opt,tso-gro,jumbo</code> (without RFS), "
               "<code>--no-buffers</code>, <code>--reps 5</code>.",
               """ip netns add sf_tx ; ip netns add sf_rx
ip -n sf_tx link add sf_tx0 type veth peer name sf_rx0 netns sf_rx
ip netns exec sf_tx ethtool -K sf_tx0 tso off gso off gro off     # No opt. (same on sf_rx0)
ip netns exec sf_tx ethtool -K sf_tx0 tso on gso on gro on        # +TSO/GSO/GRO
ip -n sf_tx link set sf_tx0 mtu 9000                              # +Jumbo (both ends)
echo 32768 > /proc/sys/net/core/rps_sock_flow_entries             # +RFS, plus in each namespace:
echo 32768 > /sys/class/net/sf_rx0/queues/rx-0/rps_flow_cnt
ip netns exec sf_rx taskset -c 2 iperf3 -s -1 -B 10.231.1.2 -p 5301
ip netns exec sf_tx taskset -c 0 iperf3 -c 10.231.1.2 -B 10.231.1.1 -p 5301 -P 1 -C cubic -O 3 -t 15 -J --get-server-output
mpstat -P ALL 1                                                   # per-CPU log during the run"""),
    "buffers": ("Part of <code>sudo python3 scripts/exp_single_flow.py</code> (runs after the levels; "
                "<code>--no-buffers</code> skips it).",
                """ip -n sf_tx link set sf_tx0 mtu 9000                              # +Jumbo level, both ends
ip netns exec sf_tx taskset -c 0 iperf3 -c 10.231.1.2 -p 5301 -C cubic -O 3 -t 15 -J -w 800K
#   -w = 100K, 200K, 400K, 800K, 1600K, 3200K (fixes both socket buffers)"""),
    "patterns": ("<code>sudo python3 scripts/exp_traffic_patterns.py</code> (all 9 patterns, ≈ 11 min). "
                 "Subset: <code>--patterns single,one-to-one,incast,outcast,all-to-all</code>; more runs: "
                 "<code>--reps 5</code>.",
                 """# example: incast = two flows, sender CPUs 0 and 1, both receivers on CPU 2
ip netns exec tp_rx taskset -c 2 iperf3 -s -1 -B 10.231.2.2 -p 5301 &
ip netns exec tp_rx taskset -c 2 iperf3 -s -1 -B 10.231.2.2 -p 5302 &
ip netns exec tp_tx taskset -c 0 iperf3 -c 10.231.2.2 -p 5301 -C cubic -O 3 -t 15 -J &
ip netns exec tp_tx taskset -c 1 iperf3 -c 10.231.2.2 -p 5302 -C cubic -O 3 -t 15 -J &
# one-to-one: second pair uses receiver CPU 3; outcast: both clients on CPU 0"""),
    "scaling": ("Part of <code>sudo python3 scripts/exp_traffic_patterns.py</code>; only these: "
                "<code>--patterns single,incast,incast-4,incast-8,outcast,outcast-4,outcast-8</code>.",
                """# incast-8: eight server processes all on CPU 2 (ports 5301-5308),
#           clients alternate: taskset -c 0 / taskset -c 1
# outcast-8: eight clients all on CPU 0,
#           servers alternate: taskset -c 2 / taskset -c 3"""),
    "loss": ("<code>sudo python3 scripts/exp_packet_loss.py</code> (4 loss rates × 3, ≈ 5 min).",
             """ip netns exec pl_tx ethtool -K pl_tx0 tso off gso off gro off   # and pl_rx0
ip -n pl_rx link add pl_ifb type ifb ; ip -n pl_rx link set pl_ifb up
ip netns exec pl_rx tc qdisc add dev pl_rx0 handle ffff: ingress
ip netns exec pl_rx tc filter add dev pl_rx0 parent ffff: protocol ip pref 10 matchall action mirred egress redirect dev pl_ifb
ip netns exec pl_rx tc qdisc del dev pl_ifb root                  # fresh counters every run
ip netns exec pl_rx tc qdisc add dev pl_ifb root netem limit 10000 loss random 0.15% seed 1004
ip netns exec pl_tx taskset -c 0 iperf3 -c 10.231.3.2 -p 5301 -C cubic -O 3 -t 15 -J
ip netns exec pl_rx tc -s -j qdisc show dev pl_ifb                # packets, drops -> measured loss
ip netns exec pl_tx nstat -asz ; cat /proc/net/softnet_stat      # counters before and after"""),
    "sizes": ("<code>sudo python3 scripts/exp_flow_sizes.py</code> (9 cases × 3, ≈ 11 min).",
              """ip netns exec fs_rx taskset -c 2 netserver -D -4 -L 10.231.4.2 -p 12867
# one short flow (16 of these run at once; request = response = 4096 bytes):
ip netns exec fs_tx taskset -c 0 netperf -4 -H 10.231.4.2 -p 12867 -l 20 -t TCP_RR -P 0 -v 0 -f x -- -r 4096,4096
# the long flow, 128 KB writes:
ip netns exec fs_tx taskset -c 0 netperf -4 -H 10.231.4.2 -p 12867 -l 20 -t TCP_STREAM -P 0 -v 0 -f m -- -m 131072"""),
    "cc": ("<code>sudo modprobe tcp_bbr tcp_dctcp</code> then "
           "<code>sudo python3 scripts/exp_congestion_control.py</code> (3 × 3, ≈ 4 min).",
           """ip netns exec cc_tx sysctl -w net.ipv4.tcp_ecn=1                      # both namespaces
ip netns exec cc_tx sysctl -w net.ipv4.tcp_congestion_control=dctcp   # both namespaces
ip netns exec cc_tx tc qdisc add dev cc_tx0 root fq limit 10000 flow_limit 1000 ce_threshold 1ms
ip netns exec cc_tx taskset -c 0 iperf3 -c 10.231.5.2 -p 5301 --cport 41000 -C dctcp -O 3 -t 15 -J
ip netns exec cc_tx ss -tinH 'sport = :41000'     # live algorithm and DCTCP's ECN state
ip netns exec cc_tx tc -s qdisc show dev cc_tx0   # ce_mark = packets marked by fq"""),
    "profile": ("<code>sudo python3 scripts/exp_cpu_profile.py</code> (4 levels, ≈ 3 min; needs "
                "<code>linux-tools-$(uname -r)</code>).",
                """perf record -e cpu-clock -F 999 -C 0,2 -o no-opt.perf.data -- sleep 10
perf script -i no-opt.perf.data -F comm,cpu,ip,sym,dso      # one line per sample
# each function name -> one of the 8 categories -> breakdown.csv, top-symbols.csv"""),
}


def glance(key):
    rows = [("In the paper", PAPER_SETUP[key])] + GLANCE[key] + [
        ("Run it", RUN[key][0]),
        ("Commands inside", f"<pre>{html.escape(RUN[key][1])}</pre>"),
    ]
    body = "".join(f"<tr><td>{name}</td><td>{cell}</td></tr>" for name, cell in rows)
    return f'<table class="glance">{body}</table>'


OVERVIEW = table(
    ["", "Experiment", "Paper", "Main question", "Runs"],
    [["6.1", "Single flow, optimisations", "§3.1, Fig. 3a/b",
      "What does one flow cost; what does each optimisation save?", "4 levels × 3"],
     ["6.2", "TCP buffer size", "§3.1, Fig. 3e", "Does buffer size change speed/efficiency?",
      "6 sizes × 3"],
     ["6.3", "Five traffic patterns", "§3.2–3.5, Fig. 2",
      "What does sharing cores between flows cost?", "5 patterns × 3"],
     ["6.4", "More flows per core", "Figs. 6 and 7", "How does efficiency change with 1–8 flows "
      "on one core?", "2 × 2 extra × 3"],
     ["6.5", "Packet loss", "§3.6, Fig. 9", "What does random loss cost?", "4 rates × 3"],
     ["6.6", "Short and mixed flows", "§3.7, Figs. 10/11",
      "Small RPCs vs long flows; mixing both on a core", "9 cases × 3"],
     ["6.7", "Congestion control", "§3.10, Fig. 13", "CUBIC vs BBR vs DCTCP", "3 × 3"],
     ["6.8", "CPU breakdown", "Table 1, Fig. 3c/d", "Where do the cycles go?", "4 levels"],
     ["6.9", "DCA / DDIO", "§3.8, Fig. 12", "What does cache DMA save?", "not possible here"],
     ["6.10", "IOMMU", "§3.9, Fig. 12", "What does address translation cost?", "not possible here"]])

NOT_REPRODUCED = """
<h3>6.9 Paper §3.8, Impact of DCA (DDIO): not reproducible here</h3>
<p><b>What the paper did.</b> It repeated the single flow of §3.1 with Intel DDIO switched off,
so the NIC wrote packets to DRAM instead of the L3 cache. <b>What it found:</b> throughput-per-core
fell by 19 % and the benefit of aRFS halved, because the receiver now copies every byte from
memory instead of cache. The CPU breakdown did not change much.</p>
<p><b>Why we cannot do it.</b> DDIO is a feature of Intel Xeon processors and of PCIe network cards
that write into memory by DMA. Our laptop has an Apple processor, and the veth "cable" has no
network card and no DMA: the receiver reads the same memory the sender's copy just wrote. There is
no switch to turn off.</p>
<p><b>What would be needed.</b> A server with an Intel Xeon and a 25–100 Gbps NIC on which DDIO can
be switched off (a platform setting on Intel servers), and access to the hardware counters to
count L3 misses.</p>
<p><b>What our data says instead.</b> Our receiver behaves like "perfect DDIO": its copy is cheap,
which is one reason the receiver core is not our bottleneck (Sections 4 and 6.1).</p>

<h3>6.10 Paper §3.9, Impact of IOMMU: not reproducible here</h3>
<p><b>What the paper did.</b> It repeated the single flow with the IOMMU switched on (it was off in
all other experiments). <b>What it found:</b> throughput-per-core fell by 26 %; memory
allocation/deallocation rose to 30 % of receiver cycles, because the driver must map every new DMA
page into the IOMMU's page table and unmap it after the DMA.</p>
<p><b>Why we cannot do it.</b> The IOMMU only translates addresses used by a <i>device</i> doing DMA.
In our data path no device does DMA; veth hands over pointers inside one kernel, so there is nothing
for an IOMMU to translate, and switching it on would change nothing.</p>
<p><b>What would be needed.</b> A physical (or emulated) NIC doing DMA. A partial approximation is
possible outside this VM: configure the VM in UTM/QEMU with a virtual IOMMU
(<code>virtio-iommu</code>) and a virtio network card, then send traffic to the Mac host with the
IOMMU on and off. That would show part of the mapping cost; it is not the paper's setup, so we list
it as future work.</p>

<h3>6.11 Other paper measurements not possible here</h3>
<ul>
<li><b>NIC-remote NUMA node (Fig. 4, −20 %):</b> the VM has one NUMA node.</li>
<li><b>L3 cache-miss rates (Figs. 3e, 4, 6c, 10c):</b> need hardware counters, which this VM does not
expose.</li>
<li><b>NIC receive descriptors (Fig. 3e) and the NAPI-to-copy latency (Fig. 3f):</b> need a real NIC
and custom kernel instrumentation.</li>
</ul>
"""


# --------------------------------------------------------------------------
# Static text
# --------------------------------------------------------------------------

CSS = """
@page { size: A4; margin: 17mm 16mm 18mm 16mm;
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 8pt; color: #777; } }
@page :first { @bottom-center { content: none; } }
body { font-family: "DejaVu Sans", "Noto Sans", Arial, sans-serif; font-size: 9.4pt;
  line-height: 1.45; color: #151515; }
h1 { font-size: 22pt; margin: 40mm 0 4pt; color: #0d366b; line-height: 1.2; }
.subtitle { font-size: 12.5pt; color: #333; margin-bottom: 18pt; }
h2 { font-size: 14.5pt; color: #0d366b; border-bottom: 1.6px solid #2a78d6;
  padding-bottom: 3px; margin-top: 0; break-before: page; }
h3 { font-size: 11.2pt; color: #184f95; margin: 14pt 0 4pt; break-after: avoid; }
h4 { font-size: 9.8pt; margin: 10pt 0 2pt; break-after: avoid; }
p { margin: 4pt 0 6pt; text-align: justify; }
ul, ol { margin: 3pt 0 6pt; padding-left: 16pt; } li { margin: 1.5pt 0; }
table { border-collapse: collapse; width: 100%; font-size: 8.3pt; margin: 6pt 0 10pt;
  break-inside: avoid; }
th, td { border: 0.6px solid #c9c8c3; padding: 3px 5px; vertical-align: top; text-align: left; }
th { background: #eaf1fb; }
table.num td + td { text-align: right; font-variant-numeric: tabular-nums; }
.box { border-left: 3px solid #2a78d6; background: #f3f7fd; padding: 6pt 10pt; margin: 8pt 0;
  break-inside: avoid; }
.box.warn { border-left-color: #eb6834; background: #fdf3ee; }
.box.good { border-left-color: #1baf7a; background: #effaf5; }
.box h4 { margin-top: 0; }
figure { margin: 8pt 0 10pt; break-inside: avoid; }
figure img { width: 100%; }
figcaption { font-size: 8.2pt; color: #444; margin-top: 2pt; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.2pt; background: #f2f1ee;
  padding: 0 2px; }
pre { font-family: "DejaVu Sans Mono", monospace; font-size: 7.9pt; background: #f4f3f0;
  padding: 6pt 8pt; white-space: pre-wrap; break-inside: avoid; border-radius: 3px; }
.missing { color: #a33; font-style: italic; }
.meta td { border: none; padding: 2px 6px 2px 0; font-size: 10pt; }
.toc a { color: #151515; text-decoration: none; }
.toc a::after { content: leader('.') target-counter(attr(href), page); }
.toc ol { list-style: none; padding-left: 0; } .toc li { margin: 3pt 0; }
dl.qa dt { font-weight: bold; margin-top: 8pt; color: #0d366b; break-after: avoid; }
dl.qa dd { margin: 2pt 0 0 0; text-align: justify; }
dl.gloss dt { font-weight: bold; float: left; width: 30mm; clear: left; }
dl.gloss dd { margin: 0 0 3pt 32mm; }
.small { font-size: 8.2pt; color: #444; }
svg text { font-family: "DejaVu Sans", sans-serif; }
table.long { break-inside: auto; } tr { break-inside: avoid; }
table.glance { break-inside: auto; }
table.glance pre { margin: 0; font-size: 7.2pt; padding: 4pt 6pt; }
table.glance { font-size: 8.4pt; border-left: 3px solid #2a78d6; }
table.glance td { border-color: #dfe7f3; }
table.glance td:first-child { width: 27mm; font-weight: bold; background: #f3f7fd; color: #0d366b; }
"""

TOPOLOGY_SVG = """
<svg viewBox="0 0 700 250" width="100%" xmlns="http://www.w3.org/2000/svg">
  <text x="10" y="18" font-size="13" font-weight="bold" fill="#0d366b">The paper: two servers</text>
  <rect x="10" y="30" width="130" height="110" rx="6" fill="#eaf1fb" stroke="#2a78d6"/>
  <text x="75" y="52" font-size="11" text-anchor="middle" font-weight="bold">Server A</text>
  <text x="75" y="68" font-size="9" text-anchor="middle">sender</text>
  <text x="75" y="84" font-size="9" text-anchor="middle">4 × 6 Xeon cores</text>
  <text x="75" y="98" font-size="9" text-anchor="middle">Linux 5.4.43</text>
  <rect x="35" y="108" width="80" height="22" rx="3" fill="#fff" stroke="#2a78d6"/>
  <text x="75" y="123" font-size="9" text-anchor="middle">100G NIC</text>
  <rect x="200" y="30" width="130" height="110" rx="6" fill="#eaf1fb" stroke="#2a78d6"/>
  <text x="265" y="52" font-size="11" text-anchor="middle" font-weight="bold">Server B</text>
  <text x="265" y="68" font-size="9" text-anchor="middle">receiver</text>
  <text x="265" y="84" font-size="9" text-anchor="middle">4 × 6 Xeon cores</text>
  <text x="265" y="98" font-size="9" text-anchor="middle">Linux 5.4.43</text>
  <rect x="225" y="108" width="80" height="22" rx="3" fill="#fff" stroke="#2a78d6"/>
  <text x="265" y="123" font-size="9" text-anchor="middle">100G NIC</text>
  <line x1="115" y1="119" x2="225" y2="119" stroke="#0d366b" stroke-width="3"/>
  <text x="170" y="160" font-size="9" text-anchor="middle">100 Gbps cable,</text>
  <text x="170" y="172" font-size="9" text-anchor="middle">no switch</text>
  <text x="170" y="200" font-size="9" text-anchor="middle" fill="#52514e">two kernels, two sets of caches,</text>
  <text x="170" y="212" font-size="9" text-anchor="middle" fill="#52514e">real DMA, interrupts, DDIO</text>

  <text x="370" y="18" font-size="13" font-weight="bold" fill="#0d366b">This project: one laptop</text>
  <rect x="370" y="28" width="320" height="200" rx="8" fill="#fafaf8" stroke="#9a9994"/>
  <text x="380" y="44" font-size="9" fill="#52514e">laptop → QEMU VM: Ubuntu 26.04, 4 vCPUs, one kernel</text>
  <rect x="385" y="60" width="120" height="120" rx="6" fill="#eaf1fb" stroke="#2a78d6"/>
  <text x="445" y="80" font-size="11" text-anchor="middle" font-weight="bold">sender "host"</text>
  <text x="445" y="95" font-size="9" text-anchor="middle">network namespace</text>
  <rect x="397" y="105" width="42" height="22" rx="3" fill="#2a78d6"/>
  <text x="418" y="120" font-size="9" text-anchor="middle" fill="#fff">CPU0</text>
  <rect x="451" y="105" width="42" height="22" rx="3" fill="#2a78d6"/>
  <text x="472" y="120" font-size="9" text-anchor="middle" fill="#fff">CPU1</text>
  <text x="445" y="148" font-size="9" text-anchor="middle">iperf3 / netperf</text>
  <text x="445" y="161" font-size="9" text-anchor="middle">clients</text>
  <rect x="555" y="60" width="120" height="120" rx="6" fill="#fdf1ec" stroke="#eb6834"/>
  <text x="615" y="80" font-size="11" text-anchor="middle" font-weight="bold">receiver "host"</text>
  <text x="615" y="95" font-size="9" text-anchor="middle">network namespace</text>
  <rect x="567" y="105" width="42" height="22" rx="3" fill="#eb6834"/>
  <text x="588" y="120" font-size="9" text-anchor="middle" fill="#fff">CPU2</text>
  <rect x="621" y="105" width="42" height="22" rx="3" fill="#eb6834"/>
  <text x="642" y="120" font-size="9" text-anchor="middle" fill="#fff">CPU3</text>
  <text x="615" y="148" font-size="9" text-anchor="middle">iperf3 / netserver</text>
  <text x="615" y="161" font-size="9" text-anchor="middle">servers</text>
  <line x1="505" y1="170" x2="555" y2="170" stroke="#0d366b" stroke-width="3"/>
  <text x="530" y="198" font-size="9" text-anchor="middle">veth pair = virtual cable</text>
  <text x="530" y="211" font-size="9" text-anchor="middle">(memory speed, no NIC)</text>
</svg>
"""

DATAPATH_SVG = """
<svg viewBox="0 0 700 300" width="100%" xmlns="http://www.w3.org/2000/svg">
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
    orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>
  <text x="130" y="16" font-size="12" font-weight="bold" text-anchor="middle" fill="#2a78d6">Sender side</text>
  <text x="570" y="16" font-size="12" font-weight="bold" text-anchor="middle" fill="#eb6834">Receiver side</text>
  <g font-size="9">
    <rect x="20" y="28" width="220" height="34" rx="4" fill="#eaf1fb" stroke="#2a78d6"/>
    <text x="130" y="43" text-anchor="middle" font-weight="bold">Application: write() 128 KB</text>
    <text x="130" y="56" text-anchor="middle">system call enters the kernel</text>
    <rect x="20" y="78" width="220" height="34" rx="4" fill="#eaf1fb" stroke="#2a78d6"/>
    <text x="130" y="93" text-anchor="middle" font-weight="bold">Data copy user → kernel</text>
    <text x="130" y="106" text-anchor="middle">skb allocated, payload copied once</text>
    <rect x="20" y="128" width="220" height="34" rx="4" fill="#eaf1fb" stroke="#2a78d6"/>
    <text x="130" y="143" text-anchor="middle" font-weight="bold">TCP/IP</text>
    <text x="130" y="156" text-anchor="middle">window/cwnd, headers, ACK processing</text>
    <rect x="20" y="178" width="220" height="34" rx="4" fill="#eaf1fb" stroke="#2a78d6"/>
    <text x="130" y="193" text-anchor="middle" font-weight="bold">qdisc + GSO / TSO</text>
    <text x="130" y="206" text-anchor="middle">split into MTU packets, or leave 64 KB</text>
    <rect x="20" y="228" width="220" height="34" rx="4" fill="#eaf1fb" stroke="#2a78d6"/>
    <text x="130" y="243" text-anchor="middle" font-weight="bold">Paper: driver + NIC DMA read</text>
    <text x="130" y="256" text-anchor="middle">Here: veth_xmit() hands the skb over</text>

    <rect x="460" y="228" width="220" height="34" rx="4" fill="#fdf1ec" stroke="#eb6834"/>
    <text x="570" y="243" text-anchor="middle" font-weight="bold">Paper: NIC DMA (DDIO) + IRQ</text>
    <text x="570" y="256" text-anchor="middle">Here: netif_rx() → per-CPU backlog</text>
    <rect x="460" y="178" width="220" height="34" rx="4" fill="#fdf1ec" stroke="#eb6834"/>
    <text x="570" y="193" text-anchor="middle" font-weight="bold">NAPI poll + GRO (softirq)</text>
    <text x="570" y="206" text-anchor="middle">skb per frame, merge same-flow packets</text>
    <rect x="460" y="128" width="220" height="34" rx="4" fill="#fdf1ec" stroke="#eb6834"/>
    <text x="570" y="143" text-anchor="middle" font-weight="bold">IP + TCP receive</text>
    <text x="570" y="156" text-anchor="middle">in-order data → socket queue, send ACK</text>
    <rect x="460" y="78" width="220" height="34" rx="4" fill="#fdf1ec" stroke="#eb6834"/>
    <text x="570" y="93" text-anchor="middle" font-weight="bold">Data copy kernel → user</text>
    <text x="570" y="106" text-anchor="middle">the paper's dominant cost (&gt; 50 %)</text>
    <rect x="460" y="28" width="220" height="34" rx="4" fill="#fdf1ec" stroke="#eb6834"/>
    <text x="570" y="43" text-anchor="middle" font-weight="bold">Application: read()</text>
    <text x="570" y="56" text-anchor="middle">returns the data</text>
  </g>
  <g stroke="#52514e" stroke-width="1.3" fill="none" marker-end="url(#a)">
    <line x1="130" y1="62" x2="130" y2="76"/><line x1="130" y1="112" x2="130" y2="126"/>
    <line x1="130" y1="162" x2="130" y2="176"/><line x1="130" y1="212" x2="130" y2="226"/>
    <line x1="240" y1="245" x2="458" y2="245"/>
    <line x1="570" y1="228" x2="570" y2="214"/><line x1="570" y1="178" x2="570" y2="164"/>
    <line x1="570" y1="128" x2="570" y2="114"/><line x1="570" y1="78" x2="570" y2="64"/>
  </g>
  <text x="350" y="238" font-size="9" text-anchor="middle">wire (paper) / pointer (veth)</text>
  <text x="350" y="285" font-size="9" text-anchor="middle" fill="#a3421a">In the VM, the two lowest receiver steps run on the CPU that called veth_xmit(),</text>
  <text x="350" y="297" font-size="9" text-anchor="middle" fill="#a3421a">i.e. usually the SENDER's core, unless RFS steers them to the receiver's core.</text>
</svg>
"""


def cover(summary):
    return f"""
<h1>Understanding Host Network Stack Overheads</h1>
<p class="subtitle">A single-laptop reproduction of Cai, Chaudhary, Vuppalapati, Hwang and
Agarwal, ACM SIGCOMM 2021: what we did, what we found, and how it maps to the paper</p>
<table class="meta">
<tr><td>Student:</td><td>______________________________</td></tr>
<tr><td>Course / supervisor:</td><td>______________________________</td></tr>
<tr><td>Report generated:</td><td>{date.today().isoformat()} (numbers filled in from analysis/summary.json)</td></tr>
</table>
<div class="box">
<h4>Summary in six points</h4>
<ol>
<li>The paper asks how much CPU the Linux kernel needs to move data when the link is so fast
(100 Gbps) that the <b>host CPU, not the network, is the bottleneck</b>. Its main metric is
<b>throughput-per-core</b>: Gbps delivered per CPU core used.</li>
<li>We reproduce its experiments in <b>one Ubuntu virtual machine with 4 vCPUs</b>. Two
<i>network namespaces</i> play the two servers and a <i>veth pair</i> plays the cable. Every
program is pinned to a CPU (sender: CPUs 0–1, receiver: CPUs 2–3).</li>
<li>The veth "cable" runs at memory speed, so, exactly as in the paper, the CPU is the
bottleneck. Two laptops joined by 1 Gbps Ethernet or Wi-Fi could never show that: the link
would saturate while the CPU sat almost idle (Section 3).</li>
<li>Reproduced: single flow and optimisations (§3.1), TCP buffer size (§3.1), the five
traffic patterns and flow scaling (§3.2–3.5), packet loss (§3.6), flow sizes and mixing
(§3.7), congestion control (§3.10), and the CPU-breakdown method of Table 1.</li>
<li>Not reproducible on this hardware: DDIO/DCA (§3.8), IOMMU (§3.9), NIC-remote NUMA,
cache-miss rates and the NAPI-to-copy latency. Section 4 explains why for each.</li>
<li>{headline(summary)}</li>
</ol>
</div>
"""


def headline(summary):
    try:
        levels = summary["single_flow"]["levels"]
        no, tg = pick(levels, "level", "no-opt"), pick(levels, "level", "tso-gro")
        best = max(levels, key=lambda r: m(r, "tpc_total_gbps"))
        text = (f"Headline numbers: turning on TSO/GSO/GRO raised single-flow throughput from "
                f"{num(m(no, 'gbps'))} to {num(m(tg, 'gbps'))} Gbps "
                f"({num(m(tg, 'tpc_total_gbps') / m(no, 'tpc_total_gbps'))}× more per busy core). "
                f"The best level reached {num(m(best, 'tpc_total_gbps'))} Gbps per busy core "
                f"counting both hosts, or {num(m(best, 'tpc_bottleneck_gbps'))} Gbps per core of "
                "the busier side. The paper reports about 42 Gbps per core.")
    except (KeyError, TypeError, AttributeError, ZeroDivisionError):
        text = "Headline numbers appear here once the single-flow experiment has been run."
    return text


TOC = """
<h2 id="toc" style="break-before: page">Contents</h2>
<div class="toc"><ol>
<li><a href="#s1">1. The paper in plain words</a></li>
<li><a href="#s2">2. Our setup: two hosts inside one laptop</a></li>
<li><a href="#s3">3. Why one laptop and not two</a></li>
<li><a href="#s4">4. What one VM cannot reproduce, and why</a></li>
<li><a href="#s5">5. How we measure</a></li>
<li><a href="#s6">6. Results, experiment by experiment</a></li>
<li><a href="#s7">7. Mistakes in the first version and how they were fixed</a></li>
<li><a href="#s8">8. How to run everything again</a></li>
<li><a href="#s9">9. Questions the professor may ask, with answers</a></li>
<li><a href="#s10">10. Glossary</a></li>
<li><a href="#s11">Appendix: project files</a></li>
</ol></div>
"""

PAPER = """
<h2 id="s1">1. The paper in plain words</h2>

<h3>1.1 The question</h3>
<p>Datacenter network links became 4–10× faster in a few years (10/40 Gbps → 100 Gbps and
more), but CPU cores did not get much faster and caches did not get much bigger (the slowdown
of Moore's law and the end of Dennard scaling). The network stack is software that runs on
those cores, so the old assumption "the network is the bottleneck, the host is fast enough"
stopped being true. The paper measures <b>how many CPU cycles the Linux kernel spends per byte
it sends or receives at 100 Gbps, where those cycles go, and how this changes with traffic
patterns, flow sizes, packet loss and kernel features</b>. Earlier studies looked mostly at short
flows on slow links, where TCP/IP protocol processing was the main cost; this paper shows that
at high speed the main cost shifts to <b>copying data</b> between kernel and application memory.</p>

<h3>1.2 Their testbed</h3>
<table>
<tr><th>Item</th><th>Paper (Section 2.2)</th></tr>
<tr><td>Machines</td><td>Two servers connected directly by one 100 Gbps cable, no switch
(so the network can never be the bottleneck)</td></tr>
<tr><td>CPU</td><td>4-socket Intel Xeon Gold 6128, 6 cores per socket at 3.4 GHz (24 cores, 4 NUMA
nodes); L1/L2/L3 = 32 KB / 1 MB / 20 MB; hyper-threading off</td></tr>
<tr><td>NIC</td><td>Mellanox ConnectX-5 Ex 100 Gbps, attached to one socket (the "NIC-local" NUMA node)</td></tr>
<tr><td>Software</td><td>Ubuntu 16.04, Linux 5.4.43; iperf for long flows, netperf for RPCs;
sysstat for CPU use; perf for CPU profiles</td></tr>
<tr><td>Defaults</td><td>DDIO on, IOMMU off, TCP CUBIC, all optimisations on (TSO, GRO,
jumbo frames 9000 B, aRFS) unless the experiment changes them</td></tr>
</table>

<h3>1.3 How a byte travels through Linux (the paper's Figure 1)</h3>
<p>The figure below follows one write from the sending application to the receiving
application. There is exactly <b>one data copy on each side</b>; everything else in the
kernel works on metadata (the <code>skb</code>, "socket buffer", describes a packet or a group of
packets and points to the data).</p>
""" + DATAPATH_SVG + """
<p><b>Sender.</b> (1) The application calls <code>write()</code>. (2) The kernel allocates skbs
and copies the data from the application's buffer into kernel memory. (3) TCP decides how much
it may send (congestion window, receiver window) and builds headers. (4) The queueing
discipline (qdisc) queues the packet; GSO splits large skbs into MTU-sized packets in software,
or TSO lets the NIC split them in hardware. (5) The driver gives the NIC the addresses and the
NIC reads the data by DMA. Almost all of this runs on the application's own core.</p>
<p><b>Receiver.</b> (1) The NIC writes each arriving frame into memory by DMA (with Intel DDIO
directly into the L3 cache). (2) It raises an interrupt on a core chosen by a steering
mechanism (RSS, or aRFS: "the core where the application runs"). (3) NAPI polls the receive
ring and builds one skb per frame. (4) GRO merges consecutive packets of the same flow into one
large skb, so the layers above run once per 64 KB instead of once per 1500 B. (5) IP and TCP
process the skb and append in-order data to the socket's receive queue; TCP sends ACKs.
(6) The application calls <code>read()</code> and the kernel copies the data into the
application's buffer. With aRFS all six steps run on one core.</p>

<h3>1.4 How they measure</h3>
<p><b>Throughput-per-core</b> = total throughput ÷ CPU utilisation (in cores) of the bottleneck
host. Example: 42 Gbps while the receiver uses 100 % of one core = 42 Gbps per core. The metric
is used instead of plain throughput because at 100 Gbps one flow cannot even fill the link: what
matters is <i>how many cores</i> a given rate costs. CPU utilisation is measured with sysstat
(all kernel and application work on every core). To see <i>where</i> the time goes they sample
with perf, take the functions covering about 95 % of CPU time, and sort them into eight
categories (Table 1 of the paper):</p>
<table>
<tr><th>Category</th><th>What it contains</th></tr>
<tr><td>data copy</td><td>copying payload user → kernel (sender) and kernel → user (receiver)</td></tr>
<tr><td>tcp/ip processing</td><td>all TCP and IP protocol work</td></tr>
<tr><td>netdevice subsystem</td><td>driver and device layer: NAPI polling, GSO/GRO, qdisc</td></tr>
<tr><td>skb management</td><td>building, splitting and releasing skbs</td></tr>
<tr><td>memory alloc/dealloc</td><td>allocating and freeing skbs and pages</td></tr>
<tr><td>lock/unlock</td><td>spin locks and socket locks</td></tr>
<tr><td>scheduling</td><td>context switches, waking and sleeping threads</td></tr>
<tr><td>etc.</td><td>everything else, e.g. interrupt handling, system-call entry</td></tr>
</table>

<h3>1.5 The optimisations the paper switches on and off</h3>
<table>
<tr><th>Name</th><th>What it does</th><th>Why it saves CPU</th></tr>
<tr><td>TSO / GSO</td><td>TCP Segmentation Offload / Generic Segmentation Offload: TCP builds
one 64 KB skb; the NIC (TSO) or the kernel just before the driver (GSO) cuts it into MTU packets</td>
<td>TCP/IP runs once per 64 KB instead of once per 1500 B</td></tr>
<tr><td>GRO / LRO</td><td>Generic / Large Receive Offload: the receiver merges packets of one
flow into one large skb (GRO in software, LRO in the NIC)</td><td>the same saving on the
receive side</td></tr>
<tr><td>Jumbo frames</td><td>MTU 9000 instead of 1500</td><td>6× fewer packets and skbs; fewer
packets for GRO to merge</td></tr>
<tr><td>RSS / RPS / RFS / aRFS</td><td>choose the core that processes an incoming packet: by a
hash (RSS in the NIC, RPS in software) or the core where the receiving application runs (RFS in
software, aRFS in the NIC)</td><td>with aRFS, interrupt, TCP/IP and application share one
core's cache, and the socket is not bounced between cores</td></tr>
<tr><td>DCA / DDIO</td><td>Direct Cache Access: the NIC writes packets straight into the L3
cache instead of DRAM</td><td>the receiver copies from cache, not from memory</td></tr>
</table>

<h3>1.6 What the paper found</h3>
<table>
<tr><th>Section</th><th>Finding</th></tr>
<tr><td>3.1 Single flow</td><td>With every optimisation on, one core processes about <b>42 Gbps</b>
(55 Gbps with hand-tuned buffers). The <b>receiver</b> is the bottleneck. <b>Data copy</b> is the
largest cost (about 50 % of receiver cycles). Even one flow sees a 49 % L3 miss rate: with large
TCP buffers, data written into the cache by DDIO is evicted before the application copies it.
A core on the NIC-remote NUMA node loses about 20 %.</td></tr>
<tr><td>3.2 One-to-one</td><td>The link saturates at 8 flows; throughput-per-core falls by 64 %
at 24 flows (less cache locality, less GRO merging, more scheduling as cores idle).</td></tr>
<tr><td>3.3 Incast</td><td>Many flows into one receiver core: throughput-per-core falls about
19 % at 8 flows because the flows fight over the cache (miss rate 48 % → 78 %). TCP is
sender-driven, so the receiver cannot limit how many flows hit one core.</td></tr>
<tr><td>3.4 Outcast</td><td>One sender core to many receivers reaches <b>89 Gbps per sender
core</b>: the sender pipeline is about 2× more efficient than the receiver's (TSO is in
hardware; the sender's cache is warm).</td></tr>
<tr><td>3.5 All-to-all</td><td>Up to 24×24 flows: throughput-per-core falls about 67 %; with
many flows each flow gets few packets per interval, so GRO cannot merge and skbs get smaller.</td></tr>
<tr><td>3.6 Packet loss</td><td>Drop rate 0 → 1.5 %: throughput-per-core falls about 24 %; more
ACK and retransmission work, higher at the sender.</td></tr>
<tr><td>3.7 Flow sizes</td><td>Small RPCs (4 KB) are dominated by per-message costs (TCP/IP,
scheduling), not copying; from 16 KB data copy dominates again. Mixing one long flow with 16
short flows on a core cuts throughput-per-core about 43 % (long flow −48 %, short flows −42 %).</td></tr>
<tr><td>3.8 DCA</td><td>Turning DDIO off costs 19 %.</td></tr>
<tr><td>3.9 IOMMU</td><td>Turning the IOMMU on costs 26 % (page mapping/unmapping; memory
management reaches 30 % of receiver cycles).</td></tr>
<tr><td>3.10 Congestion control</td><td>CUBIC, BBR and DCTCP give almost the same
throughput-per-core, because the receiver is the bottleneck and all three differ only at the
sender. BBR has more sender scheduling overhead because of pacing.</td></tr>
</table>
<p>Their overall message: host resources (cores, caches) must be orchestrated like network
resources; zero-copy receive, receiver-driven transports, and CPU schedulers that know about
the network stack are the promising directions (Section 4 of the paper).</p>
"""


def setup(summary):
    return """
<h2 id="s2">2. Our setup: two hosts inside one laptop</h2>
""" + TOPOLOGY_SVG + """
<h3>2.1 Machine</h3>
<table>
<tr><th>Item</th><th>This project</th></tr>
<tr><td>Physical machine</td><td>One Apple-silicon laptop (the VM reports CPU vendor "Apple")</td></tr>
<tr><td>Virtual machine</td><td>QEMU, Ubuntu 26.04 LTS, Linux 7.0.0-31-generic, aarch64</td></tr>
<tr><td>CPUs</td><td>4 vCPUs, 1 thread per core, a single NUMA node</td></tr>
<tr><td>Memory</td><td>7.2 GiB</td></tr>
<tr><td>Performance counters</td><td>None: only software perf events (no cache-miss counters)</td></tr>
<tr><td>Tools</td><td>iperf 3.20, netperf 2.7.1, sysstat (mpstat), perf 7.0, ethtool, iproute2 (ip, tc, ss, nstat)</td></tr>
</table>

<h3>2.2 How two "servers" are made</h3>
<p>A <b>network namespace</b> is a separate copy of the kernel's network stack: its own
interfaces, IP addresses, routing table, sockets and TCP settings. A program started "inside" a
namespace sees only that namespace's network. A <b>veth pair</b> is two virtual Ethernet
interfaces joined back-to-back: whatever is sent into one comes out of the other. Putting one
end in each namespace gives two hosts joined by a cable. Each experiment script builds its own
pair, for example:</p>
<pre>ip netns add tp_tx ; ip netns add tp_rx                 # two "hosts"
ip -n tp_tx link add tp_tx0 type veth peer name tp_rx0 netns tp_rx   # the "cable"
ip -n tp_tx address add 10.231.2.1/24 dev tp_tx0 ; ip -n tp_rx address add 10.231.2.2/24 dev tp_rx0
ip netns exec tp_rx taskset -c 2 iperf3 -s -1 -B 10.231.2.2 -p 5301          # receiver on CPU 2
ip netns exec tp_tx taskset -c 0 iperf3 -c 10.231.2.2 -p 5301 -C cubic -O 3 -t 15 -J   # sender on CPU 0</pre>
<p><code>taskset -c N</code> pins a program to CPU N, as the paper pins each application to
one core. The paper's servers have 24 cores each; our VM has 4, so each "host" gets two:
<b>CPUs 0 and 1 for the sender, CPUs 2 and 3 for the receiver</b>. The namespaces are deleted
at the end of every experiment, so every run starts from the same clean state.</p>

<h3>2.3 What corresponds to what</h3>
<table>
<tr><th>Paper</th><th>This project</th><th>Same?</th></tr>
<tr><td>Two servers</td><td>Two network namespaces in one kernel</td><td>Partly: separate network
stacks, but shared CPUs, memory, caches and scheduler</td></tr>
<tr><td>100 Gbps cable, no switch</td><td>veth pair (the skb pointer is handed over; nothing
is copied or serialised)</td><td>Same role: never the bottleneck</td></tr>
<tr><td>Application core per flow</td><td><code>taskset</code> to one vCPU</td><td>Yes</td></tr>
<tr><td>TSO in the NIC, GSO</td><td>TSO/GSO on veth: the 64 KB skb crosses the veth unsplit</td>
<td>Same effect, done in software</td></tr>
<tr><td>GRO</td><td>GRO on the veth (uses NAPI inside veth)</td><td>Yes</td></tr>
<tr><td>Jumbo frames</td><td>MTU 9000 on both veth ends</td><td>Yes</td></tr>
<tr><td>aRFS</td><td>RFS (software Receive Flow Steering), only in the single-flow study; needs root</td>
<td>Same idea, done in software</td></tr>
<tr><td>Interrupts, NAPI on a NIC queue</td><td>veth delivers with <code>netif_rx()</code> into the
current CPU's backlog, handled in softirq</td><td>No hardware interrupt</td></tr>
<tr><td>Switch dropping packets (§3.6)</td><td>netem on an IFB device at the receiver's input</td><td>Yes (random drop)</td></tr>
<tr><td>iperf / netperf</td><td>iperf3 (one process per flow) / netperf TCP_RR and TCP_STREAM</td><td>Yes</td></tr>
<tr><td>sysstat CPU utilisation</td><td>mpstat, per core, every second</td><td>Yes</td></tr>
<tr><td>perf profiles</td><td>perf with the cpu-clock timer event</td><td>Yes (timer-based sampling)</td></tr>
<tr><td>DDIO, IOMMU, NUMA, PMU counters</td><td>Not present</td><td>No (Section 4)</td></tr>
</table>
"""


def why_one(summary):
    try:
        levels = summary["single_flow"]["levels"]
        best = max(levels, key=lambda r: m(r, "gbps"))
        tpc = m(best, "tpc_total_gbps")
        gbps = m(best, "gbps")
        one_g = 100 / tpc
        ten_g = 1000 / tpc
        evidence = (f"In our single-flow runs the CPUs moved about <b>{num(gbps)} Gbps</b> and "
                    f"delivered <b>{num(tpc)} Gbps per busy core</b> (counting both hosts). At that "
                    f"efficiency, a 1 Gbps link would keep the stack busy for only about "
                    f"<b>{num(one_g)} % of one core</b>, and even a 10 Gbps adapter only about "
                    f"<b>{num(ten_g, 0)} %</b>.")
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        evidence = ("Our single-flow runs move tens of Gbps per busy core, so a 1 Gbps link "
                    "would use only a few percent of one core.")
    return f"""
<h2 id="s3">3. Why one laptop and not two</h2>
<div class="box"><h4>Short answer</h4>
The paper only makes sense when the <b>CPU is the bottleneck and the network is not</b>. Laptop
networks (1 Gbps Ethernet, Wi-Fi) are 100× slower than the paper's link, so with two laptops the
link would be full while the CPUs were almost idle, and every experiment would just measure the
link speed. A veth pair inside one machine is a "link" that runs at memory speed, so the CPU
becomes the bottleneck again: the same situation the paper creates with 100 Gbps hardware.</div>

<h3>3.1 The paper deliberately removes the network as a bottleneck</h3>
<p>Section 2.2 of the paper: "To ensure that bottlenecks are at the network stack, we setup a
testbed with two servers directly connected via a 100Gbps link (without any intervening
switches)." Every result in the paper (throughput-per-core, the CPU breakdowns, the effect of
TSO/GRO, of traffic patterns, of congestion control) assumes that the application and kernel on
the hosts are what limits the speed.</p>

<h3>3.2 Two laptops would measure the cable, not the stack</h3>
<p>{evidence} With two laptops:</p>
<ul>
<li>every experiment would report "throughput ≈ link speed" (about 0.94 Gbps of TCP payload on
1 Gbps Ethernet, and a varying 0.2–1 Gbps on Wi-Fi);</li>
<li>switching TSO/GRO off, changing the traffic pattern or the congestion control would change
only the CPU percentage, which would sit at a few percent, lost in background noise;</li>
<li>the single-flow, one-to-one, incast, outcast and all-to-all patterns would all give the same
throughput, because they would all share the same 1 Gbps link;</li>
<li>Wi-Fi adds interference, rate changes and retransmissions that have nothing to do with the
host stack; the paper even avoids a switch.</li>
</ul>
<p>In short, the host overheads the paper studies would be invisible. To see them between two
machines we would need 100 Gbps NICs and a direct cable, as in the paper.</p>

<h3>3.3 Why a veth pair recreates the paper's situation</h3>
<ul>
<li>A veth pair has no line rate. "Transmitting" hands the skb to the other end; the speed is
limited only by how fast the CPUs can run the stack. That is exactly the condition the paper
needs.</li>
<li>Evidence that the CPU is the limit: throughput changes when only CPU work changes (for
example TSO/GSO/GRO off vs on, Section 6.1), and one CPU core is close to 100 % busy in the
single-flow runs.</li>
<li>Both ends run the <b>real Linux TCP/IP stack</b> (the same code as between two servers):
sockets, TCP CUBIC/BBR/DCTCP, qdiscs, GSO/GRO, softirq processing, data copies.</li>
<li>Every experiment is controlled and repeatable: the scripts build identical fresh hosts
every time, pin every program, and record every setting.</li>
</ul>

<h3>3.4 The price we pay</h3>
<p>Without a physical NIC there is no DMA, no hardware interrupt and no DDIO, and both "hosts"
share one kernel and one set of caches. Section 4 lists every consequence. The most visible
one: the receiver's packet processing often runs on the <i>sender's</i> CPU, so in our VM the
<b>sender core is usually the bottleneck</b>, while in the paper the receiver is. We measure and
explain this in every experiment instead of hiding it.</p>

<h3>3.5 If two laptops are still required</h3>
<p>The scripts only need the two namespace names replaced by two machines' addresses. The
expected result is "throughput = link speed" with low CPU use. That run could be added as a
sanity check showing why the paper needs 100 Gbps; it cannot reproduce the paper's findings.</p>
"""


LIMITS = """
<h2 id="s4">4. What one VM cannot reproduce, and why</h2>
<table>
<tr><th>Paper item</th><th>Why it is not possible here</th><th>What we do instead</th></tr>
<tr><td>§3.8 DCA / DDIO</td><td>DDIO is an Intel Xeon feature that lets a NIC write into the L3
cache. Our CPU is Apple silicon, and a veth has no NIC and no DMA at all.</td><td>Explained
only. Our receiver copies data the sender core has just written, which is probably still in a
shared cache, so it behaves like a "perfect DDIO".</td></tr>
<tr><td>§3.9 IOMMU</td><td>The IOMMU translates addresses used by a device's DMA. There is no
device doing DMA in our data path.</td><td>Explained only.</td></tr>
<tr><td>NIC-remote NUMA (Fig. 4)</td><td>The VM has one NUMA node.</td><td>Not applicable.</td></tr>
<tr><td>L3 cache-miss rates (Figs. 3e, 4, 6c, 10c)</td><td>They need hardware performance
counters (PMU). This VM exposes none: <code>/sys/bus/event_source/devices</code> lists only
software, tracepoint, kprobe, uprobe and breakpoint.</td><td>We report throughput and CPU
use only; cache explanations are marked as the paper's.</td></tr>
<tr><td>NIC ring size (Fig. 3e)</td><td>A veth has no hardware receive descriptors.</td>
<td>Only the TCP buffer half of Fig. 3(e) is repeated.</td></tr>
<tr><td>NAPI-to-copy latency (Fig. 3f)</td><td>Needs custom timestamps inside the kernel.</td>
<td>Not done.</td></tr>
<tr><td>aRFS</td><td>A hardware NIC feature.</td><td>RFS (the software version) as the
fourth single-flow level. It needs a global kernel setting, so it runs only under real sudo.</td></tr>
<tr><td>1–24 flows per pattern</td><td>4 vCPUs in total.</td><td>2 CPUs per host; incast and
outcast scaled to 8 flows on one core.</td></tr>
<tr><td>Separate kernels and caches</td><td>Both namespaces share one kernel, one page
allocator, one scheduler and the same caches.</td><td>Accepted; per-CPU numbers show who does
what.</td></tr>
<tr><td>Quiet dedicated servers</td><td>The VM also runs the desktop and editor, and its vCPUs
are threads on macOS.</td><td>Idle CPU load is measured before every experiment and reported.</td></tr>
</table>
<div class="box warn"><h4>The most important difference: where receive processing runs</h4>
<p>With a real NIC and aRFS, the receiver's interrupt, NAPI, GRO and TCP/IP processing run on the
receiver's core. With a veth, <code>veth_xmit()</code> passes the skb to <code>netif_rx()</code>,
which queues it on the backlog of <b>the CPU that is currently running</b>, and the NET_RX softirq
processes it there. For data packets that is usually the sender's core; for ACKs it is the
receiver's core. So in our VM:</p>
<ul>
<li>the sender core does its own work <i>plus</i> much of the receiver's IP/TCP receive work
(visible as "softirq" time on CPU0 in the graphs);</li>
<li>the receiver core mostly does the kernel → user data copy and ACK work;</li>
<li>therefore the <b>sender core is usually the busiest</b>, the opposite of the paper.</li>
</ul>
<p>RFS changes this: it steers each received packet to the core where the receiving application
last ran, which is what aRFS does in the paper. The fourth single-flow level measures that effect.</p>
</div>
"""


def method(summary):
    idle = ""
    try:
        rows = []
        for key, title in (("single_flow", "Single flow"), ("traffic_patterns", "Traffic patterns"),
                           ("packet_loss", "Packet loss"), ("flow_sizes", "Flow sizes"),
                           ("congestion_control", "Congestion control")):
            base = summary.get(key, {}).get("idle")
            if base:
                rows.append([title] + [f"{base.get(str(c), base.get(c, 0)):.0f} %" for c in range(4)])
        if rows:
            idle = ("<p>Background load measured with the experiment idle (5 s just before it "
                    "started; busy % per CPU):</p>"
                    + table(["Experiment", "CPU0", "CPU1", "CPU2", "CPU3"], rows, "num"))
    except (AttributeError, TypeError, ValueError):
        pass
    return """
<h2 id="s5">5. How we measure</h2>
<h3>5.1 Run protocol (the same for every experiment)</h3>
<ul>
<li>Fresh namespaces and veth per experiment; settings recorded in <code>configuration.json</code>
(offloads from <code>ethtool -k</code>, qdiscs, MTU, TCP settings, versions).</li>
<li>One iperf3 client/server process pair <b>per flow</b>, each pinned with taskset; all flows
of a run start together.</li>
<li>iperf3 <code>-O 3 -t 15</code>: the first 3 s (TCP slow start) are omitted, the next 15 s are
measured, as in the original scripts. netperf runs 20 s and the first 2 s are excluded from
the CPU window.</li>
<li>3 repetitions per condition, in a <b>random order fixed by seed 42</b>, so slow changes in
background load do not favour whichever condition runs first. 2 s pause between runs.</li>
<li>A run counts only if every process exits successfully and its output parses; a folder gets
<code>COMPLETED.txt</code> only when all its runs succeeded, and the analysis ignores folders
without it.</li>
</ul>

<h3>5.2 How CPU use and throughput-per-core are computed</h3>
<p><code>mpstat -P ALL 1</code> prints, every second, how each CPU spent that second: user,
system (kernel on behalf of a process), softirq/irq (packet processing outside any process) and
idle. For each run we average the per-second lines that fall inside the measured 15 s window
(its start and end come from iperf3's own timestamps). Then:</p>
<pre>busy(cpu)            = 100 % − idle %          (all work: user + kernel + softirq + irq)
sender_cores         = Σ busy / 100 over the sender CPUs the run used     (e.g. CPU0)
receiver_cores       = Σ busy / 100 over the receiver CPUs the run used   (e.g. CPU2)
throughput per busy core (both hosts)   = throughput / (sender_cores + receiver_cores)
throughput per core (bottleneck side)   = throughput / cores of the side whose busiest CPU is most loaded</pre>
<p>The second formula is the paper's definition. We also give the first because in one VM
part of the receiver's work runs on the sender's CPUs (Section 4), so neither side on its own
is a clean "host". Example: 100 Gbps with CPU0 at 99 % and CPU2 at 76 % gives
100 / 1.75 = 57 Gbps per busy core for both hosts, and 100 / 0.99 = 101 Gbps per core for the
bottleneck (sender) side.</p>
<p><b>Why not iperf3's own CPU number?</b> iperf3 reports only the CPU time of its own process
(user + system). It misses softirq packet processing, which runs outside the process and, in a
veth, often on the other host's CPU. The paper uses sysstat for exactly this reason.</p>

<h3>5.3 Checks that make the numbers trustworthy</h3>
<ul>
<li>Offload settings are read back with <code>ethtool -k</code> after every change and the run
aborts if they differ.</li>
<li>Congestion control: the algorithm is read from the live data socket with
<code>ss -ti</code> (found by its fixed source port) twice per run. For DCTCP the script also checks
that ECN was negotiated.</li>
<li>Packet loss: the netem queue is re-created before every run and its packet and drop counters
give the <i>measured</i> loss rate, which is compared with the configured one.</li>
<li>Throughput is the receiver-side number (<code>sum_received</code>), i.e. data that actually
arrived.</li>
</ul>
<h3>5.4 Background load and statistics</h3>
""" + idle + """
<p>Numbers are the mean ± sample standard deviation (SD) of 3 runs. With 3 runs, treat a
difference smaller than about two SDs as "no clear difference". The VM shares the laptop with
other programs, so run-to-run variation of 5–10 % is normal here.</p>
<p>The per-CPU logs make disturbances visible: a CPU that the experiment does not use should be
nearly idle. During our first full run, a second editor window started in the VM and pushed the
unused CPUs from under 10 % to as much as 52 % busy, and throughput dropped at the same moment.
Those two experiments (single flow and traffic patterns) were therefore discarded and repeated
with the VM quiet; the results in this report come from the repeated runs.</p>
"""


# --------------------------------------------------------------------------
# Results (numbers from summary.json)
# --------------------------------------------------------------------------

LEVEL_NAMES = {"no-opt": "No opt.", "tso-gro": "+TSO/GSO/GRO", "jumbo": "+Jumbo (MTU 9000)",
               "rfs": "+RFS (≈ aRFS)"}


@safe
def res_single(summary):
    s = summary["single_flow"]
    levels = s["levels"]
    no, tg, jb = (pick(levels, "level", k) for k in ("no-opt", "tso-gro", "jumbo"))
    rf = pick(levels, "level", "rfs")
    rows = [[LEVEL_NAMES[r["level"]], pm(r, "gbps"), pm(r, "tpc_total_gbps"),
             pm(r, "tpc_bottleneck_gbps"), f"{num(m(r, 'cpu0_busy'), 0)} % ({num(m(r, 'cpu0_soft'), 0)} %)",
             f"{num(m(r, 'cpu2_busy'), 0)} % ({num(m(r, 'cpu2_soft'), 0)} %)",
             num(m(r, "retransmissions"), 0)] for r in levels]
    rfs_text = ""
    if rf:
        rfs_text = (f"<p><b>RFS.</b> Steering receive processing to the receiver's core changed "
                    f"CPU0 from {num(m(jb, 'cpu0_busy'), 0)} % to {num(m(rf, 'cpu0_busy'), 0)} % busy "
                    f"and CPU2 from {num(m(jb, 'cpu2_busy'), 0)} % to {num(m(rf, 'cpu2_busy'), 0)} %; "
                    f"throughput per busy core changed by "
                    f"{signed(change(m(rf, 'tpc_total_gbps'), m(jb, 'tpc_total_gbps')))}.</p>")
    else:
        rfs_text = ("<p class='small'>The RFS level needs real root (a global kernel table), so it "
                    "is absent from runs made without sudo. <code>sudo python3 "
                    "scripts/exp_single_flow.py</code> adds it.</p>")
    return f"""
<h3>6.1 Single flow, optimisations one at a time (paper §3.1, Fig. 3a/3b)</h3>
<p><b>Paper.</b> One long flow between two NIC-local cores. Starting from "no optimisations" they
add TSO/GRO, then jumbo frames, then aRFS. Each step raises throughput-per-core, reaching about
42 Gbps; the receiver core is always the bottleneck.</p>
{glance("single")}
{figure("fig_single_flow_levels.png", "Single flow. Left: throughput. Middle: throughput per busy core counting CPU0 + CPU2. Right: how CPU0 (sender app) and CPU2 (receiver app) spent their time. Mean ± SD of the runs.")}
{table(["Level", "Throughput (Gbps)", "Gbps per busy core (both hosts)", "Gbps per core (bottleneck side)",
        "CPU0 busy (softirq)", "CPU2 busy (softirq)", "Retrans."], rows, "num")}
<p><b>What we see.</b> Switching on TSO/GSO/GRO is by far the biggest step: throughput goes from
{num(m(no, 'gbps'))} to {num(m(tg, 'gbps'))} Gbps and throughput per busy core from
{num(m(no, 'tpc_total_gbps'))} to {num(m(tg, 'tpc_total_gbps'))}
({num(m(tg, 'tpc_total_gbps') / m(no, 'tpc_total_gbps'))}×). Jumbo frames then change throughput
per busy core by {signed(change(m(jb, 'tpc_total_gbps'), m(tg, 'tpc_total_gbps')))}.</p>
<p><b>Why.</b> With no offloads every skb holds one 1500-byte packet, so all per-packet work
(TCP/IP, qdisc, the veth hand-over, the receive path) is repeated about
{num(m(no, 'gbps') * 1e9 / 8 / 1500 / 1e6, 1)} million times per second. With TSO/GSO the
sender gives veth 64 KB skbs and veth passes them through whole, so per-packet costs are paid
about 44× less often, which is the same reason TSO/GRO help in the paper. Jumbo frames matter much less
than in the paper: there, GRO must merge 1500-byte frames arriving from the NIC, and jumbo
frames give it 6× fewer frames to merge. In veth nothing is split in the first place, so the MTU
barely matters once TSO is on. This is expected.</p>
<p><b>Who is the bottleneck.</b> In the "No opt." case CPU0 spends
{num(m(no, 'cpu0_soft'), 0)} % of its time in softirq, while CPU2 is only
{num(m(no, 'cpu2_busy'), 0)} % busy. That softirq time is the receiver's IP/TCP processing
running on the sender's core (Section 4). With offloads on, CPU0 is still the busier core
({num(m(tg, 'cpu0_busy'), 0)} % vs {num(m(tg, 'cpu2_busy'), 0)} %). <b>So the sender side is the
bottleneck here, while in the paper it is the receiver.</b> Two reasons: (1) veth makes the
sender's core do receive work; (2) the paper's receiver copies data that the NIC wrote into
memory (often a cache miss), while ours copies data the sender core wrote a moment earlier.</p>
{rfs_text}
<p><b>Compared with the paper.</b> Same direction and the same ranking of the offloads:
segmentation/receive offload is the key optimisation. Our absolute numbers are higher than 42 Gbps
per core because there is no NIC, DMA or interrupt cost, the data stays in cache, and the
receive work is split over two cores.</p>
"""


@safe
def res_buffers(summary):
    table_b = summary["single_flow"]["buffers"]
    rows = [[f"{int(r['buffer_kb'])} KB", pm(r, "gbps"), pm(r, "tpc_total_gbps"),
             f"{num(m(r, 'cpu0_busy'), 0)} %", f"{num(m(r, 'cpu2_busy'), 0)} %"] for r in table_b]
    small, large = table_b[0], table_b[-1]
    peak = max(table_b, key=lambda r: m(r, "tpc_total_gbps"))
    drop = change(m(large, "tpc_total_gbps"), m(peak, "tpc_total_gbps"))
    trend = ("stays flat up to the largest size" if drop > -5 else
             f"falls by {signed(drop)} from its peak at {int(peak['buffer_kb'])} KB to {int(large['buffer_kb'])} KB")
    return f"""
<h3>6.2 TCP buffer size (paper §3.1, Fig. 3e)</h3>
<p><b>Paper.</b> With the TCP receive buffer fixed (auto-tuning off), throughput-per-core
<i>falls</i> for large buffers: TCP keeps a buffer's worth of data in flight, host latency grows,
and data written into the L3 cache by DDIO is evicted before the application copies it
(3200 KB and ≤ 512 descriptors gave their best result, about 55 Gbps).</p>
{glance("buffers")}
{figure("fig_single_flow_buffers.png", "Throughput and throughput per busy core against the fixed TCP buffer size.")}
{table(["Buffer", "Throughput (Gbps)", "Gbps per busy core", "CPU0 busy", "CPU2 busy"], rows, "num")}
<p><b>What we see.</b> With {int(small['buffer_kb'])} KB the flow reaches only
{num(m(small, 'gbps'))} Gbps; throughput per busy core then {trend}.</p>
<p><b>Why.</b> At most one buffer of unacknowledged data can be in flight, so throughput ≤ buffer ÷
round-trip time. A small buffer therefore limits the flow even though the CPU is not full: the
cores wait. Once the buffer covers the bandwidth-delay product, a larger buffer adds nothing.
The paper's decline for large buffers comes from DDIO cache eviction; our VM has no NIC DMA and
no DDIO, so that mechanism cannot appear. This is a difference in hardware, not an error.</p>
"""


PATTERN_NAMES = {"single": "Single (0→2)", "one-to-one": "One-to-one (0→2, 1→3)",
                 "incast": "Incast (0→2, 1→2)", "outcast": "Outcast (0→2, 0→3)",
                 "all-to-all": "All-to-all (2×2)"}


@safe
def res_patterns(summary):
    s = summary["traffic_patterns"]
    T = s["patterns"]
    get = lambda name: pick(T, "pattern", name)
    single, o2o, inc, out, a2a = (get(n) for n in PATTERN_NAMES)
    rows = [[PATTERN_NAMES[r["pattern"]], pm(r, "gbps"), pm(r, "tpc_total_gbps"),
             pm(r, "tpc_bottleneck_gbps"),
             " / ".join(f"{num(m(r, f'cpu{c}_busy'), 0)}" for c in range(4)),
             f"{num(m(r, 'min_flow_gbps'))}–{num(m(r, 'max_flow_gbps'))}",
             num(m(r, "retransmissions"), 0)] for r in T]
    tpcs = [m(r, "tpc_total_gbps") for r in T]
    spread = 100 * (max(tpcs) - min(tpcs)) / max(tpcs)
    best = max(T, key=lambda r: m(r, "tpc_total_gbps"))
    worst = min(T, key=lambda r: m(r, "tpc_total_gbps"))
    return f"""
<h3>6.3 The five traffic patterns (paper §3.2–3.5, Fig. 2)</h3>
<p><b>Paper.</b> Single flow, one-to-one (each sender core to its own receiver core), incast (many
sender cores into one receiver core), outcast (one sender core to many receiver cores) and all-to-all
(every sender core to every receiver core). Sharing host resources hurts: throughput-per-core
differs by up to 66 % between patterns.</p>
{glance("patterns")}
{figure("fig_traffic_patterns.png", "Top left: total throughput (sum of all flows). Top right: throughput per busy core over the CPUs each pattern uses. Bottom: average busy % of every CPU during the measured window (a CPU the pattern does not use shows only background load).")}
{table(["Pattern", "Total Gbps", "Gbps per busy core", "Gbps per core, bottleneck side",
        "CPU0/1/2/3 busy %", "Slowest–fastest flow", "Retrans."], rows, "num")}
<p><b>What we see.</b></p>
<ul>
<li><b>One-to-one</b> gives {num(m(o2o, 'gbps') / m(single, 'gbps'), 2)}× the throughput of a
single flow: a second, independent pair of cores adds capacity because the veth "link" is not the
limit. But it is not 2×: each flow reaches only {num(m(o2o, 'gbps') / 2)} Gbps instead of
{num(m(single, 'gbps'))}, although it has its own two cores, and throughput per busy core falls from
{num(m(single, 'tpc_total_gbps'))} to {num(m(o2o, 'tpc_total_gbps'))}
({signed(change(m(o2o, 'tpc_total_gbps'), m(single, 'tpc_total_gbps')))}). This is the paper's
one-to-one finding (Fig. 5a): even with one flow per core, efficiency drops as flows are added,
because the flows share the cache and memory system. Our four vCPUs also share the laptop
processor's caches and memory bandwidth, and they are threads of one hypervisor.</li>
<li><b>Incast</b> delivers {signed(change(m(inc, 'gbps'), m(o2o, 'gbps')))} vs one-to-one:
both receiving applications share CPU2 ({num(m(inc, 'cpu2_busy'), 0)} % busy), the paper's
receiver contention.</li>
<li><b>Outcast</b> delivers {signed(change(m(out, 'gbps'), m(o2o, 'gbps')))} vs one-to-one and
about the same as one flow ({num(m(out, 'gbps'))} vs {num(m(single, 'gbps'))} Gbps): one sender
core (CPU0 {num(m(out, 'cpu0_busy'), 0)} % busy) must do the sending work for both flows plus
their receive-side softirq work, so the shared sender core caps the total.</li>
<li><b>All-to-all</b> uses all four cores and reaches {num(m(a2a, 'gbps'))} Gbps
({signed(change(m(a2a, 'gbps'), m(o2o, 'gbps')))} vs one-to-one); its throughput per busy core is
{num(m(a2a, 'tpc_total_gbps'))} vs {num(m(o2o, 'tpc_total_gbps'))} for one-to-one.</li>
<li>Across patterns, throughput per busy core ranges from {num(m(worst, 'tpc_total_gbps'))}
({worst['pattern']}) to {num(m(best, 'tpc_total_gbps'))} ({best['pattern']}), a spread of
{num(spread, 0)} % (paper: up to 66 %).</li>
</ul>
<p><b>Why.</b> Whenever two flows share one core, that core must serve both, and its cache holds
the data of both. The CPU heat map shows directly which core saturates in each pattern. In our VM
the shared <i>sender</i> core (outcast) hurts most, because the sender core also carries receive
work; in the paper the shared <i>receiver</i> core (incast) is the critical one.</p>
"""


@safe
def res_scaling(summary):
    sc = summary["traffic_patterns"]["scaling"]
    inc, out = sc["incast"], sc["outcast"]
    rows = []
    for kind, records, metric, side in (("Incast", inc, "tpc_receiver_gbps", "CPU2"),
                                        ("Outcast", out, "tpc_sender_gbps", "CPU0")):
        for r in records:
            rows.append([kind, int(r["flows"]), pm(r, "gbps"), pm(r, metric),
                         f"{num(m(r, 'cpu0_busy'), 0)} / {num(m(r, 'cpu2_busy'), 0)}"])
    i1, i8 = inc[0], inc[-1]
    o1, o8 = out[0], out[-1]
    return f"""
<h3>6.4 More flows on one core (paper Figs. 6 and 7)</h3>
<p><b>Paper.</b> Incast with 1–24 flows into one receiver core: throughput-per-core falls about
19 % at 8 flows as the flows compete for the cache. Outcast with 1–24 flows from one sender
core: throughput-per-sender-core <i>rises</i> up to 8 flows (89 Gbps) and then stays about flat.</p>
{glance("scaling")}
{figure("fig_flow_scaling.png", "Flow-count scaling. Left: total throughput. Right: throughput per busy core of the shared CPU (receiver CPU2 for incast, sender CPU0 for outcast).")}
{table(["Pattern", "Flows", "Total Gbps", "Gbps per busy shared core", "CPU0 / CPU2 busy %"], rows, "num")}
<p><b>What we see.</b> Incast: per busy receiver core, {num(m(i1, 'tpc_receiver_gbps'))} Gbps with
{int(i1['flows'])} flow and {num(m(i8, 'tpc_receiver_gbps'))} with {int(i8['flows'])}
({signed(change(m(i8, 'tpc_receiver_gbps'), m(i1, 'tpc_receiver_gbps')))}). Outcast: per busy sender
core, {num(m(o1, 'tpc_sender_gbps'))} → {num(m(o8, 'tpc_sender_gbps'))} Gbps
({signed(change(m(o8, 'tpc_sender_gbps'), m(o1, 'tpc_sender_gbps')))}).</p>
<p><b>Why.</b> More flows on one core means more sockets, more wake-ups and context switches, and
data of many flows competing for the same cache. The paper measured the cache part with miss
counters; we cannot (no PMU), so we see only the end effect on throughput per core.</p>
<p><b>Why outcast is flat here but rises in the paper.</b> In the paper one flow was limited by its
receiver, so the sender core had spare capacity that extra flows (to other receiver cores) could
use, up to 89 Gbps. In our VM the sender core is already 100 % busy with one flow, so extra flows
only divide the same capacity: the total stays at about {num(m(o1, 'gbps'), 0)} Gbps from 1 to
{int(o8['flows'])} flows.</p>
"""


@safe
def res_loss(summary):
    T = summary["packet_loss"]["table"]
    base, worst = T[0], T[-1]
    rows = [[f"{r['loss_percent']:g} %", f"{num(m(r, 'measured_loss_percent'), 4)} %", pm(r, "gbps"),
             pm(r, "tpc_total_gbps"), num(m(r, "retransmissions"), 0),
             f"{num(m(r, 'cpu0_busy'), 0)} % / {num(m(r, 'cpu2_busy'), 0)} %"] for r in T]
    retrans0 = m(base, "retransmissions")
    return f"""
<h3>6.5 Packet loss (paper §3.6, Fig. 9)</h3>
<p><b>Paper.</b> A switch drops packets at random (0, 1.5·10⁻⁴, 1.5·10⁻³, 1.5·10⁻²). At the highest
rate throughput-per-core falls about 24 %. Receivers send more duplicate ACKs, senders process
them and retransmit, so TCP/IP and netdevice costs rise, more at the sender.</p>
{glance("loss")}
<p><b>Why offloads are off here.</b> With TSO on, a 64 KB skb crosses the veth whole and netem
would drop 44 wire packets at once; a switch drops single packets. With TSO, GSO and GRO off every
skb is one 1500-byte packet, so the loss probability applies per packet. This makes the 0 % case
much slower than the default single flow: it is the "No opt." configuration of 6.1.</p>
{figure("fig_packet_loss.png", "Random loss. Throughput, throughput per busy core (CPU0 + CPU2), TCP retransmissions and CPU utilisation.")}
{table(["Loss (set)", "Loss (measured)", "Throughput (Gbps)", "Gbps per busy core", "Retrans. / 15 s",
        "CPU0 / CPU2 busy"], rows, "num")}
<p><b>What we see.</b> From 0 % to {worst['loss_percent']:g} % loss, throughput changes by
{signed(change(m(worst, 'gbps'), m(base, 'gbps')))} and throughput per busy core by
{signed(change(m(worst, 'tpc_total_gbps'), m(base, 'tpc_total_gbps')))} (paper: about −24 %).
The measured loss matches the configured probability, which validates the method.
Retransmissions grow roughly in proportion to the loss rate.</p>
<p><b>Why.</b> Every lost packet costs duplicate ACKs, a retransmission and a congestion-window
reduction (CUBIC cuts its window to 70 % when it detects a loss and then grows it again), so fewer
bytes are delivered for the same work. At {worst['loss_percent']:g} % loss CPU0 is only
{num(m(worst, 'cpu0_busy'), 0)} % busy: the sender is no longer limited by its core but by the
congestion window, which is why throughput per busy core falls less than throughput. CPU2 gets busier
({num(m(base, 'cpu2_busy'), 0)} % → {num(m(worst, 'cpu2_busy'), 0)} %): a retransmission is usually
sent when a SACK arrives, SACKs are processed on CPU2, so with veth the retransmitted packets are also
received on CPU2, where TCP merges its out-of-order queue. The paper also finds more ACK work at the
receiver (4.9× more time generating ACKs), but in its setup the sender's CPU share grows; here the
veth effect moves the extra work to the receiver's core.</p>
<p><b>Retransmissions at 0 % loss</b> ({num(retrans0, 0)} on average): netem dropped nothing, so
they come from the host. The kernel counters saved with each run (<code>nstat</code>) show what
happened: the receiver counted out-of-order packets (<code>TCPOFOQueue</code>) and reported
duplicates back to the sender (<code>TCPDSACKRecv</code>), and the sender counted reordering
(<code>TCPTSReorder</code>, <code>TCPSACKReorder</code>). So most of these retransmissions were
<i>spurious</i>: the packet was late, not lost. The cause is again the veth. New data is sent partly
from CPU0 (the application) and partly from CPU2 (when CPU2 processes an ACK, TCP may send the next
packets at once), and each CPU delivers what it sent through its own backlog queue, so the two
streams can overtake each other. Real drops in those queues were rare (0 to about 100 packets per
run in <code>/proc/net/softnet_stat</code>).</p>
"""


@safe
def res_sizes(summary):
    s = summary["flow_sizes"]
    rpc, mixed = s["rpc"], s["mixed"]
    rows = [[r["condition"].replace("rpc-", ""), pm(r, "rpc_tps", 0), pm(r, "rpc_bidirectional_gbps"),
             pm(r, "tpc_receiver_gbps"), f"{num(m(r, 'cpu2_busy'), 0)} %",
             f"{num(m(r, 'cpu0_busy'), 0)} / {num(m(r, 'cpu1_busy'), 0)} %"] for r in rpc]
    names = {"bulk-plus-0": "long flow alone", "bulk-plus-1": "long + 1 short",
             "bulk-plus-4": "long + 4 short", "bulk-plus-16": "long + 16 short",
             "rpc-only-16": "16 short alone"}
    mrows = [[names[r["condition"]], pm(r, "bulk_gbps"), pm(r, "rpc_tps", 0),
              pm(r, "goodput_gbps"), f"{num(m(r, 'cpu0_busy'), 0)} % / {num(m(r, 'cpu2_busy'), 0)} %"]
             for r in mixed]
    small, big = rpc[0], rpc[-1]
    alone, mix16 = pick(mixed, "condition", "bulk-plus-0"), pick(mixed, "condition", "bulk-plus-16")
    short_alone = pick(mixed, "condition", "rpc-only-16")
    return f"""
<h3>6.6 Short flows and mixed workloads (paper §3.7, Figs. 10 and 11)</h3>
<p><b>Paper.</b> (a) 16 applications send ping-pong RPCs (request = response = 4–64 KB) to one
receiver core. Throughput-per-core rises with message size; at 4 KB, TCP/IP processing and
scheduling (applications blocking and waking for every message) cost more than data copy.
(b) One long flow plus 0–16 short 4 KB flows on one core per side: throughput-per-core falls
43 %; the long flow loses 48 % and the short flows 42 % compared with running alone.</p>
{glance("sizes")}
{figure("fig_flow_sizes.png", "Left: RPC transactions per second for 16 connections into one receiver core. Middle: application goodput (request + response bytes) per busy receiver core. Right: long flow and short flows sharing one core per side.")}
<h4>(a) RPC size</h4>
{table(["Message", "Transactions/s", "Goodput req.+resp. (Gbps)", "Gbps per busy receiver core",
        "CPU2 busy", "CPU0 / CPU1 busy"], rows, "num")}
<p>From {small['condition'].replace('rpc-', '')} to {big['condition'].replace('rpc-', '')} messages the
transaction rate falls from {num(m(small, 'rpc_tps'), 0)} to {num(m(big, 'rpc_tps'), 0)} per second,
but the bytes moved per busy receiver core rise from {num(m(small, 'tpc_receiver_gbps'))} to
{num(m(big, 'tpc_receiver_gbps'))} Gbps. <b>Why:</b> each transaction has a fixed cost (two system
calls, a sleep and a wake-up, TCP/IP processing of a small skb, an ACK) plus a cost per byte
(the copy). Small messages are dominated by the fixed cost, large ones by the copy, which is the
paper's finding.</p>
<h4>(b) Mixing a long flow with short flows</h4>
{table(["Workload", "Long flow (Gbps)", "Short-flow transactions/s", "Total goodput (Gbps)",
        "CPU0 / CPU2 busy"], mrows, "num")}
<p>With 16 short flows the long flow drops from {num(m(alone, 'bulk_gbps'))} to
{num(m(mix16, 'bulk_gbps'))} Gbps ({signed(change(m(mix16, 'bulk_gbps'), m(alone, 'bulk_gbps')))}),
and the short flows change by {signed(change(m(mix16, 'rpc_tps'), m(short_alone, 'rpc_tps')))}
compared with running alone (paper: −48 % and −42 %). <b>Why:</b> the Linux scheduler shares one
core fairly between its runnable threads. On CPU2 the long flow's receiver is one of 17 netserver
workers, so it gets a small share, while the latency-sensitive RPC workers keep running. The
paper's conclusion holds: long and short flows should not share a core.</p>
"""


@safe
def res_cc(summary):
    s = summary["congestion_control"]
    T = s["table"]
    cubic = pick(T, "algorithm", "cubic")
    rows = [[r["algorithm"].upper(), pm(r, "gbps"), pm(r, "tpc_total_gbps"),
             f"{num(m(r, 'cpu0_busy'), 0)} % / {num(m(r, 'cpu2_busy'), 0)} %",
             num(m(r, "retransmissions"), 0)] for r in T]
    notes = []
    for r in T:
        if r is not cubic:
            notes.append(f"{r['algorithm'].upper()} {signed(change(m(r, 'gbps'), m(cubic, 'gbps')))} "
                         "throughput vs CUBIC")
    legacy = "20260909" in s["source"]
    legacy_note = ("<p class='small'>Source: the complete congestion-control run of 9 September "
                   "(same settings: MTU 1500, fq with 1 ms CE threshold, ECN on). BBR and DCTCP "
                   "need <code>modprobe</code>, i.e. real root, so this experiment was not "
                   "repeated with the new scripts; its CPU numbers are recomputed from its own "
                   "mpstat logs. <code>sudo bash scripts/run_all.sh</code> re-runs it.</p>"
                   if legacy else "")
    return f"""
<h3>6.7 Congestion control: CUBIC, BBR, DCTCP (paper §3.10, Fig. 13)</h3>
<p><b>Paper.</b> The three algorithms give almost the same throughput-per-core: the receiver is
the bottleneck and congestion control lives at the sender. BBR has more scheduling overhead at
the sender because it paces packets (qdisc timers wake the sender repeatedly).</p>
{glance("cc")}
{figure("fig_congestion_control.png", "Congestion control. Throughput, throughput per busy core (CPU0 + CPU2), and CPU time split of CPU0 and CPU2.")}
{table(["Algorithm", "Throughput (Gbps)", "Gbps per busy core", "CPU0 / CPU2 busy", "Retrans."], rows, "num")}
{legacy_note}
<p><b>What we see.</b> {"; ".join(notes)}.</p>
<p><b>Why.</b> <b>DCTCP ≈ CUBIC:</b> DCTCP slows down only in proportion to ECN marks. A veth never
builds a queue longer than 1 ms, so (almost) no packets are marked and DCTCP simply keeps its
window open, like CUBIC without loss. <b>BBR is slower here</b>, unlike in the paper: BBR paces
its packets through fq, which costs timers and extra wake-ups on the sender core (the overhead the
paper saw in its sender breakdown). In the paper that extra sender work did not matter because
the receiver was the bottleneck; in our VM the <i>sender</i> core is the bottleneck, so the same
overhead directly lowers throughput. BBR also retransmits more because it does not treat loss as
its main signal. Both observations support the paper's point: when the host is the bottleneck,
the congestion-control algorithm matters mainly through its CPU cost at the busiest side.</p>
"""


@safe
def res_profile(summary):
    prof = summary.get("cpu_profile")
    if not prof:
        return """
<h3>6.8 Where the CPU cycles go (paper Table 1, Figs. 3c/3d)</h3>
""" + glance("profile") + """
<p><b>Paper.</b> perf profiles sorted into eight categories show data copy as the largest cost at
the receiver (about half of the cycles with all optimisations), and TCP/IP processing dominating
without offloads.</p>
<p><b>Status.</b> <code>exp_cpu_profile.py</code> implements the method: for each single-flow level
it runs <code>perf record -e cpu-clock -F 999 -C 0,2</code> for 10 s of steady state, converts
the samples with <code>perf script</code>, drops idle samples and sorts every kernel function into
the paper's categories with the rules printed in its <code>configuration.json</code>. It writes
<code>breakdown.csv</code> (fractions per category) and <code>top-symbols.csv</code> (the top 30
functions per core with their category, so every classification can be checked). perf needs real
root, so this step runs only with <code>sudo python3 scripts/exp_cpu_profile.py</code> (included in
<code>run_all.sh</code>); this report is regenerated with the result afterwards.</p>
<p><b>What mpstat already shows.</b> The CPU panels of Sections 6.1 and 6.7 split each core's time
into user space, kernel on behalf of the process (system calls: mainly the data copy and
TCP send/receive) and softirq (packet processing). That coarse split already shows the key point
of Section 4: without offloads the sender core spends most of its time in softirq, doing receive
processing.</p>
<p><b>Expected result</b> (to be confirmed by the profile): data copy the largest single category
once TSO/GSO/GRO are on; TCP/IP and netdevice work dominant with "No opt."; receive-path
functions (<code>ip_rcv</code>, <code>tcp_v4_rcv</code>, <code>process_backlog</code>) visible on
the <i>sender</i> core because of the veth effect.</p>
"""
    rows = [[r["level"], r["role"], *[f"{100 * float(r[c]):.0f} %" for c in (
        "data copy", "tcp/ip processing", "netdevice subsystem", "skb mgmt",
        "memory alloc/dealloc", "lock/unlock", "scheduling", "etc.")]] for r in prof["rows"]]
    return f"""
<h3>6.8 Where the CPU cycles go (paper Table 1, Figs. 3c/3d)</h3>
{glance("profile")}
<p><b>Method.</b> <code>perf record -e cpu-clock -F 999 -C 0,2</code> for 10 s of each single-flow
level; idle samples removed; kernel functions sorted into the paper's categories (rules in the
result folder's <code>configuration.json</code>, top functions in <code>top-symbols.csv</code>).</p>
{figure("fig_cpu_breakdown.png", "Fraction of busy CPU samples per category, sender core (CPU0) and receiver core (CPU2), for each optimisation level.")}
{table(["Level", "Core", "copy", "tcp/ip", "netdev", "skb", "memory", "lock", "sched", "etc."], rows, "num")}
"""


def results(summary):
    return ('<h2 id="s6">6. Results, experiment by experiment</h2>'
            "<p>Each subsection has the same structure: what the paper did and found; a box with the "
            "question, setup, steps and measurements of our experiment; the graph and table; what "
            "we see; why; and how it compares with the paper.</p>"
            "<h3>The experiments at a glance</h3>" + OVERVIEW
            + res_single(summary) + res_buffers(summary) + res_patterns(summary)
            + res_scaling(summary) + res_loss(summary) + res_sizes(summary)
            + res_cc(summary) + res_profile(summary)
            + NOT_REPRODUCED)


FIXES = """
<h2 id="s7">7. Mistakes in the first version and how they were fixed</h2>
<p>The first version of the project (the scripts and results of 9 September) was checked
line by line against the paper. These problems were found; all are fixed in the current scripts.
A copy of the old version is in <code>~/host-stack-paper.zip</code>.</p>
<table class="long">
<tr><th>#</th><th>Problem</th><th>Why it matters</th><th>Fix</th></tr>
<tr><td>1</td><td>Only total throughput was reported. The paper's metric, throughput-per-core,
was never computed, although mpstat logs were recorded for every run.</td><td>All of the paper's
conclusions are about CPU cost per byte. Comparing total Gbps of patterns that use different
numbers of cores (e.g. "four-flow / single-flow ratio") is not the paper's comparison.</td>
<td>Per-core CPU from mpstat in the measured window; throughput per busy core for both hosts
and for the bottleneck side, per run.</td></tr>
<tr><td>2</td><td>CPU figures in the loss and congestion-control graphs came from iperf3's
<code>cpu_utilization_percent</code>.</td><td>That is only the iperf3 process's own time; it
misses softirq packet processing (which in veth often runs on the other side's CPU).</td><td>mpstat
per core, like the paper's sysstat.</td></tr>
<tr><td>3</td><td>Packet loss: <code>tc qdisc replace</code> kept netem's counters across runs, so
each run's saved drop count was cumulative (a 0 % run showed 485,973 drops).</td><td>Per-run
loss statistics were wrong. (Recomputing the old counters as differences shows that the
<i>configured</i> loss itself had been correct.)</td><td>The queue is deleted and re-created per run;
the measured loss rate is stored per run.</td></tr>
<tr><td>4</td><td>No script created the <code>hsp_tx/hsp_rx</code> namespaces used by five
experiments, and the single-flow baseline was run by hand (<code>sender.sh</code>,
<code>receiver.sh</code>).</td><td>Their settings (MTU, offloads, qdisc) were not recorded, so
nobody could rebuild the exact setup.</td><td>Every experiment creates, records and deletes its own
namespaces.</td></tr>
<tr><td>5</td><td>Four almost identical scripts (one_to_one, incast, outcast, all_to_all), six
plot scripts, and <code>packet_loss.py</code> importing helpers from <code>one_to_one.py</code>.</td>
<td>Copy-paste code drifts apart; a fix in one copy is missed in the others.</td><td>One shared module
(<code>common.py</code>), one script per paper section, one analysis script.</td></tr>
<tr><td>6</td><td>Patterns ran in separate sessions in a fixed order, and the plots used whichever
folder was newest. Two complete all-to-all sessions disagreed (means 144.1 and 173.9 Gbps); only the
second was plotted.</td><td>Session-to-session drift was mistaken for a pattern effect, and picking
the newest folder is an arbitrary selection.</td><td>All patterns interleaved in one seeded random order;
all repetitions reported with SD.</td></tr>
<tr><td>7</td><td>Aborted and partial runs were left in <code>results/</code> (an all-to-all run that
stopped after 8 s; two partial congestion-control runs).</td><td>A plot script could pick them up.</td>
<td><code>COMPLETED.txt</code> only after all runs succeed; the analysis ignores anything else.
Deleted.</td></tr>
<tr><td>8</td><td>Background load was not measured: during the first single-flow run, CPUs 1 and 3
(not used by the test) were up to 71 % busy (26 % on average), and that run was 13 % slower than
the other two.</td><td>Other programs compete with the experiment and add
variation.</td><td>Idle baseline recorded before every experiment and reported (Section 5.4).</td></tr>
<tr><td>9</td><td>In the flow-size experiment the long flow used netperf's default 16 KB writes and
reached 36.6 Gbps, while every other experiment used iperf3's 128 KB writes (≈ 98 Gbps).</td>
<td>The "long flow" of §3.7 was not the same long flow as in the other sections.</td><td>netperf
<code>-m 131072</code> (128 KB writes).</td></tr>
<tr><td>10</td><td>Paper items that are really part of §3.1–3.5 were missing: the step-by-step
optimisations (Fig. 3a), the TCP buffer study (Fig. 3e), flow-count scaling (Figs. 6/7) and the
CPU breakdown of Table 1.</td><td>These are core results of the paper.</td><td>Added:
<code>exp_single_flow.py</code>, scaling patterns, <code>exp_cpu_profile.py</code>.</td></tr>
<tr><td>11</td><td>Leftover files: <code>congestion_control.before_*.py</code>,
<code>run_congestion_control.py</code> (not needed, because root may select any loaded algorithm),
root-owned <code>__pycache__</code> and result folders, old notes describing namespaces that no
longer exist.</td><td>Clutter; files could not be edited without sudo.</td><td>Removed; results are
returned to the user after sudo runs.</td></tr>
</table>
<div class="box good"><h4>What was already right, and kept</h4>
CPU pinning with taskset; one process pair per flow; 3 s warm-up + 15 s measurement; checking the
live congestion-control algorithm with <code>ss</code> and the corrected DCTCP/ECN check; netem on an
IFB at the receiver with offloads off for per-packet loss; seeded random order in the loss and
flow-size experiments; receiver-side throughput; honest notes in the graphs.</div>
"""

RUNNING = """
<h2 id="s8">8. How to run everything again</h2>
<pre>cd ~/host-stack-paper
sudo apt install iperf3 netperf sysstat ethtool iproute2 linux-tools-$(uname -r) weasyprint
# close VS Code, the browser and Docker first (they compete for the 4 vCPUs)
sudo bash scripts/run_all.sh        # all experiments, about 70 minutes
python3 scripts/analyze.py          # graphs and tables -> analysis/
python3 scripts/make_report.py      # this report -> report/</pre>
<p>A single experiment can be repeated on its own, with more repetitions, for example
<code>sudo python3 scripts/exp_traffic_patterns.py --reps 5</code> or
<code>sudo python3 scripts/exp_single_flow.py --levels no-opt,tso-gro --no-buffers</code>.
Each script prints its results folder; the raw data of every run stays there (iperf3 JSON, mpstat
log, server logs, settings).</p>
<table>
<tr><th>Script</th><th>Paper</th><th>Runs</th><th>Time</th></tr>
<tr><td>exp_single_flow.py</td><td>§3.1, Fig. 3a/b/e</td><td>4 levels × 3 + 6 buffers × 3</td><td>≈ 12 min</td></tr>
<tr><td>exp_traffic_patterns.py</td><td>§3.2–3.5, Figs. 5–8</td><td>9 patterns × 3</td><td>≈ 11 min</td></tr>
<tr><td>exp_packet_loss.py</td><td>§3.6, Fig. 9</td><td>4 loss rates × 3</td><td>≈ 5 min</td></tr>
<tr><td>exp_flow_sizes.py</td><td>§3.7, Figs. 10–11</td><td>9 cases × 3</td><td>≈ 11 min</td></tr>
<tr><td>exp_congestion_control.py</td><td>§3.10, Fig. 13</td><td>3 algorithms × 3</td><td>≈ 4 min</td></tr>
<tr><td>exp_cpu_profile.py</td><td>Table 1, Fig. 3c/d</td><td>4 levels</td><td>≈ 3 min</td></tr>
</table>
"""

QA = """
<h2 id="s9">9. Questions the professor may ask, with answers</h2>
<dl class="qa">
<dt>1. What is the paper's main contribution, in one sentence?</dt>
<dd>A detailed measurement of where the Linux kernel spends CPU when sending and receiving at
100 Gbps, showing that the bottleneck has moved from the network to the host CPU, with data copy,
cache behaviour and resource sharing between flows as the main costs.</dd>

<dt>2. What is throughput-per-core and why not simply use throughput?</dt>
<dd>Throughput divided by the number of cores used (CPU utilisation in cores) at the bottleneck
host. At 100 Gbps one flow cannot fill the link, so throughput alone hides how expensive each byte
is; throughput-per-core tells how many cores a given rate costs, which is what limits real
servers.</dd>

<dt>3. Why did you use one laptop instead of two?</dt>
<dd>Because the paper's results only appear when the CPU, not the link, is the bottleneck. Laptop
links are about 1 Gbps; at our measured efficiency that needs only a few percent of one core, so two
laptops would measure the link speed and every experiment would look the same. A veth pair has no
line rate, so the CPU is the bottleneck, as in the paper's 100 Gbps testbed. (Section 3.)</dd>

<dt>4. Is a virtual machine realistic at all?</dt>
<dd>The whole TCP/IP stack is the real Linux code: sockets, TCP, congestion control, qdiscs,
GSO/GRO, softirqs, data copies. What is missing is the hardware below the driver (NIC, DMA,
interrupts, DDIO, IOMMU), and both hosts share one kernel and cache. So the results are realistic
for the software stack and not for NIC/cache effects, and we list exactly which parts are affected.</dd>

<dt>5. What is a network namespace? What is a veth pair? Does veth copy the data?</dt>
<dd>A namespace is an isolated copy of the network stack (interfaces, addresses, routes, sockets).
A veth pair is two virtual interfaces connected back-to-back. veth does not copy the payload: it hands
the same skb to the other side and the kernel then processes it as a received packet. So there is
one copy at the sender and one at the receiver, as in the paper.</dd>

<dt>6. How do you know the veth is not the bottleneck?</dt>
<dd>The throughput follows the CPU work: switching offloads off, or sharing a core between flows,
changes throughput, and in the single-flow runs one core is close to 100 % busy. If a link were the
limit, throughput would stay fixed while CPUs idled.</dd>

<dt>7. Why is your throughput per core higher than the paper's 42 Gbps?</dt>
<dd>No NIC, DMA or interrupts; the receiver copies data that was just written by the sender core
(so it is likely still in cache: no DDIO eviction problem); part of the receive work is done by the
sender's core; and a modern Apple core is faster than a 2017 Xeon core. The trends, not the absolute
numbers, are what we compare.</dd>

<dt>8. In the paper the receiver is the bottleneck. In yours it is the sender. Why?</dt>
<dd>veth delivers a packet on the CPU that transmitted it, so the receiver's IP/TCP processing
(softirq) runs on the sender's core; you can see this as softirq time on CPU0. In addition, the
receiver's copy is cheap because the data is warm in cache. RFS (our aRFS stand-in) moves the receive
processing back to the receiver core.</dd>

<dt>9. What do TSO, GSO and GRO do, and why does turning them off hurt so much?</dt>
<dd>They let the stack work with 64 KB skbs instead of 1500-byte packets: TSO/GSO split big skbs as
late as possible on the send side, GRO merges small packets as early as possible on the receive side.
Without them every 1500 bytes pay the full per-packet cost (TCP/IP, qdisc, skb allocation, softirq),
roughly 44× more often.</dd>

<dt>10. Why do jumbo frames help less in your setup?</dt>
<dd>In the paper GRO has to merge 1500-byte frames arriving from the NIC; with MTU 9000 there are 6×
fewer to merge. In veth, with TSO on, the 64 KB skb is never split, so there is nothing to merge and
the MTU hardly matters.</dd>

<dt>11. What is aRFS, and what did you use instead?</dt>
<dd>Accelerated Receive Flow Steering: the NIC delivers each flow's packets to the core where the
consuming application runs, so interrupt, TCP/IP and copy share one cache. We have no NIC, so we use
RFS, the kernel's software version, as the fourth single-flow level. It needs a global kernel table,
so it runs only under real sudo.</dd>

<dt>12. What is DDIO and why could you not test it (§3.8)?</dt>
<dd>Intel Data Direct I/O lets a NIC write packets into the L3 cache instead of DRAM. It needs an
Intel Xeon and a physical NIC doing DMA. We have Apple silicon and a veth, so there is nothing to
switch on or off.</dd>

<dt>13. Why no IOMMU experiment (§3.9)?</dt>
<dd>The IOMMU translates the addresses a device uses for DMA and checks permissions. The cost it adds
is mapping and unmapping pages for the NIC. Without a device doing DMA there is nothing to translate.</dd>

<dt>14. Why no cache-miss rates?</dt>
<dd>They need the CPU's hardware performance counters. The VM does not expose them
(<code>/sys/bus/event_source/devices</code> has no hardware PMU), so perf can only use timer-based
software events.</dd>

<dt>15. How did you measure CPU use? What is "busy"?</dt>
<dd>mpstat every second for every CPU; busy = 100 % − idle, which includes user, system, softirq and
irq time, like sysstat in the paper. We average the seconds inside each run's measured 15 s window
(aligned with iperf3's timestamps).</dd>

<dt>16. What does taskset guarantee? Can the kernel still use other cores?</dt>
<dd>taskset pins the application's threads. Kernel work triggered by them runs on the same core
(system calls) or wherever a softirq is raised; kernel threads and other programs can still run on any
core. That is why we measure every CPU, not just the application's.</dd>

<dt>17. Why omit 3 seconds? Why 15 seconds? Why 3 repetitions? Why random order?</dt>
<dd>The first seconds contain TCP slow start and warm-up. 15 s gives stable averages. 3 repetitions
give a mean and a standard deviation within reasonable time (more is better; <code>--reps</code>
changes it). Random order stops slow drift (for example background load) from favouring one condition.</dd>

<dt>18. How did you create packet loss, and how do you know the loss rate is correct?</dt>
<dd>Incoming packets at the receiver are redirected to an IFB device whose netem qdisc drops them at
random. The netem counters (packets and drops) are read after each run and the measured loss rate
is stored next to the configured one.</dd>

<dt>19. Why switch TSO/GSO/GRO off for the loss experiment?</dt>
<dd>With TSO on, a 64 KB skb crosses the veth whole; netem would drop the whole skb, which is 44 wire
packets at once. A switch drops individual packets. Turning segmentation off makes every skb one
1500-byte packet, so the drop probability applies per packet, as in the paper.</dd>

<dt>20. Why are there retransmissions at 0 % loss?</dt>
<dd>netem dropped nothing in those runs. The nstat counters show reordering (out-of-order
packets at the receiver, DSACK reports of duplicates at the sender), so they are mostly spurious
retransmissions: packets that were late, not lost. With veth, data can leave from two CPUs (the
application's CPU0, and CPU2 when it processes ACKs) and each CPU delivers through its own queue, so
packets can overtake each other. Real queue drops (softnet_stat) were almost zero.</dd>

<dt>21. How did you scale incast/outcast/all-to-all to 4 CPUs?</dt>
<dd>Each host gets 2 CPUs. Incast: CPUs 0 and 1 both send to CPU 2. Outcast: CPU 0 sends to CPUs 2 and 3.
All-to-all: 0→2, 0→3, 1→2, 1→3. To follow the paper's "number of flows" axis we also run 4 and 8 flows
into one receiver core (incast) and out of one sender core (outcast).</dd>

<dt>22. Why is outcast about as fast as a single flow?</dt>
<dd>All sending work, and in veth also most of the receive softirq work, of both flows lands on CPU0.
That one core is saturated, so two flows share what one core can do.</dd>

<dt>23. What does netperf TCP_RR measure, and why does throughput per core rise with message size?</dt>
<dd>A request/response ping-pong: the client sends a request of N bytes, waits for an N-byte response,
repeats. Each transaction has fixed costs (system calls, sleeping and waking, small-packet TCP work)
plus per-byte copy cost; larger messages spread the fixed cost over more bytes.</dd>

<dt>24. What happens when long and short flows share a core, and why?</dt>
<dd>The long flow loses most of its throughput and the short flows lose some. The scheduler shares
the core between all runnable threads, short flows wake up constantly, and the cache holds data for all of them.
The paper concludes that long and short flows should be scheduled on different cores.</dd>

<dt>25. How did you check that DCTCP really ran with ECN? Why is it as fast as CUBIC?</dt>
<dd><code>ss -ti</code> on the live data socket shows "dctcp" and its internal state; without ECN,
Linux switches DCTCP to a fallback ("dctcp-reno", shown as fallback_mode). It matches CUBIC because a
veth builds almost no queue, so fq marks (almost) no packets and DCTCP never slows down.</dd>

<dt>26. Why is BBR slower in your VM but not in the paper?</dt>
<dd>BBR paces packets with timers, which adds work and wake-ups on the sender (the paper saw this as
higher sender scheduling overhead). In the paper the receiver was the bottleneck, so the extra sender
work did not reduce throughput; in our VM the sender core is the bottleneck, so it does.</dd>

<dt>27. How does your perf breakdown work?</dt>
<dd>perf samples CPUs 0 and 2 about 1000 times per second and records which function was running.
Idle samples are removed; each kernel function name is mapped to one of the paper's eight categories
by a documented list of rules (for example <code>__arch_copy_to_user</code> → data copy,
<code>tcp_*</code> → tcp/ip, <code>*gro*</code> → netdevice), and the fraction per category is reported.</dd>

<dt>28. What was wrong in your first version?</dt>
<dd>See Section 7. Mainly: the paper's metric was missing, CPU came from iperf3's process counter,
netem counters were cumulative, the setup was not scripted, runs were compared across sessions and
aborted runs were mixed in. All fixed and documented.</dd>

<dt>29. How large is the run-to-run variation, and when is a difference real?</dt>
<dd>Usually 5–10 % (standard deviations are in every table). With 3 runs, differences below about two
standard deviations should not be claimed. For example, the first version had two all-to-all sessions
differing by 20 %, which is why all conditions are now interleaved in one session.</dd>

<dt>30. Which results agree with the paper and which do not?</dt>
<dd>Agree: offloads are the key optimisation; per-message costs dominate small RPCs; mixing long and
short flows hurts; loss reduces throughput-per-core by tens of percent; flows sharing a core hurt
efficiency; congestion control matters mainly through CPU cost. Differ: the bottleneck side
(sender here, because of veth), the size of the jumbo-frame benefit, no large-buffer penalty (no DDIO),
and BBR (the sender is our bottleneck). Each difference has a stated reason.</dd>

<dt>31. What would you do with more time or hardware?</dt>
<dd>Run on two servers with 25–100 Gbps NICs to include DMA, interrupts, aRFS and DDIO; use a VM with
PMU access (or bare metal) to measure cache misses; more repetitions; and try zero-copy receive
(<code>tcp_mmap</code>) or io_uring to test the paper's future-directions ideas.</dd>

<dt>32. What is the bandwidth-delay product and why does the buffer size matter?</dt>
<dd>BDP = rate × round-trip time, the amount of data that must be in flight to keep the pipe full. TCP
cannot have more unacknowledged data than its window/buffer, so throughput ≤ buffer ÷ RTT. In the paper,
host latency grows at high load, which raises the BDP.</dd>

<dt>33. What is a softirq?</dt>
<dd>Deferred kernel work that runs after an interrupt or when a CPU leaves kernel code, outside any
process. Packet receive processing (NET_RX) and some transmit completion run there. mpstat shows it as
%soft.</dd>
</dl>
"""

GLOSSARY = """
<h2 id="s10">10. Glossary</h2>
<dl class="gloss">
<dt>ACK</dt><dd>TCP acknowledgement telling the sender which bytes arrived.</dd>
<dt>aRFS / RFS</dt><dd>(Accelerated) Receive Flow Steering: process received packets on the core where the application runs (NIC / software).</dd>
<dt>BBR</dt><dd>Google's congestion control; models bandwidth and RTT and paces packets.</dd>
<dt>BDP</dt><dd>Bandwidth-delay product: data in flight needed to fill the path.</dd>
<dt>CUBIC</dt><dd>Linux's default congestion control; loss-based, cubic window growth.</dd>
<dt>cwnd</dt><dd>Congestion window: how much unacknowledged data TCP may have in flight.</dd>
<dt>DCA / DDIO</dt><dd>Direct Cache Access / Intel Data Direct I/O: NIC DMA into the L3 cache.</dd>
<dt>DCTCP</dt><dd>Datacenter TCP: reduces its window in proportion to the fraction of ECN-marked packets.</dd>
<dt>DMA</dt><dd>Direct Memory Access: a device reads or writes memory without the CPU.</dd>
<dt>ECN / CE</dt><dd>Explicit Congestion Notification: a queue marks packets "Congestion Experienced" instead of dropping them.</dd>
<dt>fq</dt><dd>Fair-queue qdisc; per-flow queues and pacing; can mark CE above a delay threshold.</dd>
<dt>GRO / LRO</dt><dd>Generic / Large Receive Offload: merge received packets of a flow into large skbs (software / NIC).</dd>
<dt>GSO / TSO</dt><dd>Generic / TCP Segmentation Offload: split large skbs into MTU packets late (software / NIC).</dd>
<dt>IFB</dt><dd>Intermediate Functional Block: virtual device that lets a qdisc act on incoming traffic.</dd>
<dt>IOMMU</dt><dd>Translates and protects device DMA addresses.</dd>
<dt>iperf3</dt><dd>Bulk TCP throughput tool (one long flow per client).</dd>
<dt>IRQ</dt><dd>Hardware interrupt request.</dd>
<dt>mpstat</dt><dd>sysstat tool printing per-CPU utilisation (user, system, softirq, idle...).</dd>
<dt>MTU</dt><dd>Maximum Transmission Unit: largest packet on the link (1500 or 9000 bytes).</dd>
<dt>NAPI</dt><dd>Linux receive API: after an interrupt the driver polls many packets at once.</dd>
<dt>netem</dt><dd>qdisc that emulates delay, loss, reordering.</dd>
<dt>netns</dt><dd>Network namespace: an isolated network stack.</dd>
<dt>netperf</dt><dd>Benchmark tool; TCP_RR = request/response, TCP_STREAM = bulk.</dd>
<dt>NUMA</dt><dd>Non-Uniform Memory Access: memory and devices are closer to some sockets than others.</dd>
<dt>perf</dt><dd>Linux profiler; samples which function each CPU is running.</dd>
<dt>PMU</dt><dd>Performance Monitoring Unit: hardware counters (cycles, cache misses).</dd>
<dt>qdisc</dt><dd>Queueing discipline: the kernel's per-interface packet scheduler.</dd>
<dt>RSS / RPS</dt><dd>Receive Side Scaling / Receive Packet Steering: spread flows over cores by hash (NIC / software).</dd>
<dt>RTT</dt><dd>Round-trip time.</dd>
<dt>skb</dt><dd>sk_buff, the kernel's packet descriptor; points to the data.</dd>
<dt>softirq</dt><dd>Deferred kernel work, e.g. NET_RX packet processing.</dd>
<dt>ss</dt><dd>Socket statistics tool; <code>ss -ti</code> shows TCP internals of live sockets.</dd>
<dt>taskset</dt><dd>Pins a program to chosen CPUs.</dd>
<dt>veth</dt><dd>Virtual Ethernet pair: two interfaces joined back-to-back.</dd>
</dl>
"""

APPENDIX = """
<h2 id="s11">Appendix: project files</h2>
<table>
<tr><th>Path</th><th>Contents</th></tr>
<tr><td>scripts/common.py</td><td>Namespaces and veth, running iperf3 flows, mpstat parsing, throughput-per-core</td></tr>
<tr><td>scripts/exp_*.py</td><td>One script per paper section (see Section 8)</td></tr>
<tr><td>scripts/analyze.py</td><td>Graphs (analysis/fig_*.png), tables (analysis/*.csv) and analysis/summary.json</td></tr>
<tr><td>scripts/make_report.py</td><td>This report</td></tr>
<tr><td>scripts/run_all.sh, record_environment.sh</td><td>Run everything; record the machine's facts in notes/environment.txt</td></tr>
<tr><td>results/&lt;experiment&gt;-&lt;date&gt;/</td><td>configuration.json (all settings), runs.csv (one line per run),
per run: iperf3 JSON (<code>*-flow-PORT.json</code>), mpstat log (<code>*-cpu.txt</code>), CPU window
(<code>*-meta.json</code>), server logs; loss: netem/nstat/softnet snapshots; congestion control: ss snapshots and queue stats</td></tr>
<tr><td>analysis/</td><td>Figures and summary tables used in this report</td></tr>
</table>
<p class="small">Reference: Q. Cai, S. Chaudhary, M. Vuppalapati, J. Hwang, R. Agarwal. Understanding Host
Network Stack Overheads. ACM SIGCOMM 2021, pp. 65–77. doi:10.1145/3452296.3472888.</p>
"""


def sources(summary):
    rows = [[key.replace("_", " "), value.get("source", "")]
            for key, value in summary.items() if isinstance(value, dict)]
    return ("<h3>Data used in this report</h3>" + table(["Experiment", "Result folder"], rows)
            if rows else "")


# --------------------------------------------------------------------------

def main():
    summary_path = ANALYSIS / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    body = (cover(summary) + TOC + PAPER + setup(summary) + why_one(summary) + LIMITS
            + method(summary) + results(summary) + FIXES + RUNNING + QA + GLOSSARY
            + APPENDIX + sources(summary))
    page = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>Host network stack '
            f"overheads: project report</title><style>{CSS}</style></head><body>{body}</body></html>")
    REPORT.mkdir(exist_ok=True)
    html_path = REPORT / f"{NAME}.html"
    html_path.write_text(page)
    pdf_path = REPORT / f"{NAME}.pdf"
    try:
        import weasyprint
        weasyprint.HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except ImportError:
        if shutil.which("weasyprint"):
            subprocess.run(["weasyprint", str(html_path), str(pdf_path)], check=True)
        else:
            print("WeasyPrint not installed (sudo apt install weasyprint); "
                  f"open {html_path} in a browser and print it to PDF.")
            return
    print(f"Report: {pdf_path}")


if __name__ == "__main__":
    main()
