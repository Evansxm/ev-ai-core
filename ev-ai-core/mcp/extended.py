# EXTENDED MCP TOOLS - Even more advanced capabilities
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
import zipfile
import tarfile
import tempfile
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import concurrent.futures
import threading
import queue

# === PARALLEL EXECUTION ===


async def parallel_exec(commands: List[str], max_workers: int = 5) -> str:
    """Execute commands in parallel"""
    results = []

    def run_cmd(cmd):
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {
            "cmd": cmd,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "returncode": p.returncode,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_cmd, cmd) for cmd in commands]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return json.dumps(results)


async def batch_process(items: List[Any], func_name: str, batch_size: int = 10) -> str:
    """Process items in batches"""
    from mcp.advanced import ADVANCED_TOOLS

    if func_name not in ADVANCED_TOOLS:
        return f"ERROR: Function {func_name} not found"

    func = ADVANCED_TOOLS[func_name]
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_results = []

        for item in batch:
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(item)
                else:
                    result = func(item)
                batch_results.append(result)
            except Exception as e:
                batch_results.append(f"ERROR: {str(e)}")

        results.extend(batch_results)

    return json.dumps(results)


# === ADVANCED FILE OPERATIONS ===


async def file_compress(format: str, paths: List[str], output: str) -> str:
    """Compress files"""
    try:
        if format == "zip":
            with zipfile.ZipFile(output, "w") as zf:
                for p in paths:
                    zf.write(p, arcname=os.path.basename(p))
        elif format in ["tar", "tar.gz", "tgz"]:
            mode = "w:gz" if format == "tar.gz" or format == "tgz" else "w"
            with tarfile.open(output, mode) as tf:
                for p in paths:
                    tf.add(p, arcname=os.path.basename(p))
        else:
            return f"ERROR: Unsupported format: {format}"
        return f"Created: {output}"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def file_extract(archive: str, dest: str = ".") -> str:
    """Extract archive"""
    try:
        if archive.endswith(".zip"):
            with zipfile.ZipFile(archive, "r") as zf:
                zf.extractall(dest)
        elif archive.endswith((".tar", ".tar.gz", ".tgz")):
            with tarfile.open(archive, "r:*") as tf:
                tf.extractall(dest)
        else:
            return f"ERROR: Unsupported format"
        return f"Extracted to: {dest}"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def file_replace_in_files(
    pattern: str, replacement: str, paths: List[str], regex: bool = False
) -> str:
    """Replace text in multiple files"""
    results = []
    for path in paths:
        try:
            with open(path, "r") as f:
                content = f.read()

            if regex:
                new_content = re.sub(pattern, replacement, content)
            else:
                new_content = content.replace(pattern, replacement)

            with open(path, "w") as f:
                f.write(new_content)

            results.append({"file": path, "status": "modified"})
        except Exception as e:
            results.append({"file": path, "status": "error", "error": str(e)})

    return json.dumps(results)


async def file_split(path: str, lines_per_file: int) -> str:
    """Split file into smaller files"""
    try:
        with open(path, "r") as f:
            lines = f.readlines()

        base_name = path.rsplit(".", 1)[0]
        ext = path.rsplit(".", 1)[1] if "." in path else ""

        for i in range(0, len(lines), lines_per_file):
            chunk = lines[i : i + lines_per_file]
            new_path = f"{base_name}_part{i // lines_per_file}.{ext}"
            with open(new_path, "w") as f:
                f.writelines(chunk)

        return f"Split into {len(range(0, len(lines), lines_per_file))} files"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def file_merge(paths: List[str], output: str) -> str:
    """Merge multiple files"""
    try:
        with open(output, "w") as out:
            for path in paths:
                with open(path, "r") as f:
                    out.write(f.read())
        return f"Merged {len(paths)} files into {output}"
    except Exception as e:
        return f"ERROR: {str(e)}"


# === ADVANCED DATABASE ===


async def db_create(db_path: str) -> str:
    """Create new database"""
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
        return f"Created: {db_path}"
    except Exception as e:
        return f"ERROR: {str(e)}"


async def db_tables(db_path: str) -> str:
    """List all tables"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        conn.close()
        return json.dumps(tables)
    except Exception as e:
        return f"ERROR: {str(e)}"


async def db_schema(db_path: str, table: str) -> str:
    """Get table schema"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        schema = [
            {
                "name": row[1],
                "type": row[2],
                "nullable": not row[3],
                "default": row[4],
                "pk": row[5],
            }
            for row in c.fetchall()
        ]
        conn.close()
        return json.dumps(schema)
    except Exception as e:
        return f"ERROR: {str(e)}"


