# v2026-02-efficient-r1 - Skills CLI system
import subprocess, json, os
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    desc: str
    cat: str
    cmd: str
    handler: Callable
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False
    enabled: bool = True


class S:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.cats: Dict[str, List[str]] = {}

    def reg(self, s: Skill):
        self.skills[s.name] = s
        self.cats.setdefault(s.cat, []).append(s.name)

    def get(self, n: str) -> Optional[Skill]:
        return self.skills.get(n)

    def by_cat(self, c: str) -> List[Skill]:
        return [self.skills[n] for n in self.cats.get(c, [])]

    def list_all(self) -> List[Dict]:
        return [
            {"n": s.name, "d": s.desc, "c": s.cat, "a": s.aliases, "e": s.enabled}
            for s in self.skills.values()
            if not s.hidden
        ]

    def en(self, n: str):
        if n in self.skills:
            self.skills[n].enabled = True

    def dis(self, n: str):
        if n in self.skills:
            self.skills[n].enabled = False


R = S()
_s = subprocess.run


def _r(cmd: str) -> str:
    return _s(cmd, shell=True, capture_output=True, text=True).stdout


def _skill(name: str, desc: str, cat: str = "general", als: List[str] = None):
    def dec(f: Callable):
        cmd = name.replace(" ", "-")
        R.reg(
            Skill(name=name, desc=desc, cat=cat, cmd=cmd, handler=f, aliases=als or [])
        )
        return f

    return dec


# Git
@_skill("git status", "Show git status", "vc")
def git_status():
    return _r("git status")


@_skill("git commit", "Commit changes", "vc", ["gc"])
def git_commit(msg):
    _r(f"git add . && git commit -m '{msg}'")
    return f"Committed: {msg}"


@_skill("git push", "Push to remote", "vc")
def git_push():
    return _r("git push")


# Docker
@_skill("docker ps", "List containers", "docker")
def docker_ps():
    return _r("docker ps")


@_skill("docker exec", "Exec in container", "docker")
def docker_exec(c, cmd):
    return _r(f"docker exec {c} {cmd}")


# System
@_skill("system info", "System info", "sys", ["si"])
def system_info():
    import platform

    return json.dumps(
        {"os": platform.system(), "ver": platform.version(), "arch": platform.machine()}
    )


@_skill("disk usage", "Disk usage", "sys", ["df"])
def disk_usage():
    return _r("df -h")


@_skill("process list", "Running processes", "sys", ["ps"])
def process_list():
    return _r("ps aux")


@_skill("kill process", "Kill PID", "sys")
def kill_process(pid):
    import signal

    os.kill(int(pid), signal.SIGTERM)
    return f"Killed {pid}"


# Network
@_skill("network connections", "Net connections", "net", ["netstat"])
def network_connections():
    return _r("netstat -tuln")


@_skill("ping", "Ping host", "net")
def ping(host, count=4):
    return _r(f"ping -c {count} {host}")


# Dev
@_skill("run python", "Run Python", "dev")
def run_python(code):
    p = _s(f"python3 -c '{code}'", shell=True, capture_output=True, text=True)
    return p.stdout + p.stderr


@_skill("run node", "Run Node", "dev")
def run_node(code):
    p = _s(f"node -e '{code}'", shell=True, capture_output=True, text=True)
    return p.stdout + p.stderr


@_skill("npm install", "npm i", "dev")
def npm_install(pkg):
    return _r(f"npm install {pkg}")


@_skill("pip install", "pip i", "dev")
def pip_install(pkg):
    return _r(f"pip install {pkg}")


@_skill("start server", "Start dev server", "dev")
def start_server(cmd):
    subprocess.Popen(cmd, shell=True)
    return f"Started: {cmd}"


# Files
@_skill("backup file", "Backup file", "file")
def backup_file(path):
    import shutil, datetime

    bp = f"{path}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, bp)
    return f"Backed up to {bp}"


@_skill("find large files", "Large files", "file")
def find_large_files(min="100M", num=10):
    return _r(
        f"find . -type f -size +{min} -exec ls -lh {{}} \\; | sort -k5 -h | tail -{num}"
    )


@_skill("extract archive", "Extract tar", "file")
def extract_archive(archive):
    _r(f"tar -xf {archive}")
    return f"Extracted {archive}"


@_skill("create archive", "Create tar", "file")
def create_archive(name, files):
    _r(f"tar -czf {name} {' '.join(files)}")
    return f"Created {name}"


# Utils
@_skill("weather", "Weather", "util")
def weather(loc):
    return f"Weather for {loc}: (API not set)"


@_skill("calculator", "Calc", "util", ["calc"])
def calculator(expr):
    try:
        return str(eval(expr))
    except Exception as e:
        return f"Error: {e}"


@_skill("password generate", "Gen password", "util")
def password_generate(length=16, special=False):
    import secrets, string

    c = string.ascii_letters + string.digits + (string.punctuation if special else "")
    return "".join(secrets.choice(c) for _ in range(length))


@_skill("url encode", "URL enc", "util")
def url_encode(text):
    import urllib.parse

    return urllib.parse.quote(text)


@_skill("url decode", "URL dec", "util")
def url_decode(text):
    import urllib.parse

    return urllib.parse.unquote(text)


def get_skill(n: str) -> Optional[Skill]:
    return R.get(n)


def list_skills(c: str = None) -> List[Dict]:
    return R.by_cat(c) if c else R.list_all()
