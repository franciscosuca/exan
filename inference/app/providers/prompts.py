"""Shared prompt templates for all providers."""

ANALYZE_STRUCTURE_PROMPT = """You are an expert at analyzing exam documents.
Look at this exam document and identify all questions.

For each question, determine:
1. The question number
2. The full question text
3. The question type: "multiple_choice", "open_ended", "true_false", or "fill_in_blank"
4. For multiple choice: list all available options (A, B, C, D, etc.)
5. Points value if shown

Return your analysis as JSON with this exact structure:
{
  "questions": [
    {
      "number": 1,
      "text": "What is the capital of France?",
      "type": "multiple_choice",
      "options": ["A) Paris", "B) London", "C) Berlin", "D) Madrid"],
      "points": 2
    }
  ]
}

Only return valid JSON, no other text."""

EXTRACT_ANSWERS_PROMPT = """You are an expert at reading filled-in exam answers.
Look at this completed exam and extract all answers that have been filled in.

For each answered question, identify:
1. The question number
2. The answer given (the selected option letter for multiple choice,
or the written text for open-ended)
3. Points value if shown

Return your extraction as JSON with this exact structure:
{
  "answers": [
    {
      "question_number": 1,
      "answer": "A",
      "points": 2
    }
  ]
}

Only return valid JSON, no other text."""


def grade_exam_prompt(exam_structure: dict, answer_key: dict) -> str:
    return f"""You are an expert exam grader. Look at this completed student exam and grade it.

The exam structure is:
{exam_structure}

The correct answer key is:
{answer_key}

For each question in the exam:
1. Identify what the student answered
2. Compare it to the correct answer
3. Determine if it is correct

For open-ended questions, use reasonable judgment - the answer doesn't need to be
word-for-word identical, just semantically correct.

Also try to identify the student's name if it appears on the exam.

Return your grading as JSON with this exact structure:
{{
  "student_name": "John Doe",
  "answers": [
    {{
      "question_number": 1,
      "student_answer": "A",
      "correct_answer": "A",
      "is_correct": true,
      "points_earned": 2,
      "points_possible": 2
    }}
  ]
}}

Only return valid JSON, no other text."""


# --- Batch Evaluation Prompts ---


def grammar_evaluation_prompt(
    correction_language: str | None = None,
    summary_language: str | None = None,
    *,
    language: str | None = None,
) -> str:
    """Build the grammar prompt while accepting the legacy ``language`` name."""
    correction_language = correction_language or language or "en"
    summary_language = summary_language or correction_language
    return f"""You are an expert language and grammar evaluator.

Analyze the following text for grammatical correctness, spelling, punctuation,
sentence structure, and overall writing quality in {correction_language}.

Provide:
1. A grammar object containing:
   - An issues array with one object for each issue. Each object must contain
    "original_text" (the exact original sentence or text) and
    "corrected_text" (the complete corrected sentence or text).
   - A plain-text summary of the overall grammar assessment.

Write every issue and correction in {correction_language}. Write the summary
in {summary_language}. Do not translate the original text merely to produce a
finding: preserve it exactly, except for the corresponding corrected text.
Do not use Markdown formatting or tables, including Markdown
table syntax, headings, bullets, asterisks, or code fences. The issues array is
the issue list: include exactly one JSON object (one row) per issue and do not
combine multiple issues in one object. If there are no issues, return an empty
issues array as "issues": [] and summarize that no grammar issues were found.
Keep the summary under 100 words.

Return your evaluation as JSON with this exact structure:
{{
  "grammar": {{
    "issues": [
      {{
        "original_text": "the complete original sentence or text",
        "corrected_text": "the complete corrected sentence or text"
      }}
    ],
    "summary": "The text is mostly well-written with minor issues."
  }}
}}

Only return valid JSON, no other text.

TEXT TO EVALUATE:
"""
