import type { ProviderConfig } from '../lib/api';
import { useLanguage } from '../lib/i18n';

interface ProviderSelectorProps {
  providers: ProviderConfig[];
  selected: string;
  onSelect: (provider: string) => void;
}

export function ProviderSelector({ providers, selected, onSelect }: ProviderSelectorProps) {
  const { t } = useLanguage();
  const available = providers.filter((p) => p.available && p.provider === 'gemini');

  if (available.length === 0) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        {t('common.noProviders')}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {available.map((p) => (
        <button
          key={p.provider}
          onClick={() => onSelect(p.provider)}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors
            ${
              selected === p.provider
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
        >
          {p.provider}
          {p.is_local && (
            <span className="ml-1.5 rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700">
              {t('common.local')}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
