# Security Policy

## Supported Versions

Security fixes are provided for the latest minor line.

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| < 0.1.0 | No |

## Reporting a Vulnerability

Please do not disclose vulnerabilities in public issues.

Preferred channel:

1. Use GitHub private vulnerability reporting ("Security" -> "Report a vulnerability") when enabled for this repository.

Fallback channel:

2. Contact maintainers privately at `anton.f@synqra.tech` and include:
   - affected component and version,
   - reproduction steps,
   - impact assessment,
   - suggested fix (if available).

## What to Expect

- Initial acknowledgement target: within 72 hours.
- Triage/update target: within 7 days.
- Fix timeline depends on severity and complexity.

## Scope Notes

This repository handles integration and transport security concerns:

- API key/HMAC verification,
- replay protection,
- secure upstream transport and fail-closed behavior.

Upstream vulnerabilities in SGraph or Omega runtime should also be reported to their corresponding repositories/owners.
