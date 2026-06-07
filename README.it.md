# VirtScope

[English](README.md) · [中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · **Italiano** · [Português](README.pt.md) · [Русский](README.ru.md)

Ricerca unificata di risorse su piattaforme di virtualizzazione e container.

Cerca in più ambienti VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes da una singola interfaccia web — per nome VM, rete, IP o qualsiasi parola chiave.

## Piattaforme supportate

| Tipo | Piattaforma | Stato |
| --- | --- | --- |
| VM | VMware vCenter | ✅ Supportato |
| VM | VMware ESXi (diretto) | ✅ Supportato |
| VM | KVM / libvirt | 🚧 Pianificato |
| VM | Proxmox VE | 🚧 Pianificato |
| Container | Docker | 🚧 Pianificato |
| Container | Kubernetes | 🚧 Pianificato |

## Funzionalità

- Ricerca multi-endpoint concorrente, risultati aggregati in un'unica tabella
- Parole chiave separate da spazi con corrispondenza **AND**; ogni termine supporta **regex**
- Corrispondenza per nome VM e indirizzi IP guest (tramite VMware Tools)
- Interfaccia in 8 lingue integrate (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Timeout per endpoint, TTL sessione e limite di capacità per stabilità a lungo termine
- Nessuna dipendenza frontend esterna — Python a file singolo; apri semplicemente il browser

## Requisiti

- Python 3.10+
- Accesso di rete agli obiettivi vCenter / ESXi / piattaforme future

## Installazione

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Configurazione

Copia il file di esempio:

```bash
cp virts-list.ini.example virts-list.ini
```

Aggiungi una `[sezione]` per endpoint:

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

> ⚠️ `virts-list.ini` contiene credenziali in chiaro ed è escluso da `.gitignore`. **Non committarlo mai.**

## Utilizzo

```bash
python virtscope.py
```

Ascolta su `0.0.0.0:6616` per impostazione predefinita. Apri `http://127.0.0.1:6616/` nel browser.

## Esempi di parole chiave

| Input | Significato |
| --- | --- |
| `web` | Nome o IP contiene "web" |
| `web 192.168.10` | Sia "web" CHE "192.168.10" devono corrispondere |
| `^db-\d+` | Regex: nomi che iniziano con `db-` seguiti da cifre |
| *(vuoto)* | Elenca tutte le VM |

## Roadmap

- [ ] Adattatore libvirt / KVM (URI di connessione, metadati dominio, IP NIC)
- [ ] Adattatore API Proxmox VE
- [ ] Ricerca servizi Docker engine e Swarm
- [ ] Ricerca Pod / Service multi-cluster Kubernetes (kubeconfig contexts)
- [ ] Interfaccia `Provider` unificata per piattaforme collegabili
- [ ] Esportazione risultati in CSV / JSON
- [ ] Controllo di accesso di base (Basic Auth / Token)

## Licenza

[MIT](LICENSE)
