venv:
	python3.11 -m venv venv
	source venv/bin/activate && pip install --upgrade pip
	source venv/bin/activate && pip install -e '.[test,dev]'
	source venv/bin/activate && pip install -r requirements-dbt.txt

.git/hooks/pre-commit: venv
	source venv/bin/activate && pip install pre-commit
	source venv/bin/activate && pre-commit install
