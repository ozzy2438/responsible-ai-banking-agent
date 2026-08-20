# Security Policy

This repository contains a synthetic reference application, not a live bank.
Do not submit real customer data, account credentials, card credentials,
authentication secrets, or production connection details in an issue.

Report suspected vulnerabilities privately through GitHub's private
vulnerability reporting feature when available. Otherwise contact the repository
owner through a private channel. Include reproduction steps using synthetic data.

The following are release blockers:

- unauthorised cross-customer disclosure;
- exposure or persistence of passwords, PINs, CVVs, tokens, or full card data;
- a high-risk request receiving an autonomous decision;
- any path that mutates synthetic financial records through the app role;
- non-append-only audit behaviour;
- an image without verifiable provenance for a published release candidate.
