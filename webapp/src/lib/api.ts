import { throwResponseError } from './response-error';

declare global {
  interface Window {
    __EXAN_API_BASE__?: string;
    __EXAN_API_SECRET__?: string;
  }
}

export function getApiBase(): string {
  return window.__EXAN_API_BASE__ || import.meta.env.VITE_API_BASE_URL || '/api';
}

function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const secret = window.__EXAN_API_SECRET__;
  if (!secret) return fetch(input, init);
  headers.set('Authorization', 'Bearer ' + secret);
  return fetch(input, { ...init, headers });
}

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
  const requestUrl = `${getApiBase()}/providers`;
  const res = await apiFetch(requestUrl);
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
  const requestUrl = `${getApiBase()}/providers/${encodeURIComponent(provider)}/models`;
  const res = await apiFetch(requestUrl);
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

  const requestUrl = `${getApiBase()}/exam-comparison/template`;
  const res = await apiFetch(requestUrl, { method: 'POST', body: form });
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

  const requestUrl = `${getApiBase()}/exam-comparison/answer-key`;
  const res = await apiFetch(requestUrl, { method: 'POST', body: form });
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
  const requestUrl = `${getApiBase()}/exam-comparison/answer-key/${encodeURIComponent(examId)}`;
  const res = await apiFetch(requestUrl, {
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

  const requestUrl = `${getApiBase()}/exam-comparison/compare`;
  const res = await apiFetch(requestUrl, { method: 'POST', body: form });
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

  const requestUrl = `${getApiBase()}/grammar-evaluation/evaluate`;
  const res = await apiFetch(requestUrl, { method: 'POST', body: form });
  if (!res.ok) {
    await throwResponseError(res, {
      fallbackMessage: 'Evaluation failed',
      method: 'POST',
      requestUrl,
    });
  }
  return res.json();
}
