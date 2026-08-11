# Feature Renaming Plan

Rename workflow-facing names as follows:

- **Batch Evaluation** -> **Grammar Evaluation** (`Grammatikbewertung`)
- **Exam Comparison** remains **Exam Comparison** (`Prüfungsvergleich`)

This plan follows the completed grammar-only and structured-comparison refactors.

## pre-requisites

- [done] Grammar Evaluation is the only grammar workflow.
- [done] Legacy grading is now implemented as exam comparison.
- [done] Structured grammar issues and summaries are the current response contract.
- [done] Confirm canonical endpoints: `/api/grammar-evaluation` and `/api/exam-comparison`.
- [done] Keep `/api/batch` and `/api/exam` as identical compatibility aliases.
- [done] Retain Exam Comparison naming for internal workflow entities.
- [done] Use `grammar-evaluation` for new grammar logs and preserve historical logs.
- [done] Define separate inference model files by workflow domain.
- [done] Remove absent planned files from the implementation inventory.

## files to change

- `webapp/src/App.tsx`
- `webapp/src/lib/i18n.tsx`
- `webapp/src/lib/api.ts`
- `webapp/src/components/GrammarEvaluation.tsx`
- `webapp/src/components/GrammarResults.tsx`
- `webapp/src/components/ExamComparison.tsx` (retained name)
- `webapp/src/components/LanguageSwitcher.tsx`
- `webapp/src/lib/response-error.test.ts`
- `webapp/src/test/App.test.tsx`
- `webapp/src/test/api.test.ts`
- `webapp/src/test/GrammarResults.test.tsx`
- `inference/app/api/routes/grammar_evaluation.py`
- `inference/app/api/routes/exam_comparison.py`
- `inference/app/services/grammar_evaluation.py`
- `inference/app/services/exam_comparison.py` (retained module)
- `inference/app/api/dependencies.py`
- `inference/app/main.py`
- `inference/app/models/__init__.py` (re-export public model types)
- `inference/app/models/exam.py`
- `inference/app/models/comparison.py`
- `inference/app/models/grammar.py`
- `inference/app/models/provider.py`
- `inference/app/providers/__init__.py`
- `inference/app/providers/prompts.py`
- `inference/tests/test_api.py`
- `inference/tests/test_grammar_evaluation.py`
- `inference/tests/test_question_identifiers.py`
- `inference/tests/test_run_logging.py`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/inference-api/INFERENCE_APP_LIFECYCLE.md`
- `docs/PROVIDER_RUNTIME.md`
- `docs/scanning/OPTIONS.md`
- `docs/scanning/OPTION_3_SELECTION_CRITERIA.md`
- `inference/examples/grammar-evaluation.md`
- `inference/examples/exam-comparison.md` (retained name)

## implementation

- [done] Remove selectable criteria from grammar evaluation.
- [done] Adopt structured grammar issues and summaries.
- [done] Separate grammar feedback from exam comparison results.
- [done] Retain Exam Comparison as the workflow and domain name.
- [done] Confirm endpoint shapes and backward-compatibility policy.
- [done] Rename grammar surfaces; retain Exam Comparison names.
- [done] Set English labels and German labels consistently.
- [done] Rename grammar backend surfaces; retain Exam Comparison domain names.
- [done] Split inference models into separate domain files with stable exports.
- [done] Update frontend request paths and backend prefixes together.
- [done] Introduce new log identifiers without rewriting historical logs.
- [done] Rename examples and update active architecture documentation.
- [done] Run webapp and inference tests; verify endpoint contracts.
