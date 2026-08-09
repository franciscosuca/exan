# Batch evaluation example

Evaluate one or more text documents using grammar and custom criteria:

```bash
curl -X POST http://localhost:8000/api/batch/evaluate \
  -F "provider=ollama" -F "language=en" -F "include_grammar=true" \
  -F 'custom_criteria=[]' -F "files=@essay.pdf"
```

Each model output, timing, and compact request snapshot is persisted under
`logs/batch-evaluation/<yymmddhhmm>/`.

With grammar enabled, each file result includes structured findings instead of
Markdown-formatted feedback:

```json
{
  "score": 78,
  "grammar": {
    "issues": [
      { "issue": "de la manara", "correction": "de la manera" }
    ],
    "summary": "El texto presenta un error ortografico."
  }
}
```

The webapp renders each issue as a row in the Detailed Findings table and the
summary in the How to Improve panel. Custom criteria continue using their
existing plain-text `feedback` field until that feature is removed.
