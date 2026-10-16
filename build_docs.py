from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
import uuid
from functools import cache
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT_DIR = Path(__file__).parent
CONFIG_FILE = ROOT_DIR / "zensical.toml"
DOCS_DIR = ROOT_DIR / "docs"
SNIPPETS_DIR = DOCS_DIR / "snippets"
SITE_DIR = ROOT_DIR / "site"

# Zensical has no `exclude_docs` setting, so anything not meant to be served is removed after the build.
EXCLUDED_SUFFIXES = frozenset({".py"})
EXCLUDED_DIRECTORIES = frozenset({"snippets", "overrides"})

CACHEABLE_SUFFIXES = frozenset({".css", ".js", ".json", ".svg", ".png", ".ico", ".woff", ".woff2", ".xml"})

LLMS_FILE_NAME = "llms.txt"
SITEMAP_FILE_NAME = "sitemap.xml"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
FRONT_MATTER_PATTERN = re.compile(r"\A---\n(?P<front_matter>.*?)\n---\n", flags=re.DOTALL)
DESCRIPTION_PATTERN = re.compile(r"^description:\s*(?P<description>.+?)\s*$", flags=re.MULTILINE)
SNIPPET_MARKER = "-8<-"
SNIPPET_PATTERN = re.compile(r'^(?P<indent>[ \t]*)-8<-\s+"(?P<path>[^"]+)"[ \t]*$')

SERVICE_WORKER_NAME = "service-worker.js"
# The placeholders include their quotes and brackets so that the template is valid JavaScript
# before this step runs. An unprocessed worker then removes itself instead of failing to install.
CACHE_NAME_PLACEHOLDER = '"__CACHE_NAME__"'
URLS_TO_CACHE_PLACEHOLDER = '["__URLS_TO_CACHE__"]'


class DocsBuildError(Exception):
    """Raised when the documentation site cannot be built."""


def main() -> int:
    process = subprocess.run([sys.executable, "-m", "zensical", "build", "--clean", "--strict"], check=False)
    if process.returncode != 0:
        return process.returncode

    if not SITE_DIR.is_dir():
        msg = f"Site directory not found: {SITE_DIR}"
        raise DocsBuildError(msg)

    remove_excluded_files(SITE_DIR)
    write_markdown_pages(SITE_DIR)
    write_llms_file(SITE_DIR)
    add_llms_file_to_sitemap(SITE_DIR)
    write_service_worker(SITE_DIR)
    return 0


def remove_excluded_files(site_dir: Path) -> None:
    for path in sorted(site_dir.rglob("*"), reverse=True):
        if path.is_dir():
            if not any(path.iterdir()):
                path.rmdir()
            continue

        relative_path = path.relative_to(site_dir)
        excluded_by_suffix = path.suffix in EXCLUDED_SUFFIXES
        excluded_by_directory = bool(set(relative_path.parts[:-1]) & EXCLUDED_DIRECTORIES)
        if excluded_by_suffix or excluded_by_directory:
            path.unlink()


def write_markdown_pages(site_dir: Path) -> None:
    """Write each page's Markdown source next to its HTML, so agents can read the docs without parsing HTML."""
    for source_file in sorted(DOCS_DIR.glob("*.md")):
        # Every page needs a description, since it is what `llms.txt` gives an agent to pick pages by.
        read_description(source_file)

        markdown_file = site_dir / source_file.name
        markdown_file.write_text(expand_snippets(source_file), encoding="utf-8")


def expand_snippets(source_file: Path) -> str:
    """Inline the snippet files a page includes, since a served Markdown file has nothing to resolve them."""
    lines: list[str] = []

    for line in source_file.read_text(encoding="utf-8").splitlines():
        if SNIPPET_MARKER not in line:
            lines.append(line)
            continue

        match = SNIPPET_PATTERN.match(line)
        if match is None:
            msg = f"Unsupported snippet syntax in {source_file}: {line!r}"
            raise DocsBuildError(msg)

        snippet_file = SNIPPETS_DIR / match["path"]
        if not snippet_file.is_file():
            msg = f"Snippet file not found: {snippet_file}"
            raise DocsBuildError(msg)

        indent = match["indent"]
        lines += [indent + snippet_line for snippet_line in snippet_file.read_text(encoding="utf-8").splitlines()]

    return "\n".join(lines) + "\n"


