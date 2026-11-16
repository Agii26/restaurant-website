---
name: qa-bug-report
description: Writes a QA bug report in this project's standard format and saves it under docs/bugs/. Use when the user reports or describes a bug, or when a failing test or review exposes a defect.
---

# Writing a bug report

Save each report as `docs/bugs/BUG-NNN-short-slug.md`. NNN is the next free number (look in `docs/bugs/`). One bug per file.

## Template

```markdown
# BUG-NNN: <short title: what is wrong, in plain words>

| Field | Value |
|---|---|
| Severity | Critical / High / Medium / Low |
| Priority | P1 (fix now) / P2 (this sprint) / P3 (backlog) |
| Status | Open / Fixed / Verified |
| Found | <date>, by <review / test / manual testing> |
| OWASP 2025 | <category, if security related> |
| Verified by running? | Yes (how) / No (read from code only) |

## Summary
One or two sentences a non-technical person could understand.

## Steps to reproduce
1. Numbered, exact, starting from a clean state.

## Expected result
## Actual result
## Evidence
Test name and output, screenshot path, or log lines. Say plainly what was and was not run.

## Impact
Who is hurt and how.

## Suggested fix
## Regression test
Test name that proves it stays fixed (fill in once written).
```

## Severity guide
- **Critical**: money or customer data at risk, or the site can be taken over. Fix immediately.
- **High**: a core flow is broken or a security hole needs little effort to use.
- **Medium**: wrong behaviour with a workaround, or it blocks developer work.
- **Low**: cosmetic or minor, no real harm.

## Rules
- Be honest about what you verified. "Read from the code, not yet run" is a valid and important label.
- Reproduce before you report. A bug you cannot reproduce is a question, not a bug.
- Report the problem, not the person. Keep the tone neutral and factual.
