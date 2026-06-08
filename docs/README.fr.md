# VirtScope

[English](../README.md) · [中文](README.zh-CN.md) · [Español](README.es.md) · **Français** · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md) · [Русский](README.ru.md)

Recherche unifiée de ressources sur les plateformes de virtualisation et de conteneurs.

Recherchez dans plusieurs environnements VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes depuis une seule interface web — par nom de VM, réseau, IP ou mot-clé.

## Plateformes prises en charge

| Type | Plateforme | Statut |
| --- | --- | --- |
| VM | VMware vCenter | ✅ Pris en charge |
| VM | VMware ESXi (direct) | ✅ Pris en charge |
| VM | KVM / libvirt | 🚧 Planifié |
| VM | Proxmox VE | 🚧 Planifié |
| Conteneur | Docker | 🚧 Planifié |
| Conteneur | Kubernetes | 🚧 Planifié |

## Fonctionnalités

- Recherche multi-endpoints concurrente, résultats agrégés dans un seul tableau
- Mots-clés séparés par espaces avec correspondance **AND** ; chaque terme supporte les **regex**
- Correspondance par nom de VM et adresses IP guest (via VMware Tools)
- Interface en 8 langues intégrées (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Timeout par endpoint, TTL de session et limite de capacité pour une stabilité à long terme
- Aucune dépendance frontend externe — Python fichier unique ; ouvrez simplement le navigateur

## Prérequis

- Python 3.10+
- Accès réseau aux cibles vCenter / ESXi / futures plateformes

## Installation

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Configuration

Copiez le fichier d'exemple :

```bash
cp virts-list.ini.example virts-list.ini
```

Ajoutez une `[section]` par endpoint :

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

> ⚠️ `virts-list.ini` contient des identifiants en clair et est exclu par `.gitignore`. **Ne le commitez jamais.**

## Utilisation

```bash
python virtscope.py
```

Écoute sur `0.0.0.0:6616` par défaut. Ouvrez `http://127.0.0.1:6616/` dans votre navigateur.

## Exemples de mots-clés

| Entrée | Signification |
| --- | --- |
| `web` | Nom ou IP contient "web" |
| `web 192.168.10` | "web" ET "192.168.10" doivent correspondre |
| `^db-\d+` | Regex : noms commençant par `db-` suivis de chiffres |
| *(vide)* | Lister toutes les VMs |

## Feuille de route

- [ ] Adaptateur libvirt / KVM (URI de connexion, métadonnées de domaine, IPs NIC)
- [ ] Adaptateur API Proxmox VE
- [ ] Recherche de services Docker engine et Swarm
- [ ] Recherche de Pods / Services multi-clusters Kubernetes (kubeconfig contexts)
- [ ] Interface `Provider` unifiée pour plateformes enfichables
- [ ] Export des résultats en CSV / JSON
- [ ] Contrôle d'accès basique (Basic Auth / Token)

## Licence

[GPL-3.0](LICENSE)
