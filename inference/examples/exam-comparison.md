# Exam comparison example

Upload a student exam after creating an exam template and answer key:

```bash
curl -X POST http://localhost:8000/api/exam/grade \
  -F "exam_id=<exam-id>" -F "provider=gemini" \
  -F "files=@student-exam.pdf"
```

The model response and compact request metadata are persisted under
`logs/exam-comparison/<yymmddhhmm>/`.
