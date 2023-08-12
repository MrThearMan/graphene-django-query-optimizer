# Contributing

Thank you for your interest in contributing!

To start, please read the library [docs] thoroughly.
If you don't find what you are looking for, proceed with the steps below.

## I found a bug!

Please file a [bug report]. If you are not using the latest version of the library,
please upgrade and see if that fixes the issue. If not, please create a minimal example
that demonstrates the bug, and instructions on how to create that setup from a new virtual
environment. Also include any error tracebacks (unabridged when possible). This will help
a lot when diagnosing the bug. Do not use pictures to include the traceback.

## I have a feature request!

You can suggest new features to be implemented via a [feature request].
You can ask me to implement it, or work on it yourself, but all features should
be discussed and agreed upon first before any coding is done.

## I have a question!

Please ask it in the [discussions section] instead of creating an issue.
If your question warrants an issue, I'll ask you to create it.
Questions about clarifying documentation are appreciated!

## Creating a pull request

Once you have created a [feature request], we have agreed on an implementation,
and you wish to work on it, follow these steps to create a pull request.

1. [Fork the repository][fork].
2. Clone your fork and create a new branch from the `main` branch.
3. [Set up the environment][setup].
4. Make changes and write tests following [these guidelines][code-guidelines].
5. Add documentation when applicable following [these guidelines][docs-guidelines].
6. Push the changes to your fork.
7. Create a [pull request] targeting the main branch.
8. Sit back while your pull request is [reviewed].

Note that a pull request should always be aimed at solving a single issue.
If you want multiple issues solved, make separate pull requests for each.
Spelling mistakes are the exception, they are always welcome!

Pull requests should be kept as small as possible while following the guidelines
mentioned above. Smaller pull request are easier to review and test, which helps
them get merged.

## Code review process

Pull requests will be reviewed automatically and manually.

In the automated phase, [GitHub Actions] will run testing pipelines for all supported
operating systems and python versions, and [pre-commit CI] will check linting rules.
If you encounter any errors, try to fix them based on what the pipelines tell you.
If coverage is lowered, add tests, noting the guidelines [here][code-guidelines].
Don't be afraid to ask for advice if you're unsure what is wrong.

> Note for first-time contributors: Checks are not allowed to run automatically for
> first-time contributors, so you'll need me to approve them each time you push new code.

> Known issues: GitHub Actions might fail unexpectedly when installing dependencies.
> If this happens, the failed jobs need to be run again a few times to get past this.

In the manual phase, I will review the pull request by adding comments with suggestions
for changes. If you agree with the suggestions, implement them, and push the changes to
you fork; the pull request wil be updated automatically. You can either amend your previous
commits or add more commits, either is fine. If you disagree with the suggestions, provide
your reasons for disagreeing, and we can discuss what to do.

Once all automated checks have passed, and I have accepted the pull request, your code will be
merged to the `main` branch. Any related issues should be closed as completed.
I'll usually make a [new release] after each new feature, but if not, you can also ask for one.

## Creating a new release

1. Increment the version in `pyproject.toml` according [semantic versioning] rules.
2. Push the change to the `main` branch with the commit message `Bump version`.
3. [Draft a new release] on GitHub.
   - Use `v{version}` (e.g. v1.2.3) for the tag name, and `Release {version}` for
     the release title, using the same version that's in `pyproject.toml`.
   - Fill in the release description.
   - Add any attachments when applicable.
4. Publish the release. This will start the `release` pipeline on [GitHub Actions].
5. Check that the release pipeline was successful. If not, delete the tag from origin
   with `git push --delete origin {tag_name}` and fix the issue before trying again.

> Note, that the release will be made with the `pyproject.toml` version and not the
> `tag` version, and that this is not checked anywhere, so make sure they match!

## Setting up the environment

1. Install [Poetry].
2. Install [Make].
    - Windows: Install [Chocolatey] and then `choco install make`.
    - Mac: Install [Homebrew] and then `brew install make`.
    - Ubuntu: `apt install make`.
3. Run `poetry install` to create a virtual environment and install project dependencies.
4. Run `make hook` to install the [pre-commit] hooks.

Run `make help` to list all existing development commands and their descriptions.

## Testing

Tests can be run with `make tests`, and individual tests with `make test <test_name>`.
This will run tests in you [local environment][setup].

You can also test your code in multiple environments with [tox]. To do this, you must
install python interpreters for all python version the library supports, then run
`make tox`.

Linting can be run on-demand with `make pre-commit`, or automatically before commits
when installed with `make hook`

## Guidelines for writing code

- All code should be tested with 100% coverage
  - Do not write test simply to archive 100% coverage. Instead, write tests for all the ways the
    feature could be used (use cases), including ways that should not work, and then test for coverage.
    If you find uncovered code, see if you can remove it, or maybe you simply missed a use case.
    You should always need more tests to cover the all use cases than to achieve 100% coverage.
  - Comments that ignore test coverage (`# pragma: no cover`) should be used _**very**_ sparingly.
    They are often not necessary and can lead to undocumented behavior if you are not careful.

