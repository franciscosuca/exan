# Feature Renaming Plan

Rename the current workflows as follows:

- **Batch Evaluation** -> **Grammar Evaluation** (`Grammatikbewertung`)
- **Exam Comparison** -> **Test Comparison** (`Prüfungsvergleich`)

## pre-requisites

- Confirm canonical public endpoints: `/api/grammar-evaluation` and `/api/test-comparison`.
- Decide whether old `/api/batch` and `/api/exam` remain aliases.
- Grammar evaluation is the sole batch-evaluation mode.
- Decide whether new log directories require migration or coexistence.

## files to change

- `webapp/src/App.tsx`
- `webapp/src/lib/i18n.tsx`
- `webapp/src/lib/api.ts`
- `webapp/src/components/BatchEvaluation.tsx` -> `GrammarEvaluation.tsx`
- `webapp/src/components/BatchResults.tsx` -> `GrammarResults.tsx`
- `webapp/src/components/ExamComparison.tsx` -> `TestComparison.tsx`
- `webapp/src/components/LanguageSwitcher.tsx`
- `webapp/src/test/App.test.tsx`
- `inference/app/api/routes/batch.py` -> `grammar_evaluation.py`
- `inference/app/api/routes/exams.py` -> `test_comparison.py`
- `inference/app/services/batch_evaluation.py` -> `grammar_evaluation.py`
- `inference/app/services/exam_comparison.py` -> `test_comparison.py`
- `inference/app/api/dependencies.py`
- `inference/app/main.py`
- `inference/app/models/__init__.py`
- `inference/app/providers/__init__.py`
- `inference/app/providers/prompts.py`
- `inference/app/repositories/exam_repository.py`
- `inference/tests/test_api.py`
- `inference/tests/test_run_logging.py`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/inference-api/INFERENCE_APP_LIFECYCLE.md`
- `docs/PROVIDER_RUNTIME.md`
- `docs/scanning/OPTIONS.md`
- `docs/scanning/OPTION_3_SELECTION_CRITERIA.md`
- `docs/todo.md`
- `inference/examples/batch-evaluation.md` -> `grammar-evaluation.md`
- `inference/examples/exam-comparison.md` -> `test-comparison.md`

## implementation

- Confirm canonical labels and endpoint names.
- Rename frontend modes, components, imports, and translation keys.
- Set English labels to Grammar Evaluation and Test Comparison.
- Set German labels to Grammatikbewertung and Prüfungsvergleich.
- Rename backend modules, services, classes, and response types.
- Update API prefixes and frontend request paths consistently.
- Update run-log identifiers without rewriting historical logs.
- Rename examples and revise architecture documentation.
- Update frontend and backend tests for names and endpoints.
- Run webapp and inference tests; verify contracts.
