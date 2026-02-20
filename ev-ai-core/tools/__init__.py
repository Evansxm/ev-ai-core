import subprocess
import os
import json
import re
import hashlib
import base64
import yaml
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import fnmatch


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, func: callable, description: str = ""):
        self.tools[name] = {"func": func, "description": description}

    def execute(self, name: str, **kwargs) -> Any:
        if name in self.tools:
            return self.tools[name]["func"](**kwargs)
        raise ValueError(f"Tool {name} not found")

    def list_tools(self) -> List[Dict]:
        return [
            {"name": k, "description": v["description"]} for k, v in self.tools.items()
        ]


registry = ToolRegistry()


def bash(command: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT: {result.returncode}"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out"
    except Exception as e:
        return f"ERROR: {str(e)}"


def read_file(path: str, encoding: str = "utf-8") -> str:
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def write_file(path: str, content: str, encoding: str = "utf-8") -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)
    return f"Written to {path}"


def file_exists(path: str) -> bool:
    return os.path.exists(path)


def list_files(pattern: str = "*", path: str = ".") -> List[str]:
    matches = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                matches.append(os.path.join(root, name))
    return matches


def search_in_file(pattern: str, path: str, context_lines: int = 2) -> List[str]:
    results = []
    with open(path, "r") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            results.append(f"Line {i + 1}: {''.join(lines[start:end])}")
    return results


def get_file_info(path: str) -> Dict:
    stat = os.stat(path)
    return {
        "path": path,
        "size": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "is_file": os.path.isfile(path),
        "is_dir": os.path.isdir(path),
    }


def json_parse(content: str) -> Any:
    return json.loads(content)


def json_create(obj: Any, indent: int = 2) -> str:
    return json.dumps(obj, indent=indent)


def yaml_parse(content: str) -> Any:
    return yaml.safe_load(content)


def yaml_create(obj: Any) -> str:
    return yaml.dump(obj)


def csv_read(path: str) -> List[Dict]:
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def csv_write(path: str, data: List[Dict], fieldnames: List[str] = None):
    if not data:
        return "No data to write"
    fieldnames = fieldnames or list(data[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    return f"Written {len(data)} rows to {path}"


def xml_parse(content: str) -> ET.Element:
    return ET.fromstring(content)


def xml_create(root_tag: str, data: Dict) -> str:
    root = ET.Element(root_tag)
    for key, value in data.items():
        child = ET.SubElement(root, key)
        child.text = str(value)
    return ET.tostring(root, encoding="unicode")


def http_request(
    url: str, method: str = "GET", headers: Dict = None, data: Any = None
) -> Dict:
    import urllib.request
    import urllib.error

    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data:
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        req.data = data

    try:
        with urllib.request.urlopen(req) as resp:
            return {
                "status": resp.status,
                "headers": dict(resp.headers),
                "body": resp.read().decode(),
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "error": str(e)}


def hash_content(content: str, algorithm: str = "sha256") -> str:
    if algorithm == "md5":
        return hashlib.md5(content.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(content.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(content.encode()).hexdigest()
    return hashlib.sha256(content.encode()).hexdigest()


def base64_encode(content: str) -> str:
    return base64.b64encode(content.encode()).decode()


def base64_decode(content: str) -> str:
    return base64.b64decode(content.encode()).decode()


def regex_match(pattern: str, content: str, flags: int = 0) -> List[str]:
    return re.findall(pattern, content, flags)


def regex_replace(pattern: str, content: str, replacement: str, flags: int = 0) -> str:
    return re.sub(pattern, replacement, content, flags=flags)


def timestamp_now() -> str:
    return datetime.now().isoformat()


def timestamp_parse(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str)


def timestamp_add(
    date_str: str, days: int = 0, hours: int = 0, minutes: int = 0
) -> str:
    dt = datetime.fromisoformat(date_str)
    dt += timedelta(days=days, hours=hours, minutes=minutes)
    return dt.isoformat()


def env_get(key: str, default: str = None) -> str:
    return os.environ.get(key, default)


def env_set(key: str, value: str):
    os.environ[key] = value
    return f"Set {key}"


def clipboard_get() -> str:
    result = subprocess.run(
        "xclip -selection clipboard -o", shell=True, capture_output=True, text=True
    )
    return result.stdout


def clipboard_set(content: str):
    subprocess.run(f"echo '{content}' | xclip -selection clipboard", shell=True)
    return "Copied to clipboard"


def screenshot(save_path: str = None):
    if not save_path:
        save_path = f"/tmp/screenshot_{timestamp_now()}.png"
    subprocess.run(f"scrot {save_path}", shell=True)
    return f"Saved to {save_path}"


def notify(title: str, message: str):
    subprocess.run(f"notify-send '{title}' '{message}'", shell=True)
    return "Notification sent"


def get_clipboard():
    return clipboard_get()


def set_clipboard(content: str):
    return clipboard_set(content)


registry.register("bash", bash, "Execute bash command")
registry.register("read", read_file, "Read file contents")
registry.register("write", write_file, "Write to file")
registry.register("exists", file_exists, "Check if file exists")
registry.register("glob", list_files, "Find files by pattern")
registry.register("grep", search_in_file, "Search in file")
registry.register("file_info", get_file_info, "Get file information")
registry.register("json_parse", json_parse, "Parse JSON")
registry.register("json_create", json_create, "Create JSON")
registry.register("yaml_parse", yaml_parse, "Parse YAML")
registry.register("yaml_create", yaml_create, "Create YAML")
registry.register("csv_read", csv_read, "Read CSV")
registry.register("csv_write", csv_write, "Write CSV")
registry.register("xml_parse", xml_parse, "Parse XML")
registry.register("xml_create", xml_create, "Create XML")
registry.register("http", http_request, "Make HTTP request")
registry.register("hash", hash_content, "Hash content")
registry.register("base64_encode", base64_encode, "Base64 encode")
registry.register("base64_decode", base64_decode, "Base64 decode")
registry.register("regex_match", regex_match, "Regex match")
registry.register("regex_replace", regex_replace, "Regex replace")
registry.register("timestamp", timestamp_now, "Get current timestamp")
registry.register("timestamp_add", timestamp_add, "Add time")
registry.register("env_get", env_get, "Get env variable")
registry.register("env_set", env_set, "Set env variable")
registry.register("clipboard_get", get_clipboard, "Get clipboard")
registry.register("clipboard_set", set_clipboard, "Set clipboard")
registry.register("screenshot", screenshot, "Take screenshot")
registry.register("notify", notify, "Send notification")


def execute_tool(tool_name: str, **kwargs) -> Any:
    return registry.execute(tool_name, **kwargs)
