import type { BatchEvaluationResponse } from '../lib/api';
import { useLanguage } from '../lib/i18n';

interface BatchResultsProps {
  response: BatchEvaluationResponse;
}

export function BatchResults({ response }: BatchResultsProps) {
  const { t } = useLanguage();
  if (response.results.length === 0) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">{t('batchResults.title')}</h2>
      <p className="text-sm text-gray-500">
        {t('batchResults.filesEvaluated', { count: response.results.length })}
      </p>

      {response.results.map((result) => (
        <div key={result.id} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">{result.filename}</h3>
            <div className="text-right">
              <p className="text-3xl font-bold text-gray-900">
                {result.overall_score.toFixed(0)}%
              </p>
              <p className="text-sm text-gray-500">{t('batchResults.overall')}</p>
            </div>
          </div>

          {/* Overall score bar */}
          <div className="mb-6 h-2 w-full rounded-full bg-gray-100">
            <div
              className={`h-2 rounded-full transition-all ${
                result.overall_score >= 70
                  ? 'bg-green-500'
                  : result.overall_score >= 50
                    ? 'bg-amber-500'
                    : 'bg-red-500'
              }`}
              style={{ width: `${result.overall_score}%` }}
            />
          </div>

          {/* Per-criteria breakdown */}
          <div className="space-y-4">
            {result.scores.map((score) => (
              <div key={score.criteria_name} className="rounded-lg border border-gray-100 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-800">
                    {score.criteria_name}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      score.score >= 70
                        ? 'bg-green-100 text-green-700'
                        : score.score >= 50
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {score.score.toFixed(0)}%
                  </span>
                </div>
                <div className="mb-2 h-1.5 w-full rounded-full bg-gray-100">
                  <div
                    className={`h-1.5 rounded-full ${
                      score.score >= 70
                        ? 'bg-green-400'
                        : score.score >= 50
                          ? 'bg-amber-400'
                          : 'bg-red-400'
                    }`}
                    style={{ width: `${score.score}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600">{score.feedback}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