async def db_export_json(db_path: str, table: str, output: str) -> str:
    """Export table to JSON"""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()
        c.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in c.fetchall()]

        data = [dict(zip(columns, row)) for row in rows]

        with open(output, "w") as f:
            json.dump(data, f, indent=2)

        conn.close()
        return f"Exported {len(data)} rows to {output}"
    except Exception as e:
        return f"ERROR: {str(e)}"


# === ADVANCED NETWORK ===


async def port_check(host: str, port: int, timeout: int = 3) -> str:
    """Check if port is open"""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((host, port))
    sock.close()
    return json.dumps({"host": host, "port": port, "open": result == 0})


async def dns_lookup(hostname: str) -> str:
    """DNS lookup"""
    import socket

    try:
        ip = socket.gethostbyname(hostname)
        return json.dumps({"hostname": hostname, "ip": ip})
    except Exception as e:
        return json.dumps({"hostname": hostname, "error": str(e)})


async def whois_lookup(domain: str) -> str:
    """Whois lookup (basic)"""
    try:
        p = subprocess.run(
            f"whois {domain}", shell=True, capture_output=True, text=True, timeout=10
        )
        return p.stdout[:2000]
    except Exception as e:
        return f"ERROR: {str(e)}"


async def ping_count(host: str, count: int = 4) -> str:
    """Ping with count"""
    try:
        p = subprocess.run(
            f"ping -c {count} {host}", shell=True, capture_output=True, text=True
        )
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


async def trace_route(host: str) -> str:
    """Traceroute"""
    try:
        p = subprocess.run(
            f"traceroute {host}", shell=True, capture_output=True, text=True, timeout=30
        )
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


# === ADVANCED CRYPTO ===


async def generate_password(length: int = 16, special: bool = True) -> str:
    """Generate secure password"""
    import secrets
    import string

    chars = string.ascii_letters + string.digits
    if special:
        chars += string.punctuation

    return "".join(secrets.choice(chars) for _ in range(length))


async def generate_token(length: int = 32) -> str:
    """Generate random token"""
    import secrets

    return secrets.token_urlsafe(length)


async def hash_verify(data: str, hash_value: str, algorithm: str = "sha256") -> str:
    """Verify hash"""
    if algorithm == "md5":
        computed = hashlib.md5(data.encode()).hexdigest()
    elif algorithm == "sha1":
        computed = hashlib.sha1(data.encode()).hexdigest()
    elif algorithm == "sha256":
        computed = hashlib.sha256(data.encode()).hexdigest()
    else:
        return "ERROR: Unknown algorithm"

    return json.dumps({"valid": computed == hash_value, "computed": computed})


# === ADVANCED TEXT PROCESSING ===


async def text_word_count(text: str) -> str:
    """Count words"""
    words = len(text.split())
    chars = len(text)
    lines = len(text.split("\n"))
    return json.dumps({"words": words, "characters": chars, "lines": lines})


async def text_unique_words(text: str) -> str:
    """Get unique words"""
    words = re.findall(r"\b\w+\b", text.lower())
    unique = sorted(set(words))
    return json.dumps({"unique": unique, "count": len(unique)})


async def text_replace(
    text: str, pattern: str, replacement: str, regex: bool = False
) -> str:
    """Replace text"""
    if regex:
        new_text = re.sub(pattern, replacement, text)
    else:
        new_text = text.replace(pattern, replacement)
    return json.dumps(
        {
            "original": text,
            "replaced": new_text,
            "count": text.count(pattern)
            if not regex
            else len(re.findall(pattern, text)),
        }
    )


async def text_lines_range(text: str, start: int, end: int) -> str:
    """Get range of lines"""
    lines = text.split("\n")
    return "\n".join(lines[start:end])


# === ADVANCED AI/ML ===


async def keyword_extract(text: str, top_n: int = 10) -> str:
    """Extract keywords (simple)"""
    from collections import Counter

    words = re.findall(r"\b\w{4,}\b", text.lower())
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "have",
        "has",
        "were",
        "been",
        "they",
        "their",
    }
    words = [w for w in words if w not in stop_words]

    counts = Counter(words)
    keywords = counts.most_common(top_n)
    return json.dumps(keywords)


