install:
	pip install -e .

eval:
	python scripts/run_system_eval.py --dataset evals/datasets/system_eval_cases.yaml --output evals/results/run_local.json

summary:
	python scripts/summarize_results.py --input evals/results/run_local.json

test:
	pytest -q
