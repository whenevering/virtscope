# VirtScope · 云镜

[English](README.md) · **中文** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md) · [Русский](README.ru.md)

跨虚拟化与容器平台的统一资源检索工具。

在同一个 Web 界面中，按名称 / 网络 / IP 等关键字，对多套虚拟化和容器平台做聚合检索，免去登录每个控制台逐个翻找。

## 项目目标

| 类型 | 平台 | 状态 |
| --- | --- | --- |
| 虚拟机 | VMware vCenter | ✅ 已支持 |
| 虚拟机 | VMware ESXi（直连） | ✅ 已支持 |
| 虚拟机 | KVM / libvirt | 🚧 规划中 |
| 虚拟机 | Proxmox VE | 🚧 规划中 |
| 容器 | Docker | 🚧 规划中 |
| 容器 | Kubernetes | 🚧 规划中 |

## 特性

- 多端点并发检索，结果聚合到同一张表
- 关键字支持空格分隔多词 **AND**，每个词均支持 **正则**
- 同时匹配虚拟机名称与 guest IP（VMware Tools 上报的 IP 列表）
- 内置 8 种语言界面（English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский）
- 单端点超时、会话表 TTL 与容量上限，长时间运行稳定
- 零外部前端依赖，单文件 Python 启动；浏览器即用

## 环境要求

- Python 3.10+
- 网络可达目标 vCenter / ESXi / 后续支持的平台

## 安装

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## 配置

复制示例配置：

```bash
cp virts-list.ini.example virts-list.ini
```

按平台分节填入连接信息：

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

> ⚠️ `virts-list.ini` 含明文凭据，已在 `.gitignore` 中排除，**切勿提交到仓库**。

## 启动

```bash
python virtscope.py
```

默认监听 `0.0.0.0:6616`。浏览器打开 `http://127.0.0.1:6616/` 即可使用。

## 关键字示例

| 输入 | 含义 |
| --- | --- |
| `web` | 名称或 IP 中含 "web" |
| `web 192.168.10` | 同时含 "web" 与 "192.168.10"（AND） |
| `^db-\d+` | 按正则匹配（命名前缀为 `db-` 后接数字的虚拟机） |
| 留空 | 列出全部虚拟机 |

## 路线图

- [ ] libvirt / KVM 端点适配（连接串、域元数据、网络接口 IP）
- [ ] Proxmox VE API 适配
- [ ] Docker 引擎与 Swarm 服务检索
- [ ] Kubernetes 多集群 Pod / Service 检索（kubeconfig contexts）
- [ ] 统一抽象层 `Provider` 接口，新增平台时只需实现少量方法
- [ ] 结果导出 CSV / JSON
- [ ] 基本访问控制（Basic Auth / Token）

## License

[MIT](LICENSE)
