interface HomeProps {
  onSelectRole: (role: 'desktop' | 'phone') => void;
}

export default function Home({ onSelectRole }: HomeProps) {
  return (
    <>
      <h1>Doc Scan MVP</h1>
      <p>
        Scan documents with your phone's camera and see them appear instantly on this
        computer. Pick a role to get started.
      </p>
      <div className="card">
        <h2>💻 I'm on the desktop</h2>
        <p>Start a session and show the QR code to your phone.</p>
        <button type="button" className="button" onClick={() => onSelectRole('desktop')}>
          Start a session
        </button>
      </div>
      <div className="card">
        <h2>📱 I'm on the phone</h2>
        <p>Scan the QR code shown on the desktop, then take photos of your documents.</p>
        <button type="button" className="button" onClick={() => onSelectRole('phone')}>
          Join a session
        </button>
      </div>
    </>
  );
}
