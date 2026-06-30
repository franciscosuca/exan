---
name: react-minor-changes
description: Apply small React/TypeScript changes safely and return a concise, high-signal summary in a consistent style.
argument-hint: Implement minor React changes and validate with release-check
user-invocable: true
---

# React Minor Changes

Use this skill for low-risk, focused updates in React/TypeScript code (typically 1-3 files), where behavior should stay consistent and scope should stay small.

## Use When
- User asks for minor React/TS changes in existing components.
- User asks to align one screen/component with an existing pattern.
- User asks for a short final summary and release readiness validation.

## Workflow
1. Clarify intent from the user request and nearby code context.
2. Implement minimal edits:
   - Reuse existing patterns from the source page/step.
   - Prefer prop wiring over new abstractions for small changes.
   - Keep naming, spacing, and visual conventions aligned with surrounding code.
3. Report with a concise summary:
   - What was changed.
   - Why it was changed.

## Guardrails
- Keep scope tight; do not refactor unrelated code.
- Preserve existing UX/style patterns unless user asks otherwise.
- Avoid task-specific assumptions unless explicitly requested.
- If a check fails, report the failing step and key error.

## Output Template
Use this exact structure in the final response:

### Summary of Changes
- `<file path>`: `<what changed and why>`
- `<file path>`: `<what changed and why>`

### Result
- `Changes ready` or `Needs follow-up`

Keep the response short and practical (about 6-12 lines when possible).
