import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { GradingResults } from '../components/GradingResults';
import type { GradingResult } from '../lib/api';

const RESULTS: GradingResult[] = [
  {
    id: '1',
    exam_id: 'exam-1',
    student_name: 'Alice',
    filename: 'alice_exam.pdf',
    total_score: 8,
    max_score: 10,
    percentage: 80,
    answers: [
      {
        question_number: 1,
        student_answer: 'A',
        correct_answer: 'A',
        is_correct: true,
        points_earned: 2,
        points_possible: 2,
      },
      {
        question_number: 2,
        student_answer: 'C',
        correct_answer: 'B',
        is_correct: false,
        points_earned: 0,
        points_possible: 2,
      },
    ],
  },
];

describe('GradingResults', () => {
  it('renders nothing when results are empty', () => {
    const { container } = render(<GradingResults results={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders student name and score', () => {
    render(<GradingResults results={RESULTS} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('80%')).toBeInTheDocument();
    expect(screen.getByText('8/10 points')).toBeInTheDocument();
  });

  it('renders the heading', () => {
    render(<GradingResults results={RESULTS} />);
    expect(screen.getByText('Grading Results')).toBeInTheDocument();
  });

  it('shows filename', () => {
    render(<GradingResults results={RESULTS} />);
    expect(screen.getByText('alice_exam.pdf')).toBeInTheDocument();
  });
});
