import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { createSession } from '../lib/session';
import { toWebSocketUrl } from '../lib/config';
import { toSafeImageObjectUrl } from '../lib/image';

interface DesktopProps {
  onBack: () => void;
}

type ConnectionStatus = 'starting' | 'waiting' | 'connected' | 'error';

export default function Desktop({ onBack }: DesktopProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('starting');
  const [error, setError] = useState<string | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [photos, setPhotos] = useState<string[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const photosRef = useRef<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function start() {
      try {
        const { sessionId: id } = await createSession();
        if (cancelled) return;
        setSessionId(id);

        const phoneUrl = new URL(window.location.href);
        phoneUrl.search = `?role=phone&session=${id}`;
        const qr = await QRCode.toDataURL(phoneUrl.toString(), { margin: 1, width: 240 });
        if (cancelled) return;
        setQrDataUrl(qr);

        const socket = new WebSocket(toWebSocketUrl(id));
        socketRef.current = socket;
        socket.onopen = () => setStatus('waiting');
        socket.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'paired') {
            setStatus('waiting');
          } else if (message.type === 'photo') {
            const objectUrl = toSafeImageObjectUrl(message.dataUrl);
            if (objectUrl) {
              setStatus('connected');
              photosRef.current = [objectUrl, ...photosRef.current];
              setPhotos(photosRef.current);
            }
          }
        };
        socket.onerror = () => setStatus('error');
        socket.onclose = () => setStatus((current) => (current === 'error' ? current : 'error'));
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Something went wrong.');
          setStatus('error');
        }
      }
    }

    start();

    return () => {
      cancelled = true;
      socketRef.current?.close();
    };
  }, []);

  useEffect(() => {
    // Revoke every object URL created for this session when the component unmounts.
    return () => {
      photosRef.current.forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  return (
    <>
      <h1>Scan from your phone</h1>
      <p>Open the camera app or scan this QR code with your phone to start sending photos.</p>

      <div className="card">
        {qrDataUrl && <img className="qr-code" src={qrDataUrl} alt="QR code to join this scanning session" width={240} height={240} />}
        {sessionId && <div className="session-code">{sessionId}</div>}
        <p className="hint">No camera on the QR reader? Open this app on the phone and enter the code above.</p>
        <span className="status">
          {status === 'starting' && 'Starting session…'}
          {status === 'waiting' && 'Waiting for a photo…'}
          {status === 'connected' && 'Receiving photos'}
          {status === 'error' && 'Disconnected'}
        </span>
        {error && <p className="error">{error}</p>}
      </div>

      {photos.length > 0 && (
        <div className="card">
          <h2>Received photos ({photos.length})</h2>
          <div className="gallery">
            {photos.map((photo, index) => (
              <img key={photo} src={photo} alt={`Scanned document ${photos.length - index}`} />
            ))}
          </div>
        </div>
      )}

      <button type="button" className="button" onClick={onBack}>
        Back
      </button>
    </>
  );
}
