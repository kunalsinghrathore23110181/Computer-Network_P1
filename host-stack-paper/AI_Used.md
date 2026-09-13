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




##PROMPT USED AND THE CONVERSATION ARE BELOW:

Tuesday 11:24 AM
3452296.3472888(5).pdf
PDF

| Understanding Host Network Stack Overheads | **Description** – Gather understanding of Network stack. Analyze and reproduce the results published in the paper and extend the evaluation <br>with various other scenarios.<br>**Tools** – Wireshark/tcpdump (packet analysis), Python/Java (traffic generation and automation), Linux networking utilities.<br>**Expected Outcomes** – Validation of published results, along with extended evaluation that highlights the impact of different network conditions<br>and configurations on performance.<br>**Reference** – [https://doi.org/10.1145/3452296.3472888](https://doi.org/10.1145/3452296.3472888) now tell me what i have to do in this project and how i can do and and what are the file i have to make and for both the laptop and also give me what are in the files and explain me as i told you what i have to do in this project

Your project is to measure how much CPU work Linux performs while sending and receiving network traffic, compare selected observations with the paper, and test additional conditions.

I’ve created the complete project folder for both laptops, including source code, setup commands, explanations, graph generation, and a report template:

Download 
host-stack-project.zip

Extract it and open README.md. It contains the complete step-by-step instructions and explains every file and command.

1. What your assignment actually requires

Requirement	What you must do
Understand the network stack	Explain how application data passes through sockets, TCP/IP, the driver, and the NIC—and how the receiver processes it
Reproduce published results	Repeat selected experiments, measure throughput and CPU consumption, and compare your observations with the paper
Extend the evaluation	Change conditions such as concurrent flows, application write sizes, offloads, or added delay
Present evidence	Submit actual measurements, graphs, packet analysis, explanations, and limitations

Sending data successfully is only the starting point. The measurements and analysis are the main project.

The paper used two servers connected by a 100 Gbps link, with hardware features that ordinary laptops may lack. Your work should therefore be described as a scaled reproduction of selected experiments with extensions, unless you have equivalent hardware. You cannot claim that a laptop experiment reproduces all its numerical findings.

2. What each laptop does

Laptop	Role	Responsibilities
Laptop 1	Sender and experiment controller	Generates traffic, measures its CPU usage, retrieves receiver CPU measurements, saves results, and creates graphs
Laptop 2	Receiver	Runs the receiving server and supplies CPU measurements

Use two separate physical hosts connected through Ethernet. Native Linux is preferable. If either Linux installation is a VM, document the virtualization because it introduces additional processing overhead.

3. What files you need—and what they contain

All these files are already written inside the download. Copy the complete extracted host-stack folder to both laptops.

File	What is inside
README.md	Full setup, commands, explanations, troubleshooting, experiment procedure, and cleanup
config.json	Both Ethernet IPs, interface names, receiver username, test duration, and repetitions
common/install.sh	Commands to install the required tools
common/inventory.py	Collects CPU, Linux, NIC, link, offload, and TCP configuration information
common/snapshot.py	Reads CPU counters and calculates CPU consumption
common/offloads.py	Saves, disables, and restores supported offload settings
receiver/start.sh	Starts the receiving server
sender/run.py	Runs repeated experiments and saves measurements from both laptops
sender/delay.sh	Runs an optional experiment with temporary added network delay
analysis/plot.py	Produces CSV tables and graphs
REPORT_TEMPLATE.md	Gives you the structure for your final report

Why use iperf3 instead of writing a basic sender yourself? It provides traffic generation and structured measurement output; Python automates the experiments around it. This lets you study networking performance without introducing unnecessary Python traffic-generation overhead. ESnet documentation

4. How you start—from zero

First, download the ZIP onto both Linux laptops. Assuming it is in Downloads, run:

sudo apt update
sudo apt install -y unzip

cd ~
unzip ~/Downloads/host-stack-project.zip

cd ~/host-stack
bash common/install.sh

These commands install the extraction tool, unpack the project, and install its dependencies.

Next, on both laptops, run:

ip -br link
ip -br addr
systemd-detect-virt

These show:

Network interface names.
Existing IP addresses.
Whether Linux is running inside a virtual environment.

Then follow README.md sections 5–8 to configure the Ethernet connection, edit config.json, and enable CPU collection over SSH.

Do not copy example interface names blindly. The actual names and receiver username must match your machines.

After that setup, start the receiver on Laptop 2:

cd ~/host-stack
bash receiver/start.sh

Leave that terminal running.

On Laptop 1, start the experiments:

cd ~/host-stack
python3 sender/run.py --label baseline

Once they finish, generate the graphs:

python3 analysis/plot.py

5. Which experiments you will perform

Experiment	What changes	What you investigate
Baseline	One TCP stream	Starting throughput and CPU consumption
Parallel-flow sweep	1, 2, 4, 8 streams	Whether concurrency changes performance or CPU cost
Write-size sweep	1, 16, 128 KiB application writes	Whether application write size affects performance
Offload comparison, if supported	Saved-default versus disabled offloads	How offloads affect CPU cost and throughput
Delay extension, optional	0, 5, 20 ms sender-egress delay	How added delay affects TCP performance

The default suite performs 18 measured tests: six conditions, each repeated three times.

Two distinctions matter:

Application write size is not Ethernet packet size.
Parallel streams do not reproduce the paper’s controlled incast/outcast CPU mappings.

The guide also includes a separate tcpdump capture for packet analysis and optional perf profiling for investigating where CPU time is spent.

6. How you explain your results

For each condition, answer:

Did delivered throughput increase, decrease, or remain similar?
Did sender or receiver CPU consumption change?
Was the change larger than the variation between repeated runs?
Which paper observation does this relate to?
What prevents a direct comparison?

For example, if disabling offloads increases CPU consumption while throughput stays similar, that could indicate an efficiency benefit hidden by the Ethernet link’s speed limit. That is an interpretation to evaluate using your measurements—not a result to assume beforehand.

The package measures whole-host CPU consumption. It does not automatically prove that copying, TCP processing, or another particular function dominates; those claims require profiling.

7. What you submit

Your final submission should contain:

Source files and configuration.
Hardware/software information from both laptops.
Raw measurements and summary CSV tables.
Throughput and CPU graphs.
A diagnostic packet capture with explanation.
A report comparing your observations with the paper and describing your extensions and limitations.

Validation: I checked Python compilation, shell syntax, CPU calculations, CSV statistics, and graph generation. The actual two-laptop Ethernet experiments still need to run on your hardware; no performance results have been fabricated.

Got it, bro. We’ll prepare Laptop 1 first, then Laptop 2, and finally run the experiments. Every command below says which laptop to use.

One thing to understand: you can finish the sender’s setup first, but you cannot test sending until the receiver is running.

The project files are already written. You only need to download them, configure your two laptops, and run the commands.

Step 1 — Laptop 1: Open the Ubuntu terminal

Run these commands inside Ubuntu, not in macOS Terminal:

cat /etc/os-release

This shows your Linux distribution.

The instructions below assume Ubuntu or Debian. If your laptop is running something else, stop here and tell me what this command prints.

Step 2 — Laptop 1: Download the project files

Download this file onto Laptop 1’s Ubuntu system, into its Downloads folder:

host-stack-project.zip

If you download it on macOS while Ubuntu runs in a VM, transfer the ZIP into Ubuntu’s Downloads folder.

The ZIP contains the sender code, receiver code, analysis code, and explanations. You do not need to create or type these files manually.

Step 3 — Laptop 1: Extract the project

Run:

sudo apt update
sudo apt install -y unzip

Meaning: update the package list and install the tool used to extract ZIP files.

Check whether an older project folder already exists:

ls -ld ~/host-stack

If it says “No such file or directory,” that is fine. Continue:

cd ~
unzip ~/Downloads/host-stack-project.zip
cd ~/host-stack
ls

If ~/host-stack already exists from your earlier attempt, use that existing folder if it contains this package; do not overwrite your previous measurements.

You should see files and folders such as:

README.md
config.json
common
sender
receiver
analysis
results
REPORT_TEMPLATE.md

Step 4 — Laptop 1: Install the experiment tools

Run:

cd ~/host-stack
bash common/install.sh

If installation asks whether to start iperf3 automatically as a service, choose No.

This installs:

Tool	Why we need it
iperf3	Generates TCP traffic and measures throughput
python3	Runs the experiment automation
python3-matplotlib	Creates graphs
ethtool	Shows Ethernet link and offload settings
sysstat	Provides CPU-monitoring tools
tcpdump	Captures packets
openssh-server	Supports remote access between the laptops
iproute2	Provides Linux network configuration tools

Step 5 — Laptop 1: Connect Ethernet and identify its interface

Connect the two laptops using your Ethernet connection.

Run:

ip -br link
ip -br addr

You may see names such as:

lo
enp0s1
enp3s0
enx...
wlp...
docker0

Choose the interface connected to the experimental Ethernet cable.

Do not choose lo.
Do not choose docker0 or a Docker bridge.
Do not choose the Wi-Fi interface.
Do not assume enp0s1 is the physical Ethernet connection merely because it appears.

Run:

systemd-detect-virt

If this identifies a VM, record that fact. Two separate physical laptops are still needed for this two-host experiment. A VM also needs an appropriate Ethernet configuration; a NAT-only virtual connection is not equivalent to a direct Linux Ethernet interface.

Now enter your sender’s Ethernet interface name:

read -r -p "Enter Laptop 1 Ethernet interface name: " SENDER_IFACE
export SENDER_IFACE
ip link show dev "$SENDER_IFACE"

For example, when prompted, you might type:

enp0s1

Use your actual name.

Inspect the connection:

sudo ethtool "$SENDER_IFACE"

Look for:

Link detected: yes

Also record Speed if reported. If the link is not detected, check the cable and adapters before continuing.

Keep this terminal open, because it holds the SENDER_IFACE variable.

Step 6 — Laptop 1: Check the experimental IP range

For this guide, we will use:

Laptop	Ethernet IP
Laptop 1: sender	192.168.50.1
Laptop 2: receiver	192.168.50.2

These addresses are intended for a dedicated experimental connection.

First run:

ip route

If 192.168.50.0/24 is already used by Wi-Fi, a VPN, Docker, or another network, do not add these addresses blindly. A different unused subnet is needed.

Otherwise, continue.

Step 7 — Laptop 1: Assign the sender IP

Run in the same terminal:

sudo ip link set dev "$SENDER_IFACE" up
sudo ip addr add 192.168.50.1/24 dev "$SENDER_IFACE"

Meaning:

The first command enables the interface.
The second adds the sender’s experimental IP address.

Check it:

ip -br addr show dev "$SENDER_IFACE"

You should see:

192.168.50.1/24

If ip addr add says “File exists,” inspect the output above. The address may already be configured.

These addresses are temporary and may need to be added again after reboot.

Step 8 — Laptop 1: Save the sender interface in the configuration

Run:

cd ~/host-stack

python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path("config.json")
config = json.loads(path.read_text())

config["sender_ip"] = "192.168.50.1"
config["receiver_ip"] = "192.168.50.2"
config["sender_iface"] = os.environ["SENDER_IFACE"]
config["duration"] = 20
config["repeats"] = 3

path.write_text(json.dumps(config, indent=2) + "\n")
print(path.read_text())
PY

Meaning: this records your sender interface, experiment addresses, 20-second tests, and three repetitions.

You will still see CHANGE_ME for the receiver interface and receiver username. That is expected—we will fill them after setting up Laptop 2.

Laptop 1’s initial preparation is complete. Now move to Laptop 2.

Step 9 — Laptop 2: Download and extract the same project

Open Ubuntu Terminal on Laptop 2.

Download the same ZIP into this laptop’s Ubuntu Downloads folder:

host-stack-project.zip

Run:

sudo apt update
sudo apt install -y unzip

If you do not already have a ~/host-stack folder, extract it:

cd ~
unzip ~/Downloads/host-stack-project.zip
cd ~/host-stack
bash common/install.sh

Again, choose No if asked to start iperf3 automatically as a service.

Step 10 — Laptop 2: Find its Ethernet interface and username

Run:

ip -br link
ip -br addr
ip route
whoami

Write down:

Laptop 2’s Ethernet interface name.
The username printed by whoami.

For example:

Receiver interface: enp3s0
Receiver username: guru

These are examples—use the actual values.

Check that 192.168.50.0/24 is not already assigned to an unrelated network on this laptop.

Enter the receiver interface:

read -r -p "Enter Laptop 2 Ethernet interface name: " RECEIVER_IFACE
export RECEIVER_IFACE

ip link show dev "$RECEIVER_IFACE"
sudo ethtool "$RECEIVER_IFACE"

Confirm the cable connection is detected.

Step 11 — Laptop 2: Assign the receiver IP

Run:

sudo ip link set dev "$RECEIVER_IFACE" up
sudo ip addr add 192.168.50.2/24 dev "$RECEIVER_IFACE"

Check:

ip -br addr show dev "$RECEIVER_IFACE"

You should see:

192.168.50.2/24

Now test communication with Laptop 1:

ping -I 192.168.50.2 -c 4 192.168.50.1

Meaning: send four test packets using the receiver’s experimental Ethernet address.

You should receive replies. If not, fix connectivity before proceeding.

Step 12 — Laptop 2: Configure the receiver

Run:

cd ~/host-stack

python3 - <<'PY'
import getpass
import json
import os
from pathlib import Path

path = Path("config.json")
config = json.loads(path.read_text())

config["sender_ip"] = "192.168.50.1"
config["receiver_ip"] = "192.168.50.2"
config["receiver_iface"] = os.environ["RECEIVER_IFACE"]
config["receiver_user"] = getpass.getuser()

path.write_text(json.dumps(config, indent=2) + "\n")
print(path.read_text())
PY

The receiver’s sender_iface may still say CHANGE_ME. Its server script does not use that field; the sender’s configuration will be completed next.

Enable SSH:

sudo systemctl enable --now ssh

Meaning: allow Laptop 1 to retrieve CPU counters from Laptop 2.

Step 13 — Laptop 2: Start the receiver server

Run:

cd ~/host-stack
bash receiver/start.sh

Leave this terminal running.

The server waits for Laptop 1 to send traffic. A quiet terminal is normal because its output goes into:

results/receiver-server.log

To inspect the log, open a second terminal on Laptop 2:

tail -f ~/host-stack/results/receiver-server.log

Laptop 2 is now ready to receive traffic. Return to Laptop 1.

Step 14 — Laptop 1: Complete the receiver details

On Laptop 1, run:

cd ~/host-stack

read -r -p "Enter Laptop 2 username: " RECEIVER_USER
read -r -p "Enter Laptop 2 Ethernet interface name: " RECEIVER_IFACE

export RECEIVER_USER RECEIVER_IFACE

Enter the values you recorded in Step 10.

Save them:

python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path("config.json")
config = json.loads(path.read_text())

config["receiver_user"] = os.environ["RECEIVER_USER"]
config["receiver_iface"] = os.environ["RECEIVER_IFACE"]

path.write_text(json.dumps(config, indent=2) + "\n")

if "CHANGE_ME" in json.dumps(config):
    raise SystemExit("Configuration is incomplete. Check config.json.")

print("Configuration completed:")
print(path.read_text())
PY

Now test the Ethernet connection:

ping -I 192.168.50.1 -c 4 192.168.50.2

Step 15 — Laptop 1: Set up automatic CPU collection

The experiment uses SSH to read the receiver’s CPU counters without repeatedly asking for its password.

Run:

RECEIVER=$(python3 -c 'import json; c=json.load(open("config.json")); print(c["receiver_user"]+"@"+c["receiver_ip"])')

printf 'Receiver login: %s\n' "$RECEIVER"

Create a dedicated SSH key if it does not already exist:

if [ -f ~/.ssh/host_stack_ed25519 ]; then
    echo "Using the existing project SSH key."
else
    ssh-keygen -t ed25519 -f ~/.ssh/host_stack_ed25519
fi

The command may ask you to choose a passphrase.

Copy the public key to Laptop 2:

ssh-copy-id -i ~/.ssh/host_stack_ed25519.pub "$RECEIVER"

Enter Laptop 2’s account password when requested.

On the first connection, verify the host fingerprint. Laptop 2 can display it using:

ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

Back on Laptop 1, run:

eval "$(ssh-agent -s)"
ssh-add ~/.ssh/host_stack_ed25519

Then test automatic CPU collection:

ssh -o BatchMode=yes "$RECEIVER" 'python3 ~/host-stack/common/snapshot.py'

You should see JSON containing CPU counters, without an account-password prompt.

Keep using this sender terminal for the experiments. Never share or submit your private SSH key.

If SSH or iperf is blocked by a firewall, use the scoped firewall instructions in README.md, section 8. Do not disable the whole firewall.

Step 16 — Laptop 1: Run one small sending test

Make sure receiver/start.sh is still running on Laptop 2.

On Laptop 1:

cd ~/host-stack

iperf3 -c 192.168.50.2 -B 192.168.50.1 -t 5
Part	Meaning
-c 192.168.50.2	Connect to Laptop 2
-B 192.168.50.1	Use Laptop 1’s Ethernet IP
-t 5	Send traffic for five seconds

You should see throughput results.

This only checks that sending works. It is not the complete experiment.

Step 17 — Laptop 1: Run the actual experiment

Before running:

Connect both laptops to power.
Close downloads and heavy applications.
Keep their power settings consistent.
Do not run packet capture during these main measurements.

Run:

cd ~/host-stack

python3 sender/run.py --label baseline

The script automatically:

Checks the sender’s network route and SSH connection.
Saves hardware and configuration information from both laptops.
Measures background CPU activity.
Runs the experiment conditions in randomized order.
Measures throughput and CPU consumption.
Repeats each condition three times.
Saves the raw measurements.

The conditions are:

Condition	Parallel TCP streams	Application write size
Baseline	1	128 KiB
More concurrent traffic	2	128 KiB
More concurrent traffic	4	128 KiB
More concurrent traffic	8	128 KiB
Small application writes	1	1 KiB
Medium application writes	1	16 KiB

Allow approximately 8–10 minutes, depending on setup overhead.

Application write size is not packet size. TCP and offloads determine how those bytes are segmented and processed.

Step 18 — Laptop 1: Generate the graphs

After the experiment finishes:

python3 analysis/plot.py

List the outputs:

ls -lh results/analysis

You will get:

Output	Purpose
all_runs.csv	Individual trial measurements
summary.csv	Means and sample standard deviations
PNG files	Throughput and CPU graphs

Open the output folder:

xdg-open results/analysis

The CPU graph compares sender and receiver whole-host busy CPU equivalents. For example, 0.5 means aggregate busy time equivalent to half one logical CPU during the measurement window.

It is not a direct measurement of one particular TCP or copying function.

Step 19 — Both laptops: Test offloads, if supported

This comparison relates more closely to the paper’s discussion of processing overhead.

First, on Laptop 1:

cd ~/host-stack

IFACE=$(python3 -c 'import json; print(json.load(open("config.json"))["sender_iface"])')

python3 common/offloads.py save "$IFACE" results/original-offloads.json
sudo python3 common/offloads.py disable "$IFACE" results/original-offloads.json

Then, in a second terminal on Laptop 2:

cd ~/host-stack

IFACE=$(python3 -c 'import json; print(json.load(open("config.json"))["receiver_iface"])')

python3 common/offloads.py save "$IFACE" results/original-offloads.json
sudo python3 common/offloads.py disable "$IFACE" results/original-offloads.json

If either laptop reports failure or unsupported settings, restore both hosts using the commands below and skip this comparison. Do not label a partially applied configuration as “offloads disabled.”

If both succeed, run on Laptop 1:

python3 sender/run.py --single --label offloads_disabled

Afterward, restore Laptop 1:

IFACE=$(python3 -c 'import json; print(json.load(open("config.json"))["sender_iface"])')

sudo python3 common/offloads.py restore "$IFACE" results/original-offloads.json

Restore Laptop 2:

IFACE=$(python3 -c 'import json; print(json.load(open("config.json"))["receiver_iface"])')

sudo python3 common/offloads.py restore "$IFACE" results/original-offloads.json

Then run on Laptop 1:

python3 sender/run.py --single --label defaults_restored
python3 analysis/plot.py

What you investigate: whether disabling offloads changes CPU consumption or throughput, and whether restoring them returns performance toward the original result.

Keep the saved original-settings files. The save command deliberately refuses to overwrite them.

Step 20 — Laptop 1: Add a network-delay extension

Do this after restoring offloads on both laptops.

Run:

cd ~/host-stack

bash sender/delay.sh 0
bash sender/delay.sh 5
bash sender/delay.sh 20

python3 analysis/plot.py

These compare 0, 5, and 20 milliseconds of added sender-egress delay.

The script removes its temporary queue configuration after each run.

If it reports that a queue configuration already exists, stop this extension rather than deleting that configuration. The README explains this case.

This is a host-based delay experiment; it does not reproduce all the paper’s congestion or hardware experiments.

Step 21 — Laptop 2: Capture packets separately

Keep the receiver server running. Open another terminal on Laptop 2:

cd ~/host-stack

IFACE=$(python3 -c 'import json; print(json.load(open("config.json"))["receiver_iface"])')

sudo tcpdump -i "$IFACE" -nn -s 128 -c 5000 \
  -w results/diagnostic.pcap \
  'host 192.168.50.1 and tcp port 5201'

Now run on Laptop 1:

iperf3 -c 192.168.50.2 -B 192.168.50.1 -t 10

If tcpdump is still waiting afterward, press Ctrl+C in its terminal.

Open diagnostic.pcap in Wireshark and use this display filter:

tcp.port == 5201

Look for:

Connection establishment: SYN, SYN-ACK, ACK.
Data packets and acknowledgments.
Advertised TCP windows.
Connection closure, if captured.

This capture is intentionally separate from the performance measurements because capturing packets adds work.

Step 22 — Write your report

Open:

cd ~/host-stack
xdg-open REPORT_TEMPLATE.md

If that does not open, use VS Code or:

nano REPORT_TEMPLATE.md

Your report should explain:

Report part	What to write
Objective	Measure host CPU cost and TCP performance
Setup	Both laptops, Linux/VM details, NICs, Ethernet speed, and configuration
Method	Conditions, duration, repetitions, and measurements
Results	Actual tables and graphs
Paper comparison	Which observations agree, differ, or remain inconclusive
Extensions	Write-size and delay experiments
Limitations	Slower link, virtualization, background activity, unsupported hardware features

Do not claim that throughput and total CPU usage prove data copying dominates. The package’s README, section 15, gives additional perf profiling instructions for investigating CPU functions.

Also, ordinary laptops cannot establish the paper’s specific 100 Gbps hardware findings merely by running these tests.

Step 23 — Finish

On Laptop 2, press Ctrl+C in the receiver-server terminal.

Make sure you restored any offload settings you changed. The README’s cleanup section explains how to remove the temporary IP addresses when you no longer need them.

Your submission will contain the code, both laptops’ configuration logs, actual measurements, CSV tables, graphs, packet analysis, and your completed report.

Start with Step 1 on Laptop 1 and follow the order. If a command fails, send its exact command and output before continuing past that step.

no bro i dont want to copy the folder i want to do it so give me this in step wise 

Understood, bro. You want to create the folders and files yourself by copying commands into the terminal. We’ll do exactly that.

Follow the steps in this order:

Create the sender files on Laptop 1.
Create the receiver files on Laptop 2.
Connect them and run the experiments.
Generate graphs and explain the results.

Whenever you see a block beginning with cat >, copy the entire block, including the final PY, JSON, or SH line. That command creates the file and writes its contents.

These instructions assume Ubuntu/Debian Linux on both laptops.

PART A — LAPTOP 1: CREATE THE SENDER

Step 1 — Open Ubuntu Terminal and install the tools

Run on Laptop 1:

sudo apt update

sudo apt install -y \
iperf3 \
sysstat \
ethtool \
openssh-client \
python3 \
python3-matplotlib \
tcpdump \
iproute2

If asked whether iperf3 should automatically run as a service, select No.

What we are doing: installing the traffic generator, CPU-monitoring tools, Python, graphing tools, and networking utilities.

Step 2 — Create your project folders

Run:

mkdir -p ~/host-stack/common
mkdir -p ~/host-stack/sender
mkdir -p ~/host-stack/analysis
mkdir -p ~/host-stack/results

cd ~/host-stack

What we are doing:

Folder	Purpose
common	CPU measurement and system-information code
sender	Experiment automation
analysis	Graph generation
results	Your actual measurements

You have now created the project structure yourself.

Step 3 — Identify the sender’s Ethernet interface

Connect the Ethernet cable and run:

ip -br link
ip -br addr
ip route
systemd-detect-virt

Find the interface connected to your experimental Ethernet link.

It might be enp3s0, enp0s1, or enx....

Do not choose lo, a Docker interface, or Wi-Fi. An interface name alone does not establish whether it represents a physical NIC or a VM’s virtual NIC.

Now run:

read -r -p "Enter Laptop 1 Ethernet interface name: " SENDER_IFACE

ip link show dev "$SENDER_IFACE"

sudo ethtool "$SENDER_IFACE"

When asked, type your actual interface name.

Check for:

Link detected: yes

Save the interface name:

printf '%s\n' "$SENDER_IFACE" > ~/host-stack/results/sender-interface.txt

What we are doing: identifying the interface that will carry your experimental traffic.

If Ubuntu is inside a VM, the VM must have appropriate access to the Ethernet connection. Record virtualization in your report; these instructions cannot make a NAT-only virtual NIC equivalent to native Ethernet.

Step 4 — Assign Laptop 1 its experimental IP address

We will use:

Laptop	Address
Sender	192.168.50.1
Receiver	192.168.50.2

Use these addresses only on a dedicated experimental connection, and only if 192.168.50.0/24 is not already used by another network shown in ip route. Otherwise, the addresses must be changed consistently throughout the instructions.

Run:

SENDER_IFACE=$(cat ~/host-stack/results/sender-interface.txt)

sudo ip link set dev "$SENDER_IFACE" up

sudo ip addr add 192.168.50.1/24 dev "$SENDER_IFACE"

Check:

ip -br addr show dev "$SENDER_IFACE"

You should see 192.168.50.1/24.

If adding the address says File exists, check whether that exact address is already configured.

What we are doing: giving the sender an address that the receiver can communicate with.

These addresses are temporary and may disappear after reboot.

Step 5 — Create the configuration file

Run:

cd ~/host-stack

python3 - <<'PY'
import json
from pathlib import Path

interface = Path("results/sender-interface.txt").read_text().strip()

config = {
    "sender_ip": "192.168.50.1",
    "receiver_ip": "192.168.50.2",
    "sender_iface": interface,
    "receiver_iface": "CHANGE_ME",
    "receiver_user": "CHANGE_ME",
    "port": 5201,
    "duration": 20,
    "repeats": 3
}

Path("config.json").write_text(json.dumps(config, indent=2) + "\n")
print(Path("config.json").read_text())
PY

What is inside this file:

Both IP addresses.
The sender interface.
Receiver details that we will fill later.
A 20-second measurement duration.
Three repetitions for each condition.

Do not run the experiment yet.

Step 6 — Create the CPU-measurement file

Copy this entire block:

cat > ~/host-stack/common/snapshot.py <<'PY'
#!/usr/bin/env python3

import json
import time
from pathlib import Path


def snapshot():
    cpus = {}

    for line in Path("/proc/stat").read_text().splitlines():
        fields = line.split()

        if fields and fields[0].startswith("cpu"):
            cpus[fields[0]] = list(map(int, fields[1:9]))

    return {
        "monotonic": time.monotonic(),
        "unix_time": time.time(),
        "cpus": cpus
    }


def usage(before, after):
    if before["cpus"].keys() != after["cpus"].keys():
        raise ValueError("CPU set changed during measurement")

    def fractions(key):
        delta = [
            end - start
            for start, end in zip(
                before["cpus"][key],
                after["cpus"][key]
            )
        ]

        if min(delta) < 0 or sum(delta) <= 0:
            raise ValueError("CPU counters reset or interval too short")

        total = sum(delta)

        busy = sum(delta[i] for i in (0, 1, 2, 5, 6)) / total
        kernel = (delta[2] + delta[5] + delta[6]) / total
        steal = delta[7] / total

        return busy, kernel, steal

    count = len(after["cpus"]) - 1
    busy, kernel, steal = fractions("cpu")

    return {
        "busy_cores": count * busy,
        "kernel_cores": count * kernel,
        "max_core_busy_pct": 100 * max(
            fractions(key)[0]
            for key in after["cpus"]
            if key != "cpu"
        ),
        "steal_pct": 100 * steal,
        "elapsed_s": after["monotonic"] - before["monotonic"]
    }


if __name__ == "__main__":
    print(json.dumps(snapshot()))
PY

Check it:

python3 ~/host-stack/common/snapshot.py

It should print CPU counters in JSON format.

What this file does: reads Linux’s cumulative CPU counters. The experiment takes readings before and after each test and calculates the CPU consumption between them.

These are whole-host CPU measurements, including background activity—not just the iperf process.

Step 7 — Create the system-information file

Copy:

cat > ~/host-stack/common/inventory.py <<'PY'
#!/usr/bin/env python3

import datetime
import subprocess
import sys
from pathlib import Path

interface = sys.argv[1]
output = Path(sys.argv[2])
output.parent.mkdir(parents=True, exist_ok=True)

commands = [
    ["uname", "-a"],
    ["lscpu"],
    ["systemd-detect-virt"],
    ["iperf3", "--version"],
    ["ip", "-br", "addr"],
    ["ip", "route"],
    ["ip", "-s", "link", "show", interface],
    ["ethtool", interface],
    ["ethtool", "-i", interface],
    ["ethtool", "-k", interface],
    ["ethtool", "-l", interface],
    ["tc", "-s", "qdisc", "show", "dev", interface],
    [
        "sysctl",
        "net.ipv4.tcp_congestion_control",
        "net.ipv4.tcp_rmem",
        "net.ipv4.tcp_wmem"
    ],
    ["cat", "/proc/interrupts"],
    ["cat", "/proc/softirqs"]
]

with output.open("w") as stream:
    stream.write(
        datetime.datetime.now(datetime.timezone.utc).isoformat() + "\n"
    )

    for command in commands:
        stream.write("\n$ " + " ".join(command) + "\n")

        try:
            result = subprocess.run(
                command,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15
            )

            stream.write(result.stdout)
            stream.write(f"\nexit={result.returncode}\n")

        except (OSError, subprocess.TimeoutExpired) as error:
            stream.write(str(error) + "\n")

print(output)
PY

What this file does: saves your CPU, Linux version, NIC, link speed, offload settings, and other configuration information.

This is necessary because your results depend on your hardware and configuration. Unsupported queries remain visible in the log.

Step 8 — Create the sender experiment program

Copy the entire block:

cat > ~/host-stack/sender/run.py <<'PY'
#!/usr/bin/env python3

import argparse
import datetime
import json
import random
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "common"))

