import click
import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import importlib.util
import sys


@dataclass
class Skill:
    name: str
    description: str
    category: str
    command: str
    handler: Callable
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False
    enabled: bool = True


class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.categories: Dict[str, List[str]] = {}

    def register(self, skill: Skill):
        self.skills[skill.name] = skill
        if skill.category not in self.categories:
            self.categories[skill.category] = []
        self.categories[skill.category].append(skill.name)

    def get(self, name: str) -> Optional[Skill]:
        return self.skills.get(name)

    def get_by_category(self, category: str) -> List[Skill]:
        names = self.categories.get(category, [])
        return [self.skills[n] for n in names]

    def list_all(self) -> List[Dict]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "aliases": s.aliases,
                "enabled": s.enabled,
            }
            for s in self.skills.values()
            if not s.hidden
        ]

    def enable(self, name: str):
        if name in self.skills:
            self.skills[name].enabled = True

    def disable(self, name: str):
        if name in self.skills:
            self.skills[name].enabled = False


skill_registry = SkillRegistry()


def skill(
    name: str, description: str, category: str = "general", aliases: List[str] = None
):
    def decorator(func: Callable):
        cmd_name = name.replace(" ", "-")
        aliases = aliases or []

        skill_obj = Skill(
            name=name,
            description=description,
            category=category,
            command=cmd_name,
            handler=func,
            aliases=aliases,
        )
        skill_registry.register(skill_obj)

        @click.command(name=cmd_name)
        @click.pass_context
        def cmd_wrapper(ctx, *args, **kwargs):
            return func(*args, **kwargs)

        for alias in aliases:

            @click.command(name=alias)
            @click.pass_context
            def alias_cmd(ctx, *args, **kwargs):
                return func(*args, **kwargs)

        return func

    return decorator


def create_click_group(commands: List[Skill] = None):
    @click.group()
    def cli():
        pass

    commands = commands or list(skill_registry.skills.values())

    for sk in commands:
        if not sk.enabled:
            continue

        @click.command(sk.command, help=sk.description)
        @click.pass_context
        def make_command(skill_obj=sk):
            def command(*args, **kwargs):
                return skill_obj.handler(*args, **kwargs)

            return command()

        cli.add_command(make_command)

        for alias in sk.aliases:
            cli.add_command(make_command, name=alias)

    return cli


@skill("git status", "Show git repository status", "version-control")
def git_status():
    import subprocess

    result = subprocess.run("git status", shell=True, capture_output=True, text=True)
    return result.stdout


@skill("git commit", "Commit changes with message", "version-control", ["gc"])
@click.argument("message")
def git_commit(message):
    import subprocess

    subprocess.run(f"git add . && git commit -m '{message}'", shell=True)
    return f"Committed: {message}"


@skill("git push", "Push to remote", "version-control")
def git_push():
    import subprocess

    result = subprocess.run("git push", shell=True, capture_output=True, text=True)
    return result.stdout


@skill("docker ps", "List running containers", "docker")
def docker_ps():
    import subprocess

    result = subprocess.run("docker ps", shell=True, capture_output=True, text=True)
    return result.stdout


@skill("docker exec", "Execute command in container", "docker")
@click.argument("container")
@click.argument("command")
def docker_exec(container, command):
    import subprocess

    result = subprocess.run(
        f"docker exec {container} {command}", shell=True, capture_output=True, text=True
    )
    return result.stdout


@skill("system info", "Get system information", "system", ["sysinfo"])
def system_info():
    import platform
    import subprocess

    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
    }

    try:
        result = subprocess.run("free -h", shell=True, capture_output=True, text=True)
        info["memory"] = result.stdout
    except:
        pass

    return json.dumps(info, indent=2)


@skill("disk usage", "Check disk usage", "system", ["df"])
def disk_usage():
    import subprocess

    result = subprocess.run("df -h", shell=True, capture_output=True, text=True)
    return result.stdout


@skill("process list", "List running processes", "system", ["ps"])
def process_list():
    import subprocess

    result = subprocess.run("ps aux", shell=True, capture_output=True, text=True)
    return result.stdout


@skill("kill process", "Kill a process by PID", "system")
@click.argument("pid", type=int)
def kill_process(pid):
    import os
    import signal

    try:
        os.kill(pid, signal.SIGTERM)
        return f"Killed process {pid}"
    except Exception as e:
        return f"Error: {e}"


@skill("network connections", "Show network connections", "network", ["netstat"])
def network_connections():
    import subprocess

    result = subprocess.run("netstat -tuln", shell=True, capture_output=True, text=True)
    return result.stdout


