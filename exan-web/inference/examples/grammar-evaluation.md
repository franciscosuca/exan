# Grammar Evaluation example

Evaluate one or more text documents for grammar:

```bash
curl -X POST http://localhost:8000/api/grammar-evaluation/evaluate \
  -F "provider=ollama" -F "model=<model-id>" \
  -F "correction_language=en" -F "summary_language=en" \
  -F "files=@essay.pdf"
```

Each model output, timing, and compact request snapshot is persisted under
`logs/grammar-evaluation/<yymmddhhmm>/`.

With grammar enabled, each file result includes structured findings instead of
Markdown-formatted feedback:

```json
{
  "grammar": {
    "issues": [
      { "original_text": "de la manara", "corrected_text": "de la manera" }
    ],
    "summary": "El texto presenta un error ortografico."
  }
}
```

The webapp renders each issue as a row in the Detailed Findings table and the
summary in the How to Improve panel.
