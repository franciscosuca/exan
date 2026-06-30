# Copilot Instructions (General)

These instructions are project-agnostic and should apply to most repositories.

## Safety and Workflow

- Never call task_complete automatically. Always wait for the user to explicitly confirm the task is done before marking it complete.
- Never merge changes to `main` directly. Always commit to the current working branch.
- In agent mode, do not create commits. Only edit files requested by the user.
- Prefer small, reversible changes and validate with the narrowest relevant checks first.
- Preserve existing conventions unless the user asks for a broader refactor.

## Context Gathering

- Before implementation, inspect the local project context (for example: `README`, package/tooling files, project-level instructions).
- If any assumption is required, stop and ask the user clarifying questions before implementing.
- Do not assume missing requirements, inputs, constraints, or expected behavior.

## Context Reuse and Token Efficiency

- Reuse previously gathered context in the same session whenever still valid.
- Do not re-scan the full project if required files were already analyzed.
- Re-scan only when:
	- user explicitly asks for a fresh scan
	- new commits or edits invalidate earlier findings
	- the task scope changes to new areas
- Prefer targeted, diff-based, or file-scoped reads over repository-wide scans.

## Agent Discovery and Recommendation

- Check whether task-specific agents exist (for example under `.github/agents/`).
- If a matching agent exists, suggest using it and explain why it fits the task.
- If no suitable agent exists, proceed normally with direct implementation.

## Design-System-Aware Behavior

- For UI, styling, or layout tasks, look for a design specification before making visual changes.
- Prefer `DESIGN.md` when present (commonly at project root, `.github/DESIGN.md`, or feature design folders).
- If no design spec exists, preserve current visual language and avoid introducing a conflicting style.

## Commit and PR Conventions

- **Format**: All commits and PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/).
- **Types**: Use specific types defined in `.releaserc.json` to trigger the correct release:
  - `feat`: Minor release (new features).
  - `fix`, `perf`, `refactor`, `style`: Patch release (bug fixes, performance, code changes).
  - `chore`, `docs`, `test`, `ci`, `build`: No release (maintenance and documentation).
- **Breaking Changes**: Use `!` after the type (e.g., `feat!:`) and include `BREAKING CHANGE:` in the footer for major releases.
- **PR Titles**: Ensure the PR title is also a valid conventional commit message, as it is often used for the final squashed commit.

## Response Style

- Keep responses non-chatty and task-focused.
- Output only:
	- files changed
	- reason for each file change
	- final summary of results (only when more than 1 file changed)
- If exactly 1 file changed, do not include a summary.
- If more than 1 file changed, keep the final summary under 50 words.
- If no files changed, state that in one short sentence.