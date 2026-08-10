# Feature Renaming Plan

Rename workflow-facing names as follows:

- **Batch Evaluation** -> **Grammar Evaluation** (`Grammatikbewertung`)
- **Exam Comparison** -> **Test Comparison** (`Prüfungsvergleich`)

This plan follows the completed grammar-only and structured-comparison refactors.

## pre-requisites

- [done] Grammar evaluation is the only batch-evaluation mode.
- [done] Legacy grading is now implemented as exam comparison.
- [done] Structured grammar issues and summaries are the current response contract.
- [pending] Confirm exact canonical route shapes for both workflows.
- [pending] Decide whether `/api/batch` and `/api/exam` remain aliases.
- [pending] Decide whether internal `exam_*` entities retain their domain names.
- [pending] Choose log-directory coexistence; preserve all historical logs.
- [pending] Define separate inference model files by workflow domain.
- [done] Remove absent `docs/todo.md` from the planned file inventory.

## files to change

- `webapp/src/App.tsx`
- `webapp/src/lib/i18n.tsx`
- `webapp/src/lib/api.ts`
- `webapp/src/lib/response-error.test.ts`
- `webapp/src/components/BatchEvaluation.tsx` -> `GrammarEvaluation.tsx`
- `webapp/src/components/BatchResults.tsx` -> `GrammarResults.tsx`
- `webapp/src/components/ExamComparison.tsx` -> `TestComparison.tsx`
- `webapp/src/components/LanguageSwitcher.tsx`
- `webapp/src/test/App.test.tsx`
- `webapp/src/test/api.test.ts`
- `webapp/src/test/BatchResults.test.tsx` -> `GrammarResults.test.tsx`
- `inference/app/api/routes/batch.py` -> `grammar_evaluation.py`
- `inference/app/api/routes/exams.py` -> `test_comparison.py`
- `inference/app/services/batch_evaluation.py` -> `grammar_evaluation.py`
- `inference/app/services/exam_comparison.py` -> `test_comparison.py`
- `inference/app/api/dependencies.py`
- `inference/app/main.py`
- `inference/app/models/__init__.py` (re-export public model types)
- `inference/app/models/exam.py`
- `inference/app/models/comparison.py`
- `inference/app/models/grammar.py`
- `inference/app/models/provider.py`
- `inference/app/providers/__init__.py`
- `inference/app/providers/prompts.py`
- `inference/app/repositories/exam_repository.py`
- `inference/tests/test_api.py`
- `inference/tests/test_batch_evaluation.py` -> `test_grammar_evaluation.py`
- `inference/tests/test_exam_scope.py`
- `inference/tests/test_question_identifiers.py`
- `inference/tests/test_providers.py`
- `inference/tests/test_run_logging.py`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/inference-api/INFERENCE_APP_LIFECYCLE.md`
- `docs/PROVIDER_RUNTIME.md`
- `docs/scanning/OPTIONS.md`
- `docs/scanning/OPTION_3_SELECTION_CRITERIA.md`
- `docs/refactory/structured-grammar-feedback-plan.md`
- `inference/examples/batch-evaluation.md` -> `grammar-evaluation.md`
- `inference/examples/exam-comparison.md` -> `test-comparison.md`

## implementation

- [done] Remove selectable criteria from grammar evaluation.
- [done] Adopt structured grammar issues and summaries.
- [done] Separate grammar feedback from exam comparison results.
- [pending] Confirm endpoint shapes and backward-compatibility policy.
- [pending] Rename frontend modes, components, translation keys, and tests.
- [pending] Set English labels and German labels consistently.
- [pending] Rename backend routes, services, response types, imports, and tests.
- [pending] Split inference models into separate domain files with stable exports.
- [pending] Update frontend request paths and backend prefixes together.
- [pending] Introduce new log identifiers without rewriting historical logs.
- [pending] Rename examples and update active architecture documentation.
- [pending] Run webapp and inference tests; verify endpoint contracts.
