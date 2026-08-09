import type { BatchEvaluationResponse } from '../lib/api';
import { useLanguage } from '../lib/i18n';
import { FileText, Lightbulb } from 'lucide-react';

interface BatchResultsProps {
  response: BatchEvaluationResponse;
}

export function BatchResults({ response }: BatchResultsProps) {
  const { language, t } = useLanguage();
  if (response.results.length === 0) return null;

  const processedDate = formatProcessedDate(response.created_at, language);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{t('batchResults.title')}</h2>
        <p className="mt-1 text-sm text-gray-500">
          {t('batchResults.filesEvaluated', { count: response.results.length })}
        </p>
      </div>

      {response.results.map((result) => (
        <article key={result.id} className="space-y-4">
          <header className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex min-w-0 items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
                  <FileText className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <h3 className="wrap-break-word text-lg font-semibold text-gray-900">{result.filename}</h3>
                  {processedDate && (
                    <p className="mt-1 text-xs text-gray-500">
                      <time dateTime={response.created_at}>
                        {t('batchResults.processed', { date: processedDate })}
                      </time>
                    </p>
                  )}
                </div>
              </div>
              <div className="shrink-0 text-left sm:text-right">
                <p className="text-3xl font-bold text-gray-900">{result.overall_score.toFixed(0)}%</p>
                <p className="text-sm text-gray-500">{t('batchResults.overall')}</p>
              </div>
            </div>

            <div className="mt-5 h-2 w-full rounded-full bg-gray-100">
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
          </header>

          {result.scores.length > 0 && (
            <section
              aria-label={t('batchResults.overall')}
              className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm"
            >
              <div className="divide-y divide-gray-100">
                {result.scores.map((score) => (
                  <div key={score.criteria_name} className="p-4 sm:p-6">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="wrap-break-word text-sm font-semibold text-gray-800">
                        {score.criteria_name}
                      </span>
                      <span
                        className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
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
                    {(!result.grammar || score.criteria_name.toLowerCase() !== 'grammar') && (
                      <p className="whitespace-pre-wrap wrap-break-word text-sm text-gray-600">
                        {score.feedback}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {result.grammar && (
            <>
              <section
                aria-labelledby={`findings-${result.id}`}
                className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm"
              >
                <div className="border-b border-gray-200 px-6 py-4">
                  <h4 id={`findings-${result.id}`} className="text-base font-semibold text-gray-900">
                    {t('batchResults.detailedFindings')}
                  </h4>
                </div>

                {result.grammar.issues.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-160 w-full border-collapse text-left text-sm">
                      <caption className="sr-only">{t('batchResults.detailedFindings')}</caption>
                      <thead className="bg-gray-50">
                        <tr>
                          <th scope="col" className="w-1/2 border-b border-gray-200 px-4 py-3 font-semibold text-gray-700">
                            {t('batchResults.originalSentence')}
                          </th>
                          <th scope="col" className="w-1/2 border-b border-gray-200 px-4 py-3 font-semibold text-gray-700">
                            {t('batchResults.correctedSentence')}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.grammar.issues.map((issue, index) => (
                          <tr key={`${issue.issue}-${index}`} className="border-b border-gray-100 last:border-b-0">
                            <td className="whitespace-pre-wrap wrap-break-word px-4 py-3 align-top text-gray-700">
                              {issue.issue}
                            </td>
                            <td className="whitespace-pre-wrap wrap-break-word px-4 py-3 align-top text-gray-700">
                              {issue.correction}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="p-6 text-sm text-gray-600" role="status">
                    {t('batchResults.noIssues')}
                  </p>
                )}
              </section>

              <div className="flex gap-3 rounded-xl border border-purple-100 bg-purple-50 p-4 shadow-sm">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-purple-600 text-white">
                  <Lightbulb className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h5 className="mb-1 text-sm font-semibold text-gray-800">
                    {t('batchResults.howToImprove')}
                  </h5>
                  <p className="whitespace-pre-wrap wrap-break-word text-sm text-gray-700">
                    {result.grammar.summary}
                  </p>
                </div>
              </div>
            </>
          )}
        </article>
      ))}
    </div>
  );
}

function formatProcessedDate(createdAt: string, language: 'de' | 'en'): string | null {
  const timestamp = Date.parse(createdAt);
  if (Number.isNaN(timestamp)) return null;

  return new Intl.DateTimeFormat(language === 'de' ? 'de-DE' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
}
