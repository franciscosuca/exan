import { afterEach, describe, expect, it, vi } from 'vitest';
import { batchEvaluate } from '../lib/api';

describe('batchEvaluate', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('submits separate correction and summary languages', async () => {
    const response = {
      id: 'batch-id',
      results: [],
      created_at: '2026-08-09T00:00:00Z',
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => response,
    } as Response);
    const file = new File(['essay'], 'essay.pdf', { type: 'application/pdf' });

    await batchEvaluate([file], 'ollama', 'es', 'de');

    const request = fetchMock.mock.calls[0]?.[1];
    const form = request?.body as FormData;
    expect(form.getAll('files')).toHaveLength(1);
    expect(form.get('provider')).toBe('ollama');
    expect(form.get('correction_language')).toBe('es');
    expect(form.get('summary_language')).toBe('de');
    expect(form.get('language')).toBeNull();
    expect(form.get('include_grammar')).toBeNull();
    expect(form.get('custom_criteria')).toBeNull();
  });
});