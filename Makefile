export DJANGO_SETTINGS_MODULE = tests.project.settings

.PHONY: create-user
.PHONY: dev
.PHONY: docs
.PHONY: flush
.PHONY: generate
.PHONY: help
.PHONY: hook
.PHONY: lint
.PHONY: Makefile
.PHONY: migrate
.PHONY: migrations
.PHONY: mypy
.PHONY: setup
.PHONY: test
.PHONY: tests
.PHONY: tox

# Trick to allow passing commands to make
# Use quotes (" ") if command contains flags (-h / --help)
args = `arg="$(filter-out $@,$(MAKECMDGOALS))" && echo $${arg:-${1}}`

# If command doesn't match, do not throw error
%:
	@:

define helptext

  Commands:

  create-user          Create a superuser called "x" with password of "x"
  dev                  Serve manual testing server
  docs                 Serve mkdocs for development.
  flush                Flush database.
  generate             Generate test data.
  hook                 Install pre-commit hook.
  lint                 Run pre-commit hooks on all files.
  migrate              Migrate database.
  migrations           Make migrations.
  mypy                 Run mypy on all files.
  setup                Make migrations, apply them, and add a superuser
  test <name>          Run all tests maching the given <name>
  tests                Run all tests with coverage.
  tox                  Run all tests with tox.

  Use quotes (" ") if command contains flags (-h / --help)
endef

export helptext

help:
	@echo "$$helptext"

create-user:
	@DJANGO_SUPERUSER_PASSWORD=x poetry run python manage.py createsuperuser --username x --email user@user.com --no-input

dev:
	@poetry run python manage.py runserver localhost:8000

docs:
	@poetry run mkdocs serve -a localhost:8080

flush:
	@poetry run python manage.py flush --no-input

generate:
	@poetry run python manage.py create_test_data

hook:
	@poetry run pre-commit install

lint:
	@poetry run pre-commit run --all-files

migrate:
	@poetry run python manage.py migrate

migrations:
	@poetry run python manage.py makemigrations

mypy:
	@poetry run mypy query_optimizer/

setup: migrations migrate create-user

test:
	@poetry run pytest -k $(call args, "")

tests:
	@poetry run coverage run -m pytest

tox:
	@poetry run tox
