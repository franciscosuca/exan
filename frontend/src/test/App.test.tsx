import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';

// Mock the API module
vi.mock('../lib/api', () => ({
  getProviders: vi.fn().mockResolvedValue([
    { provider: 'gemini', available: true, requires_api_key: true, is_local: false },
    { provider: 'ollama', available: true, requires_api_key: false, is_local: true },
  ]),
  uploadExamTemplate: vi.fn(),
  uploadAnswerKey: vi.fn(),
  uploadStudentExams: vi.fn(),
  batchEvaluate: vi.fn(),
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the app header', async () => {
    render(<App />);
    expect(screen.getByText('Exan')).toBeInTheDocument();
  });

  it('renders the landing page with two options', async () => {
    render(<App />);
    expect(screen.getByText('Exam Comparison')).toBeInTheDocument();
    expect(screen.getByText('Batch Evaluation')).toBeInTheDocument();
  });

  it('navigates to exam comparison when clicked', async () => {
    render(<App />);
    fireEvent.click(screen.getByText('Exam Comparison'));
    expect(screen.getByText('Upload Exam Template')).toBeInTheDocument();
    expect(screen.getByText('Step 1: Upload Empty Exam')).toBeInTheDocument();
  });

  it('navigates to batch evaluation when clicked', async () => {
    render(<App />);
    fireEvent.click(screen.getByText('Batch Evaluation'));
    expect(screen.getByText('Upload Exams')).toBeInTheDocument();
    expect(screen.getByText('Evaluation Criteria')).toBeInTheDocument();
  });

  it('returns to landing page when clicking Exan logo', async () => {
    render(<App />);
    fireEvent.click(screen.getByText('Exam Comparison'));
    expect(screen.getByText('Step 1: Upload Empty Exam')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Exan'));
    expect(screen.getByText('Welcome to Exan')).toBeInTheDocument();
  });
});
