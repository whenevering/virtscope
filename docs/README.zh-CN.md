# VirtScope · 云镜

[English](../README.md) · **中文** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md) · [Русский](README.ru.md)

跨虚拟化与容器平台的统一资源检索工具。

在同一个 Web 界面中，按名称 / 网络 / IP 等关键字，对多套虚拟化和容器平台做聚合检索，免去登录每个控制台逐个翻找。

---

## 为什么需要 VirtScope

### 异构基础设施的时代

现代企业的基础设施，很少甘愿栖身于单一的虚拟化平台。VMware vSphere 守护着生产核心，KVM 与 Proxmox 服务于成本敏感的负载，Docker 和 Kubernetes 编排着云原生的脉搏。每一座平台都是一个独立的宇宙——自己的控制台，自己的命名逻辑，自己观察世界的方式。

### 万草寻针

即便架构团队在设计之初便精心梳理业务需求，即便资源命名严格遵循规范，现实依然会用它的复杂性来考验秩序。一家中等规模的企业，往往拥有数千台虚拟机横跨数十个集群；再算上容器，资源条目轻易突破万量级。当事件来临——一次网络异常、一条安全告警、一场容量排查——问题总是惊人地相似：

> *那台叫 `web-prod-03` 的机器在哪里？它属于哪个 vCenter？跑在哪个 ESXi 主机上？IP 是多少？*

答案，往往需要登录三四台控制台，在层层嵌套的文件夹中逐个点击，再与 Excel 表格交叉比对。分钟在流逝，事件在升级。

### 重量级的幻象

OpenStack 与商业云管平台许诺一个统一的管理平面——交付的却是一座复杂的教堂。它们要求专属的数据库、消息队列和身份服务；需要数周的部署和专职团队的运维。而在容器资源的管理上，它们的支持往往只是一层薄薄的 API 封装——能展示 Pod 名称，却难提供更多。

对许多组织而言，建造和运营这样一个平台的代价，已经超过了它本应解决的问题。

### 另一种哲学

VirtScope 选择了一条相反的路：**最好的搜索工具，是那个你五分钟就能部署、然后可以忘记它存在的工具。**

- **单文件，零依赖。** 一个 Python 脚本，无数据库，无构建步骤。运行它，打开浏览器，搜索。
- **天生并发。** 所有配置的端点同时查询。跨十台 vCenter 的搜索，耗时等于最慢的那一台。
- **极致轻量。** 几兆内存，无需守护进程，无需轮换证书。它只是安静地待在角落，回答问题。
- **多平台基因。** VMware 今天，KVM 与 Proxmox 明天，Docker 与 Kubernetes 在望——每新增一个平台，只需实现一个适配器接口。搜索体验始终如一。

### 何时该用 VirtScope

| 场景 | 没有 VirtScope | 有 VirtScope |
| --- | --- | --- |
| 按部分名称定位虚拟机 | 登录每台 vCenter，逐个搜索 | 输入名称，跨所有平台一次呈现 |
| 查找虚拟机所在的 ESXi 主机 | 在 vSphere Client 中层层展开清单树 | 结果表中一眼可见 |
| 通过 IP 地址识别虚拟机 | 查 DHCP 租约，手动调用 VMware Tools | 输入 IP 片段，即时匹配 |
| 事件排查 | 在四台控制台之间反复切换 | 一次搜索，所有平台，五秒以内 |

### 设计信条

1. **简洁是一种特性，而非局限。** 每一行代码都必须证明自己存在的价值。
2. **速度是对使用者的尊重。** 运维人员的时间是神圣的；一个让人等待的搜索工具，已经失败了。
3. **异构是现实，不是问题。** 多平台共存不是需要被消除的混乱，而是需要被拥抱的事实。
4. **工具应当隐于无形。** 最好的界面，是用户从不需要想起它的那个。

---

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

[GPL-3.0](LICENSE)
