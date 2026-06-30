import { Check, X } from 'lucide-react';

interface StepIndicatorProps {
  steps: string[];
  currentStep: number;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((label, i) => {
        const isCompleted = i < currentStep;
        const isCurrent = i === currentStep;

        return (
          <div key={label} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium
                  ${isCompleted ? 'bg-green-600 text-white' : ''}
                  ${isCurrent ? 'bg-blue-600 text-white' : ''}
                  ${!isCompleted && !isCurrent ? 'bg-gray-200 text-gray-500' : ''}`}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : i + 1}
              </div>
              <span
                className={`text-sm font-medium
                  ${isCurrent ? 'text-blue-700' : ''}
                  ${isCompleted ? 'text-green-700' : ''}
                  ${!isCompleted && !isCurrent ? 'text-gray-400' : ''}`}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`h-0.5 w-8 ${i < currentStep ? 'bg-green-400' : 'bg-gray-200'}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

interface ResultsBadgeProps {
  correct: boolean;
}

export function ResultsBadge({ correct }: ResultsBadgeProps) {
  return correct ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
      <Check className="h-3 w-3" /> Correct
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
      <X className="h-3 w-3" /> Incorrect
    </span>
  );
}
