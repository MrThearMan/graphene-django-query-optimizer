# List all available commands
help:
    @just -l

# Create a superuser
create-user:
    @DJANGO_SUPERUSER_PASSWORD=x poetry run python manage.py createsuperuser --username x --email x@user.com --no-input

# Start the development server
dev port="8000":
    @poetry run python manage.py runserver localhost:{{port}}

# Start the docs server
docs port="8080":
    @poetry run mkdocs serve -a localhost:{{port}} -o

# Generate test data for local development
generate:
    @poetry run python manage.py create_test_data

# Install pre-commit hooks
hook:
    @poetry run pre-commit install

# Install dependencies
install:
    @poetry install --all-extras

# Run pre-commit hooks
lint:
    @poetry run pre-commit run --all-files

# Run migrations
migrate:
    @poetry run python manage.py migrate

# Create new migrations
migrations:
    @poetry run python manage.py makemigrations

# Run tests in all supported python versions using nox
nox:
    @poetry run nox

# Sync dependencies
sync:
    @poetry sync --all-extras

# Run a specific test by name
test name:
    @poetry run pytest -k "{{name}}"

# Run all tests
tests:
    @poetry run coverage run -m pytest
