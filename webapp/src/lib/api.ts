const API_BASE = '/api';

export interface ExamStructure {
  id: string;
  filename: string;
  questions: Question[];
  created_at: string;
}

export interface Question {
  number: number;
  text: string;
  type: 'multiple_choice' | 'open_ended' | 'true_false' | 'fill_in_blank';
  options?: string[];
  points?: number;
}

export interface AnswerKey {
  id: string;
  exam_id: string;
  answers: Answer[];
  created_at: string;
}

export interface Answer {
  question_number: number;
  correct_answer: string;
  points: number;
}

export interface GradingResult {
  id: string;
  exam_id: string;
  student_name?: string;
  filename: string;
  total_score: number;
  max_score: number;
  percentage: number;
  answers: StudentAnswer[];
}

export interface StudentAnswer {
  question_number: number;
  student_answer: string;
  correct_answer: string;
  is_correct: boolean;
  points_earned: number;
  points_possible: number;
}

export interface ProviderConfig {
  provider: string;
  available: boolean;
  requires_api_key: boolean;
  is_local: boolean;
}

// --- Batch Evaluation Types ---

export interface EvaluationCriteria {
  name: string;
  description: string;
  zero_description: string;
  hundred_description: string;
}

export interface CriteriaScore {
  criteria_name: string;
  score: number;
  feedback: string;
}

export interface GrammarIssue {
  issue: string;
  correction: string;
}

export interface GrammarFeedback {
  issues: GrammarIssue[];
  summary: string;
}

export interface FileEvaluationResult {
  id: string;
  filename: string;
  scores: CriteriaScore[];
  overall_score: number;
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
  const res = await fetch(`${API_BASE}/providers`);
  if (!res.ok) throw new Error('Failed to fetch providers');
  return res.json();
}

export async function uploadExamTemplate(
  file: File,
  provider: string
): Promise<ExamStructure> {
  const form = new FormData();
  form.append('file', file);
  form.append('provider', provider);

  const res = await fetch(`${API_BASE}/exam/template`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
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

  const res = await fetch(`${API_BASE}/exam/answer-key`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function uploadStudentExams(
  files: File[],
  examId: string,
  provider: string
): Promise<GradingResult[]> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('exam_id', examId);
  form.append('provider', provider);

  const res = await fetch(`${API_BASE}/exam/grade`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Grading failed' }));
    throw new Error(err.detail || 'Grading failed');
  }
  return res.json();
}

export async function batchEvaluate(
  files: File[],
  provider: string,
  language: string,
  includeGrammar: boolean,
  customCriteria: EvaluationCriteria[]
): Promise<BatchEvaluationResponse> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  form.append('provider', provider);
  form.append('language', language);
  form.append('include_grammar', includeGrammar ? 'true' : 'false');
  form.append('custom_criteria', JSON.stringify(customCriteria));

  const res = await fetch(`${API_BASE}/batch/evaluate`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Evaluation failed' }));
    throw new Error(err.detail || 'Evaluation failed');
  }
  return res.json();
}
