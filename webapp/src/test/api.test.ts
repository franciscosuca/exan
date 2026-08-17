import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  compareStudentExams,
  grammarEvaluate,
  updateAnswerKey,
  uploadExamTemplate,
} from '../lib/api';

describe('compareStudentExams', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('posts student exams to the comparison endpoint', async () => {
    const response = [
      {
        id: 'comparison-id',
        exam_id: 'exam-id',
        student_name: 'Alice',
        filename: 'alice.pdf',
        answers: [
          {
            question_number: 1,
            student_answer: 'A',
            correct_answer: 'A',
            is_correct: true,
          },
        ],
      },
    ];
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => response,
    } as Response);
    const file = new File(['exam'], 'alice.pdf', { type: 'application/pdf' });

    await compareStudentExams([file], 'exam-id', 'ollama', 'gemini-2.5-flash');

    const [requestUrl, requestInit] = fetchMock.mock.calls[0] ?? [];
    expect(requestUrl).toBe('/api/exam-comparison/compare');
    expect(requestInit?.method).toBe('POST');
    const form = requestInit?.body as FormData;
    expect(form.getAll('files')).toHaveLength(1);
    expect(form.get('exam_id')).toBe('exam-id');
    expect(form.get('provider')).toBe('ollama');
    expect(form.get('model')).toBe('gemini-2.5-flash');
  });
});

describe('grammarEvaluate', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('submits separate correction and summary languages', async () => {
    const response = {
      id: 'grammar-evaluation-id',
      results: [],
      created_at: '2026-08-09T00:00:00Z',
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => response,
    } as Response);
    const file = new File(['essay'], 'essay.pdf', { type: 'application/pdf' });

    await grammarEvaluate([file], 'ollama', 'es', 'de', 'gemini-2.5-flash');

    const request = fetchMock.mock.calls[0]?.[1];
    const form = request?.body as FormData;
    expect(form.getAll('files')).toHaveLength(1);
    expect(form.get('provider')).toBe('ollama');
    expect(form.get('correction_language')).toBe('es');
    expect(form.get('summary_language')).toBe('de');
    expect(form.get('language')).toBeNull();
    expect(form.get('include_grammar')).toBeNull();
    expect(form.get('custom_criteria')).toBeNull();
      expect(form.get('model')).toBe('gemini-2.5-flash');
  });

  it('submits the optional exam question scope', async () => {
    const response = {
      id: 'exam-id',
      filename: 'exam.pdf',
      questions: [],
      created_at: '2026-08-10T00:00:00Z',
      criteria: 'B1 and B3 only',
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => response,
    } as Response);
    const file = new File(['exam'], 'exam.pdf', { type: 'application/pdf' });

    await uploadExamTemplate(file, 'ollama', '  B1 and B3 only  ', 'gemini-2.5-flash');

    const request = fetchMock.mock.calls[0]?.[1];
    const form = request?.body as FormData;
    expect(form.get('provider')).toBe('ollama');
    expect(form.get('model')).toBe('gemini-2.5-flash');
    expect(form.get('criteria')).toBe('B1 and B3 only');
  });
});

describe('updateAnswerKey', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('puts edited answers as JSON', async () => {
    const response = {
      id: 'answer-key-id',
      exam_id: 'exam-id',
      answers: [{ question_number: 'B1', correct_answer: 'A' }],
      created_at: '2026-08-10T00:00:00Z',
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => response,
    } as Response);
    const answers = [{ question_number: 'B1', correct_answer: 'A' }];

    await updateAnswerKey('exam-id', answers);

    const [requestUrl, requestInit] = fetchMock.mock.calls[0] ?? [];
    expect(requestUrl).toBe('/api/exam-comparison/answer-key/exam-id');
    expect(requestInit?.method).toBe('PUT');
    expect(requestInit?.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(JSON.parse(requestInit?.body as string)).toEqual({ answers });
  });
});