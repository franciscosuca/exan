import type { GradingResult } from '../lib/api';
import { ResultsBadge } from './StepIndicator';
import { useLanguage } from '../lib/i18n';

interface GradingResultsProps {
  results: GradingResult[];
}

export function GradingResults({ results }: GradingResultsProps) {
  const { t } = useLanguage();
  if (results.length === 0) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">{t('gradingResults.title')}</h2>

      {results.map((result) => (
        <div key={result.id} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {result.student_name || result.filename}
              </h3>
              <p className="text-sm text-gray-500">{result.filename}</p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-gray-900">
                {result.percentage.toFixed(0)}%
              </p>
              <p className="text-sm text-gray-500">
                {t('gradingResults.points', { score: result.total_score, max: result.max_score })}
              </p>
            </div>
          </div>

          {/* Score bar */}
          <div className="mb-4 h-2 w-full rounded-full bg-gray-100">
            <div
              className={`h-2 rounded-full transition-all ${
                result.percentage >= 70 ? 'bg-green-500' : result.percentage >= 50 ? 'bg-amber-500' : 'bg-red-500'
              }`}
              style={{ width: `${result.percentage}%` }}
            />
          </div>

          {/* Per-question breakdown */}
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-800">
              {t('gradingResults.viewBreakdown')}
            </summary>
            <div className="mt-3 divide-y divide-gray-100">
              {result.answers.map((a) => (
                <div key={a.question_number} className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600">Q{a.question_number}</span>
                    <span className="text-sm text-gray-700">{a.student_answer || t('gradingResults.noAnswer')}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">
                      {t('gradingResults.pts', { earned: a.points_earned, possible: a.points_possible })}
                    </span>
                    <ResultsBadge correct={a.is_correct} />
                  </div>
                </div>
              ))}
            </div>
          </details>
        </div>
      ))}
    </div>
  );
}
