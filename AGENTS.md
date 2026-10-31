# AGENTS.md — Autonomous development rules

## Mission
Improve LiDAR signal visualization in smnar-lidar-dashboard through a small, testable, reversible experiment. This branch is for an initial autonomous Codex Cloud trial; do not assume a two-hour prompt is an enforced runtime limit.

## Non-negotiable safety boundaries
- Never access real LiDAR, Licel, GRBL, laser, PMT, serial, USB, or instrument-network hardware. Use synthetic/replayed data and existing simulators only.
- Do not change instrument communication, acquisition timing, motion control, laser/PMT control, safety interlocks, or scientific processing algorithms and numerical results.
- Do not read, print, transmit, or modify secrets, credentials, .env contents, or instrument endpoints. The repository contains a tracked .env file: treat it as sensitive even if apparently benign. Never include secrets in logs, reports, or generated test fixtures.
- Do not push to main, merge pull requests, alter GitHub settings, or deploy.
- Do not delete features or change externally observable APIs without explicit authorization.
- Avoid unnecessary dependencies, internet/network calls, or architecture rewrites.

## Scope and workflow
1. Inspect the current Flask/UI plotting path and document observed bottlenecks, distinguishing measurements from hypotheses.
2. Implement the smallest useful responsive visualization improvement while preserving current behavior.
3. Add deterministic offline tests with synthetic or repository-provided non-sensitive data. Do not connect to hardware.
4. Run relevant existing and new tests. Capture commands, pass/fail status, and limitations.
5. Iterate on failures, up to three attempts per issue, then document unresolved blockers.
6. Write AGENT_REPORT.md: architecture, modified files, rationale, dependencies, test evidence, measured performance (only if actually measured), limitations, next steps.
7. Leave all work on this experimental branch or a task-specific branch; propose changes for review rather than merging.

## Acceptance criteria
- A reviewable, functional incremental visualization improvement or a clearly documented blocker.
- No changes to hardware-facing code or scientific algorithms.
- Offline test results recorded; no unsupported performance claims.
- Changes remain isolated from main and are easy to revert.

## Resource discipline
Aim for a bounded experiment of approximately two hours; this instruction is a planning target, not a real timeout. Prioritize a verifiable minimal result and final report over scope expansion.
