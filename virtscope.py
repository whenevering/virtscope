import configparser
import html
import re
import ssl
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim, vmodl


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "virts-list.ini"
HISTORY_FILE = BASE_DIR / "history.log"
PORT = 6616
PAGE_SIZE = 30
DEFAULT_LANG = "en"

# 单个端点检索超时（秒）
ENDPOINT_TIMEOUT = 30
# 端点并发上限
MAX_ENDPOINT_WORKERS = 16
# Session 表上限及过期时间
MAX_SESSIONS = 256
SESSION_TTL_SECONDS = 3600

HISTORY_LOCK = threading.Lock()
SESSION_LOCK = threading.Lock()
SESSION_HISTORIES: "OrderedDict[str, list[str]]" = OrderedDict()
SESSION_RESULTS: "OrderedDict[str, tuple[str, list, list[str]]]" = OrderedDict()
SESSION_TIMESTAMPS: dict[str, float] = {}


# ---------------------------------------------------------------------------
# i18n - 多语言翻译
# ---------------------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Search",
        "placeholder": "VM name, IP, or keyword; space = AND each term; regex allowed; blank = list all",
        "hint": "Examples: <code>web 192.168.10</code> AND match &bull; regex: <code>^db-\\d+</code>",
        "found_records": "Found {n} matching record(s).",
        "no_records": "No matching virtual machines found.",
        "status_title": "Status / Errors",
        "col_vm": "VM Name",
        "col_ip": "IP Addresses",
        "col_vc": "vCenter",
        "col_esxi": "ESXi Host",
        "col_pool": "Resource Pool / Cluster",
        "page_xof_y": "Page {p} / {total}:",
        "lang_label": "Language",
        "cfg_missing": "Configuration file not found: {path}",
        "cfg_section_missing": "Section [{section}] is missing host, username or password.",
        "cfg_empty": "No usable endpoints in configuration: {path}",
        "ep_fail": "[{name}] {host} failed. Error type: {etype}; Detail: {reason}.",
        "ep_timeout": "[{name}] {host} timed out (>{timeout}s).",
        "ep_error": "[{name}] {host} exception: {etype}: {reason}",
        "log_search_start": "---\nSearching: {kw} from {ip}",
        "log_no_result": "No matching records found.",
        "log_found": "Found {n} matching record(s).",
        "log_polling": "Polling {n} endpoint(s) (threads={w}, timeout={t}s)",
        "log_endpoint_ok": "Completed {name} ({host}): {count} hit(s)",
    },
    "es": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Buscar",
        "placeholder": "Nombre, IP o palabra clave; espacio = AND; regex permitido; vacío = listar todo",
        "hint": "Ejemplos: <code>web 192.168.10</code> AND &bull; regex: <code>^db-\\d+</code>",
        "found_records": "Se encontraron {n} registro(s).",
        "no_records": "No se encontraron máquinas virtuales coincidentes.",
        "status_title": "Estado / Errores",
        "col_vm": "Nombre VM",
        "col_ip": "Direcciones IP",
        "col_vc": "vCenter",
        "col_esxi": "Host ESXi",
        "col_pool": "Pool / Clúster",
        "page_xof_y": "Página {p} / {total}:",
        "lang_label": "Idioma",
        "cfg_missing": "Archivo de configuración no encontrado: {path}",
        "cfg_section_missing": "A la sección [{section}] le falta host, usuario o contraseña.",
        "cfg_empty": "Sin endpoints en configuración: {path}",
        "ep_fail": "[{name}] {host} falló. Tipo: {etype}; Detalle: {reason}.",
        "ep_timeout": "[{name}] {host} excedió el tiempo (>{timeout}s).",
        "ep_error": "[{name}] {host} excepción: {etype}: {reason}",
        "log_search_start": "---\nBuscando: {kw} desde {ip}",
        "log_no_result": "Sin registros coincidentes.",
        "log_found": "Se encontraron {n} registro(s).",
        "log_polling": "Consultando {n} endpoint(s) (hilos={w}, timeout={t}s)",
        "log_endpoint_ok": "Completado {name} ({host}): {count} acierto(s)",
    },
    "fr": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Rechercher",
        "placeholder": "Nom, IP ou mot-clé ; espace = ET ; regex autorisé ; vide = tout lister",
        "hint": "Exemples : <code>web 192.168.10</code> ET &bull; regex : <code>^db-\\d+</code>",
        "found_records": "{n} enregistrement(s) trouvé(s).",
        "no_records": "Aucune machine virtuelle correspondante.",
        "status_title": "Statut / Erreurs",
        "col_vm": "Nom VM",
        "col_ip": "Adresses IP",
        "col_vc": "vCenter",
        "col_esxi": "Hôte ESXi",
        "col_pool": "Pool / Cluster",
        "page_xof_y": "Page {p} / {total} :",
        "lang_label": "Langue",
        "cfg_missing": "Fichier de configuration introuvable : {path}",
        "cfg_section_missing": "Section [{section}] manque host, utilisateur ou mot de passe.",
        "cfg_empty": "Aucun endpoint utilisable : {path}",
        "ep_fail": "[{name}] {host} a échoué. Type : {etype} ; Détail : {reason}.",
        "ep_timeout": "[{name}] {host} a dépassé le délai (>{timeout}s).",
        "ep_error": "[{name}] {host} exception : {etype} : {reason}",
        "log_search_start": "---\nRecherche : {kw} depuis {ip}",
        "log_no_result": "Aucun enregistrement correspondant.",
        "log_found": "{n} enregistrement(s) trouvé(s).",
        "log_polling": "Interrogation de {n} endpoint(s) (threads={w}, timeout={t}s)",
        "log_endpoint_ok": "Terminé {name} ({host}) : {count} résultat(s)",
    },
    "de": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Suchen",
        "placeholder": "Name, IP oder Stichwort; Leerzeichen = UND; Regex erlaubt; leer = alles auflisten",
        "hint": "Beispiele: <code>web 192.168.10</code> UND &bull; regex: <code>^db-\\d+</code>",
        "found_records": "{n} Datensatz/Datensätze gefunden.",
        "no_records": "Keine passenden virtuellen Maschinen gefunden.",
        "status_title": "Status / Fehler",
        "col_vm": "VM-Name",
        "col_ip": "IP-Adressen",
        "col_vc": "vCenter",
        "col_esxi": "ESXi-Host",
        "col_pool": "Ressourcen-Pool / Cluster",
        "page_xof_y": "Seite {p} / {total}:",
        "lang_label": "Sprache",
        "cfg_missing": "Konfigurationsdatei nicht gefunden: {path}",
        "cfg_section_missing": "Abschnitt [{section}] fehlt Host, Benutzer oder Passwort.",
        "cfg_empty": "Keine verwendbaren Endpunkte: {path}",
        "ep_fail": "[{name}] {host} fehlgeschlagen. Typ: {etype}; Detail: {reason}.",
        "ep_timeout": "[{name}] {host} Zeitüberschreitung (>{timeout}s).",
        "ep_error": "[{name}] {host} Ausnahme: {etype}: {reason}",
        "log_search_start": "---\nSuche: {kw} von {ip}",
        "log_no_result": "Keine passenden Datensätze.",
        "log_found": "{n} Datensatz/Datensätze gefunden.",
        "log_polling": "Abfrage {n} Endpunkt(e) (Threads={w}, Timeout={t}s)",
        "log_endpoint_ok": "Abgeschlossen {name} ({host}): {count} Treffer",
    },
    "it": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Cerca",
        "placeholder": "Nome, IP o parola chiave; spazio = E; regex ammesso; vuoto = elenca tutto",
        "hint": "Esempi: <code>web 192.168.10</code> E &bull; regex: <code>^db-\\d+</code>",
        "found_records": "Trovati {n} record.",
        "no_records": "Nessuna macchina virtuale corrispondente.",
        "status_title": "Stato / Errori",
        "col_vm": "Nome VM",
        "col_ip": "Indirizzi IP",
        "col_vc": "vCenter",
        "col_esxi": "Host ESXi",
        "col_pool": "Pool / Cluster",
        "page_xof_y": "Pagina {p} / {total}:",
        "lang_label": "Lingua",
        "cfg_missing": "File di configurazione non trovato: {path}",
        "cfg_section_missing": "Sezione [{section}] manca host, utente o password.",
        "cfg_empty": "Nessun endpoint utilizzabile: {path}",
        "ep_fail": "[{name}] {host} non riuscito. Tipo: {etype}; Dettaglio: {reason}.",
        "ep_timeout": "[{name}] {host} timeout (>{timeout}s).",
        "ep_error": "[{name}] {host} eccezione: {etype}: {reason}",
        "log_search_start": "---\nRicerca: {kw} da {ip}",
        "log_no_result": "Nessun record corrispondente.",
        "log_found": "Trovati {n} record.",
        "log_polling": "Interrogazione {n} endpoint (thread={w}, timeout={t}s)",
        "log_endpoint_ok": "Completato {name} ({host}): {count} risultato/i",
    },
    "pt": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Pesquisar",
        "placeholder": "Nome, IP ou palavra-chave; espaço = E; regex permitido; vazio = listar tudo",
        "hint": "Exemplos: <code>web 192.168.10</code> E &bull; regex: <code>^db-\\d+</code>",
        "found_records": "{n} registro(s) encontrado(s).",
        "no_records": "Nenhuma máquina virtual correspondente.",
        "status_title": "Estado / Erros",
        "col_vm": "Nome da VM",
        "col_ip": "Endereços IP",
        "col_vc": "vCenter",
        "col_esxi": "Host ESXi",
        "col_pool": "Pool / Cluster",
        "page_xof_y": "Página {p} / {total}:",
        "lang_label": "Idioma",
        "cfg_missing": "Ficheiro de configuração não encontrado: {path}",
        "cfg_section_missing": "Secção [{section}] falta host, utilizador ou palavra-passe.",
        "cfg_empty": "Sem endpoints utilizáveis: {path}",
        "ep_fail": "[{name}] {host} falhou. Tipo: {etype}; Detalhe: {reason}.",
        "ep_timeout": "[{name}] {host} excedeu o tempo (>{timeout}s).",
        "ep_error": "[{name}] {host} excepção: {etype}: {reason}",
        "log_search_start": "---\nPesquisa: {kw} de {ip}",
        "log_no_result": "Sem registos correspondentes.",
        "log_found": "{n} registro(s) encontrado(s).",
        "log_polling": "A consultar {n} endpoint(s) (threads={w}, timeout={t}s)",
        "log_endpoint_ok": "Concluído {name} ({host}): {count} resultado(s)",
    },
    "ru": {
        "title": "VirtScope",
        "app_name": "VirtScope",
        "search_btn": "Поиск",
        "placeholder": "Имя, IP или ключевое слово; пробел = И; regex допустим; пусто = все",
        "hint": "Примеры: <code>web 192.168.10</code> И &bull; regex: <code>^db-\\d+</code>",
        "found_records": "Найдено {n} запись(ей).",
        "no_records": "Совпадающих виртуальных машин не найдено.",
        "status_title": "Статус / Ошибки",
        "col_vm": "Имя ВМ",
        "col_ip": "IP-адреса",
        "col_vc": "vCenter",
        "col_esxi": "Хост ESXi",
        "col_pool": "Пул / Кластер",
        "page_xof_y": "Страница {p} / {total}:",
        "lang_label": "Язык",
        "cfg_missing": "Файл конфигурации не найден: {path}",
        "cfg_section_missing": "В секции [{section}] отсутствует host, username или password.",
        "cfg_empty": "Нет доступных эндпоинтов: {path}",
        "ep_fail": "[{name}] {host} ошибка. Тип: {etype}; Подробности: {reason}.",
        "ep_timeout": "[{name}] {host} превышен таймаут (>{timeout}s).",
        "ep_error": "[{name}] {host} исключение: {etype}: {reason}",
        "log_search_start": "---\nПоиск: {kw} с {ip}",
        "log_no_result": "Совпадающих записей не найдено.",
        "log_found": "Найдено {n} запись(ей).",
        "log_polling": "Опрос {n} эндпоинт(ов) (потоки={w}, таймаут={t}s)",
        "log_endpoint_ok": "Завершено {name} ({host}): {count} совпадение(ий)",
    },
    "zh-CN": {
        "title": "VirtScope - 云镜",
        "app_name": "VirtScope - 云镜",
        "search_btn": "搜索",
        "placeholder": "支持名称或 IP 关键字；空格分隔多词为 AND；每个词可写正则；留空搜索全部",
        "hint": "示例：<code>web 192.168.10</code> 表示同时包含 web 与 192.168.10；正则示例：<code>^db-\\d+</code>",
        "found_records": "找到 {n} 条匹配记录。",
        "no_records": "没有找到匹配的虚拟机记录。",
        "status_title": "状态 / 错误信息",
        "col_vm": "虚拟机完整名称",
        "col_ip": "IP 地址",
        "col_vc": "所在 vCenter",
        "col_esxi": "所在 ESXi 主机",
        "col_pool": "资源池 / 集群路径",
        "page_xof_y": "第 {p} / {total} 页：",
        "lang_label": "语言",
        "cfg_missing": "未找到配置文件：{path}",
        "cfg_section_missing": "配置节 [{section}] 缺少 host、username 或 password。",
        "cfg_empty": "配置文件中没有可用的主机配置：{path}",
        "ep_fail": "[{name}] {host} 检索失败。错误类型：{etype}；详细原因：{reason}；请检查主机地址、网络连通性、端口、用户名密码、账号权限及证书/协议兼容性。",
        "ep_timeout": "[{name}] {host} 检索超时（>{timeout}s），已放弃。",
        "ep_error": "[{name}] {host} 异常：{etype}: {reason}",
        "log_search_start": "---\n开始搜索：{kw}，客户端IP：{ip}",
        "log_no_result": "没有找到匹配的虚拟机记录。",
        "log_found": "找到 {n} 条匹配记录。",
        "log_polling": "并发检索 {n} 个端点（线程数={w}，单端点超时={t}s）",
        "log_endpoint_ok": "完成 {name} ({host})：命中 {count} 条",
    },
}

