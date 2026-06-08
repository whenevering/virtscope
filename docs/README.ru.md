# VirtScope

[English](../README.md) · [中文](README.zh-CN.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) · [Português](README.pt.md) · **Русский**

Единый поиск ресурсов по платформам виртуализации и контейнеров.

Поиск по нескольким средам VMware vCenter / ESXi / KVM / Proxmox / Docker / Kubernetes из одного веб-интерфейса — по имени ВМ, сети, IP или любому ключевому слову.

## Поддерживаемые платформы

| Тип | Платформа | Статус |
| --- | --- | --- |
| ВМ | VMware vCenter | ✅ Поддерживается |
| ВМ | VMware ESXi (напрямую) | ✅ Поддерживается |
| ВМ | KVM / libvirt | 🚧 Планируется |
| ВМ | Proxmox VE | 🚧 Планируется |
| Контейнер | Docker | 🚧 Планируется |
| Контейнер | Kubernetes | 🚧 Планируется |

## Возможности

- Одновременный поиск по нескольким эндпоинтам, агрегированные результаты в одной таблице
- Ключевые слова через пробел с логикой **И**; каждый термин поддерживает **regex**
- Совпадение по имени ВМ и гостевым IP-адресам (через VMware Tools)
- Встроенная поддержка 8 языков (English / 中文 / Español / Français / Deutsch / Italiano / Português / Русский)
- Таймаут на эндпоинт, TTL сессии и ограничение ёмкости для долгосрочной стабильности
- Никаких внешних фронтенд-зависимостей — Python в одном файле; просто откройте браузер

## Требования

- Python 3.10+
- Сетевой доступ к целевым vCenter / ESXi / будущим платформам

## Установка

```bash
git clone https://github.com/whenevering/virtscope.git
cd virtscope
pip install -r requirements.txt
```

## Конфигурация

Скопируйте пример конфигурации:

```bash
cp virts-list.ini.example virts-list.ini
```

Добавьте по одной `[секции]` на каждый эндпоинт:

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

> ⚠️ `virts-list.ini` содержит учётные данные в открытом виде и исключён из `.gitignore`. **Никогда не коммитьте его.**

## Использование

```bash
python virtscope.py
```

Слушает на `0.0.0.0:6616` по умолчанию. Откройте `http://127.0.0.1:6616/` в браузере.

## Примеры ключевых слов

| Ввод | Значение |
| --- | --- |
| `web` | Имя или IP содержит "web" |
| `web 192.168.10` | И "web" И "192.168.10" должны совпадать |
| `^db-\d+` | Regex: имена, начинающиеся с `db-` и followed by цифры |
| *(пусто)* | Показать все ВМ |

## Дорожная карта

- [ ] Адаптер libvirt / KVM (URI подключения, метаданные домена, IP NIC)
- [ ] Адаптер API Proxmox VE
- [ ] Поиск сервисов Docker engine и Swarm
- [ ] Поиск Pod / Service мультикластеров Kubernetes (kubeconfig contexts)
- [ ] Единый интерфейс `Provider` для подключаемых платформ
- [ ] Экспорт результатов в CSV / JSON
- [ ] Базовый контроль доступа (Basic Auth / Token)

## Лицензия

[GPL-3.0](LICENSE)
