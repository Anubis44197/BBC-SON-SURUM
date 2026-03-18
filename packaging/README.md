# BBC Distribution Channels

This directory contains starter packaging templates for system package managers.

## Homebrew (macOS/Linux)

- Formula template: `homebrew/bbc.rb`
- `v8.3.0` URL and SHA256 are prefilled.
- For a new release, update `url` and `sha256` with that release artifact.
- Publish in a tap repository (for example `anubis44197/homebrew-bbc`).

## APT (Debian/Ubuntu)

- Debian packaging metadata: `debian/`
- Build package (example):
  - `chmod +x packaging/debian/rules`
  - `dpkg-buildpackage -us -uc`
- CI build test is provided in `.github/workflows/debian-package-test.yml`.

## Chocolatey (Windows)

- Package template: `choco/bbc.nuspec`
- Install script: `choco/tools/chocolateyinstall.ps1`
- `v8.3.0` ZIP URL and SHA256 are prefilled.
- Build package (example):
  - `choco pack packaging/choco/bbc.nuspec`

## Notes

- These are maintainer templates. For each new release, refresh URLs/checksums.
- BBC can already be installed with Python packaging (`pip install -e .`).
