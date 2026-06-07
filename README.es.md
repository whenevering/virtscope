# VirtScope

[English](README.md) · [中文](README.zh-CN.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md) · [Русский](README.ru.md)

Búsqueda unificada de recursos en plataformas de virtualización y contenedores.

Busque en múltiples entornos VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes desde una única interfaz web — por nombre de VM, red, IP o cualquier palabra clave.

## Plataformas soportadas

| Tipo | Plataforma | Estado |
| --- | --- | --- |
| VM | VMware vCenter | ✅ Soportado |
| VM | VMware ESXi (directo) | ✅ Soportado |
| VM | KVM / libvirt | 🚧 Planificado |
| VM | Proxmox VE | 🚧 Planificado |
| Contenedor | Docker | 🚧 Planificado |
| Contenedor | Kubernetes | 🚧 Planificado |

## Características

- Búsqueda concurrente multi-endpoint, resultados agregados en una tabla
- Palabras clave separadas por espacio con coincidencia **AND**; cada término soporta **regex**
- Coincidencia tanto por nombre de VM como por direcciones IP guest (vía VMware Tools)
- Interfaz en 8 idiomas integrados (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Timeout por endpoint, TTL de sesión y límite de capacidad para estabilidad a largo plazo
- Sin dependencias externas de frontend — Python de un solo archivo; solo abra el navegador

## Requisitos

- Python 3.10+
- Acceso de red a los objetivos vCenter / ESXi / plataformas futuras

## Instalación

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Configuración

Copie el archivo de ejemplo:

```bash
cp virts-list.ini.example virts-list.ini
```

Añada una `[sección]` por endpoint:

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

> ⚠️ `virts-list.ini` contiene credenciales en texto plano y está excluido por `.gitignore`. **Nunca lo commitee.**

## Uso

```bash
python virtscope.py
```

Escucha en `0.0.0.0:6616` por defecto. Abra `http://127.0.0.1:6616/` en su navegador.

## Ejemplos de palabras clave

| Entrada | Significado |
| --- | --- |
| `web` | Nombre o IP contiene "web" |
| `web 192.168.10` | Ambos "web" Y "192.168.10" deben coincidir |
| `^db-\d+` | Regex: nombres que empiezan con `db-` seguidos de dígitos |
| *(vacío)* | Listar todas las VMs |

## Hoja de ruta

- [ ] Adaptador para libvirt / KVM (URI de conexión, metadatos de dominio, IPs de NIC)
- [ ] Adaptador para API de Proxmox VE
- [ ] Búsqueda de servicios Docker engine y Swarm
- [ ] Búsqueda de Pods / Services multi-cluster de Kubernetes (kubeconfig contexts)
- [ ] Interfaz `Provider` unificada para plataformas conectables
- [ ] Exportar resultados a CSV / JSON
- [ ] Control de acceso básico (Basic Auth / Token)

## Licencia

[MIT](LICENSE)
