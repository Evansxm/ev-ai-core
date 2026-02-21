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


# Unrestricted / Admin skills
@_skill("run anything", "Execute any command", "admin")
def run_anything(*args):
    return _r(" ".join(args))


@_skill("eval code", "Evaluate Python", "admin", ["py"])
def eval_code(code):
    try:
        return str(eval(code))
    except Exception as e:
        return f"Error: {e}"


@_skill("exec code", "Execute Python", "admin")
def exec_code(code):
    import sys

    g = {"subprocess": subprocess, "os": os, "json": json}
    exec(code, g)
    return "Executed"


@_skill("http request", "Make HTTP", "net")
def http_request(url, method="GET", data=None):
    import urllib.request, urllib.parse

    d = data.encode() if data else None
    req = urllib.request.Request(url, data=d, method=method)
    with urllib.request.urlopen(req) as r:
        return r.read().decode()


@_skill("download file", "Download URL", "net")
def download_file(url, path="/tmp"):
    import urllib.request

    fname = url.split("/")[-1]
    urllib.request.urlretrieve(url, f"{path}/{fname}")
    return f"Downloaded to {path}/{fname}"


@_skill("send email", "Send email", "net")
def send_email(to, subject, body):
    return f"Email would be sent to {to}: {subject}"


@_skill("sqlite query", "Query SQLite", "db")
def sqlite_query(db_path, query):
    import sqlite3

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(query)
    r = c.fetchall()
    conn.close()
    return str(r)


@_skill("mongo query", "Query Mongo", "db")
def mongo_query(connection_str, db, query):
    return f"Mongo query on {db}: {query}"


@_skill("redis set", "Set Redis", "db")
def redis_set(key, value, host="localhost"):
    return f"Redis: {key}={value}"


@_skill("docker run", "Run container", "docker")
def docker_run(image, command=None):
    cmd = f"docker run -d {image}"
    if command:
        cmd += f" {command}"
    return _r(cmd)


@_skill("docker exec shell", "Shell in container", "docker")
def docker_exec_shell(container):
    return _r(f"docker exec -it {container} /bin/sh")


@_skill("kubernetes exec", "K8s exec", "k8s")
def kubernetes_exec(pod, container=None):
    cmd = f"kubectl exec -it {pod}"
    if container:
        cmd += f" -c {container}"
    cmd += " -- /bin/sh"
    return cmd


@_skill("aws s3 copy", "S3 copy", "cloud")
def aws_s3_copy(src, dest):
    return _r(f"aws s3 cp {src} {dest}")


@_skill("terraform apply", "Terraform apply", "infra")
def terraform_apply(plan=None):
    cmd = "terraform apply"
    if plan:
        cmd += f" -var-file={plan}"
    return _r(cmd + " -auto-approve")


@_skill("ansible playbook", "Run Ansible", "infra")
def ansible_playbook(playbook, inventory=None):
    cmd = f"ansible-playbook {playbook}"
    if inventory:
        cmd += f" -i {inventory}"
    return _r(cmd)


@_skill("git clone", "Clone repo", "vc")
def git_clone(url, path=None):
    cmd = f"git clone {url}"
    if path:
        cmd += f" {path}"
    return _r(cmd)


@_skill("git branch", "List branches", "vc")
def git_branch():
    return _r("git branch -a")


@_skill("systemctl", "Systemctl", "sys")
def systemctl(action, service):
    return _r(f"sudo systemctl {action} {service}")


@_skill("journalctl", "View logs", "sys")
def journalctl(service, lines=50):
    return _r(f"journalctl -u {service} -n {lines}")


@_skill("lsof port", "Port usage", "net")
def lsof_port(port):
    return _r(f"lsof -i :{port}")


@_skill("curl json", "Curl JSON API", "net")
def curl_json(url, method="GET"):
    return _r(f"curl -s -X {method} {url}")


@_skill("jq parse", "Parse JSON", "util")
def jq_parse(json_str, query):
    return _r(f"echo '{json_str}' | jq '{query}'")


@_skill("base64 encode", "Base64 encode", "util")
def base64_encode(text):
    import base64

    return base64.b64encode(text.encode()).decode()


@_skill("base64 decode", "Base64 decode", "util")
def base64_decode(text):
    import base64

    return base64.b64decode(text.encode()).decode()


@_skill("hash brute", "Hash brute force", "util")
def hash_brute(hash_str, wordlist):
    return _r(f"hashcat -m 0 {hash_str} {wordlist}")


@_skill("nmap scan", "Nmap scan", "net")
def nmap_scan(target, ports=None):
    cmd = f"nmap -sV {target}"
    if ports:
        cmd += f" -p {ports}"
    return _r(cmd)


@_skill("netcat listen", "Netcat listen", "net")
def netcat_listen(port):
    return _r(f"nc -lvp {port}")