from snapshot import snapshot, usage


def command(arguments, timeout=30):
    result = subprocess.run(
        arguments,
        text=True,
        capture_output=True,
        timeout=timeout
    )

    if result.returncode:
        raise RuntimeError(
            shlex.join(arguments) + "\n" +
            (result.stderr or result.stdout)
        )

    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--single", action="store_true")
    arguments = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", arguments.label):
        parser.error("Label must contain letters, numbers, _ or -")

    config = json.loads((ROOT / "config.json").read_text())

    if "CHANGE_ME" in json.dumps(config):
        parser.error("Complete config.json first")

    for key in ("duration", "repeats", "port"):
        if not isinstance(config[key], int) or config[key] <= 0:
            parser.error(key + " must be a positive integer")

    if config["duration"] < 10:
        parser.error("Use a duration of at least 10 seconds")

    route = json.loads(command([
        "ip", "-j", "route", "get",
        config["receiver_ip"],
        "from", config["sender_ip"]
    ]))

    if route[0].get("dev") != config["sender_iface"]:
        raise RuntimeError(
            "Traffic is not routed through the configured Ethernet interface"
        )

    ssh = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        config["receiver_user"] + "@" + config["receiver_ip"]
    ]

    def receiver_snapshot():
        return json.loads(command(
            ssh + ["python3 ~/host-stack/common/snapshot.py"]
        ))

    receiver_snapshot()

    timestamp = datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y%m%dT%H%M%S%fZ")

    output = ROOT / "results" / (
        timestamp + "_" + arguments.label
    )
    output.mkdir(parents=True)

    (output / "config.json").write_text(
        json.dumps(config, indent=2)
    )

    command([
        sys.executable,
        str(ROOT / "common/inventory.py"),
        config["sender_iface"],
        str(output / "sender-inventory.txt")
    ], timeout=120)

    remote_inventory = (
        "python3 ~/host-stack/common/inventory.py "
        + shlex.quote(config["receiver_iface"])
        + " /tmp/host-stack-inventory.txt"
        + " && cat /tmp/host-stack-inventory.txt"
    )

    (output / "receiver-inventory.txt").write_text(
        command(ssh + [remote_inventory], timeout=120)
    )

    print("Measuring idle CPU for 20 seconds...", flush=True)

    receiver_before = receiver_snapshot()
    sender_before = snapshot()

    time.sleep(20)

    sender_after = snapshot()
    receiver_after = receiver_snapshot()

    (output / "idle.json").write_text(json.dumps({
        "sender": usage(sender_before, sender_after),
        "receiver": usage(receiver_before, receiver_after)
    }, indent=2))

    if arguments.single:
        conditions = [(1, 131072)]
    else:
        conditions = [
            (1, 131072),
            (2, 131072),
            (4, 131072),
            (8, 131072),
            (1, 1024),
            (1, 16384)
        ]

    tests = [
        (streams, size, repeat)
        for streams, size in conditions
        for repeat in range(1, config["repeats"] + 1)
    ]

    random.Random(2026).shuffle(tests)

    (output / "order.json").write_text(json.dumps(tests))

    for index, (streams, size, repeat) in enumerate(tests, 1):
        print(
            f"{index}/{len(tests)}: streams={streams}, "
            f"write_bytes={size}, repeat={repeat}",
            flush=True
        )

        base = [
            "iperf3",
            "-c", config["receiver_ip"],
            "-B", config["sender_ip"],
            "-p", str(config["port"]),
            "-P", str(streams),
            "-l", str(size),
            "-J"
        ]

        warmup = json.loads(command(base + ["-t", "3"]))

        if "error" in warmup:
            raise RuntimeError(warmup["error"])

        receiver_before = receiver_snapshot()
        sender_before = snapshot()

        result = subprocess.run(
            base + [
                "-t", str(config["duration"]),
                "--get-server-output"
            ],
            text=True,
            capture_output=True,
            timeout=config["duration"] + 60
        )

        sender_after = snapshot()
        receiver_after = receiver_snapshot()

        name = f"p{streams}_b{size}_r{repeat}"

        (output / (name + ".iperf.json")).write_text(result.stdout)
        (output / (name + ".stderr.txt")).write_text(result.stderr)

        data = json.loads(result.stdout)

        if result.returncode or "error" in data:
            raise RuntimeError(data.get("error", result.stderr))

        sender_cpu = usage(sender_before, sender_after)
        receiver_cpu = usage(receiver_before, receiver_after)

        measurement = {
            "label": arguments.label,
            "streams": streams,
            "write_bytes": size,
            "repeat": repeat,
            "receiver_mbps":
                data["end"]["sum_received"]["bits_per_second"] / 1e6,
            "tcp_retransmits":
                data["end"]["sum_sent"].get("retransmits"),
            "sender_busy_cores": sender_cpu["busy_cores"],
            "receiver_busy_cores": receiver_cpu["busy_cores"],
            "sender_kernel_cores": sender_cpu["kernel_cores"],
            "receiver_kernel_cores": receiver_cpu["kernel_cores"],
            "sender_max_core_pct": sender_cpu["max_core_busy_pct"],
            "receiver_max_core_pct": receiver_cpu["max_core_busy_pct"],
            "sender_cpu_window_s": sender_cpu["elapsed_s"],
            "receiver_cpu_window_s": receiver_cpu["elapsed_s"],
            "sender_steal_pct": sender_cpu["steal_pct"],
            "receiver_steal_pct": receiver_cpu["steal_pct"],
            "snapshots": {
                "sender_before": sender_before,
                "sender_after": sender_after,
                "receiver_before": receiver_before,
                "receiver_after": receiver_after
            }
        }

        (output / (name + ".result.json")).write_text(
            json.dumps(measurement, indent=2)
        )

        time.sleep(2)

    print("Saved measurements:", output)


