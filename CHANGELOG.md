# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- `requirements.txt` and `requirements-dev.txt` for dependencies
- Installed pre-commit hook for project
- `isort`, `end-of-file-fixer`, and `trailing-whitespace` hooks to pre-commit config
- Add `pyproject.toml` for `isort` configuration (due to `black`-`isort` conflicts)

### Changed
- `HISTORY.rst` renamed to `CHANGELOG.md` and now follows format of **Keep a Changelog**
- Updated versions of `black` and `flake8` in pre-commit config

## [0.1.0] - 2019-03-19
- Initial release


[Unreleased]: https://gitlab.esss.lu.se/ics-infrastructure/run-iocsh/compare/0.7.0...HEAD