LANGUAGES = [
    ("en", "English"),
    ("es", "Español"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("ru", "Русский"),
    ("zh-CN", "中文"),
]


def t(lang: str, key: str, **kwargs: object) -> str:
    """Look up a translated string and optionally format with kwargs."""
    value = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS[DEFAULT_LANG].get(key, key)
    return value.format(**kwargs) if kwargs else value


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class Endpoint:
    name: str
    host: str
    username: str
    password: str
    port: int = 443


@dataclass
class VmRecord:
    vcenter: str
    esxi_host: str
    resource_path: str
    vm_name: str
    ip_addresses: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 关键字匹配
# ---------------------------------------------------------------------------


class KeywordMatcher:
    """按空格切分关键字，每个词都需在 VM 名称或任一 IP 中命中（AND）。

    每个词优先按不区分大小写的正则解析；编译失败则回退到普通子串匹配。
    空字符串视作匹配全部。
    """

    def __init__(self, keyword: str) -> None:
        self.terms: list[tuple[str, object]] = []
        self.empty = not keyword.strip()
        if self.empty:
            return
        for part in keyword.split():
            if not part:
                continue
            try:
                self.terms.append(("regex", re.compile(part, re.IGNORECASE)))
            except re.error:
                self.terms.append(("sub", part.lower()))

    def match(self, name: str, ips: list[str]) -> bool:
        if self.empty:
            return True
        haystack = [name] + ips
        haystack_lower = [h.lower() for h in haystack]
        for kind, term in self.terms:
            if kind == "regex":
                if not any(term.search(h) for h in haystack):
                    return False
            else:
                if not any(term in h for h in haystack_lower):
                    return False
        return True


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------


def load_endpoints(lang: str = DEFAULT_LANG) -> list[Endpoint]:
    parser = configparser.ConfigParser()
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(t(lang, "cfg_missing", path=CONFIG_FILE))

    parser.read(CONFIG_FILE, encoding="utf-8")
    endpoints: list[Endpoint] = []

    for section in parser.sections():
        host = parser.get(section, "host", fallback="").strip()
        username = parser.get(section, "username", fallback="").strip()
        password = parser.get(section, "password", fallback="").strip()
        port = parser.getint(section, "port", fallback=443)

        if not host or not username or not password:
            raise ValueError(t(lang, "cfg_section_missing", section=section))

        endpoints.append(Endpoint(section, host, username, password, port))

    if not endpoints:
        raise ValueError(t(lang, "cfg_empty", path=CONFIG_FILE))

    return endpoints


def ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


# ---------------------------------------------------------------------------
# PropertyCollector 批量取属性
# ---------------------------------------------------------------------------


def collect_properties(content, view_ref, obj_type, path_set):
    """从 ContainerView 中一次性获取所有 obj_type 对象的指定属性。

    返回 {ManagedObject: {属性名: 值}}。
    """
    collector = content.propertyCollector
    traversal = vmodl.query.PropertyCollector.TraversalSpec(
        name="traverseEntities",
        path="view",
        skip=False,
        type=type(view_ref),
    )
    obj_spec = vmodl.query.PropertyCollector.ObjectSpec(
        obj=view_ref, skip=True, selectSet=[traversal]
    )
    prop_spec = vmodl.query.PropertyCollector.PropertySpec(
        type=obj_type, all=False, pathSet=list(path_set)
    )
    filter_spec = vmodl.query.PropertyCollector.FilterSpec(
        objectSet=[obj_spec], propSet=[prop_spec]
    )
    options = vmodl.query.PropertyCollector.RetrieveOptions()

    out: dict = {}
    result = collector.RetrievePropertiesEx([filter_spec], options)
    while result is not None:
        for obj in result.objects or []:
            props: dict = {}
            for prop in obj.propSet or []:
                props[prop.name] = prop.val
            out[obj.obj] = props
        token = getattr(result, "token", None)
        if not token:
            break
        result = collector.ContinueRetrievePropertiesEx(token)
    return out


def walk_parent_names(ref, entity_map: dict) -> list[str]:
    parts: list[str] = []
    seen: set = set()
    cur = ref
    while cur is not None and cur not in seen:
        seen.add(cur)
        info = entity_map.get(cur)
        if info is None:
            break
        name = info.get("name")
        if name:
            parts.append(name)
        cur = info.get("parent")
    parts.reverse()
    return parts


def format_resource_path(parts: list[str], is_vcenter: bool) -> str:
    if not parts:
        return "N/A"
    trim_count = 1 if is_vcenter else 3
    trimmed = parts[trim_count:] if len(parts) > trim_count else parts[-1:]
    return " - ".join(trimmed) if trimmed else "N/A"


def endpoint_is_vcenter(content) -> bool:
    about = getattr(content, "about", None)
    api_type = getattr(about, "apiType", "") if about else ""
    return api_type.lower() == "virtualcenter"


def collect_vm_ips(props: dict) -> list[str]:
    ips: list[str] = []
    primary = props.get("guest.ipAddress")
    if primary:
        ips.append(primary)
    nets = props.get("guest.net")
    if nets:
        for nic in nets:
            for ip in (getattr(nic, "ipAddress", None) or []):
                if ip and ip not in ips:
                    ips.append(ip)
    return ips


# ---------------------------------------------------------------------------
# 端点检索
# ---------------------------------------------------------------------------


def _smart_connect(endpoint: Endpoint):
    base_kwargs = dict(
        host=endpoint.host,
        user=endpoint.username,
        pwd=endpoint.password,
        port=endpoint.port,
        sslContext=ssl_context(),
    )
    try:
        return SmartConnect(httpConnectionTimeout=ENDPOINT_TIMEOUT, **base_kwargs)
    except TypeError:
        return SmartConnect(**base_kwargs)


def search_endpoint(endpoint: Endpoint, matcher: KeywordMatcher, lang: str = DEFAULT_LANG) -> tuple[list[VmRecord], list[str]]:
    errors: list[str] = []
    si = None
    try:
        si = _smart_connect(endpoint)

        content = si.RetrieveContent()
        is_vcenter = endpoint_is_vcenter(content)
        vcenter = endpoint.host if is_vcenter else "N/A"

        vm_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        all_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.ManagedEntity], True
        )

        try:
            vm_props_map = collect_properties(
                content,
                vm_view,
                vim.VirtualMachine,
                ["name", "runtime.host", "resourcePool", "guest.ipAddress", "guest.net"],
            )

            entity_map: dict = {}
            for entity_type in (
                vim.HostSystem,
                vim.ResourcePool,
                vim.ClusterComputeResource,
                vim.ComputeResource,
                vim.Folder,
                vim.Datacenter,
            ):
                entity_map.update(
                    collect_properties(content, all_view, entity_type, ["name", "parent"])
                )
        finally:
            for view in (vm_view, all_view):
                try:
                    view.Destroy()
                except Exception:
                    pass

        records: list[VmRecord] = []
        for _vm_ref, props in vm_props_map.items():
            name = props.get("name") or ""
            ips = collect_vm_ips(props)
            if not matcher.match(name, ips):
                continue

            host_ref = props.get("runtime.host")
            esxi_host = "N/A"
            if host_ref is not None:
                esxi_host = (entity_map.get(host_ref) or {}).get("name") or "N/A"

            rp_ref = props.get("resourcePool")
            if rp_ref is not None:
                resource_path = format_resource_path(
                    walk_parent_names(rp_ref, entity_map), is_vcenter
                )
            elif host_ref is not None:
                host_info = entity_map.get(host_ref) or {}
                parent = host_info.get("parent")
                resource_path = (
                    format_resource_path(walk_parent_names(parent, entity_map), is_vcenter)
                    if parent is not None
                    else "N/A"
                )
            else:
                resource_path = "N/A"

            records.append(
                VmRecord(
                    vcenter=vcenter,
                    esxi_host=esxi_host,
                    resource_path=resource_path,
                    vm_name=name,
                    ip_addresses=ips,
                )
            )
        return records, errors
    except Exception as exc:
        errors.append(t(lang, "ep_fail", name=endpoint.name, host=endpoint.host,
                        etype=type(exc).__name__, reason=exc))
        return [], errors
    finally:
        if si is not None:
            try:
                Disconnect(si)
            except Exception:
                pass


