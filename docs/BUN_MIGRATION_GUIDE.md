### pre-requisites
- Install Bun 1.2+ on local machines and CI runners.
- Confirm Node 20 stays available for non-Bun tooling.
- Decide lockfile policy: keep `bun.lock` as single source.
- Validate Bun compatibility for Vite, Vitest, oxlint, Tailwind, semantic-release.
- Token estimate (Sonnet5, effort medium): 25k-45k total tokens.

### files to change
- `frontend/package-lock.json` (remove after Bun lock validation)
- `frontend/bun.lock` (new lockfile from `bun install`)
- `package.json` (root scripts from npm to `bun run`)
- `README.md` (all frontend npm commands to Bun commands)
- `frontend/Dockerfile` (Bun image and `bun install` / `bun run build`)
- `.github/workflows/test-pipeline.yml` (Bun cache/install/lint/test)
- `.github/workflows/build-and-release.yml` (Bun cache/install/test/build)
- `.releaserc.json` (track `bun.lock` instead of `package-lock.json`)

### implementation
- Install Bun; verify with `bun --version` locally and in CI.
- Run `bun install` in `frontend` to generate `bun.lock`.
- Remove `frontend/package-lock.json` after deterministic install validation.
- Update root scripts to use `bun run` commands.
- Replace README frontend setup/test snippets with Bun equivalents.
- Update frontend Dockerfile to Bun base and build commands.
- Change workflow cache keys to `frontend/bun.lock`.
- Replace CI install/test/build commands with Bun script invocations.
- Update semantic-release asset list to include `bun.lock`.
- Run lint, tests, and build using Bun end-to-end.
