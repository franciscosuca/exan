"""Shared prompt templates for all providers."""

ANALYZE_STRUCTURE_PROMPT = """You are an expert at analyzing exam documents.
Look at this exam document and identify all questions.

For each question, determine:
1. The question number
2. The full question text
3. The question type: "multiple_choice", "open_ended", "true_false", or "fill_in_blank"
4. For multiple choice: list all available options (A, B, C, D, etc.)

Return your analysis as JSON with this exact structure:
{
  "questions": [
    {
      "number": 1,
      "text": "What is the capital of France?",
      "type": "multiple_choice",
      "options": ["A) Paris", "B) London", "C) Berlin", "D) Madrid"]
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

Return your extraction as JSON with this exact structure:
{
  "answers": [
    {
      "question_number": 1,
      "answer": "A"
    }
  ]
}

Only return valid JSON, no other text."""


def _scope_instructions(criteria: str | None, *, persisted: bool = False) -> str:
    normalized = criteria.strip() if criteria else ""
    if not normalized:
        return ""

    criteria_label = "persisted user criteria" if persisted else "user criteria"
    return (
        "\n\nMANDATORY EVALUATION SCOPE:\n"
        f"The {criteria_label} is exactly:\n"
        "----- BEGIN USER CRITERIA -----\n"
        f"{normalized}\n"
        "----- END USER CRITERIA -----\n"
        "This scope is mandatory. Identify only the sections and questions requested "
        "by the criteria. Ignore all other visible content, even if it appears in the "
        "uploaded document. Do not include, extract, or compare any out-of-scope section "
        "or question."
    )


def analyze_exam_structure_prompt(criteria: str | None = None) -> str:
    """Build the structure prompt with an optional mandatory question scope."""
    return ANALYZE_STRUCTURE_PROMPT + _scope_instructions(criteria)


def extract_answers_prompt(criteria: str | None = None) -> str:
    """Build the answer-extraction prompt with an optional mandatory scope."""
    return EXTRACT_ANSWERS_PROMPT + _scope_instructions(criteria)


def compare_exam_prompt(exam_structure: dict, answer_key: dict) -> str:
    criteria = exam_structure.get("criteria") or answer_key.get("criteria")
    has_scope = bool(criteria and criteria.strip())
    scope_instructions = _scope_instructions(criteria, persisted=True)
    question_instruction = (
        "For each in-scope question only:" if has_scope else "For each question in the exam:"
    )
    output_scope_instruction = (
        "\nOnly include comparison results for questions in the mandatory scope. Do not "
        "output any question outside the persisted criteria."
        if has_scope
        else ""
    )

    return f"""You are an expert at comparing exam answers. Look at this completed student exam
  and compare it to the answer key.

{scope_instructions}

The exam structure is:
{exam_structure}

The correct answer key is:
{answer_key}

{question_instruction}
1. Identify what the student answered
2. Compare it to the correct answer
3. Determine if it is correct

For open-ended questions, use reasonable judgment - the answer doesn't need to be
word-for-word identical, just semantically correct.

Also try to identify the student's name if it appears on the exam.

Return your comparison as JSON with this exact structure:
{{
  "student_name": "John Doe",
  "answers": [
    {{
      "question_number": 1,
      "student_answer": "A",
      "correct_answer": "A",
      "is_correct": true
    }}
  ]
}}

{output_scope_instruction}
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
