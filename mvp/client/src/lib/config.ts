// Base URL of the relay server (see ../../server). Defaults to a local dev server.
export const SERVER_URL: string = import.meta.env.VITE_SERVER_URL ?? 'http://localhost:4000';

export function toWebSocketUrl(sessionId: string): string {
  const wsBase = SERVER_URL.replace(/^http/, 'ws');
  return `${wsBase}/ws?sessionId=${encodeURIComponent(sessionId)}`;
}
