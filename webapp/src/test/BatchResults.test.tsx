import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { BatchResults } from '../components/BatchResults';
import { LanguageProvider, LANGUAGE_STORAGE_KEY } from '../lib/i18n';
import type { BatchEvaluationResponse } from '../lib/api';

function renderResults(response: BatchEvaluationResponse) {
  return render(
    <LanguageProvider>
      <BatchResults response={response} />
    </LanguageProvider>
  );
}

function createResponse(
  result: Omit<BatchEvaluationResponse['results'][number], 'id'> & { id?: string }
): BatchEvaluationResponse {
  return {
    id: 'batch-1',
    created_at: '2026-08-08T10:12:04+00:00',
    results: [{ id: 'file-1', ...result }],
  };
}

describe('BatchResults', () => {
  beforeEach(() => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'en');
  });

  it('renders structured grammar rows and summary without legacy grammar feedback', () => {
    renderResults(
      createResponse({
        filename: 'essay.docx',
        scores: [
          { criteria_name: 'Grammar', score: 78, feedback: 'Legacy grammar feedback' },
        ],
        overall_score: 78,
        summary: 'Grammar: 78%',
        grammar: {
          issues: [{ issue: 'a apple', correction: 'an apple' }],
          summary: 'Review article usage before singular nouns.',
        },
      })
    );

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Original Sentence' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Corrected Sentence' })).toBeInTheDocument();
    expect(screen.getByText('a apple')).toBeInTheDocument();
    expect(screen.getByText('an apple')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'How to Improve' })).toBeInTheDocument();
    expect(screen.getByText('Review article usage before singular nouns.')).toBeInTheDocument();
    expect(screen.queryByText('Legacy grammar feedback')).not.toBeInTheDocument();
  });

  it('shows an explicit no-issues state for empty structured grammar feedback', () => {
    renderResults(
      createResponse({
        filename: 'clean.pdf',
        scores: [{ criteria_name: 'Grammar', score: 100, feedback: '' }],
        overall_score: 100,
        summary: 'Grammar: 100%',
        grammar: { issues: [], summary: 'The grammar is clear and accurate.' },
      })
    );

    expect(screen.getByRole('status')).toHaveTextContent('No grammar issues found.');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText('The grammar is clear and accurate.')).toBeInTheDocument();
  });

  it('keeps legacy and custom criteria feedback when structured grammar is missing', () => {
    renderResults(
      createResponse({
        filename: 'legacy.docx',
        scores: [
          { criteria_name: 'Grammar', score: 70, feedback: 'Legacy grammar feedback' },
          { criteria_name: 'Argument Quality', score: 82, feedback: 'The argument is well supported.' },
        ],
        overall_score: 76,
        summary: 'Grammar: 70%, Argument Quality: 82%',
      })
    );

    expect(screen.getByText('Legacy grammar feedback')).toBeInTheDocument();
    expect(screen.getByText('The argument is well supported.')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText('Detailed Findings')).not.toBeInTheDocument();
  });

  it('renders one table row for each structured grammar issue', () => {
    renderResults(
      createResponse({
        filename: 'multiple-issues.pdf',
        scores: [{ criteria_name: 'Grammar', score: 50, feedback: '' }],
        overall_score: 50,
        summary: 'Grammar: 50%',
        grammar: {
          issues: [
            { issue: 'She go home.', correction: 'She goes home.' },
            { issue: 'They was ready.', correction: 'They were ready.' },
          ],
          summary: 'Review subject-verb agreement.',
        },
      })
    );

    expect(screen.getAllByRole('row')).toHaveLength(3);
    expect(screen.getByText('She go home.')).toBeInTheDocument();
    expect(screen.getByText('They were ready.')).toBeInTheDocument();
  });
});