# Batch evaluation example

Evaluate one or more text documents using grammar and custom criteria:

```bash
curl -X POST http://localhost:8000/api/batch/evaluate \
  -F "provider=ollama" -F "language=en" -F "include_grammar=true" \
  -F 'custom_criteria=[]' -F "files=@essay.pdf"
```

Each model output, timing, and compact request snapshot is persisted under
`logs/batch-evaluation/<yymmddhhmm>/`.
