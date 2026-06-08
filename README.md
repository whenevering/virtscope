# VirtScope

**English** · [中文](docs/README.zh-CN.md) · [Español](docs/README.es.md) · [Français](docs/README.fr.md) · [Deutsch](docs/README.de.md) · [Italiano](docs/README.it.md) · [Português](docs/README.pt.md) · [Русский](docs/README.ru.md)

Unified resource search across virtualization and container platforms.

Search multiple VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes environments from a single web interface — by VM name, network, IP, or any keyword.

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
