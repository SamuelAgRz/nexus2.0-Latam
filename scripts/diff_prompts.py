from __future__ import annotations

import argparse
import difflib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff two prompt files")
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    args = parser.parse_args()

    old_path = Path(args.old)
    new_path = Path(args.new)

    old_lines = old_path.read_text(encoding="utf-8").splitlines()
    new_lines = new_path.read_text(encoding="utf-8").splitlines()

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=str(old_path),
        tofile=str(new_path),
        lineterm="",
    )
    print("\n".join(diff))


if __name__ == "__main__":
    main()
