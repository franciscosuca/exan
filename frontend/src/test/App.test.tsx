import { render, screen } from '@testing-library/react';
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
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the app header', async () => {
    render(<App />);
    expect(screen.getByText('Exan')).toBeInTheDocument();
  });

  it('renders the step indicator', async () => {
    render(<App />);
    expect(screen.getByText('Upload Exam Template')).toBeInTheDocument();
    expect(screen.getByText('Upload Answer Key')).toBeInTheDocument();
    expect(screen.getByText('Grade Student Exams')).toBeInTheDocument();
  });

  it('shows step 1 content initially', async () => {
    render(<App />);
    expect(screen.getByText('Step 1: Upload Empty Exam')).toBeInTheDocument();
    expect(screen.getByText('Drop exam template here')).toBeInTheDocument();
  });

  it('renders the Start Over button', async () => {
    render(<App />);
    expect(screen.getByText('Start Over')).toBeInTheDocument();
  });

  it('shows AI Provider label', async () => {
    render(<App />);
    expect(screen.getByText('AI Provider')).toBeInTheDocument();
  });
});
