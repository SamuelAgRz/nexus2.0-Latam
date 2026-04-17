from pathlib import Path

import yaml


def test_eval_dataset_loads() -> None:
    path = Path("evals/datasets/system_eval_cases.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "cases" in data
    assert len(data["cases"]) >= 1
