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
          </header>

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
                          <tr key={`${issue.original_text}-${index}`} className="border-b border-gray-100 last:border-b-0">
                            <td className="whitespace-pre-wrap wrap-break-word px-4 py-3 align-top text-gray-700">
                              <DiffText
                                text={issue.original_text}
                                comparison={issue.corrected_text}
                                variant="original"
                              />
                            </td>
                            <td className="whitespace-pre-wrap wrap-break-word px-4 py-3 align-top text-gray-700">
                              <DiffText
                                text={issue.corrected_text}
                                comparison={issue.original_text}
                                variant="corrected"
                              />
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

interface DiffTextProps {
  text: string;
  comparison: string;
  variant: 'original' | 'corrected';
}

function DiffText({ text, comparison, variant }: DiffTextProps) {
  const tokens = tokenize(text);
  const words = tokens.filter((token) => !/^\s+$/.test(token));
  const comparisonWords = tokenize(comparison).filter((token) => !/^\s+$/.test(token));
  const unchangedIndexes = new Set(
    longestCommonSubsequenceIndexes(words, comparisonWords, variant === 'original' ? 0 : 1)
  );
  let wordIndex = 0;

  return <>{tokens.map((token, index) => (
    /^\s+$/.test(token) || unchangedIndexes.has(wordIndex++)
      ? token
      : (
        <mark
          key={`${variant}-${index}`}
          className={variant === 'original' ? 'bg-red-100 text-red-900' : 'bg-green-100 text-green-900'}
        >
          {token}
        </mark>
      )
  ))}</>;
}

function tokenize(text: string): string[] {
  return text.match(/\s+|[^\s]+/g) ?? [];
}

function longestCommonSubsequenceIndexes(
  left: string[],
  right: string[],
  side: 0 | 1
): number[] {
  const table = Array.from({ length: left.length + 1 }, () =>
    Array<number>(right.length + 1).fill(0)
  );

  for (let row = 1; row <= left.length; row += 1) {
    for (let column = 1; column <= right.length; column += 1) {
      table[row][column] = left[row - 1] === right[column - 1]
        ? table[row - 1][column - 1] + 1
        : Math.max(table[row - 1][column], table[row][column - 1]);
    }
  }

  const result: number[] = [];
  let row = left.length;
  let column = right.length;
  while (row > 0 && column > 0) {
    if (left[row - 1] === right[column - 1]) {
      result.unshift(side === 0 ? row - 1 : column - 1);
      row -= 1;
      column -= 1;
    } else if (table[row - 1][column] >= table[row][column - 1]) {
      row -= 1;
    } else {
      column -= 1;
    }
  }
  return result;
}

function formatProcessedDate(createdAt: string, language: 'de' | 'en'): string | null {
  const timestamp = Date.parse(createdAt);
  if (Number.isNaN(timestamp)) return null;

  return new Intl.DateTimeFormat(language === 'de' ? 'de-DE' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
}