def search_all(keyword: str, client_ip: str, lang: str = DEFAULT_LANG) -> tuple[list[VmRecord], list[str], list[str]]:
    matcher = KeywordMatcher(keyword)
    records: list[VmRecord] = []
    errors: list[str] = []
    events: list[str] = ["-" * 80, t(lang, "log_search_start", kw=keyword or t(lang, "no_records"), ip=client_ip)]

    try:
        endpoints = load_endpoints(lang)
    except Exception as exc:
        errors.append(str(exc))
        events.append(t(lang, "log_no_result"))
        events.extend(errors)
        append_history(events)
        return [], errors, events

    workers = max(1, min(MAX_ENDPOINT_WORKERS, len(endpoints)))
    events.append(t(lang, "log_polling", n=len(endpoints), w=workers, t=ENDPOINT_TIMEOUT))

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="vmq") as executor:
        future_map = {
            executor.submit(search_endpoint, endpoint, matcher, lang): endpoint
            for endpoint in endpoints
        }
        for future in as_completed(future_map):
            endpoint = future_map[future]
            try:
                ep_records, ep_errors = future.result(timeout=ENDPOINT_TIMEOUT)
            except FuturesTimeoutError:
                errors.append(t(lang, "ep_timeout", name=endpoint.name, host=endpoint.host, timeout=ENDPOINT_TIMEOUT))
                continue
            except Exception as exc:
                errors.append(t(lang, "ep_error", name=endpoint.name, host=endpoint.host,
                                etype=type(exc).__name__, reason=exc))
                continue

            records.extend(ep_records)
            errors.extend(ep_errors)
            events.append(t(lang, "log_endpoint_ok", name=endpoint.name, host=endpoint.host, count=len(ep_records)))

    if records:
        events.append(t(lang, "log_found", n=len(records)))
        events.extend(
            f"VC:{r.vcenter}-ESXi:{r.esxi_host}-VM:{r.vm_name}" for r in records
        )
    else:
        events.append(t(lang, "log_no_result"))

    events.extend(errors)
    append_history(events)
    return records, errors, events


