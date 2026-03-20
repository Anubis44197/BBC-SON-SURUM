# Security Policy

## Supported Versions

The `main` branch is the primary supported line.

## Reporting a Vulnerability

Please do not open public issues for sensitive vulnerabilities.

Report security issues by contacting repository maintainers through private channels available on GitHub.
Include:

- Affected version/commit
- Reproduction details
- Impact assessment
- Suggested mitigation (if available)

## Response Process

- Acknowledgement target: within 72 hours
- Initial triage: severity and scope assessment
- Fix and validation: patch, tests, and release notes

## Scope

Security-sensitive areas include:

- File write/delete paths
- Daemon execution and command invocation
- Context/manifest integrity
- Injection and cleanup logic
