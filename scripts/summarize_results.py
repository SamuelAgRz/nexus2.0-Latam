from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize eval results")
    parser.add_argument("--input", required=True, help="Path to eval results JSON")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    summary = data["summary"]
    results = data["results"]

    by_category = Counter(r["category"] for r in results)
    failures = [r for r in results if not r["passed"]]

    print("=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n=== BY CATEGORY ===")
    for k, v in sorted(by_category.items()):
        print(f"- {k}: {v}")

    print("\n=== FAILURES ===")
    if not failures:
        print("No failures")
        return

    for r in failures:
        print(f"- {r['case_id']} | category={r['category']} | latency={r['latency_seconds']}s")
        if r.get("error"):
            print(f"  error: {r['error']}")
        if r.get("missing_expected"):
            print(f"  missing_expected: {r['missing_expected']}")
        if r.get("forbidden_hits"):
            print(f"  forbidden_hits: {r['forbidden_hits']}")


if __name__ == "__main__":
    main()
