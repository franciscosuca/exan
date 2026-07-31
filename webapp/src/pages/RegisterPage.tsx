import { useState, type FormEvent } from "react";
import { register, saveToken } from "../auth.api";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useLanguage } from "../lib/i18n";

interface RegisterPageProps {
  onSuccess: (username: string) => void;
  onNavigateToLogin: () => void;
}

export function RegisterPage({
  onSuccess,
  onNavigateToLogin,
}: RegisterPageProps) {
  const { t } = useLanguage();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== repeatPassword) {
      setError(t('auth.register.passwordMismatch'));
      return;
    }

    setLoading(true);

    try {
      const result = await register(username, password, repeatPassword);
      saveToken(result.token);
      onSuccess(result.username);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gray-50 px-6">
      <div className="absolute right-6 top-6">
        <LanguageSwitcher />
      </div>
      <div className="w-full max-w-sm rounded-2xl border-2 border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">
          {t('auth.register.title')}
        </h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="username"
              className="mb-1 block text-xs font-medium text-gray-600"
            >
              {t('auth.register.username')}
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-100"
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-xs font-medium text-gray-600"
            >
              {t('auth.register.password')}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-100"
            />
          </div>
          <div>
            <label
              htmlFor="repeatPassword"
              className="mb-1 block text-xs font-medium text-gray-600"
            >
              {t('auth.register.repeatPassword')}
            </label>
            <input
              id="repeatPassword"
              type="password"
              value={repeatPassword}
              onChange={(e) => setRepeatPassword(e.target.value)}
              required
              minLength={6}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-100"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-purple-600 py-2 text-sm font-medium text-white transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? t('auth.register.submitting') : t('auth.register.submit')}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          {t('auth.register.haveAccount')}{" "}
          <button
            type="button"
            onClick={onNavigateToLogin}
            className="font-medium text-purple-600 hover:text-purple-700"
          >
            {t('auth.register.login')}
          </button>
        </p>
      </div>
    </div>
  );
}
