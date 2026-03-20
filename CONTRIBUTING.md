# Contributing

Thanks for your interest in improving BBC.

## Development Setup

1. Clone the repository.
2. Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Run tests:

```bash
python -m pytest -q
```

## Branch and Commit Guidelines

- Keep commits focused and atomic.
- Use clear commit messages in imperative style.
- Avoid unrelated refactors in feature/fix commits.

## Pull Request Checklist

- Tests pass locally.
- User-facing docs are updated when behavior changes.
- New/changed commands are reflected in README and USER_GUIDE.
- No generated runtime artifacts are committed.

## Code Style

- Preserve existing project style and public APIs.
- Prefer minimal diffs.
- Add comments only where logic is non-obvious.

## Reporting Bugs

Open an issue with:

- Reproduction steps
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant logs from `.bbc/logs/`
