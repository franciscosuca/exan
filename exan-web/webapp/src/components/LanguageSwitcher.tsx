import { Languages } from 'lucide-react';
import { useLanguage, type Language } from '../lib/i18n';

const LANGUAGE_OPTIONS: Language[] = ['de', 'en'];

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <label className="flex items-center gap-1.5 text-sm font-medium text-gray-600">
      <Languages className="h-4 w-4 text-gray-500" />
      <span className="sr-only">{t('grammarEvaluation.language')}</span>
      <select
        aria-label={t('grammarEvaluation.language')}
        value={language}
        onChange={(e) => setLanguage(e.target.value as Language)}
        className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-sm text-gray-700 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
      >
        {LANGUAGE_OPTIONS.map((code) => (
          <option key={code} value={code}>
            {t(`language.${code}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
