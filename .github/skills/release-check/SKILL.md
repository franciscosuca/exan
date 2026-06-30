---
name: release-check
description: Single release validation skill (lint, test/build, cloud semantic-release run).
argument-hint: Run release checks before publishing.
user-invocable: true
---

# Release Check

Run one pre-release flow that validates app quality locally and release behavior in pipeline.

## Commands (repo root)
1. Install clean dependencies:
   `npm ci`
2. Type/lint check:
   `npm run lint`
3. Run tests if present:
   `npm test --if-present`
4. Build production bundle:
   `npm run build`
5. Validate semantic-release in cloud (manual run):
   Queue `pipelines/Semantic_Release.yml` in the pipeline of your selection

## Pass criteria
- Local commands exit with code `0`.
- Pipeline step `Run Semantic Release` succeeds.

## If it fails
- Report which command failed and include the error output.
- Do not release until checks pass.

## Output format
After running all checks, respond with a checklist using ✅ for pass and ❌ for fail. Keep the total response under 200 words.

**All passing example:**
✅ Install clean dependencies
✅ Type/lint check
✅ Tests
✅ Build production bundle
✅ Cloud semantic-release pipeline run

**On failure, stop the list at the failed step and show only the relevant error:**
✅ Install clean dependencies
✅ Type/lint check
❌ Build production bundle
```
<error message here>
```
Do not release until all checks pass.