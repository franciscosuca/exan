import { useCallback, useState } from 'react';
import Home from './pages/Home';
import Desktop from './pages/Desktop';
import Phone from './pages/Phone';

type Role = 'home' | 'desktop' | 'phone';

function readRoleFromLocation(): Role {
  const params = new URLSearchParams(window.location.search);
  const role = params.get('role');
  return role === 'desktop' || role === 'phone' ? role : 'home';
}

function App() {
  const [role, setRole] = useState<Role>(readRoleFromLocation);

  const navigate = useCallback((next: Role, sessionId?: string) => {
    const url = new URL(window.location.href);
    if (next === 'home') {
      url.search = '';
    } else {
      url.search = `?role=${next}${sessionId ? `&session=${sessionId}` : ''}`;
    }
    window.history.pushState({}, '', url);
    setRole(next);
  }, []);

  if (role === 'desktop') {
    return <Desktop onBack={() => navigate('home')} />;
  }

  if (role === 'phone') {
    const initialSessionId = new URLSearchParams(window.location.search).get('session') ?? undefined;
    return <Phone initialSessionId={initialSessionId} onBack={() => navigate('home')} />;
  }

  return <Home onSelectRole={(selected) => navigate(selected)} />;
}

export default App;
