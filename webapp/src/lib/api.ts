import { throwResponseError } from './response-error';

const API_BASE = '/api';

export type QuestionNumber = number | string;

export interface ExamStructure {
  id: string;
  filename: string;
  questions: Question[];
  created_at: string;
  criteria?: string | null;
}

export interface Question {
  number: QuestionNumber;
  text: string;
  type: 'multiple_choice' | 'open_ended' | 'true_false' | 'fill_in_blank';
  options?: string[];
}

export interface AnswerKey {
  id: string;
  exam_id: string;
  answers: Answer[];
  created_at: string;
}

export interface Answer {
  question_number: QuestionNumber;
  correct_answer: string;
}

export interface ComparisonResult {
  id: string;
  exam_id: string;
  student_name?: string;
  filename: string;
  answers: StudentAnswer[];
}

export interface StudentAnswer {
  question_number: QuestionNumber;
  student_answer: string;
  correct_answer: string;
  is_correct: boolean;
}

export interface ProviderConfig {
  provider: string;
  available: boolean;
  requires_api_key: boolean;
  is_local: boolean;
}

// --- Batch Evaluation Types ---

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

export interface BatchEvaluationResponse {
  id: string;
  results: FileEvaluationResult[];
  created_at: string;
}

// --- API Functions ---

export async function getProviders(): Promise<ProviderConfig[]> {
  const requestUrl = `${API_BASE}/providers`;
  const res = await fetch(requestUrl);
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Failed to fetch providers',
      method: 'GET',
      requestUrl,
    });
  }
  return res.json();
}

export async function uploadExamTemplate(
  file: File,
  provider: string,
  criteria?: string
): Promise<ExamStructure> {
  const form = new FormData();
  form.append('file', file);
  form.append('provider', provider);
  const normalizedCriteria = criteria?.trim();
  if (normalizedCriteria) {
    form.append('criteria', normalizedCriteria);
  }

  const requestUrl = `${API_BASE}/exam/template`;
  const res = await fetch(requestUrl, { method: 'POST', body: form });
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Upload failed',
      method: 'POST',
      requestUrl,
    });
  }
  return res.json();
}

export async function uploadAnswerKey(
  file: File,
  examId: string,
  provider: string
): Promise<AnswerKey> {
  const form = new FormData();
  form.append('file', file);
  form.append('exam_id', examId);
  form.append('provider', provider);

  const requestUrl = `${API_BASE}/exam/answer-key`;
  const res = await fetch(requestUrl, { method: 'POST', body: form });
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Upload failed',
      method: 'POST',
      requestUrl,
    });
  }
  return res.json();
}

export async function compareStudentExams(
  files: File[],
  examId: string,
  provider: string
): Promise<ComparisonResult[]> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('exam_id', examId);
  form.append('provider', provider);

  const requestUrl = `${API_BASE}/exam/compare`;
  const res = await fetch(requestUrl, { method: 'POST', body: form });
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Comparison failed',
      method: 'POST',
      requestUrl,
    });
  }
  return res.json();
}

export async function batchEvaluate(
  files: File[],
  provider: string,
  correctionLanguage: string,
  summaryLanguage: string
): Promise<BatchEvaluationResponse> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('provider', provider);
  form.append('correction_language', correctionLanguage);
  form.append('summary_language', summaryLanguage);

  const requestUrl = `${API_BASE}/batch/evaluate`;
  const res = await fetch(requestUrl, { method: 'POST', body: form });
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Evaluation failed',
      method: 'POST',
      requestUrl,
    });
  }
  return res.json();
}
