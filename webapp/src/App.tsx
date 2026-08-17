import { useState } from 'react';
import { ExamComparison } from './components/ExamComparison';
import { GrammarEvaluation } from './components/GrammarEvaluation';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { ClipboardCheck, FileText, LogOut, UserRound } from 'lucide-react';
import { getUsername, isAuthenticated, logout, saveUsername } from './auth.api';
import { useLanguage } from './lib/i18n';

type AppMode = 'landing' | 'exam-comparison' | 'grammar-evaluation';
type AuthView = 'login' | 'register';

function App() {
  const { t } = useLanguage();
  const [mode, setMode] = useState<AppMode>('landing');
  const [authView, setAuthView] = useState<AuthView>('login');
  const [username, setUsername] = useState<string | null>(() =>
    isAuthenticated() ? getUsername() : null
  );

  function handleAuthSuccess(name: string) {
    saveUsername(name);
    setUsername(name);
    setAuthView('login');
    setMode('landing');
  }

  function handleLogout() {
    logout();
    setUsername(null);
    setMode('landing');
    setAuthView('login');
  }

  if (!username) {
    return authView === 'login' ? (
      <LoginPage
        onSuccess={handleAuthSuccess}
        onNavigateToRegister={() => setAuthView('register')}
      />
    ) : (
      <RegisterPage
        onSuccess={handleAuthSuccess}
        onNavigateToLogin={() => setAuthView('login')}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <button onClick={() => setMode('landing')} className="text-2xl font-bold text-gray-900 hover:text-blue-700">
            {t('app.name')}
          </button>
          <div className="flex items-center gap-4">
            {mode !== 'landing' && (
              <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
                {mode === 'exam-comparison'
                  ? t('app.header.examComparison')
                  : t('app.header.grammarEvaluation')}
              </span>
            )}
            <span className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
              <UserRound className="h-4 w-4 text-gray-500" />
              {username}
            </span>
            <LanguageSwitcher />
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-600"
            >
              <LogOut className="h-4 w-4" />
              {t('app.logout')}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        {mode === 'landing' && (
          <Landing
            onExamComparison={() => setMode('exam-comparison')}
            onGrammarEvaluation={() => setMode('grammar-evaluation')}
          />
        )}
        {mode === 'exam-comparison' && (
          <ExamComparison onBack={() => setMode('landing')} />
        )}
        {mode === 'grammar-evaluation' && (
          <GrammarEvaluation onBack={() => setMode('landing')} />
        )}
      </main>
    </div>
  );
}

interface LandingProps {
  onExamComparison: () => void;
  onGrammarEvaluation: () => void;
}

function Landing({ onExamComparison, onGrammarEvaluation }: LandingProps) {
  const { t } = useLanguage();
  return (
    <div className="py-12">
      <div className="mb-12 text-center">
        <h1 className="mb-3 text-4xl font-bold text-gray-900">{t('app.landing.title')}</h1>
        <p className="text-lg text-gray-600">
          {t('app.landing.subtitle')}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Exam Comparison Card */}
        <button
          onClick={onExamComparison}
          className="group rounded-2xl border-2 border-gray-200 bg-white p-8 text-left shadow-sm transition-all hover:border-blue-300 hover:shadow-md"
        >
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 text-blue-600 group-hover:bg-blue-200">
            <ClipboardCheck className="h-6 w-6" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-gray-900">{t('app.landing.examComparison.title')}</h2>
          <p className="text-sm text-gray-600">
            {t('app.landing.examComparison.description')}
          </p>
          <div className="mt-4 text-sm font-medium text-blue-600 group-hover:text-blue-700">
            {t('app.landing.getStarted')}
          </div>
        </button>

        {/* Grammar Evaluation Card */}
        <button
          onClick={onGrammarEvaluation}
          className="group rounded-2xl border-2 border-gray-200 bg-white p-8 text-left shadow-sm transition-all hover:border-purple-300 hover:shadow-md"
        >
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100 text-purple-600 group-hover:bg-purple-200">
            <FileText className="h-6 w-6" />
          </div>
          <h2 className="mb-2 text-xl font-semibold text-gray-900">{t('app.landing.grammarEvaluation.title')}</h2>
          <p className="text-sm text-gray-600">
            {t('app.landing.grammarEvaluation.description')}
          </p>
          <div className="mt-4 text-sm font-medium text-purple-600 group-hover:text-purple-700">
            {t('app.landing.getStarted')}
          </div>
        </button>
      </div>
    </div>
  );
}

export default App;

