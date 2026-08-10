export interface ResponseErrorOptions {
  fallbackMessage: string;
  method?: string;
  requestUrl: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function parseResponseErrorDetail(rawBody: string): string | undefined {
  const trimmedBody = rawBody.trim();

  if (!trimmedBody) {
    return undefined;
  }

  try {
    const payload: unknown = JSON.parse(trimmedBody);

    if (isRecord(payload)) {
      if (typeof payload.detail === 'string' && payload.detail.trim()) {
        return payload.detail;
      }

      if (typeof payload.error === 'string' && payload.error.trim()) {
        return payload.error;
      }

      return undefined;
    }

    return trimmedBody;
  } catch {
    return trimmedBody;
  }
}

export async function throwResponseError(
  response: Response,
  { fallbackMessage, method, requestUrl }: ResponseErrorOptions,
): Promise<never> {
  let rawDetail = '';

  try {
    rawDetail = await response.text();
  } catch {
  }

  console.error('HTTP request failed', {
    requestUrl: requestUrl || response.url,
    method: method || 'UNKNOWN',
    status: response.status,
    statusText: response.statusText,
    rawDetail,
  });

  throw new Error(parseResponseErrorDetail(rawDetail) || fallbackMessage);
}