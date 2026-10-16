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
    venv = session.virtualenv.location
    env = {"UV_PROJECT_ENVIRONMENT": venv}

    # "uv sync" picks its own interpreter unless "--python" names one, and would replace
    # the virtualenv nox just made with one built from the first entry in ".python-version".
    session.run_install(
        "uv",
        "sync",
        "--all-extras",
        "--all-groups",
        "--python",
        venv,
        external=True,
        env=env,
    )

    # "uv sync" removes every package the lockfile does not name, pip included,
    # so the version under test is installed with uv as well.
    session.run_install(
        "uv",
        "pip",
        "install",
        "--python",
        venv,
        f"django=={django}",
        external=True,
    )

    session.run("coverage", "run", "--parallel-mode", "-m", "pytest", *session.posargs, external="error")

    # "coverage combine" consumes all parallel data files next to the data file it writes to.
    session.run("coverage", "combine", "--append")


if __name__ == "__main__":
    nox.main()
