install:
	uv pip install -e '.[testing]'

test: install
	pytest --cov=src/preset_cli -vv tests/ --doctest-modules src/preset_cli

clean:
	rm -rf .venv __pycache__ src/**/__pycache__ *.egg-info

spellcheck:
	codespell -S "*.json" src/preset_cli docs/*rst tests templates

requirements.txt: requirements.in pyproject.toml
	uv pip install --upgrade pip-tools
	pip-compile --no-annotate

dev-requirements.txt: dev-requirements.in pyproject.toml
	uv pip install --upgrade pip-tools
	pip-compile dev-requirements.in --no-annotate

check:
	pre-commit run --all-files
