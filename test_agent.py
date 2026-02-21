#!/usr/bin/env python3
"""Test script for GitHub Actions"""

import sys

sys.path.insert(0, "ev-ai-core")

from auto_agent import *
from comm_protocols import *

print("=== AGENT TEST ===")
try:
    print("whoami:", whoami().strip())
    print("hash:", hash("test")[:20])
    print("skill:", skill("calculator", "2+2"))
    print("memory:", mem_store("t", "v") or mem_recall("t"))
    print("http:", http_request("https://httpbin.org/status/200").get("status"))
    print("=== ALL OK ===")
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
