import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ProviderSelector } from '../components/ProviderSelector';
import type { ProviderConfig } from '../lib/api';

const PROVIDERS: ProviderConfig[] = [
  { provider: 'gemini', available: true, requires_api_key: true, is_local: false },
  { provider: 'claude', available: false, requires_api_key: true, is_local: false },
  { provider: 'ollama', available: true, requires_api_key: false, is_local: true },
];

describe('ProviderSelector', () => {
  it('renders only available providers as buttons', () => {
    render(<ProviderSelector providers={PROVIDERS} selected="gemini" onSelect={() => {}} />);
    expect(screen.getByText('gemini')).toBeInTheDocument();
    expect(screen.getByText('ollama')).toBeInTheDocument();
    expect(screen.queryByText('claude')).not.toBeInTheDocument();
  });

  it('shows "local" badge for local providers', () => {
    render(<ProviderSelector providers={PROVIDERS} selected="gemini" onSelect={() => {}} />);
    expect(screen.getByText('local')).toBeInTheDocument();
  });

  it('calls onSelect when clicking a provider', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ProviderSelector providers={PROVIDERS} selected="gemini" onSelect={onSelect} />);

    await user.click(screen.getByText('ollama'));
    expect(onSelect).toHaveBeenCalledWith('ollama');
  });

  it('shows warning when no providers are available', () => {
    const noProviders: ProviderConfig[] = [
      { provider: 'gemini', available: false, requires_api_key: true, is_local: false },
    ];
    render(<ProviderSelector providers={noProviders} selected="" onSelect={() => {}} />);
    expect(screen.getByText(/No AI providers available/)).toBeInTheDocument();
  });
});
