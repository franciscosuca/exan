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

export interface ProviderModel {
  id: string;
  name: string;
  display_name: string;
  supported_actions: string[];
}

// --- Grammar Evaluation Types ---

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

export interface GrammarEvaluationResponse {
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

export async function getProviderModels(provider: string): Promise<ProviderModel[]> {
  const requestUrl = `${API_BASE}/providers/${encodeURIComponent(provider)}/models`;
  const res = await fetch(requestUrl);
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Failed to fetch models',
      method: 'GET',
      requestUrl,
    });
  }
  return res.json();
}

export async function uploadExamTemplate(
  file: File,
  provider: string,
  criteria: string | undefined,
  model: string
): Promise<ExamStructure> {
  const form = new FormData();
  form.append('file', file);
  form.append('provider', provider);
  form.append('model', model);
  const normalizedCriteria = criteria?.trim();
  if (normalizedCriteria) {
    form.append('criteria', normalizedCriteria);
  }

  const requestUrl = `${API_BASE}/exam-comparison/template`;
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
  provider: string,
  model: string
): Promise<AnswerKey> {
  const form = new FormData();
  form.append('file', file);
  form.append('exam_id', examId);
  form.append('provider', provider);
  form.append('model', model);

  const requestUrl = `${API_BASE}/exam-comparison/answer-key`;
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

export async function updateAnswerKey(examId: string, answers: Answer[]): Promise<AnswerKey> {
  const requestUrl = `${API_BASE}/exam-comparison/answer-key/${encodeURIComponent(examId)}`;
  const res = await fetch(requestUrl, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Failed to save answer key',
      method: 'PUT',
      requestUrl,
    });
  }
  return res.json();
}

export async function compareStudentExams(
  files: File[],
  examId: string,
  provider: string,
  model: string
): Promise<ComparisonResult[]> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('exam_id', examId);
  form.append('provider', provider);
  form.append('model', model);

  const requestUrl = `${API_BASE}/exam-comparison/compare`;
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

export async function grammarEvaluate(
  files: File[],
  provider: string,
  correctionLanguage: string,
  summaryLanguage: string,
  model: string
): Promise<GrammarEvaluationResponse> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('provider', provider);
  form.append('model', model);
  form.append('correction_language', correctionLanguage);
  form.append('summary_language', summaryLanguage);

  const requestUrl = `${API_BASE}/grammar-evaluation/evaluate`;
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
