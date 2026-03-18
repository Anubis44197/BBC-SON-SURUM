# Release Checklist v8.3.0

Repository: https://github.com/Anubis44197/BBC-SON-SURUM
Date: 2026-03-18

## Completed

- Main branch pushed to new repository.
- Release tag created and pushed: `v8.3.0`.
- Homebrew formula URL and SHA256 pinned.
- Chocolatey install URL and SHA256 pinned.
- Packaging metadata migrated to `pyproject.toml`.
- Debian packaging CI workflow added: `.github/workflows/debian-package-test.yml`.

## Pending (GitHub UI action)

- Open Actions tab and run workflow: **Debian Package Test** (workflow_dispatch).
- Confirm workflow succeeds on `main`.
- Create GitHub Release for tag `v8.3.0`.

## Checksums (pinned)

- tar.gz SHA256: `5c2e73f3e7fb873eb891feb5a6e5e7bb8a328cbbd1a8f4cc34ee2503ae925413`
- zip SHA256: `b5fc14ac471171ad59c8a77ea8b4250eccb72d9c5cc7fdfc355c277794eaa70e`

## Notes

- This environment does not have `gh` CLI authenticated, so workflow dispatch must be done from GitHub web UI.
