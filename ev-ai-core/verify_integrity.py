#!/usr/bin/env python3
# INTEGRCRIPT
# VerITY VERIFICATION Sifies all files match expected hashes
import hashlib
import json
import os
import sys

MANIFEST_FILE = "INTEGRITY.json"


def hash_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify():
    if not os.path.exists(MANIFEST_FILE):
        print(f"❌ Missing {MANIFEST_FILE}")
        return False

    with open(MANIFEST_FILE) as f:
        manifest = json.load(f)

    errors = []
    for path, expected_hash in manifest.items():
        if not os.path.exists(path):
            errors.append(f"Missing: {path}")
            continue

        actual = hash_file(path)
        if actual != expected_hash:
            errors.append(f"TAMPERED: {path}")

    if errors:
        print("❌ INTEGRITY CHECK FAILED:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("✅ ALL FILES VERIFIED - INTEGRITY INTACT")
        return True


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
