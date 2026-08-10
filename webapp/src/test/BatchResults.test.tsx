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

  it('renders structured grammar rows and summary with word-level highlighting', () => {
    renderResults(
      createResponse({
        filename: 'essay.docx',
        summary: 'Review article usage before singular nouns.',
        grammar: {
          issues: [{ original_text: 'a apple', corrected_text: 'an apple' }],
          summary: 'Review article usage before singular nouns.',
        },
      })
    );

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Original Sentence' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Corrected Sentence' })).toBeInTheDocument();
    expect(screen.getAllByRole('cell')[0]).toHaveTextContent('a apple');
    expect(screen.getAllByRole('cell')[1]).toHaveTextContent('an apple');
    expect(screen.getAllByRole('mark')).toHaveLength(2);
    expect(screen.getByRole('heading', { name: 'How to Improve' })).toBeInTheDocument();
    expect(screen.getByText('Review article usage before singular nouns.')).toBeInTheDocument();
    expect(screen.queryByText('Overall')).not.toBeInTheDocument();
  });

  it('shows an explicit no-issues state for empty structured grammar feedback', () => {
    renderResults(
      createResponse({
        filename: 'clean.pdf',
        summary: 'The grammar is clear and accurate.',
        grammar: { issues: [], summary: 'The grammar is clear and accurate.' },
      })
    );

    expect(screen.getByRole('status')).toHaveTextContent('No grammar issues found.');
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText('The grammar is clear and accurate.')).toBeInTheDocument();
  });

  it('does not render obsolete criteria when structured grammar is missing', () => {
    renderResults(
      createResponse({
        filename: 'legacy.docx',
        summary: 'No structured grammar feedback available.',
      })
    );

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText('Detailed Findings')).not.toBeInTheDocument();
    expect(screen.queryByText('Argument Quality')).not.toBeInTheDocument();
  });

  it('renders one table row for each structured grammar issue', () => {
    renderResults(
      createResponse({
        filename: 'multiple-issues.pdf',
        summary: 'Review subject-verb agreement.',
        grammar: {
          issues: [
            { original_text: 'She go home.', corrected_text: 'She goes home.' },
            { original_text: 'They was ready.', corrected_text: 'They were ready.' },
          ],
          summary: 'Review subject-verb agreement.',
        },
      })
    );

    expect(screen.getAllByRole('row')).toHaveLength(3);
    expect(screen.getAllByRole('cell')[0]).toHaveTextContent('She go home.');
    expect(screen.getAllByRole('cell')[1]).toHaveTextContent('She goes home.');
    expect(screen.getAllByRole('cell')[2]).toHaveTextContent('They was ready.');
    expect(screen.getAllByRole('cell')[3]).toHaveTextContent('They were ready.');
  });
});