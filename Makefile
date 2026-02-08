.PHONY: lint check check_scaffold check_eval_assets check_project_skills test_fast test_full test_unit test_all

test_fast:
	python3 ci/eval_runner.py --mode fast

test_full:
	python3 ci/eval_runner.py --mode full

test_unit:
	python3 -m unittest discover -s tests -p "test_*.py" -q

lint:
	python3 -m py_compile \
		harness/task_lock.py \
		ci/eval_runner.py \
		ci/check_eval_assets.py \
		ci/check_scaffold.py \
		ci/check_project_skills.py \
		pipeline/interfaces.py \
		pipeline/contracts.py \
		pipeline/scaffold.py \
		pipeline/run_scaffold.py

check_scaffold:
	python3 ci/check_scaffold.py

check_eval_assets:
	python3 ci/check_eval_assets.py

check_project_skills:
	python3 ci/check_project_skills.py

check: check_scaffold check_eval_assets check_project_skills

test_all: lint check test_fast test_unit test_full
