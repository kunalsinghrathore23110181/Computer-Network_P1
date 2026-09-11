# AI_Used

## Tools Used

The main AI tool used during this project was **ChatGPT (OpenAI)**. It was used as a technical assistant throughout the project to understand the research paper, set up the experiments, debug errors, interpret outputs, and prepare the final presentation.

The actual experiments were performed on the Linux system using tools such as **iperf3, tc/netem, ethtool, tcpdump, sysstat, Linux networking utilities, Bash, and Python**. AI was used for guidance, explanation, debugging, and code assistance, while the final experimental results were obtained by running the commands on the real system.

## Prompts Given to AI

Some representative prompts used during the project were:

- “Explain this paper from the beginning because I do not know this topic.”
- “Explain each experiment in the paper and what we have to reproduce.”
- “Give me the project steps from zero and explain every command.”
- “How do I identify the sender and receiver Ethernet interfaces?”
- “How can I reproduce the single-flow experiment using iperf3?”
- “How can I test packet loss, delay, congestion control, and multiple flows?”
- “Explain TSO, GSO, GRO, NUMA, DMA, NAPI, RSS, RFS, aRFS, and BDP.”
- “This command is giving an error. Explain the error and tell me how to solve it.”
- “Why is this experiment not giving the expected output?”
- “Explain this script line by line.”
- “How should I compare our results with the paper?”
- “What questions can be asked during the presentation or viva?”

These prompts were mainly used to understand the project, solve problems during execution, and prepare explanations for the final submission.

## How AI Was Integrated into the Workflow

AI was used throughout the project instead of only at the end. First, the paper **Understanding Host Network Stack Overheads** was difficult to understand because it contains concepts related to the Linux kernel, networking, CPU overhead, NUMA, cache behavior, packet processing, and hardware offloads. ChatGPT was used to simplify these concepts and explain the complete sender-side and receiver-side packet paths.

After understanding the paper, AI helped convert the research paper into practical experiments that could be performed on our available hardware. The original paper used specialized 100 Gbps Mellanox NICs, NUMA servers, and a modified Linux kernel. Since the same hardware was not available, AI helped identify which experiments could realistically be reproduced and which ones should be mentioned as limitations.

AI then guided the complete setup of the project. It explained how to install required packages, identify the Ethernet interface, check IP addresses, verify routing, start the iperf3 server, and run the client. Commands such as `ip -br link`, `ip -br addr`, `ip route`, `ethtool`, `iperf3`, and `tcpdump` were explained before being used.

## Step-by-Step Details of AI Contribution

### 1. Understanding the Research Paper

AI helped explain the main objective of the paper: to study where CPU time is spent in the Linux network stack at high bandwidth.

It explained important terms including:
- Linux host network stack
- TCP/IP processing
- `skb` or socket buffer
- DMA
- IRQ and NAPI
- TSO, GSO, and GRO
- RSS, RPS, RFS, and aRFS
- NUMA
- Bandwidth-Delay Product
- Throughput-per-core

AI also explained the five traffic patterns used in the paper: single flow, one-to-one, incast, outcast, and all-to-all.

### 2. Setting Up the Experiment Environment

AI guided the installation of required packages such as `iperf3`, `sysstat`, `ethtool`, `tcpdump`, `jq`, `iproute2`, Python, and Matplotlib.

It also helped identify the correct network interface and check whether experiment traffic was using Ethernet instead of another interface. Commands such as:

```bash
ip -br link
ip -br addr
ip route
ethtool <interface>
```

were used for this purpose. AI explained the meaning of the output so the setup could be documented correctly.

### 3. Running the Networking Experiments

AI guided the setup of the receiver using:

```bash
iperf3 -s
```

and the sender using:

```bash
iperf3 -c <receiver-ip> -t 15
```

It also helped perform experiments with multiple TCP flows using options such as `-P 4` and `-P 8`.

For packet-loss experiments, AI guided the use of Linux `tc netem`, for example:

```bash
sudo tc qdisc replace dev <interface> root netem loss 0.15%
```

AI explained that packet loss can lead to duplicate ACKs, retransmissions, congestion-control reactions, and extra TCP processing.

For delay experiments, AI helped use:

```bash
sudo tc qdisc replace dev <interface> root netem delay 20ms
```

This was used as an extension to observe the effect of increased delay and bandwidth-delay product.

### 4. Offload and Congestion-Control Experiments

AI explained the role of TSO, GSO, and GRO and showed how to inspect these features using:

```bash
ethtool -k <interface>
```

Where supported, AI also guided enabling or disabling these features using `ethtool -K`.

AI also helped compare congestion-control algorithms by first checking:

```bash
sysctl net.ipv4.tcp_available_congestion_control
```

and then testing the algorithms available on the system, such as CUBIC and Reno.

When some features or algorithms were unavailable, AI explained that this should be documented as a hardware or kernel limitation rather than forcing an incorrect experiment.

### 5. Error Solving and Debugging

One of the most important uses of AI in this project was **debugging errors**.

Whenever a command failed or produced unexpected output, the terminal output was shared with ChatGPT. AI helped:
- identify incorrect commands,
- explain permission-related problems,
- identify missing packages,
- correct interface names and IP settings,
- explain unsupported `ethtool` features,
- debug `tc/netem` configuration,
- understand congestion-control errors,
- check Bash and Python experiment scripts,
- and explain why some results differed from the original paper.

AI was not only used to provide another command after an error. It also explained **why the error occurred** and what the corrected command was doing. This was useful for learning the project while fixing problems.

### 6. Automation and Result Analysis

AI helped create Bash and Python scripts to automate repeated experiments and save the output in structured files.

It also helped process iperf3 JSON output, generate CSV summaries, and create graphs for throughput, CPU utilization, retransmissions, and throughput-per-core.

After the experiments, AI helped interpret the results and compare the observed trends with the paper. It also helped us avoid claiming exact reproduction when the available hardware was different from the original 100 Gbps testbed.

### 7. Presentation and Viva Preparation

AI was also used to prepare for the final presentation. It helped explain the entire project in simpler language and generated likely viva questions.

Examples included:
- Why is the receiver often the bottleneck?
- What is throughput-per-core?
- What is DMA?
- What is NAPI?
- What are TSO, GSO, and GRO?
- Why does packet loss increase CPU overhead?
- Why are our measured values different from those reported in the paper?
- What are the limitations of our hardware and setup?

## Final Note

AI was used as a **learning, debugging, coding, and documentation assistant** throughout the project. It helped us understand the paper, design the workflow, solve errors, automate experiments, interpret outputs, and prepare for the final presentation.

However, the experimental results were not generated or fabricated by AI. Throughput, CPU usage, retransmissions, packet captures, and other measurements were obtained by actually running the experiments on our system. AI mainly helped us perform the work correctly and understand what each step meant.
