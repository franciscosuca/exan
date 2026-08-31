import { SERVER_URL } from './config';

export interface CreateSessionResponse {
  sessionId: string;
  expiresInMs: number;
}

export async function createSession(): Promise<CreateSessionResponse> {
  const response = await fetch(`${SERVER_URL}/api/sessions`, { method: 'POST' });
  if (!response.ok) {
    throw new Error('Could not start a scanning session. Is the relay server running?');
  }
  return response.json();
}

export async function uploadPhoto(sessionId: string, dataUrl: string): Promise<void> {
  const response = await fetch(`${SERVER_URL}/api/sessions/${encodeURIComponent(sessionId)}/photos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataUrl }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error ?? 'Could not send the photo to the desktop.');
  }
}

export function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error('Could not read the selected photo.'));
    reader.readAsDataURL(file);
  });
}
