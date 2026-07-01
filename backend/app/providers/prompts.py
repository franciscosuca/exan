"""Shared prompt templates for all providers."""

ANALYZE_STRUCTURE_PROMPT = """You are an expert at analyzing exam documents. Look at this exam document and identify all questions.

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

EXTRACT_ANSWERS_PROMPT = """You are an expert at reading filled-in exam answers. Look at this completed exam and extract all answers that have been filled in.

For each answered question, identify:
1. The question number
2. The answer given (the selected option letter for multiple choice, or the written text for open-ended)
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

For open-ended questions, use reasonable judgment - the answer doesn't need to be word-for-word identical, just semantically correct.

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


def grammar_evaluation_prompt(language: str) -> str:
    return f"""You are an expert language and grammar evaluator for {language}.

Analyze the following text for grammatical correctness, spelling, punctuation, sentence structure, and overall writing quality in {language}.

Evaluate on a scale of 0 to 100 where:
- 0% means the text is completely unintelligible, full of errors in every sentence, and impossible to understand
- 100% means the text is perfectly written with flawless grammar, spelling, punctuation, and natural flow

Provide:
1. A numeric score (0-100)
2. Detailed feedback explaining the errors found and suggestions for improvement

Return your evaluation as JSON with this exact structure:
{{
  "score": 85,
  "feedback": "The text is mostly well-written with minor issues: ..."
}}

Only return valid JSON, no other text.

TEXT TO EVALUATE:
"""


def custom_criteria_evaluation_prompt(
    criteria_name: str,
    description: str,
    zero_description: str,
    hundred_description: str,
) -> str:
    return f"""You are an expert evaluator. Evaluate the following text based on this specific criteria:

CRITERIA: {criteria_name}
DESCRIPTION: {description}

SCORING GUIDE:
- 0% (lowest score): {zero_description}
- 100% (highest score): {hundred_description}

Evaluate the text on a scale of 0 to 100 based strictly on the criteria above.

Provide:
1. A numeric score (0-100)
2. Detailed feedback explaining your assessment and how the text could improve

Return your evaluation as JSON with this exact structure:
{{
  "score": 75,
  "feedback": "The text demonstrates..."
}}

Only return valid JSON, no other text.

TEXT TO EVALUATE:
"""
