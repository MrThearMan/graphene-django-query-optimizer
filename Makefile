.PHONY: help
.PHONY: dev
.PHONY: docs
.PHONY: generate
.PHONY: flush
.PHONY: migrations
.PHONY: migrate
.PHONY: create-user
.PHONY: setup
.PHONY: tests
.PHONY: test
.PHONY: tox
.PHONY: hook
.PHONY: pre-commit
.PHONY: pre-commit-update
.PHONY: mypy
.PHONY: Makefile

# Trick to allow passing commands to make
# Use quotes (" ") if command contains flags (-h / --help)
args = `arg="$(filter-out $@,$(MAKECMDGOALS))" && echo $${arg:-${1}}`

# If command doesn't match, do not throw error
%:
	@:

define helptext

  Commands:

  dev                  Serve manual testing server
  docs                 Serve mkdocs for development.
  generate             Generate test data.
  flush                Flush database.
  migrations           Make migrations.
  migrate              Migrate database.
  create-user          Create a superuser called "x" with password of "x"
  setup                Make migrations, apply them, and add a superuser
  tests                Run all tests with coverage.
  test <name>          Run all tests maching the given <name>
  tox                  Run all tests with tox.
  hook                 Install pre-commit hook.
  pre-commit           Run pre-commit hooks on all files.
  pre-commit-update    Update all pre-commit hooks to latest versions.
  mypy                 Run mypy on all files.

  Use quotes (" ") if command contains flags (-h / --help)
endef

export helptext

help:
	@echo "$$helptext"

dev:
	@poetry run python manage.py runserver localhost:8000

generate:
	@poetry run python manage.py create_test_data

flush:
	@poetry run python manage.py flush --no-input

migrations:
	@poetry run python manage.py makemigrations

migrate:
	@poetry run python manage.py migrate

create-user:
	@DJANGO_SUPERUSER_PASSWORD=x poetry run python manage.py createsuperuser --username x --email user@user.com --no-input

setup: migrations migrate create-user

docs:
	@poetry run mkdocs serve -a localhost:8080

tests:
	@poetry run coverage run -m pytest

test:
	@poetry run pytest -k $(call args, "")

tox:
	@poetry run tox

hook:
	@poetry run pre-commit install

pre-commit:
	@poetry run pre-commit run --all-files

pre-commit-update:
	@poetry run pre-commit autoupdate

mypy:
	@poetry run mypy query_optimizer/
