# Security Policy

AI Company OS controls local AI tools that may read files, write files, and run shell
commands. Treat every deployment as a local automation system with real permissions.

## Supported Versions

This project is pre-1.0. Security fixes target the current `main` branch unless a stable
release branch is created later.

## Reporting a Vulnerability

Please do not open a public issue for vulnerabilities involving:

- command execution bypasses
- approval or reviewer policy bypasses
- credential or token leakage
- unsafe defaults around local files, shell commands, or adapter permissions

Report privately through
[GitHub Security Advisories](https://github.com/MarcelLeon/ai-company-os/security/advisories/new)
if available on the repository, or contact the maintainer through the GitHub profile
linked from the project owner.

We aim to acknowledge security reports within 72 hours and to ship a fix or mitigation
within 14 days for actively exploited issues.

Useful details:

- affected commit or version
- enabled adapters and channels
- relevant environment variables, with secrets redacted
- exact command or IM message that triggered the issue
- expected vs actual approval, audit, or permission behavior

## Security Boundaries

AICO is designed to put a control layer in front of local agents. It is not a sandbox by
itself.

- Adapters must declare capabilities.
- Risky tasks should enter `/approve` before execution.
- Audit events should record approvals, rejections, interruptions, and task outcomes.
- Local CLI tools may still have their own permissions, credentials, and side effects.

Do not expose a running AICO instance to untrusted chat participants or public web
callbacks without validating channel authentication, reviewer policy, and local machine
permissions.
