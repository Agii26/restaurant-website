#!/usr/bin/env python3
"""PostToolUse syntax checker.

Runs right after Claude edits or writes a file. For .py and .json files it
checks that the file still parses. If not, we exit 2 and print the problem:
for PostToolUse, exit 2 shows our stderr to Claude (the edit already happened),
so Claude fixes its own typo immediately instead of you finding it later.

A broken checker must never block real work, so any unexpected crash exits 0.
"""
import json
import os
import sys


def main():
    event = json.load(sys.stdin)
    path = (event.get("tool_input") or {}).get("file_path")
    if not path or not os.path.isfile(path):
        return 0
    lowered = path.lower()
    try:
        if lowered.endswith(".py"):
            with open(path, "rb") as handle:
                compile(handle.read(), path, "exec")  # parse only; writes no .pyc files
        elif lowered.endswith(".json"):
            with open(path, "r", encoding="utf-8") as handle:
                json.load(handle)
    except (SyntaxError, ValueError) as exc:  # JSONDecodeError and UnicodeDecodeError are ValueErrors
        print(f"Syntax problem in {path}: {exc}\nFix this before doing anything else.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
