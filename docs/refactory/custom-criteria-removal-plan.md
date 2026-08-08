# Custom Criteria Removal Plan

Remove user-defined criteria from batch evaluation, leaving grammar evaluation as the supported scoring mode.

## pre-requisites

- Confirm grammar evaluation is the only required batch-evaluation mode.
- Decide whether obsolete `custom_criteria` requests should be rejected or ignored.
- Preserve existing batch response fields consumed by `BatchResults`.
- Ensure Python and webapp dependencies are installed.

## files to change

- `inference/app/api/routes/batch.py`
- `inference/app/services/batch_evaluation.py`
- `inference/app/models/__init__.py`
- `inference/app/providers/prompts.py`
- `inference/tests/test_batch_evaluation.py` (new)
- `inference/tests/test_providers.py`
- `inference/tests/test_run_logging.py`
- `webapp/src/components/BatchEvaluation.tsx`
- `webapp/src/lib/api.ts`
- `webapp/src/lib/i18n.tsx`
- `webapp/src/test/BatchEvaluation.test.tsx` (new)
- `docs/inference-api/INFERENCE_APP_LIFECYCLE.md`
- `docs/ARCHITECTURE.md`
- `inference/examples/batch-evaluation.md`
- `docs/todo.md`
- `docs/refactory/feature-renaming-plan.md`

## implementation

- Remove custom criteria parsing and validation from the batch route.
- Evaluate grammar once for every uploaded document.
- Remove custom criteria loops from the batch service.
- Remove the custom criteria prompt and unused request models.
- Preserve response scores, summaries, and result serialization.
- Remove custom criteria controls from the React workflow.
- Remove criteria types and multipart fields from the API client.
- Update batch-evaluation labels, descriptions, and translations.
- Add backend tests for grammar-only single-file evaluation.
- Add backend tests for grammar-only multi-file evaluation.
- Assert provider calls exclude custom criteria prompts and outputs.
- Test unsupported uploads and provider failures retain expected errors.
- Add frontend tests for grammar-only submission behavior.
- Verify frontend results still display scores and feedback.
- Update lifecycle, architecture, examples, and outstanding TODOs.
- Search code and documentation for stale criteria references.
- Run `cd inference && pytest`.
- Run `cd inference && ruff check app tests`.
- Run `cd webapp && npm test`.
- Run `cd webapp && npm run build`.
- Run `cd webapp && npm run lint`.
- Start Compose and smoke-test upload-to-results flow.
