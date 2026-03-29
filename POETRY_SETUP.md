# Poetry Setup Notes

## Why Poetry

Poetry gives the project one tool for:

- dependency management
- virtual environment management
- package installation
- script entrypoints
- lockfile-based reproducibility

That makes the setup more professional and easier to keep consistent across machines.

## Main Differences From `venv` + `pip`

### With `venv` + `pip`

You usually do this manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

That means:

- you manage the virtualenv yourself
- you install dependencies yourself
- reproducibility depends on how carefully versions are pinned
- package metadata and dependency workflow are more split across tools

### With Poetry

You usually do this:

```bash
poetry install
poetry shell
```

or:

```bash
poetry run legal-pipeline --help
```

That means:

- Poetry creates and manages the virtualenv for you
- Poetry installs dependencies from `pyproject.toml`
- Poetry can maintain a lockfile for reproducible installs
- script commands are run consistently through Poetry

## Virtual Environments In Poetry

Poetry still uses a virtual environment, but it manages it for you.

Useful commands:

```bash
poetry env info
poetry env list
poetry shell
poetry run pytest
```

If you want the virtualenv inside the project folder as `.venv`, you can run:

```bash
poetry config virtualenvs.in-project true
```

Then Poetry will behave closer to the common local-project style many teams prefer.

## Professional Enhancements Poetry Gives You

- cleaner dependency declarations
- dedicated dev dependency groups
- lockfile support
- less manual environment handling
- easier onboarding for reviewers and teammates
- better consistency between local machines and CI

## Recommended Workflow For This Repo

```bash
cp .env.example .env
poetry config virtualenvs.in-project true
poetry env use python3.11
poetry install
poetry run legal-pipeline --help
docker compose up -d
```

## Practical Trade-Off

Poetry is more opinionated than plain `pip`, but that is usually a good thing for a project like this. It reduces setup drift and makes the project feel more polished and maintainable.

## Python Version Note

This project intentionally targets **Python 3.11 or 3.12**.

That is mainly because orchestration dependencies like `dagster` are stricter than the rest of the stack. Using 3.11 is the safest option for local development, CI, and interview demos.