# ---------------------------------------------------------------------------
# 历史日志 / Session
# ---------------------------------------------------------------------------


def append_history(lines: list[str]) -> None:
    if not lines:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = "\n".join(f"[{timestamp}] {line}" for line in lines) + "\n"
    with HISTORY_LOCK:
        with HISTORY_FILE.open("a", encoding="utf-8") as file:
            file.write(text)


def _prune_sessions_locked() -> None:
    """调用方必须已持有 SESSION_LOCK。按 TTL 清理过期项，再按容量裁掉最旧的。"""
    now = time.time()
    expired = [
        sid for sid, ts in SESSION_TIMESTAMPS.items() if now - ts > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        SESSION_HISTORIES.pop(sid, None)
        SESSION_RESULTS.pop(sid, None)
        SESSION_TIMESTAMPS.pop(sid, None)
    while len(SESSION_HISTORIES) > MAX_SESSIONS:
        sid, _ = SESSION_HISTORIES.popitem(last=False)
        SESSION_RESULTS.pop(sid, None)
        SESSION_TIMESTAMPS.pop(sid, None)
    while len(SESSION_RESULTS) > MAX_SESSIONS:
        sid, _ = SESSION_RESULTS.popitem(last=False)
        SESSION_TIMESTAMPS.pop(sid, None)


def _touch_session_locked(session_id: str) -> None:
    SESSION_TIMESTAMPS[session_id] = time.time()
    if session_id in SESSION_HISTORIES:
        SESSION_HISTORIES.move_to_end(session_id)
    if session_id in SESSION_RESULTS:
        SESSION_RESULTS.move_to_end(session_id)


def append_session_history(session_id: str, lines: list[str]) -> None:
    if not lines:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamped = [f"[{timestamp}] {line}" for line in lines]
    with SESSION_LOCK:
        SESSION_HISTORIES.setdefault(session_id, []).extend(stamped)
        _touch_session_locked(session_id)
        _prune_sessions_locked()


def store_session_results(
    session_id: str, payload: tuple[str, list[VmRecord], list[str]]
) -> None:
    with SESSION_LOCK:
        SESSION_RESULTS[session_id] = payload
        _touch_session_locked(session_id)
        _prune_sessions_locked()


def get_session_results(session_id: str) -> tuple[str, list[VmRecord], list[str]]:
    with SESSION_LOCK:
        if session_id in SESSION_RESULTS:
            _touch_session_locked(session_id)
            return SESSION_RESULTS[session_id]
        return ("", [], [])


def read_session_history(session_id: str) -> str:
    with SESSION_LOCK:
        if session_id in SESSION_HISTORIES:
            _touch_session_locked(session_id)
            return "\n".join(SESSION_HISTORIES[session_id])
        return ""


def read_history() -> str:
    if not HISTORY_FILE.exists():
        return ""
    with HISTORY_LOCK:
        return HISTORY_FILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------


def render_page(
    keyword: str = "",
    records: list[VmRecord] | None = None,
    errors: list[str] | None = None,
    session_history: str = "",
    page_number: int = 1,
    searched: bool = False,
    lang: str = DEFAULT_LANG,
) -> bytes:
    records = records or []
    errors = errors or []
    page_number = max(1, page_number)
    total_records = len(records)
    total_pages = max(1, (total_records + PAGE_SIZE - 1) // PAGE_SIZE)
    page_number = min(page_number, total_pages)
    page_records = records[(page_number - 1) * PAGE_SIZE:page_number * PAGE_SIZE]
    escaped_keyword = html.escape(keyword, quote=True)

    if searched and total_records:
        status_html = f'<p class="ok">{t(lang, "found_records", n=total_records)}</p>'
    elif searched:
        status_html = f'<p class="empty">{t(lang, "no_records")}</p>'
    else:
        status_html = ""

    error_html = "".join(f"<li>{html.escape(error)}</li>" for error in errors)
    if error_html:
        error_html = f'<ul class="errors">{error_html}</ul>'

    history_html = html.escape(session_history)
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(record.vm_name)}</td>"
        f"<td>{html.escape(', '.join(record.ip_addresses))}</td>"
        f"<td>{html.escape(record.vcenter)}</td>"
        f"<td>{html.escape(record.esxi_host)}</td>"
        f"<td>{html.escape(record.resource_path)}</td>"
        "</tr>"
        for record in page_records
    )

    # 语言选择器
    lang_options = "".join(
        f'<option value="{code}"{" selected" if code == lang else ""}>{label}</option>'
        for code, label in LANGUAGES
    )
    lang_switcher = (
        '<form method="post" action="/lang" style="display:inline">'
        f'<label>{t(lang, "lang_label")}: '
        f'<select name="lang" onchange="this.form.submit()">'
        f'{lang_options}'
        f'</select></label></form>'
    )

    table_html = ""
    if searched:
        pagination_html = ""
        if total_records > PAGE_SIZE:
            links = []
            for number in range(1, total_pages + 1):
                if number == page_number:
                    links.append(f'<span class="current-page">{number}</span>')
                else:
                    links.append(f'<a href="/?page={number}">{number}</a>')
            pagination_html = (
                f'<div class="pagination">'
                f'{t(lang, "page_xof_y", p=page_number, total=total_pages)}'
                f'{" ".join(links)}</div>'
            )

        table_html = f"""
        <table id="result-table">
            <colgroup>
                <col style="width: 240px;">
                <col style="width: 18ch;">
                <col style="width: 18ch;">
                <col style="width: 18ch;">
                <col>
            </colgroup>
            <thead>
                <tr>
                    <th>{t(lang, "col_vm")}<span class="resize-handle"></span></th>
                    <th>{t(lang, "col_ip")}<span class="resize-handle"></span></th>
                    <th>{t(lang, "col_vc")}<span class="resize-handle"></span></th>
                    <th>{t(lang, "col_esxi")}<span class="resize-handle"></span></th>
                    <th>{t(lang, "col_pool")}<span class="resize-handle"></span></th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        {pagination_html}
        """

    page = f"""<!doctype html>
<html lang="{html.escape(lang, quote=True)}">
<head>
<meta charset="utf-8">
<title>{t(lang, "title")}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    background: #f4f5f7;
    color: #1f2933;
    font-family: "Microsoft YaHei", Arial, sans-serif;
    font-size: 16px;
}}
.container {{
    max-width: 1269px;
    margin: 32px auto;
    padding: 0 16px;
}}
.card {{
    background: #ffffff;
    border: 1px solid #d7dce2;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    padding: 20px;
}}
.card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;
}}
.card-header h1 {{
    margin: 0;
    font-size: 26px;
}}
.search-row {{
    display: flex;
    gap: 10px;
    margin-bottom: 18px;
}}
input[type="text"] {{
    flex: 1;
    min-width: 0;
    border: 1px solid #b9c1cc;
    border-radius: 6px;
    font-size: 16px;
    padding: 10px 12px;
}}
button {{
    border: 0;
    border-radius: 6px;
    background: #1f6feb;
    color: #ffffff;
    cursor: pointer;
    font-size: 16px;
    padding: 10px 22px;
}}
button:hover {{ background: #195fc9; }}
.result-wrap {{
    overflow-x: hidden;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}}
th {{
    background: #d9f2dc;
    border: 1px solid #a9d8ad;
    color: #111827;
    font-weight: 700;
    padding: 11px 16px 11px 10px;
    position: relative;
    text-align: left;
    user-select: none;
}}
.resize-handle {{
    bottom: 0;
    cursor: col-resize;
    position: absolute;
    right: -4px;
    top: 0;
    width: 8px;
    z-index: 2;
}}
.resize-handle:hover {{ background: rgba(31, 111, 235, 0.22); }}
td {{
    border-bottom: 1px solid #b8c0ca;
    padding: 10px;
    overflow-wrap: anywhere;
    vertical-align: top;
}}
tbody tr:nth-child(even) {{ background: #edf0f2; }}
tbody tr:nth-child(odd) {{ background: #ffffff; }}
.pagination {{
    margin-top: 12px;
    text-align: center;
}}
.pagination a,
.current-page {{
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    display: inline-block;
    margin: 0 3px;
    padding: 4px 8px;
    text-decoration: none;
}}
.current-page {{
    background: #1f6feb;
    color: #ffffff;
}}
.status {{
    background: #f8fafc;
    border: 1px solid #d7dce2;
    border-radius: 6px;
    margin-top: 18px;
    padding: 12px 14px;
}}
.status h2 {{
    font-size: 18px;
    margin: 0 0 10px;
}}
.history {{
    background: #ffffff;
    border: 1px solid #d7dce2;
    border-radius: 6px;
    max-height: 280px;
    overflow: auto;
    padding: 10px;
    white-space: pre-wrap;
}}
.hint {{
    color: #6b7280;
    font-size: 13px;
    margin: -10px 0 14px;
}}
.ok {{ color: #166534; }}
.empty {{ color: #92400e; }}
.errors {{
    color: #b42318;
    margin: 8px 0 0;
    padding-left: 22px;
}}
select {{
    padding: 4px 8px;
    border: 1px solid #b9c1cc;
    border-radius: 4px;
    font-size: 14px;
}}
@media (max-width: 700px) {{
    .container {{ margin: 16px auto; }}
    .search-row {{ flex-direction: column; }}
    button {{ width: 100%; }}
}}
</style>
</head>
<body>
<div class="container">
    <div class="card">
        <div class="card-header">
            <h1>{t(lang, "app_name")}</h1>
            <div>{lang_switcher}</div>
        </div>
        <form method="post" action="/search" class="search-row">
            <input name="keyword" type="text" value="{escaped_keyword}" placeholder="{html.escape(t(lang, 'placeholder'), quote=True)}" autofocus>
            <button type="submit">{t(lang, "search_btn")}</button>
        </form>
        <p class="hint">{t(lang, "hint")}</p>
        <div class="result-wrap">{table_html}</div>
        <div class="status">
            {status_html}{error_html}
            <h2>{t(lang, "status_title")}</h2>
            <div class="history">{history_html}</div>
        </div>
    </div>
</div>
<script>
const table = document.getElementById('result-table');
if (table) {{
    const cols = table.querySelectorAll('col');
    table.querySelectorAll('th').forEach((header, index) => {{
        const handle = header.querySelector('.resize-handle');
        handle.addEventListener('mousedown', event => {{
            event.preventDefault();
            const startX = event.pageX;
            const startWidth = header.offsetWidth;
            const resize = moveEvent => {{
                const nextWidth = Math.max(80, startWidth + moveEvent.pageX - startX);
                cols[index].style.width = `${{nextWidth}}px`;
            }};
            const stop = () => {{
                document.removeEventListener('mousemove', resize);
                document.removeEventListener('mouseup', stop);
            }};
            document.addEventListener('mousemove', resize);
            document.addEventListener('mouseup', stop);
        }});
    }});
}}
</script>
</body>
</html>"""
    return page.encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP 处理