@_skill("screen create", "Create screen", "sys")
def screen_create(name):
    return _r(f"screen -dmS {name}")


@_skill("tmux create", "Create tmux", "sys")
def tmux_create(name):
    return _r(f"tmux new -d -s {name}")


@_skill("cron add", "Add cron job", "sys")
def cron_add(schedule, command):
    return _r(f'(crontab -l 2>/dev/null; echo "{schedule} {command}") | crontab -')


@_skill("system info full", "Full system info", "sys")
def system_info_full():
    return _r(
        "echo CPU:$(cat /proc/cpuinfo | grep 'model name' | head -1) RAM:$(free -h | grep Mem) DISK:$(df -h | grep /$)"
    )


# DevOps / Cloud
@_skill("kubectl get pods", "K8s pods", "k8s")
def k8s_pods(ns="default"):
    return _r(f"kubectl get pods -n {ns}")


@_skill("kubectl apply", "K8s apply", "k8s")
def k8s_apply(f):
    return _r(f"kubectl apply -f {f}")


@_skill("kubectl logs", "K8s logs", "k8s")
def k8s_logs(pod, ns="default", lines=100):
    return _r(f"kubectl logs {pod} -n {ns} --tail {lines}")


@_skill("kubectl describe", "K8s describe", "k8s")
def k8s_describe(resource, name, ns="default"):
    return _r(f"kubectl describe {resource} {name} -n {ns}")


@_skill("helm install", "Helm install", "k8s")
def helm_install(release, chart, ns="default"):
    return _r(f"helm install {release} {chart} -n {ns}")


@_skill("helm list", "Helm list", "k8s")
def helm_list(ns="default"):
    return _r(f"helm list -n {ns}")


@_skill("terraform init", "Terraform init", "infra")
def terraform_init():
    return _r("terraform init")


@_skill("terraform plan", "Terraform plan", "infra")
def terraform_plan(var_file=None):
    cmd = "terraform plan"
    if var_file:
        cmd += f" -var-file={var_file}"
    return _r(cmd)


@_skill("terraform destroy", "Terraform destroy", "infra")
def terraform_destroy(var_file=None):
    cmd = "terraform destroy -auto-approve"
    if var_file:
        cmd += f" -var-file={var_file}"
    return _r(cmd)


@_skill("ansible run", "Run Ansible", "infra")
def ansible_run(playbook, limit=None, tags=None):
    cmd = f"ansible-playbook {playbook}"
    if limit:
        cmd += f" --limit {limit}"
    if tags:
        cmd += f" --tags {tags}"
    return _r(cmd)


@_skill("aws ec2 list", "AWS EC2 list", "cloud")
def aws_ec2_list():
    return _r(
        "aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId'"
    )


@_skill("aws s3 ls", "AWS S3 list", "cloud")
def aws_s3_list(bucket):
    return _r(f"aws s3 ls s3://{bucket}")


@_skill("aws lambda invoke", "AWS Lambda invoke", "cloud")
def aws_lambda_invoke(function):
    return _r(f"aws lambda invoke --function-name {function} /dev/null")


@_skill("gcloud list", "GCP list resources", "cloud")
def gcloud_list(resource="instances", zone="us-central1-a"):
    return _r(f"gcloud compute {resource} list --zone {zone}")


@_skill("docker-compose up", "Docker Compose up", "docker")
def docker_compose_up(d="."):
    return _r(f"docker-compose up -d")


@_skill("docker-compose down", "Docker Compose down", "docker")
def docker_compose_down(d="."):
    return _r(f"docker-compose down")


@_skill("docker build", "Docker build", "docker")
def docker_build(tag, path="."):
    return _r(f"docker build -t {tag} {path}")


@_skill("docker push", "Docker push", "docker")
def docker_push(tag):
    return _r(f"docker push {tag}")


# Security
@_skill("nmap scan", "Nmap scan", "security")
def nmap_scan(target, ports="1-1000", os_detect=False):
    cmd = f"nmap -sV -p {ports}"
    if os_detect:
        cmd += " -O"
    cmd += f" {target}"
    return _r(cmd)


@_skill("nikto scan", "Nikto scan", "security")
def nikto_scan(target):
    return _r(f"nikto -h {target}")


@_skill("sqlmap scan", "SQLMap scan", "security")
def sqlmap_scan(url):
    return _r(f"sqlmap -u {url} --batch")


# Monitoring
@_skill("top processes", "Top processes", "monitor")
def top_processes(n=10):
    return _r(f"ps aux --sort=-%cpu | head -{n}")


@_skill("memory usage", "Memory usage", "monitor")
def memory_usage():
    return _r("free -h && vmstat 1 3")


@_skill("disk io", "Disk I/O", "monitor")
def disk_io():
    return _r("iostat -x 1 3")


@_skill("network stats", "Network stats", "monitor")
def network_stats():
    return _r("netstat -s && ss -s")


