import { useState, type ChangeEvent } from 'react';
import { readFileAsDataUrl, uploadPhoto } from '../lib/session';

interface PhoneProps {
  initialSessionId?: string;
  onBack: () => void;
}

type UploadStatus = 'idle' | 'uploading' | 'sent' | 'error';

export default function Phone({ initialSessionId, onBack }: PhoneProps) {
  const [sessionId, setSessionId] = useState(initialSessionId ?? '');
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [sentCount, setSentCount] = useState(0);

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    const code = sessionId.trim().toUpperCase();
    if (!code) {
      setError('Enter the session code shown on the desktop first.');
      setStatus('error');
      return;
    }

    setStatus('uploading');
    setError(null);
    try {
      const dataUrl = await readFileAsDataUrl(file);
      await uploadPhoto(code, dataUrl);
      setStatus('sent');
      setSentCount((count) => count + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send the photo.');
      setStatus('error');
    }
  }

  return (
    <>
      <h1>Send a document photo</h1>
      <p>Enter the session code shown on the desktop, then take a photo of your document.</p>

      <div className="card">
        <label htmlFor="session-code">Session code</label>
        <input
          id="session-code"
          className="button"
          style={{ background: 'transparent', color: 'inherit', border: '1px solid var(--border)', marginTop: 8 }}
          value={sessionId}
          onChange={(event) => setSessionId(event.target.value)}
          placeholder="e.g. 4F9A2C"
          autoCapitalize="characters"
        />
      </div>

      <div className="card">
        <label htmlFor="photo-input" className="button">
          {status === 'uploading' ? 'Sending…' : '📷 Take or choose a photo'}
        </label>
        <input
          id="photo-input"
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelected}
          disabled={status === 'uploading'}
          style={{ display: 'none' }}
        />
        {status === 'sent' && <p className="status" style={{ marginTop: 12 }}>Sent to desktop ✓ ({sentCount} total)</p>}
        {error && <p className="error">{error}</p>}
      </div>

      <button type="button" className="button" onClick={onBack}>
        Back
      </button>
    </>
  );
}
