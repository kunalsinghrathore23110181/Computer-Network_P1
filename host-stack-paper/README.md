# Host network stack overheads, reproduced in one virtual machine

Scaled-down reproduction of Cai et al., *Understanding Host Network Stack
Overheads*, ACM SIGCOMM 2021, on one laptop: an Ubuntu VM with 4 vCPUs.
Two network namespaces joined by a veth pair play the paper's two servers.
The full explanation is in `report/Host_Stack_Project_Report.pdf`.

## Layout

| Path | Contents |
|---|---|
| `scripts/common.py` | Shared code: namespaces, veth, iperf3 runs, mpstat CPU accounting, throughput-per-core |
| `scripts/exp_single_flow.py` | §3.1: optimisations one at a time (Fig. 3a/b) and TCP buffer size (Fig. 3e) |
| `scripts/exp_traffic_patterns.py` | §3.1–3.5: single, one-to-one, incast, outcast, all-to-all, plus flow-count scaling |
| `scripts/exp_packet_loss.py` | §3.6: random loss 0 / 0.015 / 0.15 / 1.5 % |
| `scripts/exp_flow_sizes.py` | §3.7: RPC sizes 4–64 KiB and mixed long/short flows |
| `scripts/exp_congestion_control.py` | §3.10: CUBIC, BBR, DCTCP |
| `scripts/exp_cpu_profile.py` | Table 1 / Fig. 3c-d: perf CPU breakdown in the paper's 8 categories |
| `scripts/analyze.py` | All graphs and tables → `analysis/` |
| `scripts/make_report.py` | The report PDF → `report/` (numbers read from `analysis/summary.json`) |
| `scripts/run_all.sh` | Runs everything in order |
| `results/<experiment>-<date>/` | Raw data of every run (iperf3/netperf output, mpstat logs, settings) |
| `analysis/` | Graphs (`fig_*.png`), tables (`*.csv`), `summary.json` |
| `report/` | The project report (PDF and HTML) |

## Running

```bash
sudo apt install iperf3 netperf sysstat ethtool iproute2 linux-tools-$(uname -r)
sudo bash scripts/run_all.sh        # about 70 minutes; close other programs first
python3 scripts/analyze.py          # rebuild graphs from the newest complete runs
```

Each experiment script can also be run on its own. For example,
`sudo python3 scripts/exp_traffic_patterns.py --patterns incast,outcast --reps 5`.
Every script creates its own namespaces, deletes them when it finishes, and
writes `COMPLETED.txt` only after all runs succeed. `analyze.py` ignores any
folder without that file.