if __name__ == "__main__":
    try:
        main()
    except (
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
        subprocess.TimeoutExpired
    ) as error:
        sys.exit("Stopped: " + str(error))
PY

What this program does:

Checks that traffic uses your configured Ethernet interface.
Connects to the receiver using SSH.
Saves both laptops’ configurations.
Measures idle CPU activity.
Runs repeated TCP experiments.
Saves throughput, retransmissions, and CPU measurements.

There is a separate warm-up connection before each measured connection. The measured connection still includes its own startup; it is not a steady-state-only measurement.

Step 9 — Create the graph-generation program

Copy:

cat > ~/host-stack/analysis/plot.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
rows = []

for path in sorted((root / "results").glob("*/*.result.json")):
    row = json.loads(path.read_text())
    row.pop("snapshots", None)
    row["batch"] = path.parent.name
    rows.append(row)

if not rows:
    sys.exit("No measurements found. Run the experiments first.")

output = root / "results" / "analysis"
output.mkdir(exist_ok=True)

with (output / "all_runs.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

groups = defaultdict(list)

for row in rows:
    key = (
        row["batch"],
        row["label"],
        row["streams"],
        row["write_bytes"]
    )
    groups[key].append(row)

metrics = [
    "receiver_mbps",
    "sender_busy_cores",
    "receiver_busy_cores",
    "sender_kernel_cores",
    "receiver_kernel_cores",
    "tcp_retransmits"
]

summary = []

for (batch, label, streams, size), measurements in groups.items():
    row = {
        "batch": batch,
        "label": label,
        "streams": streams,
        "write_bytes": size,
        "n": len(measurements)
    }

    for metric in metrics:
        values = [
            item[metric]
            for item in measurements
            if item[metric] is not None
        ]

        row[metric + "_mean"] = (
            statistics.mean(values) if values else None
        )

        row[metric + "_sd"] = (
            statistics.stdev(values)
            if len(values) > 1
            else (0 if values else None)
        )

    summary.append(row)

with (output / "summary.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
    writer.writeheader()
    writer.writerows(summary)

for batch in sorted({row["batch"] for row in summary}):
    selected = sorted(
        [row for row in summary if row["batch"] == batch],
        key=lambda row: (row["streams"], row["write_bytes"])
    )

    labels = [
        f"P={row['streams']}\nwrite={row['write_bytes']//1024} KiB"
        for row in selected
    ]

    x = list(range(len(selected)))

    figure, axes = plt.subplots(
        1, 2,
        figsize=(max(10, len(selected) * 1.65), 4.5)
    )

    axes[0].bar(
        x,
        [row["receiver_mbps_mean"] for row in selected],
        yerr=[row["receiver_mbps_sd"] for row in selected],
        capsize=4,
        color="#197a9b"
    )
    axes[0].set_ylabel("Receiver TCP goodput (Mbps)")

    for offset, endpoint, color in [
        (-0.18, "sender", "#197a9b"),
        (0.18, "receiver", "#e38b39")
    ]:
        axes[1].bar(
            [value + offset for value in x],
            [row[endpoint + "_busy_cores_mean"] for row in selected],
            width=0.36,
            yerr=[
                row[endpoint + "_busy_cores_sd"]
                for row in selected
            ],
            capsize=3,
            label=endpoint,
            color=color
        )

    axes[1].set_ylabel("Whole-host busy CPU equivalents")
    axes[1].legend()

    for axis in axes:
        axis.set_xticks(x)
        axis.set_xticklabels(labels)
        axis.set_ylim(bottom=0)
        axis.grid(axis="y", alpha=0.2)

    figure.suptitle(batch + " | mean ± sample SD")
    figure.tight_layout()
    figure.savefig(output / (batch + ".png"), dpi=180)
    plt.close(figure)

print("CSV files and graphs:", output)
PY

What this file does: combines successful trials, calculates averages and variability, and draws throughput and CPU graphs.

Step 10 — Check the sender files

Run:

cd ~/host-stack

python3 -m py_compile \
common/snapshot.py \
common/inventory.py \
sender/run.py \
analysis/plot.py

No output means the Python syntax check passed.

The sender files are now ready. Do not start the experiment yet. Move to Laptop 2.

PART B — LAPTOP 2: CREATE THE RECEIVER

Step 11 — Install receiver tools and create folders

Run on Laptop 2:

sudo apt update

sudo apt install -y \
iperf3 \
sysstat \
ethtool \
openssh-server \
python3 \
tcpdump \
iproute2

Choose No if asked to run iperf3 automatically as a service.

Create the folders:

mkdir -p ~/host-stack/common
mkdir -p ~/host-stack/receiver
mkdir -p ~/host-stack/results

cd ~/host-stack

Step 12 — Identify the receiver interface and username

Run:

ip -br link
ip -br addr
ip route
whoami

Record the username printed by whoami.

Enter the receiver’s Ethernet interface:

read -r -p "Enter Laptop 2 Ethernet interface name: " RECEIVER_IFACE

ip link show dev "$RECEIVER_IFACE"

sudo ethtool "$RECEIVER_IFACE"

Save its name:

printf '%s\n' "$RECEIVER_IFACE" > ~/host-stack/results/receiver-interface.txt

Again, check that the experimental subnet is not already used by an unrelated network.

Step 13 — Assign the receiver IP

Run:

RECEIVER_IFACE=$(cat ~/host-stack/results/receiver-interface.txt)

sudo ip link set dev "$RECEIVER_IFACE" up

sudo ip addr add 192.168.50.2/24 dev "$RECEIVER_IFACE"

Check:

ip -br addr show dev "$RECEIVER_IFACE"

Test communication:

ping -I 192.168.50.2 -c 4 192.168.50.1

You should receive replies from Laptop 1.

If this fails, resolve the Ethernet connection before proceeding.

Step 14 — Create the receiver’s CPU and inventory files

On Laptop 2, paste the complete code block from Step 6.

That creates:

~/host-stack/common/snapshot.py

Then paste the complete code block from Step 7.

That creates:

~/host-stack/common/inventory.py

You are creating these files directly on Laptop 2, using the same code. You are not transferring a folder.

Check:

python3 ~/host-stack/common/snapshot.py

It should print CPU counters.

Why these files are needed on the receiver: Laptop 1 will ask Laptop 2 to execute them and return its measurements.

Step 15 — Create the receiver server file

Copy:

cat > ~/host-stack/receiver/start.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/host-stack"

mkdir -p results

exec iperf3 \
    -s \
    -B 192.168.50.2 \
    -p 5201 \
    --forceflush \
    --logfile results/receiver-server.log
SH

Meaning:

Option	Meaning
-s	Run as a server
-B 192.168.50.2	Listen on the receiver’s Ethernet address
-p 5201	Use TCP port 5201
--logfile	Save server output
--forceflush	Make log output available promptly

Step 16 — Enable SSH and start the receiver

Run:

sudo systemctl enable --now ssh

Then:

cd ~/host-stack
bash receiver/start.sh

Leave this terminal running.

A quiet terminal is expected because output is saved to the log.

You can open another receiver terminal and inspect the log:

tail -f ~/host-stack/results/receiver-server.log

If the server reports that port 5201 is already in use, inspect:

ss -ltnp 'sport = :5201'

Stop only an earlier experiment server that you own.

The receiver is ready. Return to Laptop 1.

PART C — LAPTOP 1: CONNECT AND RUN

Step 17 — Complete the sender configuration

On Laptop 1:

cd ~/host-stack

read -r -p "Enter Laptop 2 username: " RECEIVER_USER
read -r -p "Enter Laptop 2 Ethernet interface name: " RECEIVER_IFACE

export RECEIVER_USER RECEIVER_IFACE

Enter the actual receiver values from Step 12.

Save them:

python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path("config.json")
config = json.loads(path.read_text())

config["receiver_user"] = os.environ["RECEIVER_USER"]
config["receiver_iface"] = os.environ["RECEIVER_IFACE"]

path.write_text(json.dumps(config, indent=2) + "\n")

if "CHANGE_ME" in json.dumps(config):
    raise SystemExit("Configuration is incomplete.")

print(path.read_text())
PY

Check Ethernet connectivity:

ping -I 192.168.50.1 -c 4 192.168.50.2

Step 18 — Set up automatic SSH access

On Laptop 1:

cd ~/host-stack

RECEIVER=$(python3 -c 'import json; c=json.load(open("config.json")); print(c["receiver_user"]+"@"+c["receiver_ip"])')

printf 'Receiver: %s\n' "$RECEIVER"

Create a key if it does not already exist:

if [ -f ~/.ssh/host_stack_ed25519 ]; then
    echo "Using the existing experiment SSH key."
else
    ssh-keygen -t ed25519 -f ~/.ssh/host_stack_ed25519
fi

It may ask you to choose a passphrase.

Install the public key on Laptop 2:

ssh-copy-id -i ~/.ssh/host_stack_ed25519.pub "$RECEIVER"

Enter Laptop 2’s account password when requested.

On the first connection, verify the fingerprint against this command on Laptop 2:

ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

Back on Laptop 1:

eval "$(ssh-agent -s)"

ssh-add ~/.ssh/host_stack_ed25519

Test:

ssh -o BatchMode=yes "$RECEIVER" \
'python3 ~/host-stack/common/snapshot.py'

This should print the receiver’s CPU counters without asking for its account password.

What we are doing: allowing the sender program to retrieve receiver measurements automatically.

Keep using this sender terminal. Do not submit your private SSH key with the project.

If connections are blocked, inspect the receiver firewall:

sudo ufw status

Only if UFW is active, run on Laptop 2:

RECEIVER_IFACE=$(cat ~/host-stack/results/receiver-interface.txt)

sudo ufw allow in on "$RECEIVER_IFACE" \
from 192.168.50.1 to any port 22 proto tcp

sudo ufw allow in on "$RECEIVER_IFACE" \
from 192.168.50.1 to any port 5201 proto tcp

These allow the sender to reach SSH and iperf on the experimental interface.

Step 19 — Run a five-second connectivity test

On Laptop 1:

iperf3 \
-c 192.168.50.2 \
-B 192.168.50.1 \
-t 5

You should see throughput results.

What we are doing: checking that the sender can send TCP data to the receiver.

This is only a connectivity test. Your actual experiment comes next.

Step 20 — Run the main measurements

Before starting, plug both laptops into power, close heavy applications, and keep power settings consistent.

Do not run tcpdump during these main measurements.

On Laptop 1:

cd ~/host-stack

python3 sender/run.py --label baseline

The experiment runs these conditions:

Condition	TCP streams	Application write size
Baseline	1	128 KiB
Parallel-flow test	2	128 KiB
Parallel-flow test	4	128 KiB
Parallel-flow test	8	128 KiB
Write-size extension	1	1 KiB
Write-size extension	1	16 KiB

Each condition runs three times.

Expect roughly 8–10 minutes, depending on overhead.

What you are investigating:

Whether more concurrent streams change throughput.
Whether they change CPU consumption.
Whether smaller application writes change performance.

Application write size is not Ethernet packet size. Also, this parallel-stream sweep does not reproduce the paper’s controlled CPU-to-CPU incast/outcast mappings.

Step 21 — Generate the results tables and graphs

On Laptop 1:

cd ~/host-stack

python3 analysis/plot.py

List the outputs:

ls -lh results/analysis

Open the folder:

xdg-open results/analysis

You will have:

File	Contents
all_runs.csv	Every successful measurement
summary.csv	Averages, standard deviations, and sample counts
PNG graphs	Throughput and sender/receiver CPU comparisons

How to understand CPU equivalents: a value of 0.5 means aggregate busy time equivalent to half one logical CPU during the measurement window.

These CPU windows include some setup/teardown and SSH overhead. Check idle.json for background activity; do not treat small changes near background noise as strong conclusions.

PART D — ADD A PAPER-RELATED OFFLOAD COMPARISON

Step 22 — Create the offload-control file on BOTH laptops

Paste this block separately into the terminal on each laptop:

cat > ~/host-stack/common/offloads.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

features = {
    "tso": "tcp-segmentation-offload",
    "gso": "generic-segmentation-offload",
    "gro": "generic-receive-offload",
    "lro": "large-receive-offload"
}


def read(interface):
    text = subprocess.check_output(
        ["ethtool", "-k", interface],
        text=True
    )

    states = {}

    for short, long_name in features.items():
        match = re.search(
            r"^" + re.escape(long_name) + r": (on|off)(.*)$",
            text,
            re.MULTILINE
        )

        if match:
            states[short] = {
                "value": match[1],
                "fixed": "[fixed]" in match[2]
            }

    return states


parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["save", "disable", "restore"])
parser.add_argument("interface")
parser.add_argument("state_file")
args = parser.parse_args()

path = Path(args.state_file)

if args.action == "save":
    with path.open("x") as stream:
        json.dump({
            "iface": args.interface,
            "states": read(args.interface)
        }, stream, indent=2)

    print("Saved original settings:", path)
    sys.exit(0)

saved = json.loads(path.read_text())

if saved["iface"] != args.interface:
    sys.exit("Saved interface differs.")

failures = []

for feature, state in saved["states"].items():
    desired = "off" if args.action == "disable" else state["value"]

    if state["fixed"]:
        print(feature, "fixed:", state["value"])

        if state["value"] != desired:
            failures.append(feature)

        continue

    result = subprocess.run(
        ["ethtool", "-K", args.interface, feature, desired],
        text=True,
        capture_output=True
    )

    if result.returncode:
        print(result.stderr)
        failures.append(feature)

actual = read(args.interface)

for feature, state in saved["states"].items():
    expected = "off" if args.action == "disable" else state["value"]

    if actual.get(feature, {}).get("value") != expected:
        failures.append(feature)

print(json.dumps(actual, indent=2))

if failures:
    sys.exit(
        "Not fully applied: "
        + ", ".join(sorted(set(failures)))
        + ". Restore the saved settings."
    )
PY

What this file does: saves the original selected offload settings, disables changeable settings, and restores them afterward.

It checks actual states rather than assuming a change succeeded.

Step 23 — Save and disable offloads

On Laptop 1:

cd ~/host-stack

IFACE=$(cat results/sender-interface.txt)

python3 common/offloads.py save \
"$IFACE" results/original-offloads.json

sudo python3 common/offloads.py disable \
"$IFACE" results/original-offloads.json

On Laptop 2, in a second terminal:

cd ~/host-stack

IFACE=$(cat results/receiver-interface.txt)

python3 common/offloads.py save \
"$IFACE" results/original-offloads.json

sudo python3 common/offloads.py disable \
"$IFACE" results/original-offloads.json

If either laptop reports that settings were not fully applied, restore both laptops using Step 25 and mark this experiment unsupported.

Do not overwrite the original-settings file if you repeat the procedure.

Step 24 — Run the offload comparison

If disabling succeeded on both laptops, run on Laptop 1:

cd ~/host-stack

python3 sender/run.py --single --label offloads_disabled

This repeats the one-stream, 128 KiB-write condition three times.

What you are investigating: how changing offloads affects CPU consumption and throughput.

Step 25 — Restore both laptops

On Laptop 1:

cd ~/host-stack

IFACE=$(cat results/sender-interface.txt)

sudo python3 common/offloads.py restore \
"$IFACE" results/original-offloads.json

On Laptop 2:

cd ~/host-stack

IFACE=$(cat results/receiver-interface.txt)

sudo python3 common/offloads.py restore \
"$IFACE" results/original-offloads.json

Then, on Laptop 1:

python3 sender/run.py --single --label defaults_restored

python3 analysis/plot.py

Compare the one-stream, 128 KiB condition across the three batches:

Baseline.
Offloads disabled.
Defaults restored.

If throughput stays similar but CPU consumption rises when offloads are disabled, that may show an efficiency benefit hidden by the link-speed limit. Decide from your actual measurements and variability.

PART E — PACKET ANALYSIS AND REPORT

Step 26 — Capture packets on Laptop 2

Leave the receiver server running.

In another terminal on Laptop 2:

cd ~/host-stack

IFACE=$(cat results/receiver-interface.txt)

sudo tcpdump \
-i "$IFACE" \
-nn \
-s 128 \
-c 5000 \
-w results/diagnostic.pcap \
'host 192.168.50.1 and tcp port 5201'

Now on Laptop 1:

iperf3 -c 192.168.50.2 -B 192.168.50.1 -t 10

If tcpdump remains waiting after the test, press Ctrl+C in the tcpdump terminal.

Open diagnostic.pcap in Wireshark and use:

tcp.port == 5201

Identify connection establishment, data, acknowledgments, and TCP window information.

The capture contains packet headers and limited payload. Host offloads can cause captures to show aggregated packets or apparent checksum errors; these are not automatically evidence of bad packets on the wire.

Step 27 — Create your report outline on Laptop 1

Run:

cat > ~/host-stack/report.md <<'MD'
# Understanding Host Network Stack Overheads

## 1. Objective
Explain the project goal.

## 2. Understanding the network stack
Explain the sender and receiver data paths.
Discuss socket calls, copying, TCP/IP, drivers, NICs, and offloads.

## 3. Experimental setup
Record both laptops' CPU, OS, kernel, NIC, link speed, MTU,
iperf3 version, power settings, and virtualization status.

## 4. Method
Describe the conditions, duration, repetitions, warm-up,
randomized order, CPU measurement, and throughput measurement.

## 5. Results
Insert actual summary tables and graphs.
Report averages, sample standard deviations, and sample counts.

## 6. Comparison with the paper
Compare the offload observations and CPU/throughput behavior.
State which trends agree, differ, or remain inconclusive.

## 7. Extended evaluation
Discuss the application write-size and parallel-stream experiments.
Do not describe application write size as Ethernet packet size.
Do not describe parallel streams as controlled incast/outcast.

## 8. Packet analysis
Explain the captured TCP handshake, data, ACKs, and windows.
Discuss capture and offload limitations.

## 9. Limitations
Discuss link speed, USB/VM overhead, background activity,
measurement-window differences, and unsupported experiments.
Whole-host CPU usage does not identify the dominant kernel function.

## 10. Conclusion
State only conclusions supported by the measurements.
MD

Edit it:

nano ~/host-stack/report.md

Your assignment is not finished just because the scripts run. The report must explain what happened and relate it to the paper.

The paper’s 100 Gbps hardware-specific findings cannot be fully reproduced on ordinary laptops. Present this as a scaled reproduction of selected experiments with extensions. Claims that a particular function—such as receiver data copying—dominates require additional CPU profiling, not merely these total CPU measurements.

Step 28 — Stop the receiver after finishing

On Laptop 2, press Ctrl+C in the terminal running receiver/start.sh.

Keep:

Your source files.
Both laptops’ inventory information.
Raw measurement files.
CSV tables and graphs.
Diagnostic packet capture.
Completed report.

Start at Step 1 on Laptop 1. Each cat > ... block creates the named file directly, so there is no ZIP download or project-folder transfer.

Step 3 — Identify the sender’s Ethernet interface Connect the Ethernet cable and run: Bash Find the interface connected to your experimental Ethernet link. It might be enp3s0, enp0s1, or enx.... Do not choose lo, a Docker interface, or Wi-Fi. An interface name alone does not establish whether it represents a physical NIC or a VM’s virtual NIC.

 guru@ubuntu:~/host-stack$ ip -br link
ip -br addr
ip route
systemd-detect-virt
lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP> 
enp0s1           UP             3a:7e:3b:e4:7e:15 <BROADCAST,MULTICAST,UP,LOWER_UP> 
docker0          DOWN           8e:4f:94:e2:be:ca <NO-CARRIER,BROADCAST,MULTICAST,UP> 
br-5771f8a78dd3  DOWN           fa:86:7f:c1:6d:19 <NO-CARRIER,BROADCAST,MULTICAST,UP> 
lo               UNKNOWN        127.0.0.1/8 ::1/128 
enp0s1           UP             192.168.64.2/24 fdab:de7c:b940:3272:387e:3bff:fee4:7e15/64 fe80::387e:3bff:fee4:7e15/64 
docker0          DOWN           172.17.0.1/16 
br-5771f8a78dd3  DOWN           172.18.0.1/16 
default via 192.168.64.1 dev enp0s1 proto dhcp src 192.168.64.2 metric 100 
default via 192.168.64.1 dev enp0s1 proto dhcp src 192.168.64.2 metric 1024 
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown 
172.18.0.0/16 dev br-5771f8a78dd3 proto kernel scope link src 172.18.0.1 linkdown 
192.168.64.0/24 dev enp0s1 proto kernel scope link src 192.168.64.2 
192.168.64.0/24 dev enp0s1 proto kernel scope link src 192.168.64.2 metric 100 
192.168.64.1 dev enp0s1 proto dhcp scope link src 192.168.64.2 metric 1024 
qemu
guru@ubuntu:~/host-stack$ 

Bro, your output confirms that Ubuntu is running inside a QEMU virtual machine. We need to check how that VM connects to the physical Ethernet cable before continuing.

Your output	Meaning
qemu	Ubuntu is inside a virtual machine
enp0s1	Your active network interface inside Ubuntu
192.168.64.2	Its current IPv4 address
Gateway 192.168.64.1	Ubuntu currently routes external traffic through this address
Docker interfaces	These are not the experiment interfaces

We cannot yet confirm that enp0s1 connects to the Ethernet cable between your two laptops. Its UP status only shows that the interface is enabled; it does not establish the physical path.

1. Stay on Laptop 1 and run these read-only commands:

sudo ethtool -i enp0s1
sudo ethtool enp0s1

These show the interface’s driver and available link information.

2. Do not run Step 4’s IP-address commands yet.

Adding 192.168.50.1 would not, by itself, connect the VM to the physical Ethernet network.

3. Send the command output and tell me these three things:

Which application runs Ubuntu on your Mac—UTM, VMware Fusion, or something else?
Is the Ethernet cable physically connected between the two laptops, directly or through a switch?
Is Laptop 2 running native Linux or another virtual machine?

Then I can give you the correct next connection step. Your project files can stay as they are; you do not need to recreate them.

Wednesday 11:58 AM
3452296.3472888(8).pdf
PDF
this the github link of this also: 
Terabit-Ethernet/Understanding-network-stack-overheads-SIGCOMM-2021 				

Description – Gather understanding of Network stack. Analyze and reproduce the results published in the paper and extend the evaluation with various other scenarios. Tools – Wireshark/tcpdump (packet analysis), Python/Java (traffic generation and automation), Linux networking utilities. Expected Outcomes – Validation of published results, along with extended evaluation that highlights the impact of different network conditions and configurations on performance. Reference – https://doi.org/10.1145/3452296.3472888
as you know this is the paper that we have from our prof we have to do the project which have submission tomorrow and i dont know a single things from this so please teach each single things and do the project is step wise so i be able to do the project before the deadline and i be able to counter the question in presentation of this project so please do it

Yes. I went through the paper you uploaded, the authors’ GitHub repository, and the official iperf3 documentation. I also made you a ready-to-run project folder so you do not have to build everything from scratch.

Download this first: host_stack_project.zip

It contains the sender scripts, receiver scripts, automated experiments, graph-generation code, report template, and presentation/viva notes.

The important point is this: do not try to blindly reproduce every number in the paper by tomorrow. The original experiment used two 100-Gbps servers, a Mellanox ConnectX-5 Ex NIC, four-socket Intel Xeon CPUs, NUMA, DDIO, and a specially patched Linux 5.4.43 kernel. The official repository is designed around that setup. Your project can still be done properly by reproducing the main trends that your hardware supports, then extending them with loss, delay, flow count, zero-copy, congestion-control, and packet analysis. The paper itself explicitly warns that different hardware/network-stack combinations can produce different numerical results.

1. First understand exactly what your professor gave you

The paper is:

“Understanding Host Network Stack Overheads” by Qizhe Cai, Shubham Chaudhary, Midhul Vuppalapati, Jaehyun Hwang, and Rachit Agarwal, SIGCOMM 2021.

Your professor's project statement essentially asks you to do three things:

Understand the Linux network stack.
Reproduce some observations from the paper.
Extend the evaluation using additional conditions/scenarios.

So you are not developing a new network protocol.

You are doing an experimental performance study.

Your project question is basically:

When data travels through a Linux computer, where is CPU time being spent, and how do network conditions and Linux/NIC optimizations affect throughput and CPU efficiency?

2. What is a “host network stack”?

Suppose Laptop A sends some data to Laptop B.

It doesn't go:

Application → Ethernet cable

There are many layers in between.

Very simplified:

Application
     ↓
Socket API
     ↓
TCP
     ↓
IP
     ↓
Linux network subsystem
     ↓
NIC driver
     ↓
NIC hardware
     ↓
Ethernet

And the reverse happens at the receiver.

The paper's Figure 1 on page 3 shows exactly this sender/receiver pipeline.

3. Sender side: understand this for your viva

Imagine your program executes:

send(socket, buffer, size, 0);

or

write(socket, buffer, size);

The sequence is roughly:

Application memory
       ↓
write()/send()
       ↓
Kernel socket
       ↓
skb created
       ↓
Data copied user → kernel
       ↓
TCP processing
       ↓
IP processing
       ↓
GSO / TSO
       ↓
NIC driver TX queue
       ↓
DMA
       ↓
NIC
       ↓
Network

The paper explains that when an application calls write(), Linux creates socket buffers (skbs), copies the application's data into kernel buffers, performs TCP/IP processing, and eventually places data into the NIC transmission queues.

What is skb?

skb means:

socket buffer

More specifically Linux uses:

struct sk_buff

Think of it as the kernel's packet bookkeeping object.

It contains things such as:

packet metadata
header information
memory references
protocol state information

The kernel passes skbs through different layers.

4. Receiver side

Receiver processing is even more important for this paper.

Roughly:

Ethernet
   ↓
NIC receives frame
   ↓
DMA packet into memory
   ↓
Interrupt / IRQ
   ↓
NAPI polling
   ↓
NIC driver
   ↓
GRO
   ↓
TCP/IP
   ↓
Socket receive queue
   ↓
recv()/read()
   ↓
Kernel → userspace data copy
   ↓
Application

The NIC first DMAs received frames into memory. The driver then processes received data, GRO may combine packets, TCP/IP processing occurs, and eventually the application copies the payload from the socket receive queue into its userspace buffer.

This final:

kernel memory → application memory

copy becomes extremely important in this paper.

5. What is DMA?

DMA = Direct Memory Access.

Without DMA, conceptually the CPU would have to manually move NIC data byte by byte.

With DMA:

NIC ──────────→ RAM / cache
       DMA

The CPU configures the transfer, but the device performs the actual memory transfer.

This saves CPU work.

6. IRQ and NAPI

When packets arrive, the NIC must tell the CPU:

I have received packets.

Traditionally it can generate an:

IRQ = Interrupt Request

But imagine receiving millions of packets per second.

Generating millions of interrupts would itself consume huge CPU resources.

Linux therefore uses:

NAPI — New API

Instead of continuously interrupting the CPU, Linux can switch to polling/batching packets during heavy traffic.

This reduces interrupt overhead.

7. TSO, GSO and GRO — extremely important for your presentation

You will almost certainly get asked about these.

TSO

TCP Segmentation Offload

Suppose TCP has:

64 KB data

Ethernet MTU is normally around:

1500 bytes

Without offload the CPU has to create many small packets.

With TSO:

Linux:
64 KB large segment
        ↓
       NIC
        ↓
NIC splits it into ~1500-byte packets

So CPU work decreases.

GSO

Generic Segmentation Offload

Similar idea, but implemented as part of the Linux networking path.

Linux keeps larger packet representations for longer instead of processing every MTU-sized packet independently.

GRO

Generic Receive Offload

Receiver side.

Instead of:

packet
packet
packet
packet
packet

going individually through upper network layers, GRO tries to combine packets belonging to the same flow:

packet + packet + packet
          ↓
      larger skb

Then TCP/IP handles fewer objects.

This reduces per-packet overhead.

The paper found TSO/GRO and jumbo frames substantially reduce processing overhead.

8. Jumbo frames

Normal Ethernet MTU:

1500 bytes

Jumbo frame:

~9000 bytes

Instead of transmitting many 1500-byte frames, fewer larger frames are needed.

That means fewer:

headers
skb objects
driver operations
TCP/IP operations
interrupt-related operations

per GB of transferred data.

But both endpoints and the network path must support MTU 9000.

Don't force this experiment if your adapter doesn't support it.

9. RSS, RPS, RFS and aRFS

These determine which CPU core handles received network traffic.

The paper's Table 2 defines them as follows.

RSS

Receive Side Scaling.

NIC hardware hashes flows and distributes packets across receive queues/CPU cores.

RPS

Receive Packet Steering.

Software equivalent.

RFS

Receive Flow Steering.

Attempts to process packets on the CPU where the receiving application is running.

aRFS

Accelerated RFS.

Hardware-assisted form of RFS.

Why?

Cache locality.

If application and network processing occur on the same CPU/NUMA locality, fewer expensive remote-memory/cache accesses may occur.

10. NUMA

NUMA means:

Non-Uniform Memory Access.

Large servers can have:

CPU socket 0 ─ local RAM
CPU socket 1 ─ local RAM
CPU socket 2 ─ local RAM
CPU socket 3 ─ local RAM

A CPU accessing local memory is faster than accessing another NUMA node's memory.

The paper found that running a long-flow application on a NUMA node remote from the NIC caused roughly a 20% throughput-per-core reduction in its system.

Your laptop probably doesn't have this kind of four-socket NUMA configuration.

Therefore:

you do not need to pretend to reproduce this experiment.

Put it under:

Unsupported due to hardware differences.

That is scientifically correct.

11. What exactly did the paper measure?

The original setup had:

2 servers
        │
        │ 100 Gbps direct connection
        │
Intel Xeon Gold 6128
4 sockets
6 cores/socket
256 GB RAM
Mellanox ConnectX-5 Ex 100-Gbps NIC
Ubuntu 16.04
Linux 5.4.43

They normally enabled DDIO and disabled hyperthreading and IOMMU.

Long flows were generated using iPerf, while short RPC-style flows were generated using netperf. They measured throughput, CPU utilization, throughput-per-core, and detailed CPU profiles.

12. Their most important metric: throughput-per-core

Suppose:

Throughput = 40 Gbps
CPU consumed = 2 CPU cores

Then:

Throughput per core
= 40 / 2
= 20 Gbps/core

Why is this better than throughput alone?

Suppose:

System A:
100 Gbps
8 CPU cores

System B:
100 Gbps
3 CPU cores

Both have same throughput.

But B is much more CPU-efficient.

That is exactly what this paper cares about.

The paper defines throughput-per-core as total throughput divided by CPU utilization at the bottleneck.

13. The five traffic patterns

This diagram is another very likely viva question.

The paper uses five patterns.

Single
S1 ─────→ R1

One flow.

One-to-one
S1 ─────→ R1
S2 ─────→ R2
S3 ─────→ R3
S4 ─────→ R4
Incast
S1 ────┐
S2 ────┤
S3 ────┼──→ R1
S4 ────┘

Many senders → one receiver.

Outcast
            → R1
           /
S1 ───────→ R2
           \
            → R3

One sender → many receivers.

All-to-all

Every sender core communicates with every receiver core.

14. The paper's most important result

This is the main result you should memorize:

At very high network bandwidth, packet-processing overhead is no longer always the primary problem. Data copy becomes a dominant CPU bottleneck, especially at the receiver.

For a single long flow with common optimizations, the paper measured about:

~42 Gbps/core

and found receiver-side data copy to be a dominant CPU consumer.

Figure 3 further reports that data copy occupied roughly 49% of receiver CPU utilization once GRO and jumbo frames were enabled.

Don't say:

Linux maximum speed is 42 Gbps.

That's wrong.

Say:

On the authors' specific 100-Gbps testbed, they measured approximately 42 Gbps per core under their standard optimized single-flow configuration.

15. Their other important results

You don't need to memorize every graph value, but know these.

Cache problem

Even one flow produced a high L3 cache-miss rate, around 49% in their experiment. Higher TCP receive-buffer and NIC ring sizes could increase cache misses and reduce throughput.

Incast

More flows sharing the receiver increased L3-cache contention. The paper reports cache miss rate rising from about:

48% → 78%

going from one to eight flows.

Outcast

The sender processing pipeline reached roughly:

89 Gbps/core

in their outcast experiment, showing sender-side processing was substantially more CPU-efficient than receiver-side processing.

All-to-all

Throughput-per-core dropped roughly:

67%

from 1×1 to 24×24 flows because contention increased and GRO became less effective.

Packet loss

Increasing packet-loss rate caused:

duplicate ACKs
retransmissions
more TCP processing
more NIC/device processing

The paper observed about a 24% decrease in throughput-per-core when loss was raised to 0.015 (1.5%).

Short flows

For very short flows, TCP/IP and scheduling overhead become relatively important because there is less opportunity to batch packets. As flow size increases, data-copy overhead becomes dominant again.

Mixing long and short flows

The paper found about a:

43% throughput-per-core drop

when increasing the number of short flows colocated with a long flow from 0 to 16.

DCA/DDIO

Disabling DCA caused about:

19% reduction

in their single-flow optimized setup.

IOMMU

Enabling IOMMU reduced throughput-per-core by about:

26%

because memory-management overhead increased.

Congestion control

CUBIC, BBR and DCTCP showed relatively little difference in throughput-per-core in their single-flow experiment because the receiver remained the main bottleneck.

16. Why you should NOT blindly execute the official GitHub scripts tonight

The repository is real and useful:

Official SIGCOMM 2021 artifact repository

It contains:

kernel_patch/
scripts/
    sender/
    receiver/
    parse/

network_setup.py
run_experiment_sender.py
run_experiment_receiver.py
constants.py
process_output.py
symbol_mapping.tsv

The authors explain that the kernel patch changes GSO behavior and adds instrumentation for packet loss, skb latency, and skb-size histograms.

But their scripts also assume things such as:

Linux 5.4.43 patched kernel
Mellanox NIC
specific flow steering
100-Gbps NIC
specific CPU ↔ RX queue mappings
specific experiment addresses
NUMA topology

The artifact's original hardware assumptions are explicitly documented.

Therefore your presentation should say:

“We studied the official artifact but adapted the reproduction methodology for the capabilities of our available hardware.”

That is much better than pretending you ran experiments that your hardware cannot support.

17. Your actual project — this is what you should do today

I suggest five reproduction experiments + three extensions.

Reproduction
E1  Single long TCP flow
E2  Multiple simultaneous TCP flows
E3  TSO/GSO/GRO enabled vs disabled
E4  Packet-loss experiment
E5  Congestion-control comparison
Extensions
X1  Added latency / BDP experiment
X2  iperf3 zero-copy experiment
X3  Forward vs reverse direction

This is enough for a solid project because it includes:

paper understanding
reproduction
network-stack configuration
packet analysis
automation
extensions
graphs
limitations
18. Step 1 — put my folder on both Linux machines

Download:

host_stack_project.zip

Unzip it.

Then:

cd host_stack_project
chmod +x common/*.sh receiver/*.sh sender/*.sh
19. Step 2 — install everything on BOTH laptops

Run:

bash common/setup.sh

It installs:

iperf3
sysstat
ethtool
tcpdump
jq
iproute2
Python
matplotlib
git
SSH

iperf3 is a standard client/server network-throughput measurement tool. Its official documentation supports TCP tests, JSON output with -J, CPU affinity, congestion-control selection with -C, and zero-copy sending with -Z.

20. Step 3 — identify the Ethernet interface

On BOTH laptops:

ip -br link

then:

ip -br addr

then:

ip route

Example:

lo       UNKNOWN
enp3s0   UP
wlp2s0   UP

Likely:

enp3s0 = Ethernet
wlp2s0 = Wi-Fi

Do not guess.

Run:

ethtool enp3s0

You might see:

Speed: 1000Mb/s
Duplex: Full
Link detected: yes

Record this.

21. VERY IMPORTANT — verify which path the experiment uses

Suppose receiver IP is:

10.10.10.2

On sender run:

ip route get 10.10.10.2

You want something similar to:

10.10.10.2 dev enp3s0

This proves traffic is using:

enp3s0

instead of Wi-Fi.

22. If you have a direct Ethernet cable

A simple setup is:

Sender                    Receiver
10.10.10.1                10.10.10.2
    |                          |
    +------ Ethernet ----------+

Sender:

sudo ip addr add 10.10.10.1/24 dev <sender-interface>
sudo ip link set <sender-interface> up

Receiver:

sudo ip addr add 10.10.10.2/24 dev <receiver-interface>
sudo ip link set <receiver-interface> up

Sender:

ping -c 4 10.10.10.2

You should get replies.

If your interface already has appropriate IP addresses, do not change them unnecessarily.

23. Step 4 — collect your hardware information

This is important for your report because your hardware is different from the paper.

Sender:

bash common/system_info.sh <sender-interface> system_info_sender.txt

Receiver:

bash common/system_info.sh <receiver-interface> system_info_receiver.txt

It records:

CPU
number of cores
kernel
RAM
virtualization
NIC
link speed
IP addresses
routes
TSO/GSO/GRO status
congestion-control algorithms

Put this information in your report under:

Our Testbed

24. Step 5 — start receiver

On receiver:

cd host_stack_project
bash receiver/start_server.sh

You should see something like:

Server listening on 5201

Leave it running.

What does this mean?

iperf3 -s

means:

-s = server mode

TCP port 5201 is iperf3's default server port.

25. Step 6 — your first experiment manually

On sender:

iperf3 -c <RECEIVER_IP> -t 15

Example:

iperf3 -c 10.10.10.2 -t 15

Meaning:

-c 10.10.10.2
connect to receiver

-t 15
run for 15 seconds

You may see:

[SUM] 0.00-15.00 sec 1.64 GBytes 938 Mbits/sec

If you have Gigabit Ethernet, approximately:

900–950 Mbps

could be perfectly normal.

Do not expect:

42 Gbps
100 Gbps

on a 1-Gbps adapter.

26. Step 7 — run the complete automatic experiment suite

On sender:

cd host_stack_project
bash sender/run_experiments.sh <receiver-ip> <sender-interface>

Example:

bash sender/run_experiments.sh 10.10.10.2 enp3s0

It automatically runs:

baseline P=1
parallel P=4
parallel P=8

reverse direction

zero copy

loss 0.015%
loss 0.15%
loss 1.5%

delay 5 ms
delay 20 ms

CUBIC
Reno
BBR if available
DCTCP if available

Results are stored under:

results/raw/

as JSON.

27. What does -P 4 mean?

Example:

iperf3 -c 10.10.10.2 -P 4

means:

four simultaneous TCP streams

Conceptually:

Flow 1 ──────→
Flow 2 ──────→ Receiver
Flow 3 ──────→
Flow 4 ──────→

This isn't exactly the paper's multi-core one-to-one topology, but it allows you to study how multiple competing flows affect throughput and CPU efficiency.

28. Packet-loss experiment

Our script executes Linux commands equivalent to:

sudo tc qdisc replace dev <interface> root netem loss 0.15%

tc = Linux traffic control.

netem = network emulator.

It artificially drops packets.

Then TCP sees:

packet lost
      ↓
duplicate ACK / timeout
      ↓
retransmission
      ↓
congestion-control reaction
      ↓
extra CPU work

This directly connects to Section 3.6 of the paper.

After the experiment the script removes the rule:

sudo tc qdisc del dev <interface> root
29. Added delay — your extension

We run:

sudo tc qdisc replace dev <interface> root netem delay 20ms

Now the path contains artificial delay.

Why is this interesting?

Remember:

Bandwidth Delay Product
BDP = bandwidth × RTT

Suppose:

1 Gbps
20 ms

Then approximately:

1,000,000,000 bit/s × 0.020 s
= 20,000,000 bits
≈ 2.5 MB

of data can be in flight.

The paper explicitly connects growing BDP with cache behavior and host latency.

So your delay experiment is a good extension.

30. Zero-copy extension

Run:

iperf3 -c <receiver-ip> -Z

-Z asks iperf3 to use a zero-copy-style send path where supported. Official iperf3 documents this option.

Why is this especially relevant?

Because the paper proposes zero-copy mechanisms as an important future direction for reducing data-copy overhead.

This gives you a very nice project story:

Paper:
data copy is bottleneck

↓ hypothesis

Extension:
try sender-side zero-copy

↓ measure

Does CPU fall?
Does throughput increase?

On a 1-Gbps link, throughput might stay almost unchanged because the network itself is already the bottleneck.

But CPU consumption may change.

That itself is a good result.

31. Congestion-control experiment

Check available algorithms:

sysctl net.ipv4.tcp_available_congestion_control

Maybe:

reno cubic

or:

reno cubic bbr

Run:

iperf3 -c 10.10.10.2 -C cubic

and:

iperf3 -c 10.10.10.2 -C reno

Official iperf3 exposes congestion-control selection with -C.

Your hypothesis:

On a clean direct LAN where there is little congestion, congestion-control choice might not greatly change throughput.

Interestingly, that is qualitatively similar to the paper's single-flow observation.

32. Very important reproduction: turn off offloads

This gives you a closer connection to Figure 3.

First record them:

ethtool -k <interface>

Look for:

tcp-segmentation-offload
generic-segmentation-offload
generic-receive-offload

Then on BOTH machines:

bash common/offloads_off.sh <interface>

Run:

iperf3 -c <receiver-ip> -t 15 -O 3 -J > results/raw/offloads_disabled.json

Then restore the features on BOTH machines:

bash common/offloads_on.sh <interface>

Why?

You're comparing:

Offloads ON
     vs
Offloads OFF

Hypothesis:

OFF
→ more packets handled in software
→ more CPU work
→ possibly lower throughput

On a slow Ethernet link, throughput may remain the same while CPU usage increases.

That is still an excellent result.

33. Packet capture with tcpdump/Wireshark

On receiver open another terminal:

cd host_stack_project
bash receiver/capture_baseline.sh <interface> 20 baseline.pcap

Then immediately run an iperf test.

This produces:

baseline.pcap

Open it in Wireshark.

Use filter:

tcp.port == 5201

You should see:

TCP handshake

SYN
SYN ACK
ACK

data packets

ACKs

FIN

For packet-loss experiments you may see:

TCP Retransmission
Duplicate ACK

This helps you connect packet-level events to your performance graph.

34. One Wireshark trap your professor may ask about

If Wireshark shows:

TCP checksum incorrect

on locally captured packets, it does not necessarily mean your network is broken.

With checksum offloading:

tcpdump captures packet
        ↓
NIC later calculates checksum
        ↓
packet sent

So the host capture can occur before the final hardware checksum is written.

Remember that.

35. Generate your graphs

After experiments:

python3 analysis/analyze.py

The script automatically creates:

results/summary.csv

results/throughput.png
results/server_cpu.png
results/throughput_per_core.png
results/retransmissions.png
results/loss_vs_throughput.png

These become the core results section of your report.

36. How to interpret your graphs

Never say only:

Throughput changed.

For every graph, answer these four questions:

1. What changed?

Example:

Throughput decreased as loss increased.
2. Why?
TCP performed retransmissions and reduced its sending rate.
3. Does it agree with the paper?
Qualitatively yes. The paper also observed reduced
throughput-per-core and increased TCP processing under packet loss.
4. Why are our numbers different?
Our hardware is 1/2.5/10-Gbps commodity hardware rather than
the paper's 100-Gbps Mellanox/NUMA platform.

This is how to sound like you actually understand your experiment.

37. What results should you expect?

Don't fabricate these. Your real data decides.

But your hypotheses should be:

Experiment	Expected trend
1 TCP flow	Baseline
4 flows	Aggregate throughput may rise until link saturates
8 flows	Little improvement after saturation; CPU may rise
Offloads OFF	CPU usage should increase; throughput may decrease
Packet loss ↑	Retransmissions ↑ and throughput usually ↓
Delay ↑	TCP performance may decline depending on BDP/window
Zero-copy	Sender CPU may decrease
CUBIC vs Reno	Little difference on clean LAN is possible
Reverse	Reveals sender/receiver/NIC asymmetry

These are predictions, not results.

Your actual measured numbers must go into the report.

38. Why exact paper reproduction is impossible on your normal laptop

Do not be embarrassed about this limitation. Explain it technically.

Original:

100-Gbps Mellanox NIC
24 physical cores
4 NUMA nodes
Intel DDIO
special IRQ mapping
aRFS
patched Linux 5.4.43
special skb instrumentation

Your system might have:

1-Gbps / virtual NIC
single NUMA node
modern Ubuntu
different kernel
different CPU architecture
no exposed DDIO
no Mellanox aRFS

The GitHub README itself warns that other CPU/NIC configurations may produce different behavior and that some configurations are Mellanox-specific.

So write:

“We perform a partial reproduction focused on qualitative trends rather than absolute numerical replication.”

That one sentence is important.

39. Experiments you should NOT spend tonight trying to reproduce

Skip these unless you actually have the correct hardware:

DDIO on/off
NIC-local vs NIC-remote NUMA
exact aRFS configuration
24-core CPU ↔ RX queue mapping
exact 100-Gbps throughput
exact skb-size histogram
NAPI → application latency instrumentation
IOMMU reboot/configuration experiment
full patched Linux 5.4.43 kernel

The official artifact kernel patch exists specifically to expose some of these deep measurements.

Trying to install a custom kernel hours before submission can turn a working machine into a boot/debugging problem.

40. Your presentation structure

Make about 8 slides.

Slide 1 — Title

Understanding Host Network Stack Overheads

Then:

Paper reproduction and extended evaluation
Slide 2 — Motivation

Explain:

Network speed increased dramatically.

CPU/core frequency and cache capacity did not scale equally.

Therefore host CPU becomes a network bottleneck.

The paper's central motivation is exactly this shift toward host-side CPU limitations at high bandwidth.

Slide 3 — Linux networking pipeline

Show:

Sender

Application
 ↓
Socket
 ↓
TCP/IP
 ↓
GSO/TSO
 ↓
NIC


Receiver

NIC
 ↓
IRQ/NAPI
 ↓
GRO
 ↓
TCP/IP
 ↓
Socket
 ↓
Data copy
 ↓
Application
Slide 4 — Paper's original setup

Show:

100-Gbps Mellanox
Intel Xeon
4 NUMA sockets
Linux 5.4.43
two directly connected servers

Then explain their metrics.

Slide 5 — Paper findings

Put only:

~42 Gbps/core single long flow
Receiver bottleneck
Data copy dominates optimized long flow
Cache/BDP matters
Multiple flows reduce CPU efficiency
Packet loss adds ACK/retransmission work
Slide 6 — Our setup

Include actual outputs:

CPU:
NIC:
link speed:
kernel:
OS:
interface:
sender IP:
receiver IP:

Then:

Partial reproduction because hardware differs.
Slide 7 — Reproduction results

Put your graphs:

baseline
parallel flows
offloads
packet loss
congestion control
Slide 8 — Extensions + conclusion

Extensions:

latency
zero-copy
reverse direction

Conclusion:

Network-stack CPU efficiency depends not only on raw bandwidth but also on batching/offloads, number of flows, network conditions, memory/cache behavior, and the sender/receiver processing path.

41. Questions your professor can ask

Be prepared for these:

Q: What is the main contribution of the paper?

The paper provides a detailed CPU-overhead analysis of the Linux network stack at 100-Gbps speeds and shows that bottlenecks shift from traditional protocol processing toward data movement and host resource contention.

Q: Why is the receiver slower?

Receiver processing includes receive-buffer handling, skb allocation, GRO, TCP/IP processing, and copying payloads from kernel buffers to userspace. At high bandwidth, the paper found these costs, especially data copy, become dominant.

Q: What is TSO?

NIC-assisted TCP segmentation that reduces sender CPU per-packet work.

Q: What is GRO?

Receiver-side packet aggregation that allows the upper stack to process fewer, larger skb objects.

Q: What is throughput-per-core?

throughput / CPU core-equivalents used

It measures CPU efficiency rather than just network bandwidth.

Q: What is BDP?

Bandwidth × RTT

It represents approximately how much data must be in flight to fully utilize a path.

Q: What is NUMA?

A multiprocessor memory architecture where access to local memory is faster than remote-node memory.

Q: What is DMA?

A device transfers data directly to/from memory without the CPU copying every byte.

Q: What is NAPI?

Linux's receive-processing mechanism that combines interrupts with polling to reduce interrupt overhead under high packet rates.

Q: Why does loss increase CPU overhead?

Because TCP must process duplicate ACKs, retransmit lost packets, and execute congestion-control logic.

Q: Why do many flows make GRO worse?

Packets from many flows become interleaved, so fewer consecutive packets from the same flow are available for aggregation.

Q: Why aren't your numbers the same as the paper?

Because the paper used two 100-Gbps Mellanox NUMA servers and a patched kernel, while our reproduction uses different hardware. We therefore validate qualitative trends rather than claim exact numerical replication.

That last answer is particularly important.

42. What I want you to do right now

Do not read all 13 pages before touching the experiment.

Do this order:

1. Download my ZIP.
2. Put it on sender and receiver.
3. Run common/setup.sh on both.
4. Run ip -br link and ip -br addr on both.
5. Determine sender Ethernet interface.
6. Determine receiver Ethernet interface.
7. Determine receiver IP.
8. Ping receiver from sender.
9. Run system_info.sh on both.
10. Start receiver/start_server.sh.
11. Run one manual iperf3 test.
12. Run sender/run_experiments.sh.
13. Run analysis/analyze.py.
14. Run the manual offload experiment.
15. Open one .pcap in Wireshark.
16. Fill REPORT_TEMPLATE.md.
17. Use PRESENTATION_NOTES.md for viva.

The official repository also provides sender/receiver scripts for single-flow, TCP-buffer, one-to-one, incast, all-to-all, packet-loss, short-flow, mixed-flow, NUMA, and outcast experiments, confirming that these are the major experimental dimensions of the original artifact.

Your next step should be practical: on both laptops, run:

ip -br link
ip -br addr
ip route
systemd-detect-virt

and send me the outputs from Sender and Receiver separately. I can then tell you the exact interface/IP values to put into the commands and guide you through Experiment 1 → final graphs → report → presentation without guessing anything about your network setup. 

Friday 3:15 PM

The AI_Used folder should contain:

Tools – which AI tools were used
Prompts – the prompts given
Thought process – how AI was integrated into your workflow
Step-by-step details – where and how AI contributed at each stage

write me that AI help me to solve the error and also guide me throughout the project and write somethings accroding and give me AI_Used.md

I created the AI_Used.md file with the sections your professor requested: tools used, representative prompts, thought process/workflow, step-by-step AI contribution, debugging/error-solving help, experiment guidance, analysis, and presentation preparation.

Download AI_Used.md 

AI_Used.md
Document
write it in two pages

I shortened and reorganized it to approximately two pages, while keeping all four required parts: Tools, Prompts, Thought Process, and Step-by-Step Details, with emphasis on how AI helped throughout the project and during error solving.

Download the 2-page AI_Used.md 

AI_Used_2pages.md
Document

Thursday 2:48 AM
3452296.3472888(20260910-064556).pdf
PDF
now do the eexperiment 6 according to the paper 
loss_percent,receiver_gbps_mean,receiver_gbps_sd,retransmissions_mean,retransmissions_sd,sender_process_cpu_pct_mean,sender_process_cpu_pct_sd,receiver_process_cpu_pct_mean,receiver_process_cpu_pct_sd,throughput_change_percent
0.0,12.6969277917137,0.7278802611084182,1906.0,844.4459722208402,98.83675492315635,0.5087932415488077,33.655605382757194,0.7616347772822887,0.0
0.015,11.107728716302514,0.3903491060102277,4606.0,128.51459061133875,92.99605470532892,8.359008529208323,36.88634612672359,2.524990399404952,-12.516406342393571
0.15,10.248952962485223,1.0154019970462427,22205.333333333332,2578.403446579556,77.00631974537698,11.952105194290597,47.313094719942946,2.945785821702252,-19.28005632060127
1.5,9.054421606927692,0.8795950834668604,179439.66666666666,17476.457430879214,35.213142240591665,0.5014857398770061,66.89861520231774,1.8444706185451545,-28.688090887334095
EXPERIMENT 6: PACKET LOSS
Loss 0%: 12.697 Gbps; SD 0.728; mean retransmissions 1906.0; throughput change +0.00%
Loss 0.015%: 11.108 Gbps; SD 0.390; mean retransmissions 4606.0; throughput change -12.52%
Loss 0.15%: 10.249 Gbps; SD 1.015; mean retransmissions 22205.3; throughput change -19.28%
Loss 1.5%: 9.054 Gbps; SD 0.880; mean retransmissions 179439.7; throughput change -28.69%

Source: /home/guru/host-stack-paper/results/packet-loss-20260909-212203-582328

now give me the full explainatio of  this experiment  and give me the pdf 

Experiment 7 studies short TCP request–response traffic and what happens when it shares CPU resources with a continuous TCP transfer. It follows the workloads in §3.7, “Impact of Flow Sizes,” Figures 10 and 11 of your paper.

We will do both parts:

Part	What we change	What stays fixed
7A: Request size	Request and response sizes: 4, 16, 32 and 64 KiB	16 simultaneous TCP request–response flows
7B: Mixed traffic	0, 1, 4 or 16 short flows alongside one continuous flow	Short requests and responses are 4 KiB; applications share one sender vCPU and one receiver vCPU

We also measure 16 short flows alone under the same CPU placement as Part 7B, giving us a fair comparison with the mixed case.

This is a scaled adaptation. Your VM cannot reproduce the paper’s physical NIC, NUMA or hardware-cache experiments. Also, the tool below uses separate receiver worker processes pinned to one vCPU; the paper describes a single receiver application. This difference can affect scheduling overhead and must be mentioned in your report.

Copy only the code boxes into the VS Code terminal. The surrounding text is for learning.

Step 1 — Understand the traffic before running it

Previously, a sender continuously supplied TCP data.

A request–response flow behaves differently:

The sender sends one complete request.
The receiver reads it and sends a response of the same size.
The sender receives the complete response.
Only then does it send its next request.

The TCP connection stays open across these exchanges. Therefore, “short flow” here means small request–response messages, not a new TCP connection for every message.

We will use:

netperf TCP_RR for persistent TCP request–response exchanges.
netperf TCP_STREAM for continuous TCP traffic.
netserver as the receiver.

These workload types are documented in the official Netperf manual.

Step 2 — Install the tools

Paste:

cd ~/host-stack-paper
sudo apt update
sudo apt install -y netperf sysstat ethtool python3-matplotlib

Then:

netperf -V
command -v netserver
sudo ip netns list

You should see the namespaces used in Experiments 1–5:

hsp_tx
hsp_rx

If installation fails or these namespaces are missing, stop here and send me that output. Do not substitute a different namespace or experiment script.

This experiment uses the original virtual path from Experiments 1–5. It does not use Experiment 6’s temporary packet-loss path.

Step 3 — Create the experiment script

This script will:

Run both parts, with three repetitions per setting.
Use 20-second tests.
Randomize setting order within each repetition.
Save every flow’s output and CPU activity.
Save configuration and network settings.
Produce a summary only after every test succeeds.
Return ownership of its result files to your normal user.

Unlike your earlier iperf3 experiments, these tests do not omit an initial warm-up interval. They therefore use their own baselines.

Paste this entire block:

cat > scripts/flow_sizes.py <<'PY'
import csv
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import statistics
import subprocess
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
TX, RX = "hsp_tx", "hsp_rx"
TX_IP, RX_IP = "10.204.0.1", "10.204.0.2"
PORT = 12867
SECONDS = 20
REPEATS = 3
ENV = dict(os.environ, LC_ALL="C")

def inside(namespace, *args):
    return ["ip", "netns", "exec", namespace, *map(str, args)]

def run(args):
    return subprocess.run(
        args, check=True, capture_output=True, text=True,
        env=ENV, timeout=10
    ).stdout

def stop_group(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()

def listening():
    output = run(inside(RX, "ss", "-ltnH"))
    return any(
        len(line.split()) > 3
        and line.split()[3].endswith(f":{PORT}")
        for line in output.splitlines()
    )

def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def scalar(path):
    try:
        value = float(path.read_text().strip())
    except ValueError:
        raise RuntimeError(
            f"Expected one numeric netperf result. Inspect: {path}"
        )
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(f"Invalid or zero result in {path}")
    return value

def main():
    if os.geteuid() != 0:
        raise SystemExit("Run: sudo python3 scripts/flow_sizes.py")

    for tool in ("ip", "tc", "taskset", "netperf",
                 "netserver", "mpstat", "ethtool"):
        if not shutil.which(tool):
            raise SystemExit(f"Missing tool: {tool}")

    if not {0, 1, 2}.issubset(os.sched_getaffinity(0)):
        raise SystemExit("This experiment requires guest CPUs 0, 1 and 2.")

    for namespace in (TX, RX):
        active = run(["ip", "netns", "pids", namespace]).strip()
        if active:
            raise SystemExit(
                f"{namespace} has running processes: {active}. "
                "Finish previous tests before starting this experiment."
            )

    run(inside(TX, "ping", "-c", "1", "-W", "2", RX_IP))

    if listening():
        raise SystemExit(f"Receiver port {PORT} is already in use.")

    network = {}
    for namespace, device in ((TX, "hsp_tx0"), (RX, "hsp_rx0")):
        qdisc = run(inside(namespace, "tc", "qdisc", "show"))
        filters = run(
            inside(namespace, "tc", "filter", "show",
                   "dev", device, "ingress")
        )
        if "netem" in qdisc or filters.strip():
            raise SystemExit(
                f"Unexpected traffic shaping or ingress filter in {namespace}. "
                "Send this output before continuing:\n" + qdisc + filters
            )
        network[namespace] = {
            "qdisc": qdisc,
            "ingress_filters": filters,
            "link": run(inside(namespace, "ip", "-details",
                               "link", "show", "dev", device)),
            "offloads": run(inside(namespace, "ethtool", "-k", device)),
            "tcp_congestion_control": run(
                inside(namespace, "sysctl", "-n",
                       "net.ipv4.tcp_congestion_control")
            ).strip(),
        }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder = ROOT / "results" / f"flow-sizes-{stamp}"
    folder.mkdir(parents=True)
    print(f"Results: {folder}", flush=True)

    # phase, label, number of RPC flows, bytes per message, bulk present
    cases = [
        ("sizes", f"rpc-{size // 1024}KiB", 16, size, 0)
        for size in (4096, 16384, 32768, 65536)
    ]
    cases += [
        ("mixed", f"bulk-plus-{count}", count, 4096, 1)
        for count in (0, 1, 4, 16)
    ]
    cases += [("mixed", "short-only-16", 16, 4096, 0)]

    config = {
        "reference": "Paper section 3.7; scaled VM adaptation",
        "duration_seconds": SECONDS,
        "repetitions": REPEATS,
        "warmup_omitted": False,
        "random_seed": 42,
        "sizes_sender_cpus": [0, 1],
        "mixed_sender_cpus": [0],
        "receiver_cpu": 2,
        "receiver_architecture": "netserver forked workers sharing CPU 2",
        "rpc": "TCP_RR, one outstanding transaction per data connection",
        "tcp_nodelay": "not explicitly enabled",
        "netperf_version": run(["netperf", "-V"]).strip(),
        "network": network,
        "cases": cases,
    }
    (folder / "configuration.json").write_text(
        json.dumps(config, indent=2)
    )

    server = None
    rows = []
    server_log = (folder / "netserver.txt").open("w")

    try:
        server = subprocess.Popen(
            inside(RX, "taskset", "-c", "2",
                   "netserver", "-D", "-4",
                   "-L", RX_IP, "-p", PORT),
            stdout=server_log, stderr=subprocess.STDOUT,
            env=ENV, start_new_session=True,
        )

        deadline = time.monotonic() + 10
        while not listening():
            if server.poll() is not None:
                raise RuntimeError("netserver exited. Inspect netserver.txt")
            if time.monotonic() > deadline:
                raise RuntimeError("netserver did not become ready.")
            time.sleep(0.1)

        rng = random.Random(42)

        for phase in ("sizes", "mixed"):
            phase_cases = [case for case in cases if case[0] == phase]

            for repeat in range(1, REPEATS + 1):
                order = phase_cases.copy()
                rng.shuffle(order)

                for _, label, count, size, bulk in order:
                    prefix = f"{phase}-{label}-r{repeat}"
                    print(f"\n{prefix}", flush=True)
                    processes, handles, outputs = [], [], []
                    launch_times, commands = [], []
                    monitor = None

                    try:
                        cpu_log = (folder / f"{prefix}-cpu.txt").open("w")
                        handles.append(cpu_log)
                        monitor = subprocess.Popen(
                            ["mpstat", "-P", "ALL", "1"],
                            stdout=cpu_log, stderr=subprocess.STDOUT,
                            env=ENV, start_new_session=True,
                        )

                        jobs = []
                        if bulk:
                            jobs.append(("bulk", 0, "TCP_STREAM"))

                        for index in range(count):
                            cpu = index % 2 if phase == "sizes" else 0
                            jobs.append((f"rpc-{index:02d}", cpu, "TCP_RR"))

                        for name, cpu, test in jobs:
                            output = folder / f"{prefix}-{name}.txt"
                            error = folder / f"{prefix}-{name}-errors.txt"
                            out_handle, err_handle = output.open("w"), error.open("w")
                            handles.extend([out_handle, err_handle])

                            args = inside(
                                TX, "taskset", "-c", cpu,
                                "netperf", "-4", "-H", RX_IP,
                                "-p", PORT, "-l", SECONDS,
                                "-t", test, "-P", "0", "-v", "0",
                                "-f", "x" if test == "TCP_RR" else "m"
                            )
                            if test == "TCP_RR":
                                args += ["--", "-r", f"{size},{size}"]

                            commands.append(args)
                            launch_times.append(time.monotonic())
                            process = subprocess.Popen(
                                args, stdout=out_handle, stderr=err_handle,
                                env=ENV, start_new_session=True,
                            )
                            processes.append(process)
                            outputs.append((test, output, error))

                        (folder / f"{prefix}-commands.json").write_text(
                            json.dumps(commands, indent=2)
                        )

                        deadline = time.monotonic() + SECONDS + 30
                        for process, (_, output, error) in zip(processes, outputs):
                            process.wait(
                                timeout=max(0.1, deadline - time.monotonic())
                            )
                            if process.returncode != 0:
                                raise RuntimeError(
                                    f"Test failed. Inspect {output.name} "
                                    f"and {error.name}"
                                )

                    finally:
                        for process in processes:
                            stop_group(process)
                        stop_group(monitor)
                        for handle in handles:
                            handle.close()

                    rpc_tps, bulk_gbps = 0.0, 0.0
                    for test, output, _ in outputs:
                        value = scalar(output)
                        if test == "TCP_RR":
                            rpc_tps += value
                        else:
                            bulk_gbps += value / 1000.0

                    rpc_request_gbps = rpc_tps * size * 8 / 1e9
                    span_ms = (max(launch_times) - min(launch_times)) * 1000

                    row = {
                        "phase": phase,
                        "condition": label,
                        "repeat": repeat,
                        "rpc_flows": count,
                        "message_bytes": size,
                        "bulk_flows": bulk,
                        "rpc_tps": rpc_tps,
                        "rpc_request_gbps": rpc_request_gbps,
                        "rpc_bidirectional_gbps": 2 * rpc_request_gbps,
                        "bulk_gbps": bulk_gbps,
                        "forward_total_gbps": bulk_gbps + rpc_request_gbps,
                        "launch_span_ms": span_ms,
                    }
                    rows.append(row)
                    write_csv(folder / "runs.csv", rows)

                    print(f"RPC transactions/s: {rpc_tps:.2f}")
                    print(f"RPC request+response: {2 * rpc_request_gbps:.3f} Gbps")
                    print(f"Continuous flow: {bulk_gbps:.3f} Gbps")
                    print(f"Forward total: {row['forward_total_gbps']:.3f} Gbps")
                    print(f"Process launch span: {span_ms:.1f} ms", flush=True)
                    time.sleep(2)

        summary = []
        metrics = (
            "rpc_tps", "rpc_request_gbps", "rpc_bidirectional_gbps",
            "bulk_gbps", "forward_total_gbps", "launch_span_ms"
        )

        for phase, label, count, size, bulk in cases:
            selected = [
                row for row in rows
                if row["phase"] == phase and row["condition"] == label
            ]
            if {row["repeat"] for row in selected} != {1, 2, 3}:
                raise RuntimeError(f"Incomplete condition: {label}")

            result = {
                "phase": phase, "condition": label,
                "rpc_flows": count, "message_bytes": size,
                "bulk_flows": bulk, "repetitions": len(selected),
            }
            for metric in metrics:
                values = [row[metric] for row in selected]
                result[f"{metric}_mean"] = statistics.mean(values)
                result[f"{metric}_sd"] = statistics.stdev(values)
            summary.append(result)

        write_csv(folder / "summary.csv", summary)
        (folder / "COMPLETED.txt").write_text(
            "All 27 tests completed successfully.\n"
        )
        print(f"\nCOMPLETE: {folder / 'summary.csv'}", flush=True)

    finally:
        stop_group(server)
        server_log.close()
        if "SUDO_UID" in os.environ and "SUDO_GID" in os.environ:
            uid = int(os.environ["SUDO_UID"])
            gid = int(os.environ["SUDO_GID"])
            for path in folder.rglob("*"):
                os.chown(path, uid, gid)
            os.chown(folder, uid, gid)

if __name__ == "__main__":
    main()
PY

What the CPU placement means

Workload	Sender applications	Receiver workers
Part 7A	16 processes distributed across vCPUs 0 and 1	All share vCPU 2
Part 7B	Continuous sender and all RPC senders share vCPU 0	All share vCPU 2

The 16 senders are 16 application processes, not 16 physical cores. Application affinity also does not guarantee that every related kernel operation runs on those same vCPUs.

Step 4 — Run Experiment 7

Close other running benchmarks. Then paste:

cd ~/host-stack-paper
sudo python3 scripts/flow_sizes.py

Allow approximately 10–15 minutes, depending on your VM.

You will see settings in a shuffled order. That is deliberate: it reduces the chance that warming up or a gradual change in laptop load always affects the same setting.

The final successful line will look like:

COMPLETE: /home/guru/host-stack-paper/results/flow-sizes-.../summary.csv

Do not start another copy while this one is running. If it fails, keep its result folder and send the error. An incomplete folder will not be used by the plotting script.

Step 5 — Create the graphs and comparison report

Paste:

cat > scripts/plot_flow_sizes.py <<'PY'
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

folders = sorted(
    folder for folder in (ROOT / "results").glob("flow-sizes-*")
    if folder.is_dir()
    and (folder / "COMPLETED.txt").exists()
    and (folder / "summary.csv").exists()
)
if not folders:
    raise SystemExit("No completed Experiment 7 result folder found.")

folder = folders[-1]
with (folder / "summary.csv").open() as handle:
    rows = list(csv.DictReader(handle))

if len(rows) != 9 or any(int(row["repetitions"]) != 3 for row in rows):
    raise SystemExit("Summary does not contain all nine completed settings.")

def value(row, key):
    return float(row[key])

sizes = sorted(
    [row for row in rows if row["phase"] == "sizes"],
    key=lambda row: int(row["message_bytes"])
)
mixed = sorted(
    [row for row in rows
     if row["phase"] == "mixed" and int(row["bulk_flows"]) == 1],
    key=lambda row: int(row["rpc_flows"])
)
short_alone = next(row for row in rows if row["condition"] == "short-only-16")

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

def bars(ax, data, metric, labels, title, ylabel, color):
    x = list(range(len(data)))
    means = [value(row, metric + "_mean") for row in data]
    errors = [value(row, metric + "_sd") for row in data]
    ax.bar(x, means, yerr=errors, capsize=5, color=color)
    ax.set_xticks(x, labels)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)

size_labels = [str(int(row["message_bytes"]) // 1024) for row in sizes]
mix_labels = [row["rpc_flows"] for row in mixed]

bars(
    axes[0, 0], sizes, "rpc_bidirectional_gbps", size_labels,
    "7A: 16 RPC flows — useful data rate",
    "Request + response goodput (Gbps)", "#4477AA"
)
axes[0, 0].set_xlabel("Request size = response size (KiB)")

bars(
    axes[0, 1], sizes, "rpc_tps", size_labels,
    "7A: 16 RPC flows — transaction rate",
    "Completed transactions/s", "#228833"
)
axes[0, 1].set_xlabel("Request size = response size (KiB)")

bars(
    axes[1, 0], mixed, "bulk_gbps", mix_labels,
    "7B: Continuous TCP flow with competing RPCs",
    "Continuous-flow throughput (Gbps)", "#CC6677"
)
axes[1, 0].set_xlabel("Number of competing 4 KiB RPC flows")

mix16 = next(row for row in mixed if int(row["rpc_flows"]) == 16)
bars(
    axes[1, 1], [short_alone, mix16], "rpc_tps",
    ["16 RPCs alone", "16 RPCs + bulk"],
    "7B: RPC performance with identical CPU placement",
    "Completed transactions/s", "#AA8833"
)

fig.suptitle("Experiment 7: TCP request size and mixed workloads", fontsize=16)
fig.tight_layout(rect=[0, 0.10, 1, 0.95])
fig.text(
    0.5, 0.025,
    "Means ± sample SD; 3 repetitions; 20-second tests without omitted warm-up.\n"
    "Single VM and virtual Ethernet; receiver workers share one vCPU.\n"
    "Rates are sums of individual flow averages, not throughput per fully accounted CPU core.",
    ha="center", fontsize=9
)
fig.savefig(folder / "experiment7.png", dpi=180)
fig.savefig(folder / "experiment7.pdf")
plt.close(fig)

bulk_baseline = value(mixed[0], "bulk_gbps_mean")
short_baseline = value(short_alone, "rpc_tps_mean")

lines = [
    "EXPERIMENT 7: REQUEST SIZE AND MIXED TCP WORKLOADS",
    "",
    "PART 7A: 16 persistent TCP request-response flows",
]
for row in sizes:
    lines.append(
        f"{int(row['message_bytes']) // 1024} KiB: "
        f"{value(row, 'rpc_tps_mean'):.2f} transactions/s; "
        f"request+response {value(row, 'rpc_bidirectional_gbps_mean'):.3f} Gbps; "
        f"SD {value(row, 'rpc_bidirectional_gbps_sd'):.3f}"
    )

lines += ["", "PART 7B: One continuous flow plus 4 KiB RPC flows"]
for row in mixed:
    change = 100 * (value(row, "bulk_gbps_mean") / bulk_baseline - 1)
    lines.append(
        f"{row['rpc_flows']} RPC flows: "
        f"bulk {value(row, 'bulk_gbps_mean'):.3f} Gbps; "
        f"change versus bulk alone {change:+.2f}%; "
        f"RPC rate {value(row, 'rpc_tps_mean'):.2f} transactions/s; "
        f"forward total {value(row, 'forward_total_gbps_mean'):.3f} Gbps"
    )

rpc_change = 100 * (value(mix16, "rpc_tps_mean") / short_baseline - 1)
lines += [
    "",
    f"16 RPC flows alone: {short_baseline:.2f} transactions/s",
    f"16 RPC flows with bulk: {value(mix16, 'rpc_tps_mean'):.2f} transactions/s",
    f"RPC rate change with bulk: {rpc_change:+.2f}%",
    "",
    "Forward total counts bulk data plus RPC requests in the same direction.",
    "It excludes RPC responses travelling in the opposite direction.",
    f"Source: {folder}",
]

report = "\n".join(lines) + "\n"
(folder / "comparison.txt").write_text(report)
print(report)
print(f"Graph: {folder / 'experiment7.png'}")
print(f"Graph PDF: {folder / 'experiment7.pdf'}")
PY

Run:

python3 scripts/plot_flow_sizes.py

Open the newest flow-sizes-... folder in VS Code and click experiment7.png.

Step 6 — Understand what you measured

There are several different quantities. Keep them separate when explaining the experiment.

Measurement	Meaning
RPC transactions/s	Complete request–response exchanges per second, summed across RPC flows
RPC request goodput	Useful request bytes delivered per second, converted to Gbps
RPC bidirectional goodput	Useful request plus response bytes per second
Continuous-flow throughput	The continuous TCP transfer’s rate
Forward total	Continuous traffic plus RPC requests travelling toward the receiver
Sample standard deviation	Variation across the three repetitions

For example, suppose the combined RPC rate is 100,000 transactions/s, and each request and response is 4,096 bytes.

Request-direction goodput:

$$ 100{,}000 \times 4096 \times 8 / 10^9 = 3.2768\ \text{Gbps} $$

Request plus response goodput:

$$ 2 \times 3.2768 = 6.5536\ \text{Gbps} $$

These are application payload rates. They do not count Ethernet/IP/TCP headers or retransmitted bytes as additional useful data.

Also, a 4 KiB request is not one packet. TCP presents a byte stream; segmentation and offloads affect how those bytes are processed.

Step 7 — What to look for in the results

For Part 7A: compare both transactions/s and goodput.

Larger messages carry more useful bytes per transaction, but take longer to transfer. Therefore, goodput can increase while transactions/s decreases. That is a meaningful result, not a contradiction.

The paper reports increasing throughput per core with larger RPC messages. Your graph measures application goodput under fixed application placement, so compare the qualitative behavior carefully rather than expecting identical numbers.

For Part 7B: compare the continuous flow against its new zero-RPC baseline.

As more RPC flows compete for the same application CPUs, the continuous transfer may lose throughput. Compare the 16-RPC workload alone against the same workload with the continuous flow to see whether the RPC traffic is also affected.

A decrease is not guaranteed. Report the measured direction and variability. Do not change settings simply to force the graph to resemble the paper.

The CPU logs provide supporting evidence about guest CPU activity. They do not by themselves identify the costs of data copying, TCP processing, cache misses or scheduling. Those claims require additional profiling.

What you can tell your professor

“Experiment 7 investigates TCP request–response message size and interference between continuous and request–response traffic. First, I used 16 persistent TCP connections and varied equal request and response sizes from 4 to 64 KiB. Second, I mixed one continuous TCP transfer with 0, 1, 4 and 16 request–response flows while keeping their application CPU placement fixed. I measured transaction rate, useful data throughput and variation across three repetitions.”

If asked “Is this exactly the paper’s experiment?”, answer:

“It follows the workload questions in Section 3.7, but it is a scaled virtual-machine adaptation. My receiver uses Netperf worker processes sharing one vCPU, whereas the paper describes one receiver application. I have not reproduced the physical NIC, NUMA comparisons or detailed kernel CPU breakdown.”

After running it, send me the printed comparison report and graph. We can then explain your actual results without guessing what happened.

Close other running benchmarks. Then paste: Bash

how time do i have to run this 

Run it once and allow approximately 10–15 minutes. The script automatically runs both parts and all three repetitions—you do not need to run it three times.

Use:

cd ~/host-stack-paper
sudo python3 scripts/flow_sizes.py

It performs 27 tests × 20 seconds = 9 minutes of measurements, plus pauses and startup time.

Keep the terminal open until you see:

COMPLETE: .../summary.csv

Then create the graphs:

python3 scripts/plot_flow_sizes.py

If it is already running, let it finish; do not launch another copy.

python3 scripts/plot_flow_sizes.py after this their is no graph of expe 7 guru@ubuntu:~/host-stack-paper$ python3 scripts/plot_flow_sizes.py
EXPERIMENT 7: REQUEST SIZE AND MIXED TCP WORKLOADS

PART 7A: 16 persistent TCP request-response flows
4 KiB: 107544.71 transactions/s; request+response 7.048 Gbps; SD 0.918
16 KiB: 89013.26 transactions/s; request+response 23.334 Gbps; SD 3.667
32 KiB: 67488.70 transactions/s; request+response 35.384 Gbps; SD 5.429
64 KiB: 43349.76 transactions/s; request+response 45.456 Gbps; SD 4.394

PART 7B: One continuous flow plus 4 KiB RPC flows
0 RPC flows: bulk 36.592 Gbps; change versus bulk alone +0.00%; RPC rate 0.00 transactions/s; forward total 36.592 Gbps
1 RPC flows: bulk 22.599 Gbps; change versus bulk alone -38.24%; RPC rate 62174.03 transactions/s; forward total 24.636 Gbps
4 RPC flows: bulk 10.604 Gbps; change versus bulk alone -71.02%; RPC rate 117201.55 transactions/s; forward total 14.445 Gbps
16 RPC flows: bulk 3.523 Gbps; change versus bulk alone -90.37%; RPC rate 159819.20 transactions/s; forward total 8.760 Gbps

16 RPC flows alone: 162485.88 transactions/s
16 RPC flows with bulk: 159819.20 transactions/s
RPC rate change with bulk: -1.64%

Forward total counts bulk data plus RPC requests in the same direction.
It excludes RPC responses travelling in the opposite direction.
Source: /home/guru/host-stack-paper/results/flow-sizes-20260909-214523-146972

Graph: /home/guru/host-stack-paper/results/flow-sizes-20260909-214523-146972/experiment7.png
Graph PDF: /home/guru/host-stack-paper/results/flow-sizes-20260909-214523-146972/experiment7.pdf
guru@ubuntu:~/host-stack-paper$ 

Your Experiment 7 graph was saved successfully. The script saves image files instead of opening a graph window automatically.

1. Open the graph in VS Code

Copy this command:

code ~/host-stack-paper/results/flow-sizes-20260909-214523-146972/experiment7.png

Alternatively, in VS Code’s left Explorer panel, open:

results → flow-sizes-20260909-214523-146972 → experiment7.png

If the folder is not visible, click Refresh in the Explorer.

2. Open the PDF version

xdg-open ~/host-stack-paper/results/flow-sizes-20260909-214523-146972/experiment7.pdf

The graph contains four panels:

Panel	What it shows
Top left	Request–response goodput for different message sizes
Top right	Completed transactions per second for different message sizes
Bottom left	Continuous TCP throughput as competing RPC flows increase
Bottom right	Performance of 16 RPC flows alone versus with continuous traffic

You do not need to rerun the experiment. Your output shows both parts completed and the plotting script saved the PNG and PDF.

i want to add like the other experiment  in  the graph folder 

Yes—copy the Experiment 7 graphs into your project’s graphs folder, keeping the originals in the results folder.

Paste:

cd ~/host-stack-paper

mkdir -p graphs

cp results/flow-sizes-20260909-214523-146972/experiment7.png graphs/experiment7.png

cp results/flow-sizes-20260909-214523-146972/experiment7.pdf graphs/experiment7.pdf

Then open the graph:

code graphs/experiment7.png

You will now find experiment7.png and experiment7.pdf inside graphs in VS Code. No need to rerun the experiment.

give the fully explainiatation of this experiment in pdf 

The DCTCP permission issue is fixed. This time, the DCTCP transfer ran and passed the algorithm-name check, but the script could not verify ECN from the saved socket output.

We need to inspect that output to distinguish an ECN problem from an overly strict check in my script. Do not rerun the experiment yet.

1. Print the two DCTCP socket snapshots

Paste:

cd ~/host-stack-paper

python3 <<'PY'
from pathlib import Path

folder = Path("results/congestion-control-20260909-222921-666328")

for name in (
    "dctcp-r1-socket-1.txt",
    "dctcp-r1-socket-2.txt",
    "dctcp-r1-queue-after.json",
):
    path = folder / name
    print(f"\n--- {name} ---")
    if path.exists():
        print(path.read_text())
    else:
        print("File not found.")
PY

2. Send me the complete output.

The socket snapshots may contain DCTCP-specific information even if the exact ecn label the script expects is absent. The queue records will help check whether congestion marking occurred.

Your original allowed-algorithm list was restored successfully. Experiment 10 remains incomplete; keep the validation check in place until we examine the evidence.

guru@ubuntu:~/host-stack-paper$ cd ~/host-stack-paper

python3 <<'PY'
from pathlib import Path

folder = Path("results/congestion-control-20260909-222921-666328")

for name in (
    "dctcp-r1-socket-1.txt",
    "dctcp-r1-socket-2.txt",
    "dctcp-r1-queue-after.json",
):
    path = folder / name
    print(f"\n--- {name} ---")
    if path.exists():
        print(path.read_text())
    else:
        print("File not found.")
PY

--- dctcp-r1-socket-1.txt ---
ESTAB 0      260696 10.210.0.1:41002 10.210.0.2:5210
         dctcp wscale:10,10 rto:201 rtt:0.017/0.006 mss:1448 pmtu:1500 rcvmss:536 advmss:1448 cwnd:5708 bytes_sent:51379700557 bytes_retrans:864 bytes_acked:51379306534 segs_out:35660028 segs_in:456826 data_segs_out:35660026 dctcp:(ce_state:0,alpha:0,ab_ecn:0,ab_tot:0) send 3889498352941bps lastrcv:3998 pacing_rate 7398206657336bps delivery_rate 143220363632bps delivered:35659755 app_limited busy:3983ms rwnd_limited:28ms(0.7%) unacked:272 retrans:0/1 dsack_dups:1 reordering:300 rcv_space:14480 rcv_ssthresh:64088 notsent:56 minrtt:0.001 snd_wnd:3034112 rcv_wnd:64512


--- dctcp-r1-socket-2.txt ---
ESTAB 0      262144 10.210.0.1:41002 10.210.0.2:5210
         dctcp wscale:10,10 rto:201 rtt:0.038/0.024 mss:1448 pmtu:1500 rcvmss:536 advmss:1448 cwnd:5708 bytes_sent:102379423349 bytes_retrans:1616 bytes_acked:102379421734 segs_out:71057456 segs_in:911021 data_segs_out:71057454 dctcp:(ce_state:0,alpha:0,ab_ecn:0,ab_tot:0) send 1740038736842bps lastsnd:1 lastrcv:8021 pacing_rate 4681166159288bps delivery_rate 34028000000bps delivered:71057455 busy:7977ms rwnd_limited:31ms(0.4%) retrans:0/2 dsack_dups:2 reordering:300 rcv_space:14480 rcv_ssthresh:64088 minrtt:0.001 snd_wnd:3427328 rcv_wnd:64512


--- dctcp-r1-queue-after.json ---
{
  "h10_tx": "qdisc fq 800a: root refcnt 5 limit 10000p flow_limit 1000p buckets 1024 orphan_mask 1023 bands 3 priomap 1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1 weights 589824 196608 65536 quantum 3028b initial_quantum 15140b low_rate_threshold 550Kbit refill_delay 40ms ce_threshold 1ms timer_slack 10us horizon 10s horizon_drop offload_horizon 0us \n Sent 630953202586 bytes 418467281 pkt (dropped 0, overlimits 0 requeues 0) \n backlog 0b 0p requeues 0\n  flows 5 (inactive 5 throttled 0) band0_pkts 0 band1_pkts 0 band2_pkts 0\n  gc 0 highprio 0 fastpath 11283391 throttled 1180651 latency 4.57us ce_mark 132\n",
  "h10_rx": "qdisc fq 800b: root refcnt 5 limit 10000p flow_limit 1000p buckets 1024 orphan_mask 1023 bands 3 priomap 1 2 2 2 1 2 0 0 1 1 1 1 1 1 1 1 weights 589824 196608 65536 quantum 3028b initial_quantum 15140b low_rate_threshold 550Kbit refill_delay 40ms ce_threshold 1ms timer_slack 10us horizon 10s horizon_drop offload_horizon 0us \n Sent 360850610 bytes 5467186 pkt (dropped 0, overlimits 0 requeues 0) \n backlog 0b 0p requeues 0\n  flows 0 (inactive 0 throttled 0) band0_pkts 0 band1_pkts 0 band2_pkts 0\n  gc 0 highprio 0 fastpath 5467183 throttled 0\n"
}

guru@ubuntu:~/host-stack-paper$ 

Your output shows active DCTCP. The failure came from my validation check being too narrow.

Both snapshots contain:

dctcp ... dctcp:(ce_state:0,alpha:0,ab_ecn:0,ab_tot:0)

Linux exposes this enabled DCTCP state separately from its dctcp-reno fallback. That provides evidence of active DCTCP even though your output lacks the standalone ecn word my script expected. Linux DCTCP implementation

Two details matter:

alpha:0 does not mean DCTCP is disabled. It is the congestion estimate at the sampling instant. The other displayed counters are not lifetime totals.
ce_mark 132 is a queue counter. We cannot attribute all 132 marks to DCTCP without checking the before/after counters. My use of qdisc replace could retain queue statistics across tests.

We’ll fix the validation and explicitly recreate the experiment queues between runs.

1. Apply the corrections

Copy this entire block:

cd ~/host-stack-paper

python3 <<'PY'
import ast
from pathlib import Path
import shutil

path = Path("scripts/congestion_control.py")
source = path.read_text()
tree = ast.parse(source)
lines = source.splitlines(keepends=True)

queue_functions = [
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "configure_queue"
]

ecn_assignments = [
    node for node in ast.walk(tree)
    if isinstance(node, ast.Assign)
    and any(
        isinstance(target, ast.Name) and target.id == "ecn_verified"
        for target in node.targets
    )
]

if len(queue_functions) != 1 or len(ecn_assignments) != 1:
    raise SystemExit(
        "Script differs from the expected version. No changes made."
    )

if "ecn_evidence" in source:
    raise SystemExit(
        "This correction appears to be installed already. No changes made."
    )

queue_replacement = '''def configure_queue(namespace, device):
    if (namespace, device) not in ((TX, DEV_TX), (RX, DEV_RX)):
        raise RuntimeError("Refusing to change a non-experiment queue.")

    # Remove the previous experiment queue so counters start fresh.
    # The first setup may have no removable root queue.
    subprocess.run(
        inside(namespace, "tc", "qdisc", "del",
               "dev", device, "root"),
        text=True, capture_output=True, timeout=10, env=ENV,
    )
    run(inside(
        namespace, "tc", "qdisc", "add",
        "dev", device, "root", "fq",
        "limit", "10000", "flow_limit", "1000",
        "ce_threshold", "1ms",
    ))
'''

ecn_replacement = r'''            ecn_flags_present = bool(samples) and all(
                re.search(r"\becn\b", snapshot) is not None
                for snapshot in samples
            )

            active_dctcp_state = (
                algorithm == "dctcp"
                and bool(samples)
                and all(
                    re.search(r"(?m)^\s*dctcp(?:\s|$)", snapshot)
                    and re.search(r"\bdctcp:\(ce_state:", snapshot)
                    for snapshot in samples
                )
            )

            ecn_evidence = (
                "ss_ecn_flag" if ecn_flags_present
                else "active_dctcp_kernel_state" if active_dctcp_state
                else "not_established"
            )
            ecn_verified = ecn_evidence != "not_established"
'''

edits = []
for node, replacement in (
    (queue_functions[0], queue_replacement),
    (ecn_assignments[0], ecn_replacement),
):
    edits.append((node.lineno - 1, node.end_lineno, replacement))

for start, end, replacement in sorted(edits, reverse=True):
    lines[start:end] = [replacement]

updated = "".join(lines)

old_field = '"ecn_verified": ecn_verified,'
if updated.count(old_field) != 1:
    raise SystemExit("Could not safely update result fields. No changes made.")

updated = updated.replace(
    old_field,
    old_field + '\n                "ecn_evidence": ecn_evidence,',
    1,
)

updated = updated.replace(
    'f"ECN verified: {ecn_verified}"',
    'f"ECN evidence: {ecn_evidence}"',
)

ast.parse(updated)

backup = path.with_name("congestion_control.before_ecn_fix.py")
if not backup.exists():
    shutil.copy2(path, backup)

path.write_text(updated)
print("Updated DCTCP validation and queue initialization.")
print("Backup:", backup)

plot_path = Path("scripts/plot_congestion_control.py")
if plot_path.exists():
    plot_source = plot_path.read_text()
    plot_updated = plot_source.replace(
        "DCTCP live algorithm and ECN negotiation were checked.",
        "DCTCP live state and ECN-support evidence were checked.",
    ).replace(
        "ECN negotiation does not establish that CE marking occurred.",
        "ECN-support evidence does not establish a measured congestion response.",
    )
    ast.parse(plot_updated)
    plot_path.write_text(plot_updated)
    print("Updated comparison-report wording.")
PY

This keeps validation in place: a missing DCTCP state or a dctcp-reno fallback will not pass the active-DCTCP check.

2. Run the complete experiment again

Use the wrapper so the temporary allowed-algorithm setting is restored afterward:

sudo python3 scripts/run_congestion_control.py

Allow approximately 4–5 minutes. DCTCP should now report either:

ECN evidence: active_dctcp_kernel_state

or:

ECN evidence: ss_ecn_flag

Earlier incomplete folders remain saved. The fresh run also gives each test its own queue counters; these still cover the whole test, including warm-up and control traffic.

3. Generate the graph after COMPLETE: appears

python3 scripts/plot_congestion_control.py
code graphs/experiment10.png

Send me the completed comparison output. We can then explain the algorithm differences and inspect the new queue evidence without treating cumulative marks or sampled zero values as proof of a particular congestion response.

is everything is doen 

Not everything is confirmed complete yet. Here is your current status:

Experiment	Status
1–5: TCP traffic patterns	Measurements and comparison graphs completed
6: Packet loss	Measurements, graph and explanation PDF completed
7: Request sizes and mixed traffic	Measurements, graph and explanation PDF completed
8: DCA	Performance experiment not performed; hardware-assessment instructions provided
9: IOMMU	Performance experiment not performed; hardware-assessment instructions provided
10: Congestion control	Fix provided; successful completion still needs confirmation

If you have not run the corrected Experiment 10 yet, paste:

sudo python3 scripts/run_congestion_control.py

After it prints COMPLETE:, run:

python3 scripts/plot_congestion_control.py

Send me that output.

For the whole project submission, you still need a final report/presentation that combines the results, explains the VM adaptations, and marks Experiments 8–9 as not reproduced. The paper’s detailed kernel profiling and hardware findings have not been fully reproduced by these laptop tests.
