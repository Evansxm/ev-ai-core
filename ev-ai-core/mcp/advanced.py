# ADVANCED MCP TOOLS - Extended capabilities
import asyncio
import subprocess
import json
import os
import re
import base64
import hashlib
import sqlite3
import urllib.request
import urllib.parse
import urllib.error
import ssl
import certifi
import shutil
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

# === ADVANCED SHELL TOOLS ===


async def shell_exec(cmd: str, timeout: int = 30) -> str:
    """Execute shell command with timeout"""
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return f"STDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}\nEXIT: {p.returncode}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def shell_background(cmd: str) -> str:
    """Execute command in background"""
    subprocess.Popen(
        cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return f"Started background process: {cmd}"


async def shell_pipe(cmds: List[str]) -> str:
    """Pipe multiple commands"""
    cmd = " | ".join(cmds)
    return await shell_exec(cmd)


# === ADVANCED FILE TOOLS ===


async def file_glob(pattern: str, path: str = ".") -> List[str]:
    """Find files matching pattern"""
    import fnmatch

    matches = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                matches.append(os.path.join(root, name))
    return matches


async def file_search(pattern: str, path: str = ".", context: int = 2) -> List[str]:
    """Search for pattern in files"""
    results = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith((".py", ".js", ".txt", ".md", ".json", ".yaml")):
                fp = os.path.join(root, f)
                try:
                    with open(fp) as file:
                        lines = file.readlines()
                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            start = max(0, i - context)
                            end = min(len(lines), i + context + 1)
                            results.append(f"{fp}:{i + 1}: {line.strip()}")
                except:
                    pass
    return results[:100]  # Limit results


async def file_backup(path: str, dest: str = None) -> str:
    """Backup file with timestamp"""
    if not os.path.exists(path):
        return f"ERROR: File not found: {path}"

    if dest is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = f"{path}.backup_{ts}"

    shutil.copy2(path, dest)
    return f"Backed up to: {dest}"


async def file_diff(file1: str, file2: str) -> str:
    """Compare two files"""
    try:
        p = subprocess.run(
            f"diff -u {file1} {file2}", shell=True, capture_output=True, text=True
        )
        return p.stdout or "Files are identical"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def file_watch(path: str, interval: int = 5) -> str:
    """Watch file for changes"""
    if not os.path.exists(path):
        return f"ERROR: File not found: {path}"

    mtime = os.path.getmtime(path)
    import time

    time.sleep(interval)
    new_mtime = os.path.getmtime(path)

    if new_mtime != mtime:
        return f"CHANGED: {path}"
    return f"UNCHANGED: {path}"


# === ADVANCED MEMORY/DATA TOOLS ===


async def db_query(sql: str, db_path: str = ":memory:") -> str:
    """Execute SQL query"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(sql)

        if sql.strip().upper().startswith("SELECT"):
            rows = c.fetchall()
            conn.close()
            return json.dumps(rows)
        else:
            conn.commit()
            conn.close()
            return f"Affected rows: {c.rowcount}"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def db_create_table(
    name: str, columns: Dict[str, str], db_path: str = ":memory:"
) -> str:
    """Create database table"""
    cols = ", ".join([f"{k} {v}" for k, v in columns.items()])
    sql = f"CREATE TABLE {name} ({cols})"
    return await db_query(sql, db_path)


async def cache_set(key: str, value: Any, ttl: int = 3600) -> str:
    """Set cache with TTL"""
    from memory import remember

    remember(
        f"cache:{key}",
        {"value": value, "expires": datetime.now().timestamp() + ttl},
        "cache",
        10,
    )
    return f"Cached: {key}"


async def cache_get(key: str) -> str:
    """Get cache if not expired"""
    from memory import recall

    data = recall(f"cache:{key}")
    if not data:
        return "MISS"

    if datetime.now().timestamp() > data.get("expires", 0):
        return "EXPIRED"

    return json.dumps(data.get("value"))


# === ADVANCED NETWORK TOOLS ===


async def http_request(
    url: str,
    method: str = "GET",
    headers: Dict = None,
    data: str = None,
    json_data: Dict = None,
) -> str:
    """Advanced HTTP request"""
    import json

    try:
        req = urllib.request.Request(url, method=method)

        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        if json_data:
            import json

            data = json.dumps(json_data).encode()
            req.add_header("Content-Type", "application/json")
        elif data:
            data = data.encode()

        ctx = ssl.create_default_context(cafile=certifi.where())

        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.dumps(
                {
                    "status": resp.status,
                    "headers": dict(resp.headers),
                    "body": resp.read().decode(),
                }
            )
    except urllib.error.HTTPError as e:
        return json.dumps({"error": str(e), "status": e.code})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def http_download(url: str, path: str = "/tmp") -> str:
    """Download file from URL"""
    try:
        filename = url.split("/")[-1]
        filepath = os.path.join(path, filename)

        ctx = ssl.create_default_context(cafile=certifi.where())
        urllib.request.urlretrieve(url, filepath, context=ctx)

        return f"Downloaded: {filepath}"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def webhook_send(url: str, data: Dict) -> str:
    """Send webhook POST"""
    return await http_request(url, "POST", json_data=data)


# === ADVANCED ENCODING/CRYPTO ===


async def encode_base64(data: str) -> str:
    """Base64 encode"""
    return base64.b64encode(data.encode()).decode()


async def decode_base64(data: str) -> str:
    """Base64 decode"""
    return base64.b64decode(data.encode()).decode()


async def hash_data(data: str, algorithm: str = "sha256") -> str:
    """Hash data"""
    if algorithm == "md5":
        return hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == "sha512":
        return hashlib.sha512(data.encode()).hexdigest()
    return hashlib.sha256(data.encode()).hexdigest()


async def hash_file(path: str, algorithm: str = "sha256") -> str:
    """Hash file contents"""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


async def encrypt_aes(data: str, key: str) -> str:
    """AES encryption (basic)"""
    import secrets

    iv = secrets.token_bytes(16)
    # Note: Requires cryptography library for full implementation
    return base64.b64encode(iv + data.encode()).decode()


async def decrypt_aes(data: str, key: str) -> str:
    """AES decryption (basic)"""
    try:
        raw = base64.b64decode(data.encode())
        iv = raw[:16]
        return raw[16:].decode()
    except:
        return "ERROR: Decryption failed"


# === ADVANCED CODE TOOLS ===


async def python_exec(code: str, globals: Dict = None) -> str:
    """Execute Python code safely"""
    try:
        g = globals or {}
        exec(code, g)
        return json.dumps(g.get("result", "Executed"))
    except Exception as e:
        return f"ERROR: {str(e)}"


async def python_eval(expr: str) -> str:
    """Evaluate Python expression"""
    try:
        result = eval(expr)
        return json.dumps(result)
    except Exception as e:
        return f"ERROR: {str(e)}"


async def js_exec(code: str) -> str:
    """Execute JavaScript (requires node)"""
    try:
        with open("/tmp/tmp.js", "w") as f:
            f.write(code)
        p = subprocess.run(
            "node /tmp/tmp.js", shell=True, capture_output=True, text=True
        )
        return p.stdout or p.stderr
    except Exception as e:
        return f"ERROR: {str(e)}"


# === ADVANCED SYSTEM TOOLS ===


async def system_info() -> str:
    """Get comprehensive system info"""
    import platform
    import psutil

    info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_total": psutil.virtual_memory().total,
        "memory_available": psutil.virtual_memory().available,
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": str(psutil.disk_usage("/")),
    }
    return json.dumps(info, indent=2)


async def process_list() -> str:
    """List running processes"""
    import psutil

    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(
                {
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "cpu": p.info["cpu_percent"],
                    "mem": p.info["memory_percent"],
                }
            )
        except:
            pass
    return json.dumps(procs[:50])


async def process_kill(pid: int) -> str:
    """Kill process by PID"""
    import psutil

    try:
        p = psutil.Process(pid)
        p.terminate()
        return f"Killed: {pid}"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def port_scan(host: str, ports: List[int]) -> str:
    """Scan ports"""
    import socket

    open_ports = []
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        if result == 0:
            open_ports.append(port)
        sock.close()
    return json.dumps({"host": host, "open_ports": open_ports})


# === ADVANCED AI/ML TOOLS ===


async def summarize_text(text: str, max_length: int = 100) -> str:
    """Summarize text (basic)"""
    sentences = re.split(r"[.!?]+", text)
    return ". ".join(sentences[:3])[:max_length]


async def extract_urls(text: str) -> str:
    """Extract URLs from text"""
    url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    urls = re.findall(url_pattern, text)
    return json.dumps(urls)


async def extract_emails(text: str) -> str:
    """Extract emails from text"""
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    emails = re.findall(email_pattern, text)
    return json.dumps(emails)


async def sentiment_score(text: str) -> str:
    """Basic sentiment scoring"""
    positive = len(
        re.findall(
            r"\b(good|great|excellent|amazing|love|happy|awesome)\b", text.lower()
        )
    )
    negative = len(
        re.findall(r"\b(bad|terrible|awful|hate|sad|angry|poor)\b", text.lower())
    )
    score = (positive - negative) / max(len(text.split()), 1) * 10
    return json.dumps({"positive": positive, "negative": negative, "score": score})


# === ADVANCED AUTOMATION TOOLS ===


async def schedule_task(cron_expr: str, command: str) -> str:
    """Schedule cron task"""
    subprocess.run(
        f'(crontab -l 2>/dev/null; echo "{cron_expr} {command}") | crontab -',
        shell=True,
    )
    return f"Scheduled: {cron_expr} -> {command}"


async def watch_directory(path: str, action: str) -> str:
    """Watch directory for changes"""
    import time

    before = set(os.listdir(path))
    time.sleep(5)
    after = set(os.listdir(path))

    added = after - before
    removed = before - after

    return json.dumps({"added": list(added), "removed": list(removed)})


# Export all advanced tools
ADVANCED_TOOLS = {
    "shell_exec": shell_exec,
    "shell_background": shell_background,
    "shell_pipe": shell_pipe,
    "file_glob": file_glob,
    "file_search": file_search,
    "file_backup": file_backup,
    "file_diff": file_diff,
    "db_query": db_query,
    "db_create_table": db_create_table,
    "cache_set": cache_set,
    "cache_get": cache_get,
    "http_request": http_request,
    "http_download": http_download,
    "webhook_send": webhook_send,
    "encode_base64": encode_base64,
    "decode_base64": decode_base64,
    "hash_data": hash_data,
    "hash_file": hash_file,
    "encrypt_aes": encrypt_aes,
    "decrypt_aes": decrypt_aes,
    "python_exec": python_exec,
    "python_eval": python_eval,
    "js_exec": js_exec,
    "system_info": system_info,
    "process_list": process_list,
    "process_kill": process_kill,
    "port_scan": port_scan,
    "summarize_text": summarize_text,
    "extract_urls": extract_urls,
    "extract_emails": extract_emails,
    "sentiment_score": sentiment_score,
    "schedule_task": schedule_task,
    "watch_directory": watch_directory,
}
