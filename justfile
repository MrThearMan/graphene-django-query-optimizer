# List all available commands
help:
    @just -l

# Run all tests with coverage and show coverage report
coverage:
    @uv run coverage run -m pytest .
    @uv run coverage report

# Show files without test coverage
coverage-missing:
    @uv run coverage report --skip-covered --show-missing

# Create a superuser
create-user:
    @DJANGO_SUPERUSER_PASSWORD=x uv run python manage.py createsuperuser --username x --email x@user.com --no-input

# Print top level dependencies
deps-top:
    @uv tree --depth 1 --no-default-groups

# Print all outdated dependencies
deps-out:
    @uv pip list --outdated

# Print all dependencies as a tree
deps-tree:
    @uv tree --all-groups

# Start the development server
dev port="8000":
    @uv run python manage.py runserver localhost:{{port}}

# Start the docs server
docs port="8080":
    @uv run mkdocs serve -a localhost:{{port}} -o

# Generate test data for local development
generate:
    @uv run python manage.py create_test_data

# Install pre-commit hooks
hook:
    @uv run prek install

# Update all pre-commit hooks
hook-update:
    @uv run prek update

# Install all dependencies & make sure they are up to date
install:
    @uv sync

# Run pre-commit hooks on all files
lint:
    @uv run prek run --all-files

# Generate a new dependency lock file
lock:
    @uv lock

# Run migrations
migrate:
    @uv run python manage.py migrate

# Create new migrations
migrations:
    @uv run python manage.py makemigrations

# Run mypy
mypy dir=".":
    @uv run mypy {{dir}}

# Run tests in all supported python and django versions using nox
nox:
    @uv run nox

# List all available nox sessions
nox-list:
    @uv run nox --list

# Run a single nox session
nox-one name:
    @uv run nox -s "{{name}}"

# Run all tests
test dir=".":
    @uv run pytest {{dir}}

# Run a specific test(s) by keyword (pytest "-k" option)
test-one name:
    @uv run pytest -k "{{name}}"
