from __future__ import annotations

import logging
import re
import tomllib
from functools import cache
from pathlib import Path

import nox

logger = logging.getLogger(__name__)


def python_versions() -> list[str]:
    python_version_pattern = re.compile(r"^Programming Language :: Python :: (?P<version>\d+\.\d+)$")
    versions = get_versions(python_version_pattern)
    logger.debug(f"Python versions: {', '.join(versions)}")
    return versions


def django_versions() -> list[str]:
    django_versions_pattern = re.compile(r"^Framework :: Django :: (?P<version>\d+\.\d+)$")
    versions = get_versions(django_versions_pattern)
    logger.debug(f"Django versions: {', '.join(versions)}")
    return [f"{version}.*" for version in versions]


@cache
def get_classifiers() -> list[str]:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    toml_data = tomllib.loads(pyproject)
    return toml_data["project"]["classifiers"]


def get_versions(pattern: re.Pattern[str]) -> list[str]:
    classifiers = get_classifiers()
    versions: list[str] = []
    for classifier in classifiers:
        match = pattern.match(classifier)
        if match is not None:
            versions.append(match.group("version"))
    return versions


@nox.session(python=python_versions(), reuse_venv=True)
@nox.parametrize("django", django_versions())
def tests(session: nox.Session, django: str) -> None:
    # Django 6.0 is only supports Python 3.12 and above
    if session.python == "3.11" and django == "6.0.*":
        session.skip()

    # Python 3.14 only supported for Django 5.2 and above
    if session.python == "3.14" and django in {"5.0.*", "5.1.*"}:
        session.skip()

    env = {
        "POETRY_VIRTUALENVS_PATH": str(Path(session.virtualenv.bin).parent),
    }

    session.run_install("poetry", "install", "--all-extras", external=True, env=env)
    session.install(f"django=={django}")

    session.run("coverage", "run", "-m", "pytest", external="error")


if __name__ == "__main__":
    nox.main()
