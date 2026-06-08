# VirtScope

[English](../README.md) · [中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · **Português** · [Русский](README.ru.md)

Pesquisa unificada de recursos em plataformas de virtualização e containers.

Pesquise em múltiplos ambientes VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes a partir de uma única interface web — por nome de VM, rede, IP ou qualquer palavra-chave.

## Plataformas suportadas

| Tipo | Plataforma | Estado |
| --- | --- | --- |
| VM | VMware vCenter | ✅ Suportado |
| VM | VMware ESXi (direto) | ✅ Suportado |
| VM | KVM / libvirt | 🚧 Planeado |
| VM | Proxmox VE | 🚧 Planeado |
| Container | Docker | 🚧 Planeado |
| Container | Kubernetes | 🚧 Planeado |

## Funcionalidades

- Pesquisa concorrente multi-endpoint, resultados agregados numa única tabela
- Palavras-chave separadas por espaço com correspondência **AND**; cada termo suporta **regex**
- Correspondência por nome de VM e endereços IP guest (via VMware Tools)
- Interface em 8 idiomas integrados (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Timeout por endpoint, TTL de sessão e limite de capacidade para estabilidade a longo prazo
- Sem dependências externas de frontend — Python de ficheiro único; basta abrir o navegador

## Requisitos

- Python 3.10+
- Acesso de rede aos alvos vCenter / ESXi / plataformas futuras

## Instalação

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Configuração

Copie o ficheiro de exemplo:

```bash
cp virts-list.ini.example virts-list.ini
```

Adicione uma `[secção]` por endpoint:

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

> ⚠️ `virts-list.ini` contém credenciais em texto simples e é excluído pelo `.gitignore`. **Nunca o commite.**

## Utilização

```bash
python virtscope.py
```

Escuta em `0.0.0.0:6616` por defeito. Abra `http://127.0.0.1:6616/` no seu navegador.

## Exemplos de palavras-chave

| Entrada | Significado |
| --- | --- |
| `web` | Nome ou IP contém "web" |
| `web 192.168.10` | Tanto "web" QUANTO "192.168.10" devem corresponder |
| `^db-\d+` | Regex: nomes que começam com `db-` seguidos de dígitos |
| *(vazio)* | Listar todas as VMs |

## Roadmap

- [ ] Adaptador libvirt / KVM (URI de conexão, metadados de domínio, IPs NIC)
- [ ] Adaptador API Proxmox VE
- [ ] Pesquisa de serviços Docker engine e Swarm
- [ ] Pesquisa de Pods / Services multi-cluster Kubernetes (kubeconfig contexts)
- [ ] Interface `Provider` unificada para plataformas conectáveis
- [ ] Exportação de resultados para CSV / JSON
- [ ] Controlo de acesso básico (Basic Auth / Token)

## Licença

[GPL-3.0](LICENSE)
