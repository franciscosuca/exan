# Structured Grammar Feedback Plan

## pre-requisites

- Scope structured feedback exclusively to grammar evaluation.
- Require a grammar-only provider response for batch feedback.
- Confirm grammar issue fields: `original_text` and `corrected_text`.
- Confirm grammar summary is one plain-text string.
- Derive the top-level batch summary from the grammar summary.
- Coordinate Python and React contract changes in one release.

## files to change

- `inference/app/models/__init__.py`
- `inference/app/providers/prompts.py`
- `inference/app/providers/gemini.py`
- `inference/app/services/batch_evaluation.py`
- `inference/tests/test_providers.py`
- `inference/tests/test_batch_evaluation.py` (new)
- `webapp/src/lib/api.ts`
- `webapp/src/components/BatchResults.tsx`
- `webapp/src/lib/i18n.tsx`
- `webapp/src/test/BatchResults.test.tsx` (new)
- `docs/ARCHITECTURE.md`
- `inference/examples/batch-evaluation.md`

## response contract

`BatchEvaluationResponse` keeps `id`, `results`, and `created_at`.
`FileEvaluationResult` contains an optional `grammar` object holding the table
rows and the summary. Its top-level `summary` mirrors the grammar summary.

### backend — `inference/app/models/__init__.py`

```python
class GrammarIssue(BaseModel):
    original_text: str  # exact fragment found in the document
    corrected_text: str  # recommended replacement


class GrammarFeedback(BaseModel):
    issues: list[GrammarIssue] = []
    summary: str = ""


class FileEvaluationResult(BaseModel):
    id: str
    filename: str
    summary: str
    grammar: GrammarFeedback | None = None
```

### frontend — `webapp/src/lib/api.ts`

```ts
export interface GrammarIssue {
  original_text: string;
  corrected_text: string;
}

export interface GrammarFeedback {
  issues: GrammarIssue[];
  summary: string;
}

export interface FileEvaluationResult {
  id: string;
  filename: string;
  summary: string;
  grammar?: GrammarFeedback | null;
}
```

### wire format

```json
{
  "id": "b1f0…",
  "created_at": "2026-08-08T10:12:04+00:00",
  "results": [
    {
      "id": "9c22…",
      "filename": "carta.docx",
      "summary": "El texto presenta errores ortográficos y de concordancia.",
      "grammar": {
        "issues": [
          { "original_text": "de la manara", "corrected_text": "de la manera" },
          { "original_text": "un perspectiva", "corrected_text": "una perspectiva" }
        ],
        "summary": "El texto presenta errores ortográficos y de concordancia."
      }
    }
  ]
}
```

### rendering rules

- `grammar.issues` renders one table row per item, columns `Issue found` and `Correction`.
- `grammar.summary` renders as a paragraph section below the table.
- Empty `issues` renders an explicit no-issues message, not an empty table.
- Absent or `null` `grammar` renders no grammar findings section.

## frontend component skeleton

Use this component inside `BatchResults` for each result's `grammar` object.
The production version should replace the default labels with `useLanguage()`
translation keys already used by the webapp.

```tsx
import { useId } from 'react';
import type { GrammarFeedback } from '../lib/api';

interface GrammarFeedbackTableProps {
  feedback: GrammarFeedback;
  issueLabel?: string;
  correctionLabel?: string;
  summaryLabel?: string;
  noIssuesLabel?: string;
}

export function GrammarFeedbackTable({
  feedback,
  issueLabel = 'Issue found',
  correctionLabel = 'Correction',
  summaryLabel = 'Summary',
  noIssuesLabel = 'No grammar issues found.',
}: GrammarFeedbackTableProps) {
  const headingId = useId();

  return (
    <section aria-labelledby={headingId} className="mt-6 space-y-3">
      <h4 id={headingId} className="text-base font-semibold text-gray-900">
        Grammar feedback
      </h4>

      {feedback.issues.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 font-semibold text-gray-700">
                  {issueLabel}
                </th>
                <th scope="col" className="px-4 py-3 font-semibold text-gray-700">
                  {correctionLabel}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {feedback.issues.map((item, index) => (
                <tr key={`${item.original_text}-${index}`}>
                  <td className="whitespace-pre-wrap px-4 py-3 align-top text-gray-700">
                    {item.original_text}
                  </td>
                  <td className="whitespace-pre-wrap px-4 py-3 align-top text-gray-700">
                    {item.corrected_text}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-gray-600" role="status">
          {noIssuesLabel}
        </p>
      )}

      <div className="rounded-lg bg-gray-50 p-4">
        <h5 className="mb-1 text-sm font-semibold text-gray-800">{summaryLabel}</h5>
        <p className="whitespace-pre-wrap text-sm text-gray-600">{feedback.summary}</p>
      </div>
    </section>
  );
}
```

`BatchResults` should render `<GrammarFeedbackTable feedback={result.grammar} />`
when structured grammar data exists. The batch response always supplies that
grammar object after validation.

## package recommendations

| Option | Recommendation | Reason |
| --- | --- | --- |
| Native HTML `<table>` + Tailwind | Recommended | No dependency; accessible and sufficient for two columns. |
| `@tanstack/react-table` | Future option | Add when sorting, filtering, pagination, or column visibility matters. |
| MUI Data Grid | Avoid for now | Adds a full design system for a small static table. |
| AG Grid | Avoid for now | Powerful enterprise features exceed this result's needs. |

Do not add a package for the initial implementation. Prefer the native table,
then introduce TanStack Table only when interaction requirements justify it.

## implementation

- Backend: Add `GrammarIssue` with original and corrected text fields.
- Backend: Add `GrammarFeedback` containing issues and summary.
- Backend: Add optional `grammar` field to `FileEvaluationResult`.
- Backend: Keep `BatchEvaluationResponse` top-level fields unchanged.
- Backend: Request issues and summary as JSON properties.
- Backend: Configure Gemini with the grammar response schema.
- Backend: Validate provider output before service-level mapping.
- Backend: Reject malformed grammar responses with actionable errors.
- Backend: Test valid, empty, and malformed grammar feedback.
- Frontend: Mirror grammar feedback interfaces in TypeScript.
- Frontend: Mark `grammar` optional on `FileEvaluationResult`.
- Frontend: Render grammar issues in a semantic table.
- Frontend: Display issue and correction columns responsively.
- Frontend: Add the reusable grammar table component skeleton.
- Frontend: Render grammar summary beneath the issues table.
- Frontend: Show an explicit no-issues state when empty.
- Frontend: Test tables, summaries, empty issues, and fallback.
- Documentation: Record the transitional grammar-only response contract.
- Verification: Run backend tests and Ruff checks.
- Verification: Run frontend tests, lint, and production build.
- Verification: Smoke-test Gemini grammar evaluation through Compose.
