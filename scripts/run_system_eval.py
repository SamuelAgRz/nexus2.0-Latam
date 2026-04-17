from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import requests
import yaml


@dataclass
class CaseResult:
    case_id: str
    category: str
    passed: bool
    latency_seconds: float
    expected_hits: list[str]
    missing_expected: list[str]
    forbidden_hits: list[str]
    response_text: str
    error: str | None = None


def load_dataset(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_system(url: str, api_key: str | None, query: str, timeout: int) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"query": query}
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    # Ajusta esto según el contrato real de tu endpoint
    if isinstance(data, dict):
        for candidate_key in ["answer", "response", "output", "result"]:
            if candidate_key in data and isinstance(data[candidate_key], str):
                return data[candidate_key]

    return json.dumps(data, ensure_ascii=False)


def evaluate_text(response_text: str, expected: list[str], forbidden: list[str]) -> tuple[list[str], list[str], list[str]]:
    lowered = response_text.lower()
    expected_hits = [x for x in expected if x.lower() in lowered]
    missing_expected = [x for x in expected if x.lower() not in lowered]
    forbidden_hits = [x for x in forbidden if x.lower() in lowered]
    return expected_hits, missing_expected, forbidden_hits


def run_case(case: dict[str, Any], url: str, api_key: str | None, timeout: int) -> CaseResult:
    start = time.perf_counter()
    try:
        response_text = call_system(url, api_key, case["user_query"], timeout)
        latency = time.perf_counter() - start
        expected_hits, missing_expected, forbidden_hits = evaluate_text(
            response_text=response_text,
            expected=case.get("expected_contains", []),
            forbidden=case.get("forbidden_contains", []),
        )
        passed = not missing_expected and not forbidden_hits and latency <= case.get("max_latency_seconds", 999)
        return CaseResult(
            case_id=case["id"],
            category=case.get("category", "uncategorized"),
            passed=passed,
            latency_seconds=round(latency, 3),
            expected_hits=expected_hits,
            missing_expected=missing_expected,
            forbidden_hits=forbidden_hits,
            response_text=response_text,
        )
    except Exception as exc:  # noqa: BLE001
        latency = time.perf_counter() - start
        return CaseResult(
            case_id=case["id"],
            category=case.get("category", "uncategorized"),
            passed=False,
            latency_seconds=round(latency, 3),
            expected_hits=[],
            missing_expected=case.get("expected_contains", []),
            forbidden_hits=[],
            response_text="",
            error=str(exc),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run system-level evals against Nexus endpoint")
    parser.add_argument("--dataset", required=True, help="Path to YAML dataset")
    parser.add_argument("--output", required=True, help="Path to output JSON")
    args = parser.parse_args()

    url = os.getenv("SYSTEM_UNDER_TEST_URL", "").strip()
    api_key = os.getenv("SYSTEM_API_KEY", "").strip() or None
    timeout = int(os.getenv("SYSTEM_TIMEOUT_SECONDS", "90"))

    if not url:
        raise ValueError("SYSTEM_UNDER_TEST_URL is required")

    dataset = load_dataset(Path(args.dataset))
    cases = dataset.get("cases", [])

    results = [asdict(run_case(case, url, api_key, timeout)) for case in cases]

    summary = {
        "total_cases": len(results),
        "passed_cases": sum(1 for r in results if r["passed"]),
        "failed_cases": sum(1 for r in results if not r["passed"]),
        "pass_rate": round(sum(1 for r in results if r["passed"]) / max(len(results), 1), 4),
        "avg_latency_seconds": round(sum(r["latency_seconds"] for r in results) / max(len(results), 1), 3),
    }

    output = {"summary": summary, "results": results}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
