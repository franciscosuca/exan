import { afterEach, describe, expect, it, vi } from 'vitest';
import { throwResponseError } from './response-error';

describe('throwResponseError', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses a JSON detail and logs the raw response once', async () => {
    const rawBody = JSON.stringify({ detail: 'Provider unavailable' });
    const response = new Response(rawBody, {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'application/json' },
    });
    const readBody = vi.spyOn(response, 'text');
    const logError = vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(
      throwResponseError(response, {
        fallbackMessage: 'Request failed',
        method: 'GET',
        requestUrl: '/api/providers',
      }),
    ).rejects.toThrow('Provider unavailable');

    expect(readBody).toHaveBeenCalledTimes(1);
    expect(logError).toHaveBeenCalledWith('HTTP request failed', {
      requestUrl: '/api/providers',
      method: 'GET',
      status: 503,
      statusText: 'Service Unavailable',
      rawDetail: rawBody,
    });
  });

  it('uses a JSON error field', async () => {
    const response = new Response(JSON.stringify({ error: 'Invalid credentials' }), {
      status: 401,
      statusText: 'Unauthorized',
      headers: { 'Content-Type': 'application/json' },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(
      throwResponseError(response, {
        fallbackMessage: 'Login failed',
        method: 'POST',
        requestUrl: '/api/auth/login',
      }),
    ).rejects.toThrow('Invalid credentials');
  });

  it('uses a text response as the server detail', async () => {
    const response = new Response('Plain text failure', {
      status: 502,
      statusText: 'Bad Gateway',
      headers: { 'Content-Type': 'text/plain' },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});

    await expect(
      throwResponseError(response, {
        fallbackMessage: 'Evaluation failed',
        method: 'POST',
        requestUrl: '/api/batch/evaluate',
      }),
    ).rejects.toThrow('Plain text failure');
  });
});