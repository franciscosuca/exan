import type { ComparisonResult } from '../lib/api';
import { CorrectnessBadge } from './StepIndicator';
import { useLanguage } from '../lib/i18n';

interface ComparisonResultsProps {
  results: ComparisonResult[];
}

export function ComparisonResults({ results }: ComparisonResultsProps) {
  const { t } = useLanguage();
  if (results.length === 0) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">{t('comparisonResults.title')}</h2>

      {results.map((result) => (
        <div key={result.id} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              {result.student_name || result.filename}
            </h3>
            <p className="text-sm text-gray-500">{result.filename}</p>
          </div>

          <div className="space-y-3">
            {result.answers.map((answer) => (
              <div key={`${result.id}-${answer.question_number}`} className="rounded-lg bg-gray-50 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <span className="text-sm font-semibold text-gray-700">
                    {t('comparisonResults.question', { number: answer.question_number })}
                  </span>
                  <CorrectnessBadge correct={answer.is_correct} />
                </div>
                <dl className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
                      {t('comparisonResults.studentAnswer')}
                    </dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {answer.student_answer || t('comparisonResults.noAnswer')}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
                      {t('comparisonResults.correctAnswer')}
                    </dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {answer.correct_answer || t('comparisonResults.noAnswer')}
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}