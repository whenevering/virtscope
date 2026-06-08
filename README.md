# VirtScope

**English** · [中文](docs/README.zh-CN.md) · [Español](docs/README.es.md) · [Français](docs/README.fr.md) · [Deutsch](docs/README.de.md) · [Italiano](docs/README.it.md) · [Português](docs/README.pt.md) · [Русский](docs/README.ru.md)

Unified resource search across virtualization and container platforms.

Search multiple VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes environments from a single web interface — by VM name, network, IP, or any keyword.

---

## Why VirtScope

### The Age of Heterogeneous Infrastructure

Modern enterprises rarely confine themselves to a single virtualization platform. VMware vSphere governs the production estate; KVM and Proxmox serve cost-sensitive workloads; Docker and Kubernetes orchestrate the cloud-native layer. Each platform is a universe unto itself, with its own console, its own naming conventions, its own way of seeing the world.

### The Needle in Ten Thousand Haystacks

Even when architecture teams meticulously classify business requirements and enforce disciplined naming conventions, reality has a way of humbling order. A mid-size enterprise may harbor thousands of virtual machines across dozens of clusters; add containers, and the count can swell to tens of thousands. When an incident strikes — a network anomaly, a security alert, a capacity investigation — the question is always the same:

> *Where is the resource named `web-prod-03`? Which vCenter does it belong to? What ESXi host runs it? What are its IPs?*

The answer, more often than not, requires logging into three or four consoles, clicking through nested folders, and cross-referencing spreadsheets. Minutes tick by. The incident escalates.

### The Heavyweight Mirage

OpenStack and commercial cloud management platforms promise a unified pane of glass — and deliver a cathedral of complexity. They demand their own databases, message queues, and identity services. They require weeks of deployment and dedicated teams to maintain. And when it comes to container resources, their support is often an afterthought: a thin API wrapper that surfaces pod names but little else.

For many organizations, the cost of building and operating such a platform exceeds the problem it was meant to solve.

### A Different Philosophy

VirtScope takes a contrarian stance: **the best search tool is the one you can deploy in five minutes and forget about.**

- **Single file, zero dependencies.** One Python script. No database. No build step. Run it, open the browser, search.
- **Concurrent by design.** All configured endpoints are queried in parallel. A search across ten vCenters returns in the time of the slowest one.
- **Lightweight everywhere.** A few megabytes of memory. No daemons to babysit. No certificates to rotate. It simply sits in the corner and answers questions.
- **Polyglot from day one.** VMware today, KVM and Proxmox tomorrow, Docker and Kubernetes on the horizon — each added by implementing a single adapter interface. The search experience remains the same.

### When to Reach for VirtScope

| Scenario | Without VirtScope | With VirtScope |
| --- | --- | --- |
| Locate a VM by partial name | Log into each vCenter, search manually | Type the name, see all matches across all platforms |
| Find which ESXi host a VM lives on | Navigate the inventory tree in vSphere Client | One glance at the results table |
| Identify a VM by its IP address | Check DHCP leases, query VMware Tools manually | Enter the IP fragment, instant match |
| Investigate during an incident | Context-switch between 4 consoles | One search, all platforms, under 5 seconds |

### Design Principles

1. **Simplicity is a feature, not a limitation.** Every line of code must justify its existence.
2. **Speed is respect.** An operator's time is sacred; a search tool that makes them wait has already failed.
3. **Plurality is reality.** Heterogeneous infrastructure is not a problem to be solved — it is a fact to be embraced.
4. **The tool should disappear.** The best interface is the one the user never thinks about.

---

## Supported Platforms

| Type | Platform | Status |
| --- | --- | --- |
| VM | VMware vCenter | ✅ Supported |
| VM | VMware ESXi (direct) | ✅ Supported |
| VM | KVM / libvirt | 🚧 Planned |
| VM | Proxmox VE | 🚧 Planned |
| Container | Docker | 🚧 Planned |
| Container | Kubernetes | 🚧 Planned |

## Features

- Concurrent multi-endpoint search, aggregated results in one table
- Space-separated multi-keyword **AND** matching; each term supports **regex**
- Matches both VM names and guest IP addresses (via VMware Tools)
- Built-in 8-language UI (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Per-endpoint timeout, session TTL and capacity cap for long-running stability
- Zero external frontend dependencies — single-file Python; just open the browser

## Requirements

- Python 3.10+
- Network access to target vCenter / ESXi / future platforms

## Installation

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Configuration

Copy the sample config:

```bash
cp virts-list.ini.example virts-list.ini
```

Add one `[section]` per endpoint:

```ini
[vcenter-prod]
host = vcenter.example.com
username = admin@vsphere.local
password = your-password
port = 443

[esxi-edge-01]
host = 10.0.0.11
username = root
password = your-password
```

> ⚠️ `virts-list.ini` contains plain-text credentials and is excluded by `.gitignore`. **Never commit it.**

## Usage

```bash
python virtscope.py
```

Listens on `0.0.0.0:6616` by default. Open `http://127.0.0.1:6616/` in your browser.

## Keyword Examples

| Input | Meaning |
| --- | --- |
| `web` | Name or IP contains "web" |
| `web 192.168.10` | Both "web" AND "192.168.10" must match |
| `^db-\d+` | Regex: names starting with `db-` followed by digits |
| *(blank)* | List all VMs |

## Roadmap

- [ ] libvirt / KVM endpoint adapter (connection URI, domain metadata, NIC IPs)
- [ ] Proxmox VE API adapter
- [ ] Docker engine and Swarm service search
- [ ] Kubernetes multi-cluster Pod / Service search (kubeconfig contexts)
- [ ] Unified `Provider` interface for pluggable platforms
- [ ] Export results to CSV / JSON
- [ ] Basic access control (Basic Auth / Token)

## License

[MIT](LICENSE)
