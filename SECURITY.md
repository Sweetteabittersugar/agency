# Security Policy

## Supported release

Security fixes target the latest GitHub source release. Version 0.5.0 is source-only and is not distributed through PyPI or npm.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting flow:

1. open the repository **Security** tab;
2. choose **Advisories**;
3. select **Report a vulnerability**.

Do not put a real API key, token, exploit payload containing a secret, or private project data in a public Issue. Include the affected commit or release, impact, reproduction steps with redacted data, and a suggested mitigation if available.

Reports are handled on a best-effort basis; no fixed response SLA is promised.

## Security model

- Agency listens on `127.0.0.1` by default.
- Non-loopback startup requires an explicitly configured `AGENCY_TOKEN`.
- User project access is limited to canonical paths under one or more `--project-root` arguments.
- Paths are resolved on each request so symlink and Windows junction targets are checked before use.
- API keys and prompt content are sent to the model provider selected by the user.
- Browser `localStorage` is exposed if the page has an XSS vulnerability.
- Without a Docker-backed feature, commands run with the current operating-system user's permissions.
- The local run ledger prevents concurrent runners and automatic replay of unresolved side effects; it does not prove whether an external side effect succeeded.
