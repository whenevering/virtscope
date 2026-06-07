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
CONFIG_FILE = BASE_DIR / "vm-list.ini"
HISTORY_FILE = BASE_DIR / "history.log"
PORT = 6616
PAGE_SIZE = 30

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


class VmSearchError(Exception):
    pass


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


def load_endpoints() -> list[Endpoint]:
    parser = configparser.ConfigParser()
    if not CONFIG_FILE.exists():
        raise VmSearchError(f"未找到配置文件：{CONFIG_FILE}")

    parser.read(CONFIG_FILE, encoding="utf-8")
    endpoints: list[Endpoint] = []

    for section in parser.sections():
        host = parser.get(section, "host", fallback="").strip()
        username = parser.get(section, "username", fallback="").strip()
        password = parser.get(section, "password", fallback="").strip()
        port = parser.getint(section, "port", fallback=443)

        if not host or not username or not password:
            raise VmSearchError(f"配置节 [{section}] 缺少 host、username 或 password。")

        endpoints.append(Endpoint(section, host, username, password, port))

    if not endpoints:
        raise VmSearchError(f"配置文件中没有可用的主机配置：{CONFIG_FILE}")

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
        # 老版本 pyVmomi 不支持 httpConnectionTimeout
        return SmartConnect(**base_kwargs)


def search_endpoint(endpoint: Endpoint, matcher: KeywordMatcher) -> tuple[list[VmRecord], list[str]]:
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
        errors.append(
            f"[{endpoint.name}] {endpoint.host} 检索失败。"
            f"错误类型：{type(exc).__name__}；详细原因：{exc}；"
            "请检查主机地址、网络连通性、端口、用户名密码、账号权限及证书/协议兼容性。"
        )
        return [], errors
    finally:
        if si is not None:
            try:
                Disconnect(si)
            except Exception:
                pass


def search_all(keyword: str, client_ip: str) -> tuple[list[VmRecord], list[str], list[str]]:
    matcher = KeywordMatcher(keyword)
    records: list[VmRecord] = []
    errors: list[str] = []
    events: list[str] = ["-" * 80, f"开始搜索：{keyword or '全部虚拟机'}，客户端IP：{client_ip}"]

    try:
        endpoints = load_endpoints()
    except Exception as exc:
        errors.append(str(exc))
        events.append("没有找到匹配的虚拟机记录。")
        events.extend(errors)
        append_history(events)
        return [], errors, events

    workers = max(1, min(MAX_ENDPOINT_WORKERS, len(endpoints)))
    events.append(
        f"并发检索 {len(endpoints)} 个端点（线程数={workers}，单端点超时={ENDPOINT_TIMEOUT}s）"
    )

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="vmq") as executor:
        future_map = {
            executor.submit(search_endpoint, endpoint, matcher): endpoint
            for endpoint in endpoints
        }
        for future in as_completed(future_map):
            endpoint = future_map[future]
            try:
                ep_records, ep_errors = future.result(timeout=ENDPOINT_TIMEOUT)
            except FuturesTimeoutError:
                errors.append(
                    f"[{endpoint.name}] {endpoint.host} 检索超时（>{ENDPOINT_TIMEOUT}s），已放弃。"
                )
                continue
            except Exception as exc:
                errors.append(
                    f"[{endpoint.name}] {endpoint.host} 异常：{type(exc).__name__}: {exc}"
                )
                continue

            records.extend(ep_records)
            errors.extend(ep_errors)
            events.append(
                f"完成 {endpoint.name} ({endpoint.host})：命中 {len(ep_records)} 条"
            )

    if records:
        events.append(f"找到 {len(records)} 条匹配记录。")
        events.extend(
            f"VC:{r.vcenter}-ESXi:{r.esxi_host}-VM:{r.vm_name}" for r in records
        )
    else:
        events.append("没有找到匹配的虚拟机记录。")

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
        status_html = f'<p class="ok">找到 {total_records} 条匹配记录。</p>'
    elif searched:
        status_html = '<p class="empty">没有找到匹配的虚拟机记录。</p>'
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
            pagination_html = f'<div class="pagination">第 {page_number} / {total_pages} 页：{" ".join(links)}</div>'

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
                    <th>虚拟机完整名称<span class="resize-handle"></span></th>
                    <th>IP 地址<span class="resize-handle"></span></th>
                    <th>所在 vCenter<span class="resize-handle"></span></th>
                    <th>所在 ESXi 主机<span class="resize-handle"></span></th>
                    <th>资源池/集群路径<span class="resize-handle"></span></th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        {pagination_html}
        """

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>VirtScope - 云镜</title>
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
h1 {{
    margin: 0 0 18px;
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
        <h1>VirtScope - 云镜</h1>
        <form method="post" action="/search" class="search-row">
            <input name="keyword" type="text" value="{escaped_keyword}" placeholder="支持名称或 IP 关键字；空格分隔多词为 AND；每个词可写正则；留空搜索全部" autofocus>
            <button type="submit">搜索</button>
        </form>
        <p class="hint">示例：<code>web 192.168.10</code> 表示同时包含 “web” 与 “192.168.10”；正则示例：<code>^db-\\d+</code></p>
        <div class="result-wrap">{table_html}</div>
        <div class="status">
            {status_html}{error_html}
            <h2>状态/错误信息</h2>
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
            ),
            session_id,
        )

    def do_POST(self) -> None:
        if self.path != "/search":
            self.send_error(404, "Not Found")
            return

        session_id, _is_new_session = self.get_session_id()
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        keyword = parse_qs(body).get("keyword", [""])[0].strip()
        client_ip = self.client_address[0]

        records, errors, events = search_all(keyword, client_ip)
        append_session_history(session_id, events)
        store_session_results(session_id, (keyword, records, errors))
        self.send_html(
            render_page(
                keyword,
                records,
                errors,
                read_session_history(session_id),
                searched=True,
            ),
            session_id,
        )

    def get_session_id(self) -> tuple[str, bool]:
        cookie_header = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(cookie_header)
        morsel = jar.get("vmq_session")
        if morsel and morsel.value:
            return morsel.value, False
        return uuid4().hex, True

    def get_page_number(self, query: str) -> int:
        try:
            return max(1, int(parse_qs(query).get("page", ["1"])[0]))
        except ValueError:
            return 1

    def send_html(self, body: bytes, session_id: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Set-Cookie",
            f"vmq_session={session_id}; Path=/; HttpOnly; SameSite=Lax",
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
