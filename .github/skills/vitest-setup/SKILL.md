---
name: vitest-setup
description: Bootstrap or maintain a Vitest unit/component test suite for React/TypeScript projects. Use when setting up Vitest from scratch, fixing a broken test configuration, or running the full unit test suite before a release.
argument-hint: Bootstrap or run Vitest tests for this project.
user-invocable: true
---

# Vitest Setup & Maintenance

Use this skill to install, configure, and run Vitest for React/TypeScript projects, or to verify an existing setup before releasing.

## Use When

- Vitest is not yet configured in the project.
- The test configuration is broken or outdated.
- User asks to run unit or component tests as part of a release check.

## Workflow

### 1. Check existing setup

```bash
cat package.json | grep -E '"test"|"vitest"'
ls vitest.config.* vite.config.* 2>/dev/null
```

### 2. Bootstrap (run only when Vitest is missing)

#### Install dependencies

```bash
npm install --save-dev vitest @vitest/coverage-v8 jsdom \
  @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

#### Add test scripts to `package.json`

```json
"test": "vitest",
"test:coverage": "vitest run --coverage"
```

#### Create `vitest.config.ts`

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
});
```

> If a `vite.config.ts` already exists, merge the `test` block into it rather than creating a separate file.

#### Create `src/test/setup.ts`

```ts
import '@testing-library/jest-dom';
```

### 3. Run tests

```bash
# Run in watch mode (development)
npm test

# Run once and exit (CI / release gate)
npx vitest run

# Run with coverage
npm run test:coverage
```

### 4. Verify

- All tests pass with exit code `0`.
- Coverage report is generated under `coverage/`.

## Pass Criteria

- `npx vitest run` exits with code `0`.
- No configuration errors in `vitest.config.ts`.

## If It Fails

- Report which test or config step failed with the full error output.
- Do not proceed to release until all tests pass.

## Output Format

After running all checks, respond with a checklist using ✅ for pass and ❌ for fail:

✅ Dependencies installed  
✅ `vitest.config.ts` present  
✅ `src/test/setup.ts` present  
✅ `npm run test:coverage` exits 0  

**On failure, stop at the failed step and show the relevant error.**  
Do not release until all checks pass.