def write_llms_file(site_dir: Path) -> None:
    """Write an `llms.txt` index, which is where agents look for the Markdown versions of the pages."""
    config = read_config()
    site_url = config["site_url"].rstrip("/")

    lines = [
        f"# {config['site_name']}",
        "",
        f"> {config['site_description']}",
        "",
        "## Docs",
        "",
    ]

    for nav_item in config["nav"]:
        title, page = next(iter(nav_item.items()))
        description = read_description(DOCS_DIR / page)
        lines.append(f"- [{title}]({site_url}/{page}): {description}")

    (site_dir / LLMS_FILE_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_llms_file_to_sitemap(site_dir: Path) -> None:
    """Add `llms.txt` to the sitemap, since the sitemap only lists the pages the site navigation renders."""
    sitemap_file = site_dir / SITEMAP_FILE_NAME
    if not sitemap_file.is_file():
        msg = f"Sitemap file not found: {sitemap_file}"
        raise DocsBuildError(msg)

    site_url = read_config()["site_url"].rstrip("/")

    # Registering the empty prefix keeps the sitemap namespace as the default one, as the schema requires.
    ET.register_namespace("", SITEMAP_NAMESPACE)
    tree = ET.parse(sitemap_file)  # noqa: S314  # The sitemap is our own build output, not untrusted input.

    url_element = ET.SubElement(tree.getroot(), f"{{{SITEMAP_NAMESPACE}}}url")
    location_element = ET.SubElement(url_element, f"{{{SITEMAP_NAMESPACE}}}loc")
    location_element.text = f"{site_url}/{LLMS_FILE_NAME}"

    ET.indent(tree)
    tree.write(sitemap_file, encoding="utf-8", xml_declaration=True)


@cache
def read_config() -> dict[str, Any]:
    return tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))["project"]


@cache
def read_description(source_file: Path) -> str:
    """Read a page's front matter description. Raises if the page does not have one."""
    front_matter = FRONT_MATTER_PATTERN.match(source_file.read_text(encoding="utf-8"))
    match = None if front_matter is None else DESCRIPTION_PATTERN.search(front_matter["front_matter"])
    description = "" if match is None else match["description"].strip("\"'").strip()

    if not description:
        msg = (
            f"Page is missing a front matter description: {source_file.relative_to(ROOT_DIR)}\n"
            f"Add one to the top of the file:\n"
            f"---\n"
            f"description: <what the page is about>\n"
            f"---"
        )
        raise DocsBuildError(msg)

    return description


def write_service_worker(site_dir: Path) -> None:
    service_worker_file = site_dir / SERVICE_WORKER_NAME
    if not service_worker_file.is_file():
        msg = f"Service worker file not found: {service_worker_file}"
        raise DocsBuildError(msg)

    urls_to_cache = collect_cacheable_urls(site_dir)

    file_data = service_worker_file.read_text(encoding="utf-8")
    # A fresh cache name on every build stops browsers from serving the previous build from cache.
    file_data = file_data.replace(CACHE_NAME_PLACEHOLDER, json.dumps(uuid.uuid4().hex))
    file_data = file_data.replace(URLS_TO_CACHE_PLACEHOLDER, json.dumps(urls_to_cache, indent=2))
    service_worker_file.write_text(file_data, encoding="utf-8")


def collect_cacheable_urls(site_dir: Path) -> list[str]:
    urls: set[str] = set()

    for path in site_dir.rglob("*"):
        if not path.is_file() or path.name == SERVICE_WORKER_NAME:
            continue

        relative_path = path.relative_to(site_dir)

        if path.name == "index.html":
            # Relative URLs resolve against the service worker's URL, so the site root must be "./", not "".
            parent = relative_path.parent.as_posix()
            urls.add("./" if parent == "." else f"{parent}/")
        elif path.suffix in CACHEABLE_SUFFIXES:
            urls.add(relative_path.as_posix())

    urls.add("404.html")
    return sorted(urls)


if __name__ == "__main__":
    sys.exit(main())