@skill("ping", "Ping a host", "network")
@click.argument("host")
@click.option("-c", "--count", default=4, help="Number of pings")
def ping(host, count):
    import subprocess

    result = subprocess.run(
        f"ping -c {count} {host}", shell=True, capture_output=True, text=True
    )
    return result.stdout


@skill("curl request", "Make HTTP request", "network")
@click.argument("url")
@click.option("-X", "--method", default="GET")
@click.option("-d", "--data", default=None)
@click.option("-H", "--header", multiple=True)
def curl_request(url, method, data, header):
    import subprocess

    cmd = f"curl -X {method}"
    for h in header:
        cmd += f" -H '{h}'"
    if data:
        cmd += f" -d '{data}'"
    cmd += f" {url}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


@skill("run python", "Run Python code", "development")
@click.argument("code")
def run_python(code):
    import subprocess

    result = subprocess.run(
        f"python3 -c '{code}'", shell=True, capture_output=True, text=True
    )
    return result.stdout + result.stderr


@skill("run node", "Run Node.js code", "development")
@click.argument("code")
def run_node(code):
    import subprocess

    result = subprocess.run(
        f"node -e '{code}'", shell=True, capture_output=True, text=True
    )
    return result.stdout + result.stderr


@skill("npm install", "Install npm package", "development")
@click.argument("package")
def npm_install(package):
    import subprocess

    result = subprocess.run(
        f"npm install {package}", shell=True, capture_output=True, text=True
    )
    return result.stdout


@skill("pip install", "Install Python package", "development")
@click.argument("package")
def pip_install(package):
    import subprocess

    result = subprocess.run(
        f"pip install {package}", shell=True, capture_output=True, text=True
    )
    return result.stdout


@skill("start server", "Start a development server", "development")
@click.argument("command", default="npm run dev")
def start_server(command):
    import subprocess

    subprocess.Popen(command, shell=True)
    return f"Started: {command}"


@skill("backup file", "Backup a file", "files", ["cp"])
@click.argument("path")
def backup_file(path):
    import shutil
    import datetime

    backup_path = f"{path}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, backup_path)
    return f"Backed up to {backup_path}"


@skill("find large files", "Find large files", "files")
@click.option("-m", "--min-size", default="100M", help="Minimum size (e.g., 100M)")
@click.option("-n", "--num", default=10, help="Number of results")
def find_large_files(min_size, num):
    import subprocess

    result = subprocess.run(
        f"find . -type f -size +{min_size} -exec ls -lh {{}} \\; | sort -k5 -h | tail -{num}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


@skill("extract archive", "Extract archive file", "files")
@click.argument("archive")
def extract_archive(archive):
    import subprocess
    import shutil

    result = subprocess.run(f"tar -xf {archive}", shell=True)
    return f"Extracted {archive}"


@skill("create archive", "Create archive", "files")
@click.argument("name")
@click.argument("files", nargs=-1)
def create_archive(name, files):
    import subprocess

    files_str = " ".join(files)
    result = subprocess.run(f"tar -czf {name} {files_str}", shell=True)
    return f"Created {name}"


@skill("weather", "Get weather for location", "utilities")
@click.argument("location")
def weather(location):
    return f"Weather for {location}: (API not configured)"


@skill("calculator", "Calculate expression", "utilities", ["calc"])
@click.argument("expression")
def calculator(expression):
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@skill("password generate", "Generate random password", "utilities")
@click.option("-l", "--length", default=16)
@click.option("-s", "--special", is_flag=True)
def password_generate(length, special):
    import secrets
    import string

    chars = string.ascii_letters + string.digits
    if special:
        chars += string.punctuation
    return "".join(secrets.choice(chars) for _ in range(length))


@skill("url encode", "URL encode string", "utilities")
@click.argument("text")
def url_encode(text):
    import urllib.parse

    return urllib.parse.quote(text)


@skill("url decode", "URL decode string", "utilities")
@click.argument("text")
def url_decode(text):
    import urllib.parse

    return urllib.parse.unquote(text)


def load_skills_from_file(filepath: str):
    spec = importlib.util.spec_from_file_location("skills_module", filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules["skills_module"] = module
    spec.loader.exec_module(module)


def get_skill(name: str) -> Optional[Skill]:
    return skill_registry.get(name)


def list_skills(category: str = None) -> List[Dict]:
    if category:
        return [
            {"name": s.name, "description": s.description}
            for s in skill_registry.get_by_category(category)
        ]
    return skill_registry.list_all()
