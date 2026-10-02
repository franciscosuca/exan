import { AlertCircle } from 'lucide-react';
import { useLanguage } from '../lib/i18n';

interface SelectionRequiredNoticeProps {
  hasProvider: boolean;
  hasModel: boolean;
}

export function SelectionRequiredNotice({ hasProvider, hasModel }: SelectionRequiredNoticeProps) {
  const { t } = useLanguage();
  if (hasProvider && hasModel) return null;

  return (
    <div
      role="status"
      className="mb-6 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p className="font-medium">{t('common.selectionRequired')}</p>
        <p className="mt-1">
          {hasProvider ? t('common.selectionMissingModel') : t('common.selectionMissingProvider')}
        </p>
      </div>
    </div>
  );
}
