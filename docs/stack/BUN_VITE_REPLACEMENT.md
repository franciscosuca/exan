# Replacing Vite with Bun

## Summary

Replacing Vite with Bun for the webapp is **moderately difficult**. A prototype
could take less than a day, but a production-ready migration would likely take
2-4 engineering days including development workflow and container validation.
Removing Vitest as well would increase the estimate to roughly 3-5 days.

The project already uses Bun as its package manager and script runtime. Bun
currently starts Vite, while Vite provides the development server, React
integration, Tailwind processing, API proxy, and production bundle. Keeping
this combination is the lower-risk choice unless build speed or tool
consolidation is a measured problem.

## Current Responsibilities

| Responsibility | Current tool |
| --- | --- |
| Dependency installation and lockfile | Bun |
| Script execution | Bun |
| React development server and refresh | Vite |
| Tailwind CSS processing | `@tailwindcss/vite` |
| Local `/api` and `/api/auth` proxies | Vite |
| Production asset bundling | Vite |
| Unit and component tests | Vitest |
| Production static serving and API proxies | Nginx |

The Docker image already builds with Bun, but `bun run build` delegates to
`vite build`. Nginx then serves the generated `dist` directory.

## Migration Scope

A Bun-only app build would need to replace the following behavior:

1. Configure Bun's bundler with the HTML or TypeScript entry point.
2. Preserve React JSX transformation and development refresh behavior.
3. Add a supported Tailwind CSS build integration.
4. Recreate both local API proxy routes with the correct precedence.
5. Emit an Nginx-compatible `dist` directory with production assets.
6. Replace `vite/client` TypeScript types where necessary.
7. Move Vitest settings out of `vite.config.ts` if Vitest is retained.
8. Update development, build, preview, Docker, and CI commands.

There are no current `import.meta.env` usages, so environment-variable
compatibility is not a migration concern today.

### Retaining Vitest

Keeping Vitest limits changes to the app development and build workflow.
However, Vitest uses Vite internally, so this removes Vite as the app bundler
but does not eliminate it from the dependency tree. Test configuration should
move to a dedicated `vitest.config.ts`.

### Removing Vite Completely

Eliminating the Vite ecosystem also means replacing Vitest with `bun test` or
another test runner. The existing tests import Vitest APIs and use
`@testing-library/jest-dom/vitest`, so their imports, DOM setup, mocks, and CI
behavior would need compatibility work and regression testing.

## Pros

- Uses one primary tool for package management, scripts, serving, and builds.
- May improve cold-start and build times after benchmarking and tuning.
- Removes direct Vite and Vite plugin configuration from the app workflow.
- Makes Bun-native watch, server, and bundler APIs available directly.
- Reduces duplicated responsibility between the runtime and bundler.

## Cons

- Requires custom replacements for mature Vite plugin behavior.
- React refresh and Tailwind behavior may be less turnkey.
- The development API proxies must be implemented and maintained explicitly.
- A Bun-specific build setup reduces runtime portability.
- Keeping Vitest means Vite still exists transitively.
- Removing Vitest expands the migration into the test suite.
- Production behavior remains mostly unchanged because Nginx serves static
  output regardless of which bundler creates it.
- Migration effort may outweigh small speed improvements for this webapp.

## Recommended Approach

Keep Bun and Vite together for now. This already provides Bun's installation
and script performance while retaining Vite's React, Tailwind, proxy, and test
ecosystem.

If a full replacement is still desired, migrate incrementally:

1. Benchmark current development startup and production build times.
2. Prototype a Bun production build with identical `dist` output.
3. Validate routing, Tailwind output, source maps, and browser compatibility.
4. Add the Bun development server, API proxies, and React refresh.
5. Decide separately whether removing Vitest provides enough value.
6. Validate lint, tests, production build, Docker, and both API routes.

Proceed only if the prototype demonstrates a meaningful improvement over the
current setup without reducing development or testing reliability.