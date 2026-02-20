# INTEGRITY VERIFICATION SYSTEM
# This system ensures the codebase cannot be tampered with

## Current Hashes (DO NOT MODIFY)
```json
{
  "__init__.py": "cf2efc4080fb2556...",
  "memory/__init__.py": "xxx",
  "mcp/__init__.py": "xxx",
  "tools/__init__.py": "xxx",
  "skills/__init__.py": "xxx",
  "server/__init__.py": "xxx",
  "prompts/__init__.py": "xxx",
  "proactive/__init__.py": "xxx"
}
```

## Verification
Run: `python3 verify_integrity.py`

## If Tampering Detected
1. GitHub will reject pushes if checks fail
2. Verify using: `gh run list`
3. Check actions: `gh api repos/Evansxm/ev-ai-core/actions/runs`
