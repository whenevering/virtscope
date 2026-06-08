# VirtScope

[English](../README.md) · [中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · **Deutsch** · [Italiano](README.it.md) · [Português](README.pt.md) · [Русский](README.ru.md)

Einheitliche Ressourcensuche über Virtualisierungs- und Container-Plattformen.

Durchsuchen Sie mehrere VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes Umgebungen über eine einzige Weboberfläche — nach VM-Name, Netzwerk, IP oder beliebigen Stichwörtern.

## Unterstützte Plattformen

| Typ | Plattform | Status |
| --- | --- | --- |
| VM | VMware vCenter | ✅ Unterstützt |
| VM | VMware ESXi (direkt) | ✅ Unterstützt |
| VM | KVM / libvirt | 🚧 Geplant |
| VM | Proxmox VE | 🚧 Geplant |
| Container | Docker | 🚧 Geplant |
| Container | Kubernetes | 🚧 Geplant |

## Funktionen

- Gleichzeitige Multi-Endpoint-Suche, aggregierte Ergebnisse in einer Tabelle
- Durch Leerzeichen getrennte Stichwörter mit **UND**-Verknüpfung; jeder Begriff unterstützt **Regex**
- Übereinstimmung mit VM-Namen und Gast-IP-Adressen (über VMware Tools)
- Eingebaute 8-Sprachen-Oberfläche (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Timeout pro Endpoint, Session-TTL und Kapazitätsgrenze für langfristige Stabilität
- Keine externen Frontend-Abhängigkeiten — Python-Einzeldatei; einfach den Browser öffnen

## Anforderungen

- Python 3.10+
- Netzwerkzugriff auf vCenter / ESXi / zukünftige Plattformen

## Installation

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Konfiguration

Kopieren Sie die Beispieldatei:

```bash
cp virts-list.ini.example virts-list.ini
```

Fügen Sie einen `[Abschnitt]` pro Endpoint hinzu:

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

> ⚠️ `virts-list.ini` enthält Klartext-Anmeldeinformationen und wird von `.gitignore` ausgeschlossen. **Niemals committen.**

## Verwendung

```bash
python virtscope.py
```

Hört standardmäßig auf `0.0.0.0:6616`. Öffnen Sie `http://127.0.0.1:6616/` in Ihrem Browser.

## Stichwort-Beispiele

| Eingabe | Bedeutung |
| --- | --- |
| `web` | Name oder IP enthält "web" |
| `web 192.168.10` | Sowohl "web" ALS AUCH "192.168.10" müssen übereinstimmen |
| `^db-\d+` | Regex: Namen, die mit `db-` gefolgt von Ziffern beginnen |
| *(leer)* | Alle VMs auflisten |

## Roadmap

- [ ] libvirt / KVM Endpoint-Adapter (Verbindungs-URI, Domain-Metadaten, NIC-IPs)
- [ ] Proxmox VE API-Adapter
- [ ] Docker Engine und Swarm Service-Suche
- [ ] Kubernetes Multi-Cluster Pod / Service-Suche (kubeconfig contexts)
- [ ] Einheitliche `Provider`-Schnittstelle für erweiterbare Plattformen
- [ ] Ergebnisse als CSV / JSON exportieren
- [ ] Einfache Zugriffskontrolle (Basic Auth / Token)

## Lizenz

[GPL-3.0](LICENSE)
