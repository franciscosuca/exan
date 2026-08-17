### pre-requisites
- Install Bun 1.2+ on local machines and CI runners.
- Confirm Node 20 stays available for non-Bun tooling.
- Decide lockfile policy: keep `bun.lock` as single source.
- Validate Bun compatibility for Vite, Vitest, oxlint, Tailwind, semantic-release.
- Token estimate (Sonnet5, effort medium): 25k-45k total tokens.

### files to change
- `webapp/package-lock.json` (remove after Bun lock validation)
- `webapp/bun.lock` (new lockfile from `bun install`)
- `package.json` (root scripts from npm to `bun run`)
- `README.md` (all webapp npm commands to Bun commands)
- `webapp/Dockerfile` (Bun image and `bun install` / `bun run build`)
- `.github/workflows/test-pipeline.yml` (Bun cache/install/lint/test)
- `.github/workflows/build-and-release.yml` (Bun cache/install/test/build)
- `.releaserc.json` (track `webapp/bun.lock` alongside the root `package-lock.json`)

### implementation
- Install Bun; verify with `bun --version` locally and in CI.
- Run `bun install` in `webapp` to generate `bun.lock`.
- Remove `webapp/package-lock.json` after deterministic install validation.
- Update root scripts to use `bun run` commands.
- Replace README webapp setup/test snippets with Bun equivalents.
- Update webapp Dockerfile to Bun base and build commands.
- Change workflow cache keys to `webapp/bun.lock`.
- Replace CI install/test/build commands with Bun script invocations.
- Update semantic-release asset list to include `webapp/bun.lock`.
- Run lint, tests, and build using Bun end-to-end.
