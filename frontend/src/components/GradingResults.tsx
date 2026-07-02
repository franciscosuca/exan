import type { GradingResult } from '../lib/api';
import { ResultsBadge } from './StepIndicator';

interface GradingResultsProps {
  results: GradingResult[];
}

export function GradingResults({ results }: GradingResultsProps) {
  if (results.length === 0) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Grading Results</h2>

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
                {result.total_score}/{result.max_score} points
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
              View question breakdown
            </summary>
            <div className="mt-3 divide-y divide-gray-100">
              {result.answers.map((a) => (
                <div key={a.question_number} className="flex items-center justify-between py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600">Q{a.question_number}</span>
                    <span className="text-sm text-gray-700">{a.student_answer || '(no answer)'}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">
                      {a.points_earned}/{a.points_possible} pts
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
