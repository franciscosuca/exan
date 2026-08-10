# Batch Grammar Evaluation Migration

The migration to grammar-only batch evaluation is complete.

## Contract

- The route accepts files, provider, and feedback language.
- Every uploaded document receives exactly one grammar provider evaluation.
- Legacy multipart evaluation controls are ignored.
- Response identifiers, summaries, and grammar feedback remain stable.

## Implementation

- The route and service accept no selectable evaluation controls.
- The webapp submits only the supported multipart fields.
- Run logs record language, files, provider output, and timing.
- Architecture docs and the API example describe the grammar-only workflow.

## Validation

- Backend application modules compile successfully.
- The webapp production build passes.