@_skill("tail logs", "Tail logs", "monitor")
def tail_logs(path, lines=50):
    return _r(f"tail -{lines} {path}")


@_skill("grep logs", "Grep logs", "monitor")
def grep_logs(pattern, path="/var/log/*.log"):
    return _r(f"grep -r '{pattern}' {path} | head -50")


# Database
@_skill("mysql query", "MySQL query", "db")
def mysql_query(query, db="mysql"):
    return _r(f"mysql -e '{query}' {db}")


@_skill("postgres query", "PostgreSQL query", "db")
def postgres_query(query, db="postgres"):
    return _r(f"psql -c '{query}' {db}")


@_skill("redis keys", "Redis keys", "db")
def redis_keys(pattern="*"):
    return _r(f"redis-cli KEYS '{pattern}'")


@_skill("mongo find", "MongoDB find", "db")
def mongo_find(collection, db="test", query="{}"):
    return _r(f"mongo {db} --quiet --eval 'db.{collection}.find({query}).pretty()'")


# Text Processing
@_skill("json format", "Format JSON", "text")
def json_format(file):
    return _r(f"python3 -m json.tool {file}")


@_skill("yaml to json", "YAML to JSON", "text")
def yaml_to_json(file):
    return _r(
        f"python3 -c 'import json,yaml; print(json.dumps(yaml.safe_load(open(\"{file}\"))))'"
    )


@_skill("csv to json", "CSV to JSON", "text")
def csv_to_json(file):
    return _r(
        f"python3 -c 'import csv,json; print(json.dumps(list(csv.DictReader(open(\"{file}\")))))'"
    )


@_skill("sort lines", "Sort lines", "text")
def sort_lines(file, unique=False):
    cmd = f"sort {file}"
    if unique:
        cmd += " | uniq"
    return _r(cmd)


# Network
@_skill("curl headers", "Get HTTP headers", "net")
def curl_headers(url):
    return _r(f"curl -I {url}")


@_skill("curl json", "Get JSON", "net")
def curl_json(url):
    return _r(f"curl -s {url} | python3 -m json.tool")


@_skill("wget download", "Wget download", "net")
def wget_download(url, out="/tmp"):
    return _r(f"wget -P {out} {url}")


@_skill("ssh copy id", "SSH copy key", "net")
def ssh_copy_id(user, host):
    return _r(f"ssh-copy-id {user}@{host}")


# File Management
@_skill("find by name", "Find by name", "file")
def find_by_name(pattern, path="."):
    return _r(f"find {path} -name '{pattern}'")


@_skill("find by size", "Find by size", "file")
def find_by_size(size="+100M", path="."):
    return _r(f"find {path} -size {size}")


@_skill("find by time", "Find by time", "file")
def find_by_time(days=7, path="."):
    return _r(f"find {path} -mtime -{days}")


@_skill("chmod recursive", "Chmod recursive", "file")
def chmod_recursive(mode, path="."):
    return _r(f"chmod -R {mode} {path}")


@_skill("chown recursive", "Chown recursive", "file")
def chown_recursive(user, path="."):
    return _r(f"chown -R {user} {path}")


@_skill("rsync copy", "Rsync copy", "file")
def rsync_copy(src, dest, archive=True):
    cmd = "rsync -avz" if archive else "rsync -vz"
    return _r(f"{cmd} {src} {dest}")


# System
@_skill("check ports", "Check listening ports", "sys")
def check_ports():
    return _r("ss -tulpn")


@_skill("user list", "List users", "sys")
def user_list():
    return _r("cat /etc/passwd | cut -d: -1")


@_skill("service status", "Service status", "sys")
def service_status(name):
    return _r(f"systemctl status {name} || service {name} status")


@_skill("restart service", "Restart service", "sys")
def restart_service(name):
    return _r(f"sudo systemctl restart {name} && sudo systemctl status {name}")


@_skill("reload daemon", "Reload systemd", "sys")
def reload_daemon():
    return _r("sudo systemctl daemon-reload")


@_skill("fail2ban status", "Fail2ban status", "security")
def fail2ban_status():
    return _r("sudo fail2ban-client status")


@_skill("ufw status", "UFW firewall status", "security")
def ufw_status():
    return _r("sudo ufw status numbered")


@_skill("iptables list", "IPTables rules", "security")
def iptables_list():
    return _r("sudo iptables -L -n -v")


# Containers
@_skill("podman ps", "Podman containers", "container")
def podman_ps():
    return _r("podman ps -a")


@_skill("crictl pods", "CRI-O pods", "container")
def crictl_pods():
    return _r("crictl pods")


def get_skill(n: str) -> Optional[Skill]:
    return R.get(n)


def list_skills(c: str = None) -> List[Dict]:
    return R.by_cat(c) if c else R.list_all()
