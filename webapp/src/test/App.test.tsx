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

// Mock the auth API module used for login/register/logout
vi.mock('../auth.api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  saveToken: vi.fn(),
  getToken: vi.fn(),
  clearToken: vi.fn(),
  saveUsername: vi.fn(),
  getUsername: vi.fn(),
  clearUsername: vi.fn(),
  isAuthenticated: vi.fn(),
  logout: vi.fn(),
}));

import * as authApi from '../auth.api';

function signInAs(username: string) {
  vi.mocked(authApi.isAuthenticated).mockReturnValue(true);
  vi.mocked(authApi.getUsername).mockReturnValue(username);
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authApi.isAuthenticated).mockReturnValue(false);
    vi.mocked(authApi.getUsername).mockReturnValue(null);
  });

  describe('when authenticated', () => {
    beforeEach(() => {
      signInAs('testuser');
    });

    it('renders the app header', async () => {
      render(<App />);
      expect(screen.getByText('Exan')).toBeInTheDocument();
    });

    it('renders the logged-in username and a logout button', async () => {
      render(<App />);
      expect(screen.getByText('testuser')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
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

    it('logs out and returns to the login page when clicking Logout', async () => {
      render(<App />);
      fireEvent.click(screen.getByRole('button', { name: /logout/i }));
      expect(authApi.logout).toHaveBeenCalled();
      expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
    });
  });

  describe('when not authenticated', () => {
    it('renders the login page instead of the app', async () => {
      render(<App />);
      expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
      expect(screen.queryByText('Welcome to Exan')).not.toBeInTheDocument();
    });

    it('navigates to the registration page and back to login', async () => {
      render(<App />);
      fireEvent.click(screen.getByRole('button', { name: 'Register' }));
      expect(screen.getByRole('heading', { name: 'Register' })).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: 'Login' }));
      expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
    });
  });
});