# ---------------------------------------------------------------------------


class VmSearchHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(404, "Not Found")
            return

        session_id, is_new_session = self.get_session_id()
        lang = self.get_lang()
        session_history = "" if is_new_session else read_session_history(session_id)
        page_number = self.get_page_number(parsed.query)
        keyword, records, errors = get_session_results(session_id)
        self.send_html(
            render_page(
                keyword,
                records,
                errors,
                session_history,
                page_number,
                bool(records or errors),
                lang=lang,
            ),
            session_id,
            lang,
        )

    def do_POST(self) -> None:
        if self.path == "/lang":
            # 语言切换请求
            session_id, _ = self.get_session_id()
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            lang = parse_qs(body).get("lang", [DEFAULT_LANG])[0].strip()
            if lang not in dict(LANGUAGES):
                lang = DEFAULT_LANG
            self.send_response(303)
            self.send_header("Location", "/")
            self.send_header(
                "Set-Cookie",
                f"vmq_lang={lang}; Path=/; SameSite=Lax",
            )
            self.send_header(
                "Set-Cookie",
                f"vmq_session={session_id}; Path=/; HttpOnly; SameSite=Lax",
            )
            self.end_headers()
            return

        if self.path != "/search":
            self.send_error(404, "Not Found")
            return

        session_id, _is_new_session = self.get_session_id()
        lang = self.get_lang()
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        keyword = parse_qs(body).get("keyword", [""])[0].strip()
        client_ip = self.client_address[0]

        records, errors, events = search_all(keyword, client_ip, lang)
        append_session_history(session_id, events)
        store_session_results(session_id, (keyword, records, errors))
        self.send_html(
            render_page(
                keyword,
                records,
                errors,
                read_session_history(session_id),
                searched=True,
                lang=lang,
            ),
            session_id,
            lang,
        )

    def get_session_id(self) -> tuple[str, bool]:
        cookie_header = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(cookie_header)
        morsel = jar.get("vmq_session")
        if morsel and morsel.value:
            return morsel.value, False
        return uuid4().hex, True

    def get_lang(self) -> str:
        """从 Cookie 或 Accept-Language 头获取语言偏好。"""
        cookie_header = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(cookie_header)
        morsel = jar.get("vmq_lang")
        if morsel and morsel.value:
            lang = morsel.value
            if lang in dict(LANGUAGES):
                return lang

        accept_lang = self.headers.get("Accept-Language", "")
        for part in accept_lang.split(","):
            code = part.split(";")[0].strip().lower()
            if code in dict(LANGUAGES):
                return code
            prefix = code.split("-")[0]
            for full_code, _ in LANGUAGES:
                if full_code.startswith(prefix + "-"):
                    return full_code

        return DEFAULT_LANG

    def get_page_number(self, query: str) -> int:
        try:
            return max(1, int(parse_qs(query).get("page", ["1"])[0]))
        except ValueError:
            return 1

    def send_html(self, body: bytes, session_id: str, lang: str = DEFAULT_LANG) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Set-Cookie",
            f"vmq_session={session_id}; Path=/; HttpOnly; SameSite=Lax",
        )
        self.send_header(
            "Set-Cookie",
            f"vmq_lang={lang}; Path=/; SameSite=Lax",
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"{self.client_address[0]} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), VmSearchHandler)
    print(f"VirtScope - 云镜 服务已启动：http://127.0.0.1:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
