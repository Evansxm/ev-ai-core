# v2026-02-efficient-r1 - Tools library
import subprocess, os, json, re, hashlib, base64, yaml, csv, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timedelta


class ToolRegistry:
    __slots__ = ("tools",)

    def __init__(self):
        self.tools = {}

    def reg(self, n: str, f: callable, d: str = ""):
        self.tools[n] = (f, d)

    def exec(self, n: str, **kw):
        return self.tools[n][0](**kw)

    def list(self):
        return [{"n": k, "d": v[1]} for k, v in self.tools.items()]


r = ToolRegistry()
_b = subprocess.run


def bash(cmd: str, to: int = 30) -> str:
    try:
        p = _b(cmd, shell=True, capture_output=True, text=True, timeout=to)
        return f"STDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}\nEXIT: {p.returncode}"
    except subprocess.TimeoutExpired:
        return "ERROR: Timeout"
    except Exception as e:
        return f"ERROR: {e}"


def read(p: str, enc: str = "utf-8") -> str:
    return open(p, "r", encoding=enc).read()


def write(p: str, c: str, enc: str = "utf-8") -> str:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    open(p, "w", encoding=enc).write(c)
    return f"Written to {p}"


def exists(p: str) -> bool:
    return os.path.exists(p)


def glob(pat: str = "*", path: str = ".") -> List[str]:
    import fnmatch

    return [
        os.path.join(root, f)
        for root, _, files in os.walk(path)
        for f in files
        if fnmatch.fnmatch(f, pat)
    ]


def grep(pat: str, path: str, ctx: int = 2) -> List[str]:
    with open(path) as f:
        lines = f.readlines()
    return [
        f"Line {i + 1}: {''.join(lines[max(0, i - ctx) : min(len(lines), i + ctx + 1)])}"
        for i, line in enumerate(lines)
        if re.search(pat, line)
    ]


def file_info(p: str) -> Dict:
    s = os.stat(p)
    return {
        "p": p,
        "s": s.st_size,
        "c": datetime.fromtimestamp(s.st_ctime).isoformat(),
        "m": datetime.fromtimestamp(s.st_mtime).isoformat(),
        "if": os.path.isfile(p),
        "id": os.path.isdir(p),
    }


_jd = json.dumps
_jl = json.loads


def json_parse(c: str) -> Any:
    return _jl(c)


def json_create(o: Any, ind: int = 2) -> str:
    return _jd(o, indent=ind)


def yaml_parse(c: str) -> Any:
    return yaml.safe_load(c)


def yaml_create(o: Any) -> str:
    return yaml.dump(o)


def csv_read(p: str) -> List[Dict]:
    with open(p) as f:
        return list(csv.DictReader(f))


def csv_write(p: str, data: List[Dict], fn: List[str] = None):
    if not data:
        return "No data"
    fn = fn or list(data[0].keys())
    with open(p, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=fn).writeheader()
        csv.DictWriter(f, fieldnames=fn).writerows(data)
    return f"Written {len(data)} rows"


def xml_parse(c: str) -> ET.Element:
    return ET.fromstring(c)


def xml_create(root: str, d: Dict) -> str:
    r = ET.Element(root)
    for k, v in d.items():
        ET.SubElement(r, k).text = str(v)
    return ET.tostring(r, encoding="unicode")


def http(url: str, method: str = "GET", hdrs: Dict = None, data: Any = None) -> Dict:
    import urllib.request, urllib.error

    req = urllib.request.Request(url, method=method)
    [req.add_header(k, v) for k, v in (hdrs or {}).items()]
    if data:
        req.data = (
            json.dumps(data).encode() if isinstance(data, dict) else data.encode()
        )
    try:
        with urllib.request.urlopen(req) as resp:
            return {
                "s": resp.status,
                "h": dict(resp.headers),
                "b": resp.read().decode(),
            }
    except urllib.error.HTTPError as e:
        return {"s": e.code, "e": str(e)}


_algs = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256}


def hash(c: str, alg: str = "sha256") -> str:
    return _algs.get(alg, hashlib.sha256)(c.encode()).hexdigest()


def b64e(c: str) -> str:
    return base64.b64encode(c.encode()).decode()


def b64d(c: str) -> str:
    return base64.b64decode(c.encode()).decode()


def re_match(pat: str, c: str, f: int = 0) -> List[str]:
    return re.findall(pat, c, f)


def re_replace(pat: str, c: str, repl: str, f: int = 0) -> str:
    return re.sub(pat, repl, c, flags=f)


def ts_now() -> str:
    return datetime.now().isoformat()


def ts_parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


def ts_add(s: str, d: int = 0, h: int = 0, m: int = 0) -> str:
    return (
        datetime.fromisoformat(s) + timedelta(days=d, hours=h, minutes=m)
    ).isoformat()


def env_get(k: str, d: str = None) -> str:
    return os.environ.get(k, d)


def env_set(k: str, v: str):
    os.environ[k] = v
    return f"Set {k}"


def clip_get() -> str:
    return _b(
        "xclip -selection clipboard -o", shell=True, capture_output=True, text=True
    ).stdout


def clip_set(c: str):
    _b(f"echo '{c}' | xclip -selection clipboard", shell=True)
    return "Copied"


def screenshot(p: str = None):
    if not p:
        p = f"/tmp/screenshot_{ts_now()}.png"
    _b(f"scrot {p}", shell=True)
    return f"Saved to {p}"


def notify(t: str, m: str):
    _b(f"notify-send '{t}' '{m}'", shell=True)
    return "Sent"


# Register all
for n, f, d in [
    ("bash", bash, "Run bash"),
    ("read", read, "Read file"),
    ("write", write, "Write file"),
    ("exists", exists, "Check exists"),
    ("glob", glob, "Find files"),
    ("grep", grep, "Search file"),
    ("file_info", file_info, "File info"),
    ("json_parse", json_parse, "Parse JSON"),
    ("json_create", json_create, "Create JSON"),
    ("yaml_parse", yaml_parse, "Parse YAML"),
    ("yaml_create", yaml_create, "Create YAML"),
    ("csv_read", csv_read, "Read CSV"),
    ("csv_write", csv_write, "Write CSV"),
    ("xml_parse", xml_parse, "Parse XML"),
    ("xml_create", xml_create, "Create XML"),
    ("http", http, "HTTP req"),
    ("hash", hash, "Hash"),
    ("b64e", b64e, "Base64 enc"),
    ("b64d", b64d, "Base64 dec"),
    ("re_match", re_match, "Regex match"),
    ("re_replace", re_replace, "Regex replace"),
    ("ts", ts_now, "Timestamp"),
    ("ts_add", ts_add, "Add time"),
    ("env_get", env_get, "Get env"),
    ("env_set", env_set, "Set env"),
    ("clip_get", clip_get, "Get clipboard"),
    ("clip_set", clip_set, "Set clipboard"),
    ("screenshot", screenshot, "Screenshot"),
    ("notify", notify, "Notify"),
]:
    r.reg(n, f, d)

exec_tool = r.exec