- All code should be typed when possible.
  - Tests are an exception to this; typing them is optional.
  - Make sure the typing methods used are supported in all python versions
    the library supports (e.g., use `List[int]` instead of `list[int]` for Python 3.8 support).
    CI will yell at you if you don't.
  - Create all custom types in `query_optimizer/typing.py` and import them from there.
    This avoids circular imports.
  - Use of `TypedDict` is encouraged where dicts would be used.
  - Also import common types like `List` from `query_optimizer/typing.py` instead of the built-in `typing` module.
    This is to make importing types more consistent across the codebase, and allows conditional import
    logic with the `typing_extensions` module for newer typing methods like `ParamSpec` to be contained
    in a single place.
  - Using `mypy` for static type checking is optional, and will likely lead to many "errors" detected.

- All functions, methods, and classes should include a docstring (*) in [reStructuredText format][pep287].
  - (*) Code that is short and _clearly_ self-documenting does not necessarily need a docstring.
    As a dumb example, `def sum(i: int, j: int) -> int: return i + j` does not need a docstring.
    This applies more broadly to arguments, e.g., when a function might need a docstring, the arguments
    might not need explicit documentation.
  - Keep the docstring to the point. Each line of documentation has a maintenance cost.
    Documentation is not an excuse to write code that is hard to understand.
    Docstrings should not include code examples, they belong to [docs].

- All code should be linted using the provided [pre-commit] hooks.
  - Easiest way to do this is to install the pre-commit hooks with `make hook`. This will make
    sure the pre-commit hooks will run automatically when you make a commit.
  - Comments that ignore linting rules (`# type: ignore`, `# fmt: off`, `# noqa`) should be used
    _**very**_ sparingly. They are often not necessary and can lead to undocumented behavior
    if you are not careful.

## Guidelines for writing documentation

- All documentation is written in `docs/` using markdown, and built with [mkdocs].
- Write in idiomatic english, using simple language.
- Keep examples simple and self-contained. Don't try to list all possible scenarios at once.
  Give the reader time to understand the basics before going over edge cases.
- Use markdown features, like [fenced code blocks][code block], [blockquotes], [horizontal rules],
  or [links], to emphasize and format text.
- If diagrams are needed, use [mermaid.js] inside a [fenced code block][code block].
- Break up lines around the 100 characters mark. This improves readability on wider monitors
  without adjusting the window size (and when not using text-wrapping).
- Do not use emojis.
- Double-check for spelling mistakes and grammar.

## License

By contributing, you agree that your contributions will be licensed under the [MIT Licence].


[docs]: https://mrthearman.github.io/graphene-django-query-optimizer/
[Issue]: https://github.com/MrThearMan/graphene-django-query-optimizer/issues/new/choose
[bug report]: https://github.com/MrThearMan/graphene-django-query-optimizer/issues/new?template=bug_report.yml
[feature request]: https://github.com/MrThearMan/graphene-django-query-optimizer/issues/new?template=feature_request.yml
[discussions section]: https://github.com/MrThearMan/graphene-django-query-optimizer/discussions
[pull request]: https://github.com/MrThearMan/graphene-django-query-optimizer/compare
[fork]: https://github.com/MrThearMan/graphene-django-query-optimizer/fork
[setup]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md#setting-up-the-environment
[tox]: https://tox.wiki/
[code-guidelines]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md#guidelines-for-writing-code
[docs-guidelines]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md#guidelines-for-writing-documentation
[reviewed]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md#code-review-process
[Github Actions]: https://github.com/features/actions
[pre-commit ci]: https://pre-commit.ci/
[new release]: https://github.com/MrThearMan/graphene-django-query-optimizer/blob/main/CONTRIBUTING.md#creating-a-new-release
[semantic versioning]: https://semver.org/
[Draft a new release]: https://github.com/MrThearMan/graphene-django-query-optimizer/releases/new
[poetry]: https://python-poetry.org/docs/#installation
[make]: https://man7.org/linux/man-pages/man1/make.1.html
[chocolatey]: https://chocolatey.org/install
[homebrew]: https://docs.brew.sh/Installation
[pre-commit]: https://pre-commit.com/
[pep287]: https://peps.python.org/pep-0287/
[mkdocs]: https://www.mkdocs.org/
[mermaid.js]: https://mermaid.js.org/
[code block]: https://www.mkdocs.org/user-guide/writing-your-docs/#fenced-code-blocks
[blockquotes]: https://www.markdownguide.org/basic-syntax#blockquotes-1
[horizontal rules]: https://www.markdownguide.org/basic-syntax#horizontal-rules
[links]: https://www.markdownguide.org/basic-syntax#links
[MIT Licence]: http://choosealicense.com/licenses/mit/
