# Security Policy

Calix is an engineering preview. There is no published support window or security
response SLA. The application license and public repository are not yet selected.

## Reporting

Report a suspected vulnerability privately to the maintainer through the channel
where you obtained Calix. No public security email or private reporting URL has
been configured in this checkout. Once a public repository exists, its maintainer
should enable a private reporting channel before inviting vulnerability reports.

Include the affected version, operating system, minimal reproduction, impact and
any workaround. Do not include live credentials, private notebooks or an exploit
against someone else's system. Do not put a sensitive report into a public issue.

## Local API

The service binds to loopback and uses a per-connection token. Treat connection
files and `X-Calix-Token` as secrets. Do not publish them in logs, notebook text,
screen recordings, prompts or issue attachments. Do not expose the loopback
service through port forwarding or an unauthenticated proxy.

## Untrusted Inputs

Calix supports a restricted calculation language and process isolation, not a
general-purpose sandbox for hostile inputs. Resource limits reduce accidental
resource exhaustion but do not establish a security boundary for arbitrary
untrusted notebooks. Inspect notebooks and scripts before executing them.

For distribution, preserve third-party notices, verify the exact installer hash,
and review dependency advisories. Maintainers can use the checklist in
[release preparation](docs/RELEASING.md).
