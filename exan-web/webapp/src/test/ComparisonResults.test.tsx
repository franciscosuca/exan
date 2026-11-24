import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { ComparisonResults } from '../components/ComparisonResults';
import { LanguageProvider, LANGUAGE_STORAGE_KEY } from '../lib/i18n';
import type { ComparisonResult } from '../lib/api';

const RESULTS: ComparisonResult[] = [
  {
    id: '1',
    exam_id: 'exam-1',
    student_name: 'Alice',
    filename: 'alice_exam.pdf',
    answers: [
      {
        question_number: 1,
        student_answer: 'A',
        correct_answer: 'A',
        is_correct: true,
      },
      {
        question_number: 2,
        student_answer: 'C',
        correct_answer: 'B',
        is_correct: false,
      },
    ],
  },
];

describe('ComparisonResults', () => {
  beforeEach(() => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, 'en');
  });

  it('renders nothing when results are empty', () => {
    const { container } = render(
      <LanguageProvider>
        <ComparisonResults results={[]} />
      </LanguageProvider>
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders every answer with both answers and correctness status', () => {
    render(
      <LanguageProvider>
        <ComparisonResults results={RESULTS} />
      </LanguageProvider>
    );

    expect(screen.getByText('Answer Comparison Results')).toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('alice_exam.pdf')).toBeInTheDocument();
    expect(screen.getByText('Question 1')).toBeInTheDocument();
    expect(screen.getByText('Question 2')).toBeInTheDocument();
    expect(screen.getAllByText('Student answer')).toHaveLength(2);
    expect(screen.getAllByText('Correct answer')).toHaveLength(2);
    expect(screen.getByText('Correct')).toBeInTheDocument();
    expect(screen.getByText('Incorrect')).toBeInTheDocument();
    expect(screen.getAllByText('A')).toHaveLength(2);
    expect(screen.getByText('B')).toBeInTheDocument();
    expect(screen.getByText('C')).toBeInTheDocument();
  });

  it('does not render score or point text', () => {
    render(
      <LanguageProvider>
        <ComparisonResults results={RESULTS} />
      </LanguageProvider>
    );

    expect(document.body.textContent).not.toMatch(/\d+%|\b(score|points?|pts)\b/i);
    expect(screen.queryByText('View question breakdown')).not.toBeInTheDocument();
  });
});