async def text_classify(text: str) -> str:
    """Simple text classification"""
    categories = {
        "programming": [
            "code",
            "function",
            "class",
            "python",
            "javascript",
            "programming",
        ],
        "data": ["data", "database", "sql", "query", "table"],
        "network": ["http", "request", "server", "client", "api"],
        "system": ["system", "process", "memory", "cpu", "disk"],
    }

    text_lower = text.lower()
    scores = {}

    for cat, keywords in categories.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[cat] = score

    return json.dumps(
        {
            "scores": scores,
            "category": max(scores, key=scores.get)
            if max(scores.values()) > 0
            else "unknown",
        }
    )


# === ADVANCED SYSTEM ===


async def docker_ps() -> str:
    """List Docker containers"""
    try:
        p = subprocess.run(
            "docker ps -a --format '{{json .}}'",
            shell=True,
            capture_output=True,
            text=True,
        )
        containers = [json.loads(line) for line in p.stdout.strip().split("\n") if line]
        return json.dumps(containers, indent=2)
    except Exception as e:
        return f"ERROR: {str(e)}"


async def docker_logs(container: str, lines: int = 100) -> str:
    """Get container logs"""
    try:
        p = subprocess.run(
            f"docker logs --tail {lines} {container}",
            shell=True,
            capture_output=True,
            text=True,
        )
        return p.stdout[-5000:]  # Last 5000 chars
    except Exception as e:
        return f"ERROR: {str(e)}"


async def docker_exec(container: str, command: str) -> str:
    """Execute command in container"""
    try:
        p = subprocess.run(
            f"docker exec {container} {command}",
            shell=True,
            capture_output=True,
            text=True,
        )
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


async def systemd_status(service: str) -> str:
    """Get systemd service status"""
    try:
        p = subprocess.run(
            f"systemctl status {service}", shell=True, capture_output=True, text=True
        )
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


async def systemd_restart(service: str) -> str:
    """Restart systemd service"""
    try:
        p = subprocess.run(
            f"sudo systemctl restart {service}",
            shell=True,
            capture_output=True,
            text=True,
        )
        return f"Restarted: {service}" if p.returncode == 0 else f"Failed: {p.stderr}"
    except Exception as e:
        return f"ERROR: {str(e)}"


# === ADVANCED GIT ===


async def git_status() -> str:
    """Git status"""
    try:
        p = subprocess.run("git status", shell=True, capture_output=True, text=True)
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


async def git_log(limit: int = 10) -> str:
    """Git log"""
    try:
        p = subprocess.run(
            f"git log --oneline -n {limit}", shell=True, capture_output=True, text=True
        )
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


async def git_diff(file: str = None) -> str:
    """Git diff"""
    try:
        cmd = f"git diff {file}" if file else "git diff"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


async def git_branches() -> str:
    """List git branches"""
    try:
        p = subprocess.run("git branch -a", shell=True, capture_output=True, text=True)
        return p.stdout
    except Exception as e:
        return f"ERROR: {str(e)}"


# Export all extended tools
EXTENDED_TOOLS = {
    "parallel_exec": parallel_exec,
    "batch_process": batch_process,
    "file_compress": file_compress,
    "file_extract": file_extract,
    "file_replace_in_files": file_replace_in_files,
    "file_split": file_split,
    "file_merge": file_merge,
    "db_create": db_create,
    "db_tables": db_tables,
    "db_schema": db_schema,
    "db_export_json": db_export_json,
    "port_check": port_check,
    "dns_lookup": dns_lookup,
    "whois_lookup": whois_lookup,
    "ping_count": ping_count,
    "trace_route": trace_route,
    "generate_password": generate_password,
    "generate_token": generate_token,
    "hash_verify": hash_verify,
    "text_word_count": text_word_count,
    "text_unique_words": text_unique_words,
    "text_replace": text_replace,
    "text_lines_range": text_lines_range,
    "keyword_extract": keyword_extract,
    "text_classify": text_classify,
    "docker_ps": docker_ps,
    "docker_logs": docker_logs,
    "docker_exec": docker_exec,
    "systemd_status": systemd_status,
    "systemd_restart": systemd_restart,
    "git_status": git_status,
    "git_log": git_log,
    "git_diff": git_diff,
    "git_branches": git_branches,
}
